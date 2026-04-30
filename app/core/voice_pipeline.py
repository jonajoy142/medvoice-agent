import whisper
import sounddevice as sd
from scipy.io.wavfile import write
import pyttsx3

# use better model for accuracy
model = whisper.load_model("medium")

def record_audio(filename="input.wav", duration=8, fs=16000):
    print("Speak now...")

    audio = sd.rec(int(duration * fs), samplerate=fs, channels=1)
    sd.wait()

    write(filename, fs, audio)
    return filename


def transcribe_audio(file):
    result = model.transcribe(
        file,
        language="en"   # force english
    )
    return result["text"]


def speak(text):
    engine = pyttsx3.init()

    engine.setProperty('rate', 180)

    engine.say(text)
    engine.runAndWait()
    engine.stop()