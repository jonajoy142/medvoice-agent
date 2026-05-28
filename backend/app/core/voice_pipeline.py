import whisper
import sounddevice as sd
from scipy.io.wavfile import write
import numpy as np
import logging
import warnings

# Suppress all warnings and progress bars
warnings.filterwarnings("ignore")
logging.getLogger("whisper").setLevel(logging.CRITICAL)

# Load model only once globally
try:
    model = whisper.load_model("base", download_root=None)
except:
    model = whisper.load_model("base")

def record_audio(filename="input.wav", duration=4, fs=16000):
    audio = sd.rec(int(duration * fs), samplerate=fs, channels=1)
    sd.wait()

    # Check if audio is empty or too quiet (very low threshold for better sensitivity)
    max_level = np.max(np.abs(audio))
    if max_level < 0.001:
        return None  # Silence detected
    
    # Apply gain to boost quiet audio
    if max_level < 0.1:
        audio = audio * 5.0  # Boost quiet audio
        # Clip to prevent distortion
        audio = np.clip(audio, -1.0, 1.0)

    write(filename, fs, audio)
    return filename


def transcribe_audio(file):
    if not file:
        return ""
    
    try:
        result = model.transcribe(
            file,
            language="en",   # force english
            fp16=False,      # Use FP32 for better compatibility
            verbose=False    # Suppress verbose output
        )
        text = result["text"].strip()
        return text
    except Exception as e:
        # Log the error for debugging but don't crash
        print(f"Transcription error: {e}")
        return ""


def speak(text, voice_type="female"):
    # Import TTS service to avoid circular imports
    from app.services.tts_service import tts_service
    
    if not text:
        return
    
    try:
        tts_service.speak(text, voice_type)
    except Exception as e:
        print(f"TTS Error: {e}")