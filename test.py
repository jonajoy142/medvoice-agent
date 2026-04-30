from app.core.voice_pipeline import record_audio, transcribe_audio, speak
from app.services.llm_service import generate_reply

conversation = []

while True:
    file = record_audio()

    text = transcribe_audio(file).strip()

    # ignore empty input
    if not text:
        continue

    print("You:", text)

    reply = generate_reply(text, conversation)

    print("AI:", reply)

    speak(reply)

    conversation.append({"role": "user", "content": text})
    conversation.append({"role": "assistant", "content": reply})