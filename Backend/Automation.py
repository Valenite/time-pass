"""
automation.py

Natural-language automation (no strict scripting).
- Multi-command in one line
- Smart handling: local apps, Windows settings (ms-settings:...), known websites, Google first link
- AI content generation via Groq -> opens modern GUI editor (customtkinter preferred)
- Keeps original behaviors: play youtube, google search, system commands
"""

import os
import re
import asyncio
import subprocess
import webbrowser
import threading
import time
import json
from datetime import datetime
from dotenv import dotenv_values
from AppOpener import close, open as appopen
from pywhatkit import search, playonyt
from groq import Groq
import keyboard
import requests
from bs4 import BeautifulSoup

# GUI libs: try customtkinter, fallback to tkinter
USE_CUSTOM = False
try:
    import customtkinter as ctk
    from tkinter import filedialog, messagebox
    from tkinter.scrolledtext import ScrolledText
    USE_CUSTOM = True
except Exception:
    import tkinter as ctk  # use tkinter under alias for shared code
    from tkinter import filedialog, messagebox
    from tkinter.scrolledtext import ScrolledText

# optional docx support
DOCX_AVAILABLE = True
try:
    from docx import Document
except Exception:
    DOCX_AVAILABLE = False

# ---------------- ENV & GROQ ----------------
env = dotenv_values(".env")
GROQ_KEY = env.get("GROQ_API_KEY")
client = Groq(api_key=GROQ_KEY) if GROQ_KEY else None

SystemChatBot = [
    {"role": "system", "content": "You are an assistant that converts natural language into one clear intent/action."}
]

# ---------------- Known websites & Windows settings ----------------
WEB_APPS = {
    "facebook": "https://www.facebook.com",
    "instagram": "https://www.instagram.com",
    "youtube": "https://www.youtube.com",
    "whatsapp": "https://web.whatsapp.com",
    "telegram": "https://web.telegram.org",
    "twitter": "https://twitter.com",
    "x": "https://twitter.com",
}

WINDOWS_SETTINGS = {
    "bluetooth": "ms-settings:bluetooth",
    "wifi": "ms-settings:network-wifi",
    "network": "ms-settings:network",
    "display": "ms-settings:display",
    "sound": "ms-settings:sound",
    "apps & features": "ms-settings:appsfeatures",
    "settings": "ms-settings:",
    "control panel": "control.exe",
    "explorer": "explorer.exe",
    "file explorer": "explorer.exe",
}

# common aliases
ALIASES = {
    "fb": "facebook",
    "insta": "instagram",
    "yt": "youtube",
    "files": "explorer",
    "file explorer": "explorer",
    "explorer": "explorer",
}

# ---------------- Helpers ----------------
def normalize_name(s: str) -> str:
    return s.lower().strip()

def open_windows_uri(uri: str):
    """Open ms-settings uri or control.exe/explorer; works on Windows."""
    try:
        # use os.startfile for ms-settings: URIs and executables
        os.startfile(uri)
        return True
    except Exception:
        try:
            subprocess.Popen(uri, shell=True)
            return True
        except Exception:
            return False

def first_google_result_and_open(query: str):
    """Fetch Google search results and open the first 'real' link (skip ads/navigation)."""
    try:
        url = f"https://www.google.com/search?q={requests.utils.requote_uri(query)}"
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=8)
        if r.status_code != 200:
            webbrowser.open(url)
            return True
        soup = BeautifulSoup(r.text, "html.parser")

        # Google uses /url?q= for organic links — pick first such link that looks valid
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.startswith("/url?q="):
                link = href.split("/url?q=")[1].split("&")[0]
                # skip google internal or support links heuristics
                if "support.google" in link or "accounts.google" in link:
                    continue
                webbrowser.open(link)
                return True

        # fallback open search page
        webbrowser.open(url)
        return True
    except Exception:
        webbrowser.open(f"https://www.google.com/search?q={requests.utils.requote_uri(query)}")
        return True

# ---------------- Execution primitives ----------------
def try_appopen(name: str) -> bool:
    try:
        appopen(name, match_closest=True, output=True, throw_error=True)
        return True
    except Exception:
        return False

