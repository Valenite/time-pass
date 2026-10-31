
import json
import logging
from pathlib import Path

import ollama
from dotenv import dotenv_values


# ============================================================
# PATH CONFIGURATION
# ============================================================

# Automatically locate the main project folder containing .env.
CURRENT_DIR = Path(__file__).resolve().parent

PROJECT_DIR = next(
    (folder for folder in CURRENT_DIR.parents if (folder / ".env").exists()),
    CURRENT_DIR
)

ENV_FILE = PROJECT_DIR / ".env"
LOG_FILE = PROJECT_DIR / "Jarvis.log"

env_vars = dotenv_values(ENV_FILE)


# ============================================================
# CONFIGURATION
# ============================================================

MODEL_NAME = env_vars.get("MODEL_NAME", "qwen3:1.7b")

MAX_TOKENS = 256
CONTEXT_SIZE = 2048

logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.ERROR,
    format="%(asctime)s - %(levelname)s - %(message)s",
    encoding="utf-8"
)


# ============================================================
# OLLAMA CLIENT
# ============================================================

client = ollama.Client(
    host="http://localhost:11434"
)


# ============================================================
# RECOGNISED TASK CATEGORIES
# ============================================================

FUNCS = [
    "exit",
    "general",
    "realtime",
    "open",
    "close",
    "play",
    "generate image",
    "system",
    "content",
    "google search",
    "reminder",
    "youtube search"
]


# ============================================================
# DECISION-MAKING SYSTEM PROMPT
# ============================================================

PREAMBLE = """
You are the First Layer Decision-Making Model (DMM) of Jarvis.

Your ONLY responsibility is to classify user messages into executable
task categories.

NEVER answer the user's questions.
NEVER explain your classification.
NEVER generate additional conversational text.

Return ONLY valid JSON in this exact format:

{
    "tasks": [
        "category task description"
    ]
}

AVAILABLE CATEGORIES:

1. general
Use when the message is conversational, educational, informational,
or can be answered by a normal language model.

Examples:
- "How are you?" -> general How are you?
- "Explain quantum physics" -> general Explain quantum physics
- "Who was Mahatma Gandhi?" -> general Who was Mahatma Gandhi?
- "Thanks Jarvis" -> general Thanks Jarvis
- "What time is it?" -> general What time is it?
- "Tell me more about him" -> general Tell me more about him

Incomplete messages and pronouns referring to earlier context
should normally be classified as general.

2. realtime
Use when the user requests current, changing, or up-to-date
information that requires an external information source.

Examples:
- "Who is the current Indian Prime Minister?"
- "What is today's news?"
- "Tell me the latest updates about NVIDIA"
- "What is the current price of Bitcoin?"

Do not classify ordinary historical or educational questions as realtime.

3. open
Use when the user wants to open an application or website.

Examples:
- "Open Chrome" -> open Chrome
- "Open Facebook and Telegram" ->
  open Facebook, open Telegram

4. close
Use when the user wants to close an application or website.

Examples:
- "Close Notepad" -> close Notepad
- "Close Chrome and Discord" ->
  close Chrome, close Discord

5. play
Use when the user wants to play a song or music.

Examples:
- "Play Afsanay by YS" -> play Afsanay by YS
- "Play Let Her Go" -> play Let Her Go

6. generate image
Use when the user requests image generation.

Examples:
- "Generate an image of a lion"
  -> generate image of a lion
- "Create a futuristic city"
  -> generate image of a futuristic city

7. reminder
Use when the user requests a reminder.

Preserve the date, time, and reminder description.

Example:
- "Remind me at 9 PM tomorrow to study"
  -> reminder 9 PM tomorrow study

Never invent missing dates or times.

8. system
Use for computer or operating-system controls.

Examples:
- "Mute the volume" -> system mute volume
- "Increase brightness" -> system increase brightness
- "Turn off Wi-Fi" -> system turn off Wi-Fi
- "Volume up and mute" ->
  system volume up, system mute

9. content
Use when the user wants something written, created, or generated
as text or code.

Examples:
- "Write an email to my teacher"
  -> content Write an email to my teacher
- "Create a Python calculator"
  -> content Create a Python calculator
- "Write a formal application"
  -> content Write a formal application

10. google search
Use when the user explicitly wants to search for something on Google.

Example:
- "Google search best gaming laptops"
  -> google search best gaming laptops

11. youtube search
Use when the user wants to search for videos on YouTube.

Example:
- "Search YouTube for Python tutorials"
  -> youtube search Python tutorials

12. exit
Use when the user clearly wants to end the conversation.

Examples:
- "Goodbye Jarvis"
- "Exit"
- "See you later"

MULTIPLE TASKS:

A message can contain multiple independent tasks.

Classify EVERY task separately and preserve their original order.

Example:
User: "Open Chrome and tell me about Mahatma Gandhi"

Output:
{
    "tasks": [
        "open Chrome",
        "general tell me about Mahatma Gandhi"
    ]
}

Example:
User: "Open Chrome, search YouTube for Python tutorials,
and remind me at 8 PM to study"

Output:
{
    "tasks": [
        "open Chrome",
        "youtube search Python tutorials",
        "reminder 8 PM study"
    ]
}

Example:
User: "Search Google for AI news and open Notepad"

Output:
{
    "tasks": [
        "google search AI news",
        "open Notepad"
    ]
}

IMPORTANT RULES:

- Do not omit any requested task.
- Do not combine different categories into one task.
- Do not split one task unnecessarily.
- Preserve important names, dates, times, and descriptions.
- Do not invent information.
- If uncertain, use general.
- If the user says goodbye, return only exit.
- Return valid JSON and nothing else.
"""


