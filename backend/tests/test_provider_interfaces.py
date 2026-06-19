import pytest

from app.stt.base import STTRequest
from app.stt.sarvam import SarvamSTTProvider
from app.telephony.exotel import ExotelTelephonyProvider
from app.tts.base import TTSRequest
from app.tts.sarvam import SarvamTTSProvider


def test_sarvam_stt_requires_real_config(tmp_path):
    import app.stt.sarvam as sarvam_stt

    audio = tmp_path / "audio.wav"
    audio.write_bytes(b"audio")
    original = sarvam_stt.settings.sarvam_api_key
    object.__setattr__(sarvam_stt.settings, "sarvam_api_key", "")
    try:
        with pytest.raises(RuntimeError):
            SarvamSTTProvider().transcribe(STTRequest(str(audio), "en-IN"))
    finally:
        object.__setattr__(sarvam_stt.settings, "sarvam_api_key", original)


def test_sarvam_tts_requires_real_config():
    import app.tts.sarvam as sarvam_tts

    original = sarvam_tts.settings.sarvam_api_key
    object.__setattr__(sarvam_tts.settings, "sarvam_api_key", "")
    try:
        with pytest.raises(RuntimeError):
            SarvamTTSProvider().synthesize(TTSRequest("hello", "en-IN", "female"))
    finally:
        object.__setattr__(sarvam_tts.settings, "sarvam_api_key", original)


def test_exotel_webhook_parser_normalizes_status_payload():
    parsed = ExotelTelephonyProvider().parse_status_webhook({"CallSid": "abc", "CallStatus": "completed"})
    assert parsed["provider"] == "exotel"
    assert parsed["provider_call_id"] == "abc"
    assert parsed["status"] == "completed"
