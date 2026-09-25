"""Audio format conversion utilities for Exotel VoiceBot integration."""

import io
import struct
from typing import Optional


class AudioConverter:
    """Convert between different audio formats for Exotel compatibility."""
    
    @staticmethod
    def mulaw_to_pcm16(mulaw_bytes: bytes) -> bytes:
        """Convert mulaw (G.711) to 16-bit PCM little-endian."""
        try:
            import audioop
            return audioop.ulaw2lin(mulaw_bytes, 2)
        except ImportError:
            # Fallback: simple implementation if audioop not available
            return AudioConverter._mulaw_to_pcm16_fallback(mulaw_bytes)
    
    @staticmethod
    def _mulaw_to_pcm16_fallback(mulaw_bytes: bytes) -> bytes:
        """Fallback mulaw to PCM16 conversion."""
        pcm_bytes = bytearray()
        for byte in mulaw_bytes:
            # Simplified mulaw decode (not production quality)
            mu = byte ^ 0x85
            if mu & 0x80:
                mu = -((mu ^ 0x7F) + 1)
            sample = int(mu * 32767 / 255)
            pcm_bytes.extend(struct.pack('<h', sample))
        return bytes(pcm_bytes)
    
    @staticmethod
    def pcm16_to_mulaw(pcm_bytes: bytes) -> bytes:
        """Convert 16-bit PCM little-endian to mulaw (G.711)."""
        try:
            import audioop
            return audioop.lin2ulaw(pcm_bytes, 2)
        except ImportError:
            # Fallback: simple implementation
            return AudioConverter._pcm16_to_mulaw_fallback(pcm_bytes)
    
    @staticmethod
    def _pcm16_to_mulaw_fallback(pcm_bytes: bytes) -> bytes:
        """Fallback PCM16 to mulaw conversion."""
        mulaw_bytes = bytearray()
        for i in range(0, len(pcm_bytes), 2):
            sample = struct.unpack('<h', pcm_bytes[i:i+2])[0]
            # Simplified mulaw encode (not production quality)
            mu = int((sample / 32767) * 255)
            if mu < 0:
                mu = -mu + 128
            mulaw_bytes.append(mu ^ 0x85)
        return bytes(mulaw_bytes)
    
    @staticmethod
    def resample_pcm16(pcm_bytes: bytes, from_rate: int, to_rate: int) -> bytes:
        """Resample PCM16 audio from one sample rate to another."""
        if from_rate == to_rate:
            return pcm_bytes
        
        try:
            import numpy as np
            samples = np.frombuffer(pcm_bytes, dtype=np.int16)
            
            # Simple linear interpolation
            ratio = to_rate / from_rate
            new_length = int(len(samples) * ratio)
            indices = np.linspace(0, len(samples) - 1, new_length)
            resampled = np.interp(indices, np.arange(len(samples)), samples).astype(np.int16)
            
            return resampled.tobytes()
        except ImportError:
            # Fallback: simple truncation/replication
            if to_rate > from_rate:
                # Upsample by repetition
                factor = to_rate // from_rate
                return pcm_bytes * factor
            else:
                # Downsample by skipping
                factor = from_rate // to_rate
                return pcm_bytes[::factor]
    
    @staticmethod
    def ensure_exotel_format(audio_bytes: bytes, source_format: str, target_format: str = "mulaw") -> bytes:
        """
        Convert audio to Exotel-compatible format.
        
        Args:
            audio_bytes: Raw audio data
            source_format: Source format ("pcm16", "mulaw")
            target_format: Target format ("pcm16", "mulaw")
        
        Returns:
            Converted audio bytes
        """
        if source_format == target_format:
            return audio_bytes
        
        if source_format == "pcm16" and target_format == "mulaw":
            return AudioConverter.pcm16_to_mulaw(audio_bytes)
        elif source_format == "mulaw" and target_format == "pcm16":
            return AudioConverter.mulaw_to_pcm16(audio_bytes)
        else:
            raise ValueError(f"Unsupported format conversion: {source_format} -> {target_format}")