def open_known_website(name: str) -> bool:
    name = normalize_name(name)
    name = ALIASES.get(name, name)
    url = WEB_APPS.get(name)
    if url:
        webbrowser.open(url)
        return True
    return False

def open_windows_setting_by_name(name: str) -> bool:
    name = normalize_name(name)
    # exact or contains match
    for key, uri in WINDOWS_SETTINGS.items():
        if key in name or name in key:
            return open_windows_uri(uri)
    return False

def open_local_or_system_or_web(name: str) -> bool:
    """Attempt local app -> windows setting -> known website -> google-first-link"""
    name_norm = normalize_name(name)
    name_norm = ALIASES.get(name_norm, name_norm)

    # 1. System settings (explicit keywords presence -> prioritize)
    if any(k in name_norm for k in WINDOWS_SETTINGS.keys()):
        if open_windows_setting_by_name(name_norm):
            return True

    # 2. Try AppOpener
    if try_appopen(name_norm):
        return True

    # 3. Try Windows settings mapping again (for phrases like "bluetooth settings")
    if open_windows_setting_by_name(name_norm):
        return True

    # 4. Known website
    if open_known_website(name_norm):
        return True

    # 5. First google result
    return first_google_result_and_open(name_norm)

# System commands
def handle_system_command(text: str) -> bool:
    t = normalize_name(text)
    if "mute" in t:
        keyboard.press_and_release("volume mute")
        return True
    if "unmute" in t:
        keyboard.press_and_release("volume mute")
        return True
    if "increase" in t or "up" in t and "volume" in t:
        keyboard.press_and_release("volume up")
        return True
    if "decrease" in t or "down" in t and "volume" in t:
        keyboard.press_and_release("volume down")
        return True
    return False

# YouTube / Google helpers
def play_on_youtube(query: str):
    try:
        playonyt(query)
    except Exception:
        webbrowser.open(f"https://www.youtube.com/results?search_query={requests.utils.requote_uri(query)}")

def google_search(query: str):
    try:
        search(query)
    except Exception:
        webbrowser.open(f"https://www.google.com/search?q={requests.utils.requote_uri(query)}")

# ---------------- AI: content generation ----------------
def ContentWriterAI(prompt: str) -> str:
    """Generate content via Groq (streaming if possible)."""
    if client is None:
        return "[AI client not configured. Set GROQ_API_KEY in .env]\n\n" + prompt
    messages = SystemChatBot + [{"role": "user", "content": prompt}]
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        max_tokens=2048,
        temperature=0.7,
        top_p=1,
        stream=True,
    )
    out = ""
    for chunk in completion:
        try:
            delta = chunk.choices[0].delta.content
            if delta:
                out += delta
        except Exception:
            pass
    out = out.replace("</s>", "")
    return out

