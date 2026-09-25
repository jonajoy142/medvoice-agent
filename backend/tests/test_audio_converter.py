"""Unit tests for audio format conversion."""

import pytest
from app.voice.audio.converter import AudioConverter


def test_mulaw_to_pcm16():
    """Test mulaw to PCM16 conversion."""
    mulaw_bytes = bytes(range(256))
    pcm_bytes = AudioConverter.mulaw_to_pcm16(mulaw_bytes)
    assert len(pcm_bytes) == len(mulaw_bytes) * 2  # 16-bit = 2 bytes per sample


def test_pcm16_to_mulaw():
    """Test PCM16 to mulaw conversion."""
    pcm_bytes = b"\x00\x01" * 128  # 256 bytes of PCM16
    mulaw_bytes = AudioConverter.pcm16_to_mulaw(pcm_bytes)
    assert len(mulaw_bytes) == len(pcm_bytes) // 2  # 1 byte per mulaw sample


def test_same_format_passthrough():
    """Test that same format returns original bytes."""
    audio_bytes = b"test audio data"
    result = AudioConverter.ensure_exotel_format(
        audio_bytes, source_format="pcm16", target_format="pcm16"
    )
    assert result == audio_bytes


def test_format_conversion_pcm_to_mulaw():
    """Test PCM16 to mulaw conversion."""
    pcm_bytes = b"\x00\x01" * 128
    mulaw_bytes = AudioConverter.ensure_exotel_format(
        pcm_bytes, source_format="pcm16", target_format="mulaw"
    )
    assert len(mulaw_bytes) == len(pcm_bytes) // 2


def test_format_conversion_mulaw_to_pcm():
    """Test mulaw to PCM16 conversion."""
    mulaw_bytes = bytes(range(256))
    pcm_bytes = AudioConverter.ensure_exotel_format(
        mulaw_bytes, source_format="mulaw", target_format="pcm16"
    )
    assert len(pcm_bytes) == len(mulaw_bytes) * 2


def test_unsupported_format_conversion():
    """Test unsupported format conversion raises error."""
    with pytest.raises(ValueError):
        AudioConverter.ensure_exotel_format(
            b"test", source_format="unknown", target_format="pcm16"
        )


def test_resample_same_rate():
    """Test resampling with same rate returns original."""
    pcm_bytes = b"\x00\x01" * 100
    result = AudioConverter.resample_pcm16(pcm_bytes, from_rate=8000, to_rate=8000)
    assert result == pcm_bytes


def test_resample_upsample():
    """Test upsampling increases size."""
    pcm_bytes = b"\x00\x01" * 100
    result = AudioConverter.resample_pcm16(pcm_bytes, from_rate=8000, to_rate=16000)
    assert len(result) >= len(pcm_bytes)


def test_resample_downsample():
    """Test downsampling decreases size."""
    pcm_bytes = b"\x00\x01" * 100
    result = AudioConverter.resample_pcm16(pcm_bytes, from_rate=16000, to_rate=8000)
    assert len(result) <= len(pcm_bytes)
