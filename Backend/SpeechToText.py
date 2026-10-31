import sounddevice as sd
import numpy as np
import time
from faster_whisper import WhisperModel
from dotenv import dotenv_values

try:
    from Backend.speech_state import speaking_event
except ImportError:
    from speech_state import speaking_event

env_vars = dotenv_values(".env")
InputLanguage = env_vars.get("InputLanguage", "en")

SAMPLE_RATE = 16000

# model sizes: tiny, base, small, medium, large-v3
# "base" is a good speed/accuracy balance for real-time assistants
WHISPER_MODEL_SIZE = env_vars.get("WhisperModelSize", "base")

# device="cpu" works everywhere; use "cuda" if you have an NVIDIA GPU
model = WhisperModel(WHISPER_MODEL_SIZE, device="cpu", compute_type="int8")


def listen_microphone():
    """
    STT-only: listens once and returns recognized text using faster-whisper.
    Will not record while the assistant is speaking (avoids self-listening).
    """
    try:
        while speaking_event.is_set():
            time.sleep(0.1)

        time.sleep(0.2)

        print(f"🎙️ Listening in {InputLanguage}... Speak now")
        duration = 8
        audio = sd.rec(
            int(duration * SAMPLE_RATE),
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="float32",
        )

        while sd.get_stream().active:
            if speaking_event.is_set():
                sd.stop()
                print("⚠️ Assistant started speaking mid-recording, discarding input.")
                return None
            time.sleep(0.05)

        audio_flat = audio.flatten()

        segments, info = model.transcribe(
            audio_flat,
            language=InputLanguage if InputLanguage != "en" else "en",
            beam_size=5,
        )

        text = " ".join(segment.text for segment in segments).strip().lower()

        if not text:
            print("❌ Couldn't understand. Please repeat.")
            return None

        print(f"🧠 You said: {text}")
        return text

    except Exception as e:
        print(f"⚠️ Error: {e}")
        return None