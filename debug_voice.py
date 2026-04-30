#!/usr/bin/env python3
"""
Debug script to test voice pipeline step by step
"""

import numpy as np
import sounddevice as sd
from scipy.io.wavfile import write
import tempfile
import os
from app.core.voice_pipeline import record_audio, transcribe_audio, speak
from app.services.voice_service import VoiceService

def test_audio_recording():
    """Test audio recording with actual microphone input"""
    print("🎤 Testing audio recording...")
    print("Please speak something for 3 seconds...")
    
    # Record audio
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
        filename = temp_file.name
    
    try:
        # Record for 3 seconds
        audio = sd.rec(int(3 * 16000), samplerate=16000, channels=1)
        sd.wait()
        
        # Check audio levels
        max_level = np.max(np.abs(audio))
        print(f"📊 Audio max level: {max_level:.4f}")
        
        if max_level < 0.005:
            print("⚠️ Audio is below threshold (0.005)")
            return None
        
        write(filename, 16000, audio)
        print(f"✅ Audio recorded successfully")
        return filename
        
    except Exception as e:
        print(f"❌ Recording failed: {e}")
        return None
    finally:
        try:
            os.unlink(filename)
        except:
            pass

def test_transcription(audio_file):
    """Test transcription with recorded audio"""
    if not audio_file:
        return ""
    
    print("🔍 Testing transcription...")
    try:
        text = transcribe_audio(audio_file)
        print(f"📝 Transcription result: '{text}'")
        return text
    except Exception as e:
        print(f"❌ Transcription failed: {e}")
        return ""

def test_complete_flow():
    """Test complete voice service flow"""
    print("🔄 Testing complete voice service flow...")
    
    try:
        voice_service = VoiceService()
        
        # Test with actual recording
        result = voice_service.process_voice(session_id="debug_session", voice="female")
        
        print(f"📊 Status: {result.get('status')}")
        print(f"📝 User input: {result.get('user_input')}")
        print(f"🤖 Response: {result.get('response')}")
        print(f"🎯 Intent: {result.get('intent')}")
        
        return result
        
    except Exception as e:
        print(f"❌ Voice service failed: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    print("🔧 Voice System Debug")
    print("=" * 50)
    
    # Test 1: Audio recording
    audio_file = test_audio_recording()
    
    # Test 2: Transcription
    if audio_file:
        text = test_transcription(audio_file)
        
        # Test 3: Complete flow
        if text:
            print("\n" + "=" * 50)
            test_complete_flow()
        else:
            print("⚠️ No transcription, skipping complete flow test")
    else:
        print("⚠️ No audio recorded, skipping transcription test")
    
    print("\n🔧 Debug complete")
