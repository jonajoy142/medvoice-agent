"""Voice Activity Detection (VAD) for speech start/end detection."""

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class SpeechState(Enum):
    """States of speech detection."""
    SILENCE = "silence"
    SPEAKING = "speaking"
    UNKNOWN = "unknown"


@dataclass
class VADConfig:
    """Configuration for Voice Activity Detection."""
    speech_threshold: float = 0.3  # Energy threshold for speech detection
    silence_threshold_ms: int = 800  # Silence duration to detect speech end
    min_speech_duration_ms: int = 200  # Minimum speech duration to consider valid
    max_silence_duration_ms: int = 2000  # Maximum silence before timeout
    energy_window_size: int = 10  # Number of samples for energy calculation
    no_speech_timeout_ms: int = 5000  # Maximum time without speech before ending turn
    silence_leakage_ms: int = 100  # Allow brief silence within speech


@dataclass
class VADMetrics:
    """Metrics for VAD performance."""
    speech_start_time: Optional[float] = None
    speech_end_time: Optional[float] = None
    total_speech_duration_ms: float = 0.0
    total_silence_duration_ms: float = 0.0
    speech_segments: int = 0
    interruption_count: int = 0
    barge_in_count: int = 0
    average_speech_energy: float = 0.0
    peak_speech_energy: float = 0.0
    last_interruption_time: Optional[float] = None
    valid_speech_count: int = 0
    false_positive_count: int = 0


