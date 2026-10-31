from googlesearch import search
from groq import Groq
from json import load, dump
import datetime
from dotenv import dotenv_values
import requests
from bs4 import BeautifulSoup
import os

# -------------------------------
# Load Environment Variables
# -------------------------------
env_vars = dotenv_values(".env")
Username = env_vars.get("Username", "User")
Assistantname = env_vars.get("Assistantname", "Jarvis")
GroqAPIKey = env_vars.get("GROQ_API_KEY")

if not GroqAPIKey:
    raise ValueError("❌ GROQ_API_KEY not found in .env file!")

client = Groq(api_key=GroqAPIKey)

# -------------------------------
# Ensure Data folder exists
# -------------------------------
os.makedirs("Data", exist_ok=True)

# -------------------------------
# Load or initialize chat log
# -------------------------------
try:
    with open(r"Data\ChatLog.json", "r") as f:
        messages = load(f)
except:
    messages = []
    with open(r"Data\ChatLog.json", "w") as f:
        dump(messages, f)

# -------------------------------
# System Instructions
# -------------------------------
System = f"""Hello, I am {Username}. You are a highly accurate AI chatbot named {Assistantname} with real-time internet information.
*** Answer professionally with proper grammar, punctuation, and clear sentences. ***
*** Only provide answers based on verified information or reliable sources. ***"""

SystemChatBot = [
    {"role": "system", "content": System},
    {"role": "user", "content": "Hi"},
    {"role": "assistant", "content": "Hello, how can I help you?"}
]

# -------------------------------
# Google Search Fallback
# -------------------------------
def GoogleSearch(query):
    try:
        results = list(search(query, advanced=True, num_results=5))
        Answer = f"The search results for '{query}' are:\n[start]\n"
        for i in results:
            Answer += f"Title: {i.title}\nDescription: {i.description}\n\n"
        Answer += "[end]"
        return Answer
    except Exception:
        return "⚠️ Unable to fetch Google search results."

# -------------------------------
# Real-time Info
# -------------------------------
def RealTimeInfo():
    now = datetime.datetime.now()
    return f"Use this Real-time Information:\nDay: {now.strftime('%A')}\nDate: {now.strftime('%d %B %Y')}\nTime: {now.strftime('%H:%M:%S')}"

# -------------------------------
# Authoritative Check
# -------------------------------
def AuthoritativeCheck(query):
    try:
        if "cm of delhi" in query.lower() or "chief minister of delhi" in query.lower():
            url = "https://delhi.gov.in/cmo"
            resp = requests.get(url, timeout=6)
            soup = BeautifulSoup(resp.text, "html.parser")
            for tag in soup.find_all(['h1', 'h2', 'strong', 'b']):
                text = tag.get_text(strip=True)
                if "Rekha Gupta" in text:
                    return f"[Authoritative Source]\n{text}\nRekha Gupta is the current Chief Minister of Delhi."
            for p in soup.find_all("p"):
                text = p.get_text(strip=True)
                if "Chief Minister" in text and "Rekha Gupta" in text:
                    return f"[Authoritative Source]\n{text[:400]}"
    except:
        return None
    return None

# -------------------------------
# Fact Overrides
# -------------------------------
FACT_OVERRIDES = {"cm of delhi": "Rekha Gupta"}

def SelfCorrectAnswer(prompt, raw_answer):
    lower_prompt = prompt.lower()
    for key, correct in FACT_OVERRIDES.items():
        if key in lower_prompt and correct.lower() not in raw_answer.lower():
            return f"{correct} is the current Chief Minister of Delhi.\n\n{raw_answer}"
    latest_info = AuthoritativeCheck(prompt)
    if latest_info and latest_info.lower() not in raw_answer.lower():
        return f"{latest_info}\n\n{raw_answer}"
    return raw_answer

# -------------------------------
# Answer Formatter
# -------------------------------
def AnswerModifier(Answer):
    lines = Answer.split('\n')
    non_empty_lines = [line.strip() for line in lines if line.strip()]
    return '\n'.join(non_empty_lines)

# -------------------------------
# Main Realtime Search Engine
# -------------------------------
def RealtimeSearchEngine(prompt):
    global SystemChatBot, messages
    with open(r"Data\ChatLog.json", "r") as f:
        messages = load(f)
    messages.append({"role": "user", "content": prompt})

    auth = AuthoritativeCheck(prompt)
    if auth:
        SystemChatBot.append({"role": "system", "content": auth})
    else:
        SystemChatBot.append({"role": "system", "content": GoogleSearch(prompt)})

    context = [{"role": "system", "content": RealTimeInfo()}]

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",  # ✅ working model
            messages=SystemChatBot + context + messages[-10:],
            temperature=0.7,
            max_tokens=2048,
            top_p=1,
            stream=True
        )
        Answer = ""
        for chunk in completion:
            if chunk.choices[0].delta.content:
                Answer += chunk.choices[0].delta.content

        Answer = Answer.strip().replace("</s>", "")
        messages.append({"role": "assistant", "content": Answer})
        Answer = SelfCorrectAnswer(prompt, Answer)

        if len(messages) > 20:
            messages = messages[-20:]

        with open(r"Data\ChatLog.json", "w") as f:
            dump(messages, f, indent=4)

        SystemChatBot.pop()
        return AnswerModifier(Answer)

    except Exception as e:
        return f"❌ Error during Groq completion: {e}\n⚠️ No response received."

# -------------------------------
# Run Loop
# -------------------------------
if __name__ == "__main__":
    print(f"✅ {Assistantname} Realtime Engine Started. Type 'exit' to quit.\n")
    while True:
        prompt = input("Enter your query: ")
        if prompt.lower() in ["exit", "quit", "stop"]:
            print("Goodbye!")
            break
        print("\n" + "-"*50)
        print(RealtimeSearchEngine(prompt))
        print("-"*50 + "\n")