# ============================================================
# RESPONSE VALIDATION
# ============================================================

def ValidateTasks(tasks):
    """
    Validate and clean the categories returned by the model.
    """

    if not isinstance(tasks, list):
        return []

    valid_tasks = []

    for task in tasks:

        if not isinstance(task, str):
            continue

        task = task.strip()

        if not task:
            continue

        task_lower = task.lower()

        for func in FUNCS:

            if task_lower == func or task_lower.startswith(func + " "):

                # Keep the original task description.
                valid_tasks.append(task)
                break

    return valid_tasks


# ============================================================
# MAIN DECISION-MAKING FUNCTION
# ============================================================

def FirstLayerDMM(prompt: str = "test"):

    prompt = str(prompt).strip()

    if not prompt:
        return []

    try:

        response = client.chat(
            model=MODEL_NAME,

            messages=[
                {
                    "role": "system",
                    "content": PREAMBLE
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],

            format="json",
            think=False,
            stream=False,
            keep_alive="30m",

            options={
                "temperature": 0.1,
                "num_predict": MAX_TOKENS,
                "num_ctx": CONTEXT_SIZE
            }
        )

        result = response["message"]["content"].strip()

        # Parse the model's JSON response.
        parsed = json.loads(result)

        tasks = parsed.get("tasks", [])

        # Validate the returned tasks.
        tasks = ValidateTasks(tasks)

        # Safe fallback if the model returns invalid output.
        if not tasks:
            return [f"general {prompt}"]

        return tasks

    except json.JSONDecodeError:

        logging.error("DMM returned invalid JSON: %s", prompt)

        return [f"general {prompt}"]

    except Exception as error:

        logging.exception("DMM classification failed: %s", error)

        return [f"general {prompt}"]


# ============================================================
# TESTING
# ============================================================

if __name__ == "__main__":

    print("\n[JARVIS] Decision-Making Model Initialized")
    print(f"[JARVIS] Model: {MODEL_NAME}")
    print("[JARVIS] Type 'exit' to stop.\n")

    while True:

        query = input(">>> ").strip()

        if not query:
            continue

        if query.lower() in ["exit", "quit"]:

            print("DMM shutting down...")
            break

        tasks = FirstLayerDMM(query)

        print("\n[JARVIS] Classified Tasks:")

        for task in tasks:
            print(f"  -> {task}")

        print()