class VoiceActivityDetector:
    """Detects speech activity in audio streams for turn management."""
    
    def __init__(self, config: Optional[VADConfig] = None):
        self.config = config or VADConfig()
        self.state = SpeechState.SILENCE
        self.speech_start_time: Optional[float] = None
        self.last_speech_time: Optional[float] = None
        self.energy_buffer: list[float] = []
        self.metrics = VADMetrics()
        
        # Async event for speech detection
        self.speech_detected_event = asyncio.Event()
        self.silence_detected_event = asyncio.Event()
        
        # Barge-in detection
        self.ai_speaking_state: bool = False
        self.barge_in_energy_threshold: float = 0.5  # Higher threshold for barge-in
        self.barge_in_duration_threshold_ms: int = 150  # Minimum duration for valid barge-in
        self.barge_in_start_time: Optional[float] = None
        
        # Silence timeout tracking
        self.last_activity_time: Optional[float] = None
        self.silence_accumulator_ms: float = 0.0
    
    def process_audio_chunk(self, audio_bytes: bytes) -> None:
        """Process an audio chunk and update speech state."""
        energy = self._calculate_energy(audio_bytes)
        self.energy_buffer.append(energy)
        
        # Keep buffer size manageable
        if len(self.energy_buffer) > self.config.energy_window_size:
            self.energy_buffer.pop(0)
        
        # Detect speech based on energy
        avg_energy = sum(self.energy_buffer) / len(self.energy_buffer) if self.energy_buffer else 0
        is_speech = avg_energy > self.config.speech_threshold
        
        current_time = time.perf_counter()
        
        # Update activity tracking
        if is_speech or (energy > self.config.speech_threshold * 0.5):  # Track significant audio activity
            self.last_activity_time = current_time
            self.silence_accumulator_ms = 0.0
        else:
            # Accumulate silence
            if self.last_activity_time:
                silence_ms = (current_time - self.last_activity_time) * 1000
                self.silence_accumulator_ms = silence_ms
        
        # Update energy metrics
        if is_speech:
            self.metrics.average_speech_energy = (
                (self.metrics.average_speech_energy * self.metrics.valid_speech_count + energy) /
                (self.metrics.valid_speech_count + 1)
            )
            self.metrics.peak_speech_energy = max(self.metrics.peak_speech_energy, energy)
        
        if is_speech:
            if self.state == SpeechState.SILENCE:
                # Speech started
                self.state = SpeechState.SPEAKING
                self.speech_start_time = current_time
                self.metrics.speech_segments += 1
                self.speech_detected_event.set()
                self.silence_detected_event.clear()
                
                # Check for barge-in if AI is speaking
                if self.ai_speaking_state and energy > self.barge_in_energy_threshold:
                    self.barge_in_start_time = current_time
            
            self.last_speech_time = current_time
        else:
            if self.state == SpeechState.SPEAKING:
                # Use silence leakage - allow brief silence within speech
                if self.last_speech_time:
                    silence_duration = (current_time - self.last_speech_time) * 1000
                    
                    # Check if silence exceeds threshold (considering leakage)
                    if silence_duration >= self.config.silence_threshold_ms:
                        # Speech ended
                        self.state = SpeechState.SILENCE
                        if self.speech_start_time:
                            duration_ms = (current_time - self.speech_start_time) * 1000
                            if duration_ms >= self.config.min_speech_duration_ms:
                                self.metrics.total_speech_duration_ms += duration_ms
                                self.metrics.valid_speech_count += 1
                            else:
                                self.metrics.false_positive_count += 1
                        self.speech_detected_event.clear()
                        self.silence_detected_event.set()
                        
                        # Check if this was a valid barge-in
                        if self.barge_in_start_time:
                            barge_in_duration = (current_time - self.barge_in_start_time) * 1000
                            if barge_in_duration >= self.barge_in_duration_threshold_ms:
                                self.metrics.barge_in_count += 1
                                self.metrics.last_interruption_time = current_time
                            self.barge_in_start_time = None
                    elif silence_duration > self.config.silence_leakage_ms:
                        # Brief silence within speech - reset last speech time
                        self.last_speech_time = current_time
    
    def _calculate_energy(self, audio_bytes: bytes) -> float:
        """Calculate audio energy from PCM16 bytes."""
        if len(audio_bytes) < 2:
            return 0.0
        
        # Simple RMS energy calculation
        import struct
        samples = []
        for i in range(0, len(audio_bytes) - 1, 2):
            sample = struct.unpack('<h', audio_bytes[i:i+2])[0]
            samples.append(sample)
        
        if not samples:
            return 0.0
        
        # RMS energy
        rms = sum(s ** 2 for s in samples) / len(samples)
        return rms ** 0.5 / 32768.0  # Normalize to 0-1
    
    def is_speaking(self) -> bool:
        """Check if currently detecting speech."""
        return self.state == SpeechState.SPEAKING
    
    def is_silence(self) -> bool:
        """Check if currently detecting silence."""
        return self.state == SpeechState.SILENCE
    
    def get_speech_duration_ms(self) -> float:
        """Get duration of current speech segment in milliseconds."""
        if not self.speech_start_time:
            return 0.0
        return (time.perf_counter() - self.speech_start_time) * 1000
    
    def get_silence_duration_ms(self) -> float:
        """Get duration since last speech in milliseconds."""
        if not self.last_speech_time:
            return 0.0
        return (time.perf_counter() - self.last_speech_time) * 1000
    
    def set_ai_speaking_state(self, is_speaking: bool) -> None:
        """Set AI speaking state for barge-in detection."""
        self.ai_speaking_state = is_speaking
        if not is_speaking:
            self.barge_in_start_time = None
    
    def detect_barge_in(self) -> bool:
        """Check if a valid barge-in was detected."""
        return self.barge_in_start_time is not None
    
    def get_barge_in_duration_ms(self) -> float:
        """Get duration of current barge-in in milliseconds."""
        if not self.barge_in_start_time:
            return 0.0
        return (time.perf_counter() - self.barge_in_start_time) * 1000
    
    def check_no_speech_timeout(self) -> bool:
        """Check if no-speech timeout has been reached."""
        if not self.last_activity_time:
            return False
        elapsed_ms = (time.perf_counter() - self.last_activity_time) * 1000
        return elapsed_ms >= self.config.no_speech_timeout_ms
    
    def get_silence_accumulator_ms(self) -> float:
        """Get accumulated silence duration in milliseconds."""
        return self.silence_accumulator_ms
    
    def should_end_turn(self) -> bool:
        """Determine if the current turn should end based on silence/timeout."""
        # Check if we have enough silence to end the turn
        if self.get_silence_duration_ms() >= self.config.silence_threshold_ms:
            return True
        
        # Check for no-speech timeout
        if self.check_no_speech_timeout():
            return True
        
        return False
    
    def reset(self) -> None:
        """Reset VAD state for new call."""
        self.state = SpeechState.SILENCE
        self.speech_start_time = None
        self.last_speech_time = None
        self.energy_buffer.clear()
        self.metrics = VADMetrics()
        self.speech_detected_event.clear()
        self.silence_detected_event.clear()
        self.ai_speaking_state = False
        self.barge_in_start_time = None
        self.last_activity_time = None
        self.silence_accumulator_ms = 0.0
    
    def get_metrics(self) -> dict:
        """Get current VAD metrics."""
        return {
            "state": self.state.value,
            "speech_duration_ms": self.get_speech_duration_ms(),
            "silence_duration_ms": self.get_silence_duration_ms(),
            "total_speech_duration_ms": self.metrics.total_speech_duration_ms,
            "total_silence_duration_ms": self.metrics.total_silence_duration_ms,
            "speech_segments": self.metrics.speech_segments,
            "interruption_count": self.metrics.interruption_count,
            "barge_in_count": self.metrics.barge_in_count,
            "average_speech_energy": self.metrics.average_speech_energy,
            "peak_speech_energy": self.metrics.peak_speech_energy,
            "last_interruption_time": self.metrics.last_interruption_time,
            "valid_speech_count": self.metrics.valid_speech_count,
            "false_positive_count": self.metrics.false_positive_count,
            "ai_speaking_state": self.ai_speaking_state,
            "barge_in_detected": self.detect_barge_in(),
            "barge_in_duration_ms": self.get_barge_in_duration_ms(),
            "silence_accumulator_ms": self.get_silence_accumulator_ms(),
            "no_speech_timeout_reached": self.check_no_speech_timeout(),
            "should_end_turn": self.should_end_turn(),
        }
