from app.core.voice_pipeline import record_audio, transcribe_audio, speak
from app.services.llm_service import generate_reply


class VoiceService:

    def __init__(self):
        self.conversation = []

    def process_voice(self):
        file = record_audio()
        text = transcribe_audio(file)

        print("User:", text)

        reply = generate_reply(text, self.conversation)

        print("AI:", reply)

        speak(reply)

        # save conversation
        self.conversation.append({"role": "user", "content": text})
        self.conversation.append({"role": "assistant", "content": reply})

        return {
            "user_input": text,
            "response": reply
        }