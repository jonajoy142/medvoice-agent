from pydantic import BaseModel

class VoiceResponse(BaseModel):
    user_input: str
    response: str