# ------------------ GUI Editor (only for content) ------------------
class JarvisEditor:
    def __init__(self, text: str, suggested_filename: str):
        self.text = text or ""
        self.filename = suggested_filename or f"content_{int(time.time())}"
        self.auto_save = True
        self.auto_interval = 60
        self._stop = threading.Event()
        # start UI thread (daemon=False to keep process alive while editor open)
        t = threading.Thread(target=self._start_ui, daemon=False)
        t.start()

    def _start_ui(self):
        # customtkinter version (modern) or fallback to tkinter
        if USE_CUSTOM:
            ctk.set_appearance_mode("dark")
            ctk.set_default_color_theme("blue")
            root = ctk.CTk()
            root.title("Jarvis Editor — AI Content")
            root.geometry("900x650")
            bg = "#0b0f14"
            # controls frame
            ctrl = ctk.CTkFrame(root)
            ctrl.pack(fill="x", padx=10, pady=(10, 0))
            save_btn = ctk.CTkButton(ctrl, text="Save .txt", command=self.save_txt)
            save_btn.pack(side="left", padx=6)
            save_docx_btn = ctk.CTkButton(ctrl, text="Save .docx", command=self.save_docx)
            save_docx_btn.pack(side="left", padx=6)
            self.auto_btn = ctk.CTkButton(ctrl, text=f"Auto-save: ON ({self.auto_interval}s)", command=self.toggle_autosave)
            self.auto_btn.pack(side="left", padx=6)
            close_btn = ctk.CTkButton(ctrl, text="Close", command=self._on_close)
            close_btn.pack(side="right", padx=6)
            self.word_var = ctk.StringVar(value="Words: 0")
            word_lbl = ctk.CTkLabel(ctrl, textvariable=self.word_var)
            word_lbl.pack(side="right", padx=6)

            # Text area (use ScrolledText from tkinter inside CTk frame)
            frame_text = ctk.CTkFrame(root)
            frame_text.pack(fill="both", expand=True, padx=10, pady=10)
            txt = ScrolledText(frame_text, wrap="word", font=("Consolas", 12), bg="#071017", fg="#8be9fd", insertbackground="#8be9fd")
            txt.pack(fill="both", expand=True)
            txt.insert("1.0", self.text)
            txt.bind("<<Modified>>", lambda e=None: self._on_modified(txt))
            self._txt_widget = txt

            self._start_autosave_loop()
            self._update_word_count(txt)

            root.mainloop()
        else:
            # tkinter fallback with dark styling
            root = ctk.Tk()
            root.title("Jarvis Editor — AI Content")
            root.geometry("900x650")
            ctrl = ctk.Frame(root, bg="#0b0f14")
            ctrl.pack(fill="x", padx=10, pady=(10,0))
            btn_save = ctk.Button(ctrl, text="Save .txt", command=self.save_txt)
            btn_save.pack(side="left", padx=6)
            btn_docx = ctk.Button(ctrl, text="Save .docx", command=self.save_docx)
            btn_docx.pack(side="left", padx=6)
            self.auto_btn = ctk.Button(ctrl, text=f"Auto-save: ON ({self.auto_interval}s)", command=self.toggle_autosave)
            self.auto_btn.pack(side="left", padx=6)
            btn_close = ctk.Button(ctrl, text="Close", command=self._on_close)
            btn_close.pack(side="right", padx=6)
            self.word_var = ctk.StringVar(value="Words: 0")
            tk_word = ctk.Label(ctrl, textvariable=self.word_var, bg="#0b0f14", fg="#8be9fd")
            try:
                tk_word.pack(side="right", padx=6)
            except Exception:
                pass

            txt = ScrolledText(root, wrap="word", font=("Consolas", 12), bg="#071017", fg="#8be9fd", insertbackground="#8be9fd")
            txt.pack(fill="both", expand=True, padx=10, pady=10)
            txt.insert("1.0", self.text)
            txt.bind("<<Modified>>", lambda e=None: self._on_modified(txt))
            self._txt_widget = txt

            self._start_autosave_loop()
            self._update_word_count(txt)
            root.mainloop()

    def _on_modified(self, widget):
        try:
            widget.edit_modified(False)
        except Exception:
            pass
        self._update_word_count(widget)

    def _update_word_count(self, widget):
        content = widget.get("1.0", "end-1c")
        words = len(content.split())
        try:
            self.word_var.set(f"Words: {words}")
        except Exception:
            pass

    def save_txt(self):
        content = self._txt_widget.get("1.0", "end-1c")
        os.makedirs("Data", exist_ok=True)
        suggested = os.path.join("Data", f"{self.filename}.txt")
        path = filedialog.asksaveasfilename(initialfile=suggested, defaultextension=".txt", filetypes=[("Text files","*.txt")])
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            try:
                messagebox.showinfo("Saved", f"Saved to {path}")
            except Exception:
                pass

    def save_docx(self):
        if not DOCX_AVAILABLE:
            try:
                messagebox.showwarning("Missing dependency", "python-docx not installed")
            except Exception:
                pass
            return
        content = self._txt_widget.get("1.0", "end-1c")
        os.makedirs("Data", exist_ok=True)
        suggested = os.path.join("Data", f"{self.filename}.docx")
        path = filedialog.asksaveasfilename(initialfile=suggested, defaultextension=".docx", filetypes=[("Word doc","*.docx")])
        if path:
            doc = Document()
            for para in content.split("\n\n"):
                doc.add_paragraph(para.strip())
            doc.save(path)
            try:
                messagebox.showinfo("Saved", f"Saved to {path}")
            except Exception:
                pass

    def toggle_autosave(self):
        self.auto_save = not self.auto_save
        try:
            self.auto_btn.configure(text=f"Auto-save: {'ON' if self.auto_save else 'OFF'} ({self.auto_interval}s)")
        except Exception:
            pass

    def _start_autosave_loop(self):
        def loop():
            while True:
                time.sleep(self.auto_interval)
                if self.auto_save:
                    try:
                        content = self._txt_widget.get("1.0", "end-1c")
                        os.makedirs("Data", exist_ok=True)
                        with open(os.path.join("Data", f"{self.filename}.txt"), "w", encoding="utf-8") as f:
                            f.write(content)
                    except Exception:
                        pass
        threading.Thread(target=loop, daemon=True).start()

    def _on_close(self):
        try:
            if messagebox.askyesno("Close Editor", "Close editor? Unsaved changes may be lost."):
                try:
                    # close the UI by destroying the window that created _txt_widget
                    self._txt_widget.master.destroy()
                except Exception:
                    pass
        except Exception:
            try:
                self._txt_widget.master.destroy()
            except Exception:
                pass

