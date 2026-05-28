from app.core.voice_pipeline import record_audio, transcribe_audio, speak
from app.services.llm_service import llm_service

conversation = []

while True:
    print("\nListening...")
    file = record_audio()

    if not file:
        print("No speech detected. Please try again.")
        continue

    text = transcribe_audio(file)

    # ignore empty input
    if not text:
        print("Could not understand. Please try again.")
        continue

    print("You:", text)

    reply = llm_service.generate_reply(text, conversation, session_id="legacy-cli")

    print("AI:", reply)

    speak(reply)

    conversation.append({"role": "user", "content": text})
    conversation.append({"role": "assistant", "content": reply})
