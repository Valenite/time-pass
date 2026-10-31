import threading

# Shared flag: True while TTS audio is playing
speaking_event = threading.Event()