# ------------------ NLP parsing to intents ------------------
def parse_nl_to_intents(nl_text: str):
    """
    Attempt to get one or more structured intents from the user's natural language input.
    - Uses the LLM if available (request outline: list of JSON command objects)
    - If LLM fails, fallback to splitting + simple heuristics
    """
    # Split multiple natural commands by conjunctions first (light split)
    # We'll still send whole sentence to LLM because it handles multi-intent nicely,
    # but if LLM fails we fallback to this splitting
    connectors = [" and ", " then ", ",", " & "]
    pieces = [nl_text]
    for c in connectors:
        temp = []
        for p in pieces:
            temp.extend(p.split(c))
        pieces = temp
    pieces = [p.strip() for p in pieces if p.strip()]

    if client:
        # Ask model to return JSON array of intents.
        prompt = (
            "Parse the following user requests into a JSON array of commands. Each command must be an object "
            "with keys: intent (one of: open_app, open_settings, open_website, google_search, play_youtube, write_content, system), "
            "and fields like 'name'/'query'/'text' appropriate for the intent. Output only valid JSON.\n\n"
            f"User input: {nl_text}\n\n"
            "Example output:\n"
            '[{\"intent\":\"open_app\",\"name\":\"calculator\"}, {\"intent\":\"open_settings\",\"name\":\"bluetooth\"}]'  
        )
        try:
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role":"user","content":prompt}],
                max_tokens=400,
                temperature=0.0,
            )
            resp = completion.choices[0].message.content.strip()
            # attempt to extract JSON substring
            json_text = resp
            # If the model sometimes includes backticks or text, try to find the first '[' and last ']'
            if "[" in resp and "]" in resp:
                start = resp.find("[")
                end = resp.rfind("]") + 1
                json_text = resp[start:end]
            commands = json.loads(json_text)
            if isinstance(commands, dict):
                commands = [commands]
            return commands
        except Exception:
            # LLM failed — fallback to heuristics below
            pass

    # Fallback heuristic parsing per piece
    out = []
    for piece in pieces:
        t = piece.lower()
        # settings priority (user said 'settings' or known keywords)
        if "setting" in t or any(k in t for k in ["bluetooth", "wifi", "display", "sound", "network", "control panel", "apps & features"]):
            out.append({"intent": "open_settings", "name": piece})
            continue
        # play youtube
        if "play" in t and "youtube" in t or (t.startswith("play ") and "youtube" in t or "play " in t and "song" in t):
            # extract query
            q = t.replace("play", "").replace("on youtube", "").strip()
            out.append({"intent":"play_youtube","song":q or piece})
            continue
        if "play" in t and not ("youtube" in t):
            q = t.replace("play", "").strip()
            out.append({"intent":"play_youtube","song":q})
            continue
        # write content
        if any(w in t for w in ["write", "generate", "create"]) or "paragraph" in t or "essay" in t:
            out.append({"intent":"write_content","text":piece})
            continue
        # system volume
        if any(w in t for w in ["volume", "mute", "unmute", "increase", "decrease"]):
            out.append({"intent":"system","text":piece})
            continue
        # open website/url explicit
        if "http" in t or "." in t and ("www" in t or t.split(".")[-1] in ("com","org","net","in","edu")):
            # try to extract url
            url = piece.strip()
            out.append({"intent":"open_website","url":url})
            continue
        # otherwise assume open app or google search; prefer app attempt
        out.append({"intent":"open_app","name":piece})
    return out

