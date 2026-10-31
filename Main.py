from Frontend.GUI import (
    GraphicalUserInterface,
    SetAssistantStatus,
    ShowTextToScreen,
    TempDirectoryPath,
    SetMicrophoneStatus,
    AnswerModifier,
    QueryModifier,
    GetMicrophoneStatus,
    GetAssistantStatus
)
from Backend.Model import FirstLayerDMM
from Backend.RealtimeSearchEngine import RealtimeSearchEngine
from Backend.Automation import Automation
from Backend.SpeechToText import listen_microphone  # <-- now STT-only
from Backend.Chatbot import ChatBot
from Backend.TextToSpeech import TextToSpeech
from dotenv import dotenv_values
from asyncio import run
from time import sleep
import subprocess
import threading
import json
import os
from PyQt5.QtCore import QObject, pyqtSignal

# ------------------- Environment -------------------
env_vars = dotenv_values(".env")
Username = env_vars.get("Username")
Assistantname = env_vars.get("Assistantname")
DefaultMessage  = f'''{Username} : Hello {Assistantname}, How are you?
{Assistantname} : Welcome {Username}. I am doing well. How may I help you?'''

subprocesses = []
Functions = ["open", "close", "play", "system", "content", "google search", "youtube search"]

# ------------------- GUI Signals -------------------
class GUISignals(QObject):
    update_text = pyqtSignal(str)
    update_status = pyqtSignal(str)

signals = GUISignals()
signals.update_text.connect(ShowTextToScreen)
signals.update_status.connect(SetAssistantStatus)

# ------------------- Chat Handling -------------------
def ShowDefaultChatIfNoChats():
    with open(r'Data\ChatLog.json', "r", encoding='utf-8') as File:
        if len(File.read()) < 5:
            with open(TempDirectoryPath('Database.data'), 'w', encoding='utf-8') as file:
                file.write("")
            with open(TempDirectoryPath('Responses.data'), 'w', encoding='utf-8') as file:
                file.write(DefaultMessage)

def ReadChatLogJson():
    with open(r'Data\ChatLog.json', 'r', encoding='utf-8') as file:
        return json.load(file)

def ChatLogIntegration():
    json_data = ReadChatLogJson()
    formatted_chatlog = ""
    for entry in json_data:
        if entry["role"] == "user":
            formatted_chatlog += f"User: {entry['content']}\n"
        elif entry["role"] == "assistant":
            formatted_chatlog += f"Assistant: {entry['content']}\n"
    formatted_chatlog = formatted_chatlog.replace("User", Username + " ")
    formatted_chatlog  = formatted_chatlog.replace("Assistant", Assistantname + " ")
    with open(TempDirectoryPath('Database.data'), 'w', encoding='utf-8') as file:
        file.write(AnswerModifier(formatted_chatlog))

def ShowChatsOnGui():
    with open(TempDirectoryPath('Database.data'), "r", encoding='utf-8') as File:
        Data = File.read()
    if len(str(Data)) > 0:
        lines = Data.split("\n")
        result = '\n'.join(lines)
        with open(TempDirectoryPath('Responses.data'), "w", encoding='utf-8') as File:
            File.write(result)

def InitialExecution():
    SetMicrophoneStatus("False")
    ShowTextToScreen("")
    ShowDefaultChatIfNoChats()
    ChatLogIntegration()
    ShowChatsOnGui()

InitialExecution()

# ------------------- Main Assistant Logic -------------------
def MainExecution():
    try:
        TaskExecution = False
        ImageExecution = False
        ImageGenerationQuery = ""

        # --- Listen to user ---
        signals.update_status.emit("Listening...")
        Query = listen_microphone()  # STT-only
        if not Query:
            signals.update_status.emit("Available...")
            print("No speech detected.")
            return

        signals.update_text.emit(f"{Username} : {Query}")
        signals.update_status.emit("Thinking...")

        # --- Decide using your model ---
        Decision = FirstLayerDMM(Query)
        print("Query received:", Query)
        print("Decision returned by FirstLayerDMM:", Decision)

        if not Decision:
            signals.update_text.emit("Sorry, I didn't understand that.")
            signals.update_status.emit("Available...")
            return

        G = any([i for i in Decision if i.startswith("general")])
        R = any([i for i in Decision if i.startswith("realtime")])
        Mearged_query = " and ".join(
            [" ".join(i.split()[1:]) for i in Decision if i.startswith("general") or i.startswith("realtime")]
        )

        # --- Check for image generation ---
        for q in Decision:
            if "generate " in q:
                ImageGenerationQuery = str(q)
                ImageExecution = True

        # --- Execute automation tasks ---
        for q in Decision:
            if not TaskExecution and any(q.startswith(func) for func in Functions):
                print("Executing Automation for:", q)
                run(Automation(list(Decision)))
                TaskExecution = True

        # --- Execute image generation ---
        if ImageExecution:
            with open(r"Frontend\Files\ImageGeneration.data", "w") as file:
                file.write(f"{ImageGenerationQuery},True")
            try:
                p1 = subprocess.Popen(['python', r'Backend\ImageGeneration.py'],
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                      stdin=subprocess.PIPE, shell=False)
                subprocesses.append(p1)
            except Exception as e:
                print(f"Error starting ImageGeneration.py: {e}")

        # --- Get AI Answer ---
        Answer = None

        if G and R or R:
            # Realtime search
            try:
                signals.update_status.emit("Searching...")
                Answer = RealtimeSearchEngine(QueryModifier(Mearged_query))
                print("RealtimeSearchEngine Answer:", Answer)
            except Exception as e:
                print("❌ RealtimeSearchEngine error:", e)

        for q in Decision:
            if "general" in q:
                try:
                    signals.update_status.emit("Thinking...")
                    QueryFinal = q.replace("general ", "")
                    Answer = ChatBot(QueryModifier(QueryFinal))
                    print("ChatBot Answer:", Answer)
                except Exception as e:
                    print("❌ ChatBot error:", e)

        # --- Strip Assistant name prefix from Answer ---
        if Answer:
            prefix = Assistantname.upper() + ":"
            if Answer.upper().startswith(prefix):
                Answer = Answer[len(prefix):].lstrip()

            # Display and speak the cleaned answer
            signals.update_text.emit(Answer)
            signals.update_status.emit("Answering...")
            try:
                TextToSpeech(Answer)
            except Exception as e:
                print("❌ TextToSpeech error:", e)
            signals.update_status.emit("Available...")
        else:
            signals.update_text.emit("Sorry, I couldn't generate a response.")
            signals.update_status.emit("Available...")

    except Exception as e:
        print("❌ Error in MainExecution:", e)
        signals.update_status.emit("Available...")

# ------------------- Threading -------------------
def FirstThread():
    while True:
        CurrentStatus = GetMicrophoneStatus()
        if CurrentStatus == "True":
            MainExecution()
        else:
            AIStatus = GetAssistantStatus()
            if "Available..." in AIStatus:
                sleep(0.1)
            else:
                signals.update_status.emit("Available...")

def SecondThread():
    GraphicalUserInterface()


# ------------------- Main -------------------
if __name__ == "__main__":
    thread2 = threading.Thread(target=FirstThread, daemon=True)
    thread2.start()
    SecondThread()

