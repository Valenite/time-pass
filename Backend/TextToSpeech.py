import pygame
import random
import asyncio
import edge_tts
import io
from dotenv import dotenv_values
import threading

try:
    from Backend.speech_state import speaking_event  # when imported via main.py
except ImportError:
    from speech_state import speaking_event  # when run directly

env_vars = dotenv_values(".env")
AssistantVoice = env_vars.get("AssistantVoice") or "en-US-GuyNeural"

pygame.mixer.init()

# ------------ AUTO VOICE SELECTOR (NOT SCRIPT-BASED) ------------
def auto_voice(text):

    if any('\u0900' <= c <= '\u097F' for c in text):
        return "hi-IN-SwaraNeural"

    if any('\u0B80' <= c <= '\u0BFF' for c in text):
        return "ta-IN-ValluvarNeural"

    if any('\u0C00' <= c <= '\u0C7F' for c in text):
        return "te-IN-ShrutiNeural"

    if any('\u0D00' <= c <= '\u0D7F' for c in text):
        return "ml-IN-SobhanaNeural"

    if any('\u0C80' <= c <= '\u0CFF' for c in text):
        return "kn-IN-SapnaNeural"

    if any('\u0980' <= c <= '\u09FF' for c in text):
        return "bn-IN-TanishaaNeural"

    if any('\u0A80' <= c <= '\u0AFF' for c in text):
        return "gu-IN-DhwaniNeural"

    if any('\u0600' <= c <= '\u06FF' for c in text):
        return "ur-IN-GulNeural"

    if any('\u4E00' <= c <= '\u9FFF' for c in text):
        return "zh-CN-XiaoxiaoNeural"

    if any('\uAC00' <= c <= '\uD7AF' for c in text):
        return "ko-KR-SunHiNeural"

    if any('\u3040' <= c <= '\u30FF' for c in text):
        return "ja-JP-NanamiNeural"

    return AssistantVoice
# ---------------------------------------------------------------

async def TextToAudioBytes(text, voice):
    communicate = edge_tts.Communicate(text, voice, pitch='+5Hz', rate='+13%')
    stream = io.BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            stream.write(chunk["data"])
    stream.seek(0)
    return stream

def run_async(coro):
    try:
        return asyncio.run(coro)
    except RuntimeError:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(coro)

def play_audio_bytes(audio_bytes):
    sound = pygame.mixer.Sound(audio_bytes)
    sound.play()
    while pygame.mixer.get_busy():
        pygame.time.Clock().tick(10)

def chunk_text(text, max_sentences=10):
    sentences = [s.strip() for s in text.split(".") if s.strip()]
    chunks = []
    for i in range(0, len(sentences), max_sentences):
        chunks.append(". ".join(sentences[i:i+max_sentences]) + ".")
    return chunks

def TextToSpeech(text, func=lambda r=None: True, blocking=False):
    """
    blocking=False (default): runs in a background thread, returns immediately.
    blocking=True: waits for speech to finish before returning.
    """

    def tts_thread():
        speaking_event.set()  # tell the mic: don't record
        try:
            chunks = chunk_text(text, max_sentences=10)

            responses = [
                "The rest of the text is now on the chat screen, sir, please check it.",
                "Sir, you'll find more text on the chat screen for you to see.",
                "You'll find the complete answer on the chat screen, sir.",
                "Please review the chat screen for the rest of the text, sir."
            ]

            if len(chunks) > 1:
                chunks[0] += " " + random.choice(responses)

            for chunk in chunks:

                if not func():
                    break

                voice = auto_voice(chunk)
                print("Using Voice:", voice)

                audio_bytes = run_async(TextToAudioBytes(chunk, voice))
                play_audio_bytes(audio_bytes)
        finally:
            speaking_event.clear()  # mic is free again

    t = threading.Thread(target=tts_thread, daemon=True)
    t.start()

    if blocking:
        t.join()

    return t


# Test
if __name__ == "__main__":
    while True:
        text = input("Enter text: ")
        TextToSpeech(text, blocking=True)