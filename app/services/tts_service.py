"""
TTS Service for MedVoice AI
Provides text-to-speech with multiple voice options using gtts and system audio
"""

import os
import tempfile
import subprocess
import logging
from typing import Optional
try:
    from gtts import gTTS
    GTTS_AVAILABLE = True
except ImportError:
    GTTS_AVAILABLE = False

# Configure logging
logging.getLogger("gtts").setLevel(logging.ERROR)

class TTSService:
    def __init__(self):
        self.available_voices = ["female", "male"]
        self.current_voice = "female"
        self._check_availability()
    
    def _check_availability(self):
        """Check if TTS libraries are available"""
        global GTTS_AVAILABLE
        if not GTTS_AVAILABLE:
            print("⚠️ gTTS not available. Installing fallback TTS...")
            try:
                import subprocess
                subprocess.run(["pip3", "install", "gtts"], check=True, capture_output=True)
                from gtts import gTTS
                GTTS_AVAILABLE = True
                print("✅ gTTS installed successfully")
            except:
                print("❌ Could not install gTTS. Using system TTS fallback.")
    
    def speak(self, text: str, voice: str = "female") -> bool:
        """
        Convert text to speech and play it
        Returns True if successful, False otherwise
        """
        if not text:
            return False
        
        # Use available voice if requested voice not available
        if voice not in self.available_voices:
            voice = self.current_voice
        
        try:
            if GTTS_AVAILABLE:
                return self._speak_gtts(text, voice)
            else:
                return self._speak_system(text, voice)
        except Exception as e:
            print(f"TTS error: {e}")
            return False
    
    def _speak_gtts(self, text: str, voice: str) -> bool:
        """Speak using Google TTS"""
        try:
            from gtts import gTTS
            
            # Create temporary file for audio
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
                output_path = temp_file.name
            
            # Generate speech
            tts = gTTS(text=text, lang='en', slow=False)
            tts.save(output_path)
            
            # Convert to WAV for better compatibility (optional)
            wav_path = output_path.replace('.mp3', '.wav')
            try:
                # Try to convert to WAV using ffmpeg if available
                subprocess.run([
                    'ffmpeg', '-i', output_path, '-acodec', 'pcm_s16le', 
                    '-ar', '22050', '-ac', '1', wav_path
                ], check=True, capture_output=True)
                os.unlink(output_path)
                output_path = wav_path
            except:
                # Use MP3 directly if conversion fails
                pass
            
            # Play the audio file
            self._play_audio(output_path)
            
            # Clean up temporary file
            try:
                os.unlink(output_path)
            except:
                pass
            
            return True
            
        except Exception as e:
            print(f"gTTS error: {e}")
            return False
    
    def _speak_system(self, text: str, voice: str) -> bool:
        """Speak using system TTS as fallback"""
        try:
            # macOS system TTS
            if os.name == 'posix' and os.uname().sysname == 'Darwin':
                voice_name = "Samantha" if voice == "female" else "Alex"
                subprocess.run(['say', '-v', voice_name, text], check=True)
                return True
            
            # Linux system TTS (espeak)
            elif os.name == 'posix':
                subprocess.run(['espeak', '-ven+f3' if voice == 'female' else '-ven+m1', text], 
                             check=True, capture_output=True)
                return True
            
            # Windows system TTS
            elif os.name == 'nt':
                # Use PowerShell for Windows TTS
                ps_script = f'Add-Type -AssemblyName System.Speech; $synth = New-Object System.Speech.Synthesis.SpeechSynthesizer; $synth.Speak("{text}")'
                subprocess.run(['powershell', '-Command', ps_script], check=True, capture_output=True)
                return True
            
            return False
            
        except Exception as e:
            print(f"System TTS error: {e}")
            return False
    
    def _play_audio(self, file_path: str):
        """Play audio file using sounddevice for proper speed"""
        try:
            import soundfile as sf
            import sounddevice as sd
            
            # Read audio file
            data, samplerate = sf.read(file_path)
            
            # Ensure correct sample rate (22050 Hz for normal speed)
            if samplerate != 22050:
                # Resample if needed
                import numpy as np
                ratio = 22050 / samplerate
                new_length = int(len(data) * ratio)
                data = np.interp(
                    np.linspace(0, len(data), new_length), 
                    np.arange(len(data)), 
                    data
                )
                samplerate = 22050
            
            # Play audio with sounddevice
            sd.play(data, samplerate)
            sd.wait()  # Wait until playback finishes
            
        except ImportError:
            # Fallback to system players if sounddevice not available
            self._play_audio_fallback(file_path)
        except Exception as e:
            print(f"Audio playback error: {e}")
            self._play_audio_fallback(file_path)
    
    def _play_audio_fallback(self, file_path: str):
        """Fallback audio playback using system players"""
        try:
            # macOS uses afplay
            if os.name == 'posix' and os.uname().sysname == 'Darwin':
                subprocess.run(['afplay', file_path], check=True, capture_output=True)
            # Linux uses aplay or mpg123
            elif os.name == 'posix':
                try:
                    subprocess.run(['mpg123', file_path], check=True, capture_output=True)
                except:
                    subprocess.run(['aplay', file_path], check=True, capture_output=True)
            # Windows uses start
            elif os.name == 'nt':
                subprocess.run(['start', file_path], shell=True, check=True, capture_output=True)
            else:
                print(f"Unsupported OS for audio playback: {os.name}")
                
        except Exception as e:
            print(f"Fallback audio playback error: {e}")
    
    def get_available_voices(self) -> list:
        """Get list of available voice names"""
        return self.available_voices.copy()
    
    def is_voice_available(self, voice: str) -> bool:
        """Check if a specific voice is available"""
        return voice in self.available_voices

# Global TTS service instance
tts_service = TTSService()