# ------------------ Execute parsed intents ------------------
async def execute_intent(cmd: dict):
    intent = cmd.get("intent", "unknown")
    if intent == "open_app":
        name = cmd.get("name") or cmd.get("text") or ""
        if not name:
            return False
        return open_local_app_flow(name)
    elif intent == "open_settings":
        name = cmd.get("name") or cmd.get("text") or ""
        # open windows settings directly
        if open_windows_setting_by_name(name):
            return True
        # fallback try local app then google
        if try_appopen(name):
            return True
        return first_google_result_and_open(name)
    elif intent == "open_website":
        url = cmd.get("url") or cmd.get("name") or cmd.get("text")
        if not url:
            return False
        webbrowser.open(url)
        return True
    elif intent == "google_search":
        q = cmd.get("query") or cmd.get("text") or cmd.get("name")
        if q:
            google_search(q)
            return True
        return False
    elif intent == "play_youtube":
        q = cmd.get("song") or cmd.get("query") or cmd.get("text")
        if q:
            play_on_youtube(q)
            return True
        return False
    elif intent == "write_content":
        prompt = cmd.get("text") or cmd.get("query") or cmd.get("name")
        if not prompt:
            return False
        ai_text = ContentWriterAI(prompt)
        # save default file
        base = re.sub(r"\W+", "_", (prompt or "content")).strip("_").lower()[:60] or f"content_{int(time.time())}"
        os.makedirs("Data", exist_ok=True)
        with open(os.path.join("Data", f"{base}.txt"), "w", encoding="utf-8") as f:
            f.write(ai_text)
        # open GUI editor only for content
        JarvisEditor(ai_text, base)
        return True
    elif intent == "system":
        t = cmd.get("text") or cmd.get("name") or ""
        return handle_system_command(t)
    else:
        # unknown fallback -> open google first result
        q = cmd.get("text") or cmd.get("name") or cmd.get("input") or ""
        return first_google_result_and_open(q or "")
    
def open_local_app_flow(name: str) -> bool:
    """Try app -> settings -> website -> google-first-link"""
    name_norm = normalize_name(name)
    name_norm = ALIASES.get(name_norm, name_norm)
    # 1. If contains a settings keyword, open setting
    if any(k in name_norm for k in WINDOWS_SETTINGS.keys()) or "setting" in name_norm:
        if open_windows_setting_by_name(name_norm):
            return True
   
    # 2. Try open installed app
    if try_appopen(name_norm):
        return True
   
    # 3. Check windows settings mapping again
    if open_windows_setting_by_name(name_norm):
        return True
  
    # 4. Known website
    if open_known_website(name_norm):
        return True
    
    # 5. Google first link
    return first_google_result_and_open(name_norm)


# ------------------ High-level Automation: multi-command support ------------------
async def Automation(nl_inputs):
    """
    nl_inputs: list of natural-language strings; each can contain multiple sub-commands.
    """
    if isinstance(nl_inputs, str):
        nl_inputs = [nl_inputs]
    
    for nt in nl_inputs:
        print("\n[USER INPUT]:", nt)
        intents = parse_nl_to_intents(nt)
       
        # intents is list of dicts
        for c in intents:
            print("[INTENT]", c)
            await execute_intent(c)
    print("\nAll commands executed.")



# ------------------ MAIN (example) ------------------
if __name__ == "__main__":
    # Example multiline test - replace with dynamic input in actual use
    sample = "open file explorer and open facebook then play Despacito on YouTube, write a paragraph about AI automation and open bluetooth settings"
    asyncio.run(Automation(sample))
