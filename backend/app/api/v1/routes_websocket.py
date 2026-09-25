"""WebSocket routes for real-time voice streaming."""

from fastapi import APIRouter, WebSocket, WebSocketException, status
from app.voice.realtime.websocket_handler import exotel_voicebot_websocket

router = APIRouter(tags=["websocket"])


@router.websocket("/voice/stream")
async def voice_stream_endpoint(websocket: WebSocket):
    """
    Exotel VoiceBot WebSocket endpoint for bidirectional audio streaming.
    
    This endpoint handles:
    - WebSocket connections from Exotel VoiceBot applet
    - Real-time bidirectional audio streaming
    - Call lifecycle events (start, media, dtmf, stop)
    
    Authentication:
    - IP whitelisting (contact hello@exotel.com) OR
    - Basic Auth: wss://<API_KEY>:<API_TOKEN>@domain/voice/stream
    
    Audio Format:
    - Encoding: Raw PCM 16-bit little-endian or mulaw
    - Sample Rate: 8000, 16000, or 24000 Hz
    - Payload: Base64-encoded audio
    """
    await exotel_voicebot_websocket(websocket)
