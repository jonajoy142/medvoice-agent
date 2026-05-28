import logging
import warnings

from app.core.config import settings

warnings.filterwarnings("ignore")
logging.getLogger("whisper").setLevel(logging.CRITICAL)

_model = None
_model_load_failed = False


def _get_whisper_model():
    global _model, _model_load_failed
    if _model or _model_load_failed:
        return _model
    if not settings.enable_whisper:
        _model_load_failed = True
        return None
    try:
        import whisper

        _model = whisper.load_model("base", download_root=None)
    except Exception as exc:
        _model_load_failed = True
        print(f"Whisper unavailable; local STT disabled: {exc}")
    return _model


def record_audio(filename="input.wav", duration=4, fs=16000):
    if not settings.enable_local_stt:
        print("Local STT is disabled by ENABLE_LOCAL_STT=false.")
        return None

    try:
        import numpy as np
        import sounddevice as sd
        from scipy.io.wavfile import write
    except Exception as exc:
        print(f"Local audio capture unavailable: {exc}")
        return None

    audio = sd.rec(int(duration * fs), samplerate=fs, channels=1)
    sd.wait()

    max_level = np.max(np.abs(audio))
    if max_level < 0.001:
        return None

    if max_level < 0.1:
        audio = np.clip(audio * 5.0, -1.0, 1.0)

    write(filename, fs, audio)
    return filename


def transcribe_audio(file):
    if not file or not settings.enable_local_stt:
        return ""

    model = _get_whisper_model()
    if not model:
        return ""

    try:
        result = model.transcribe(file, language="en", fp16=False, verbose=False)
        return result["text"].strip()
    except Exception as exc:
        print(f"Transcription error: {exc}")
        return ""


def speak(text, voice_type="female"):
    if not text or not settings.enable_local_tts:
        return

    from app.services.tts_service import tts_service

    try:
        tts_service.speak(text, voice_type)
    except Exception as exc:
        print(f"TTS Error: {exc}")
