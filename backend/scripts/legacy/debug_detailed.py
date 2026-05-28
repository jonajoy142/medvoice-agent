#!/usr/bin/env python3
"""
Detailed debug script to identify the exact issue with voice service
"""

import tempfile
import os
import numpy as np
import sounddevice as sd
from scipy.io.wavfile import write
from app.core.voice_pipeline import record_audio, transcribe_audio
from app.services.voice_service import VoiceService

def debug_step_by_step():
    """Debug each step of the voice service process"""
    print("🔍 DETAILED VOICE SERVICE DEBUG")
    print("=" * 60)
    
    # Step 1: Test record_audio function
    print("\n📝 Step 1: Testing record_audio function...")
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            filename = temp_file.name
        
        print("🎤 Recording 4 seconds...")
        result = record_audio(filename)
        
        if result:
            print(f"✅ record_audio returned: {result}")
            
            # Check file properties
            file_size = os.path.getsize(result)
            print(f"📊 File size: {file_size} bytes")
            
            # Read and analyze audio
            from scipy.io.wavfile import read
            rate, audio_data = read(result)
            print(f"📊 Sample rate: {rate}")
            print(f"📊 Audio shape: {audio_data.shape}")
            print(f"📊 Audio max level: {np.max(np.abs(audio_data)):.6f}")
            print(f"📊 Audio dtype: {audio_data.dtype}")
            
            # Step 2: Test transcribe_audio function
            print("\n📝 Step 2: Testing transcribe_audio function...")
            text = transcribe_audio(result)
            print(f"📝 Transcription result: '{text}'")
            print(f"📝 Transcription length: {len(text)}")
            print(f"📝 Transcription type: {type(text)}")
            
            # Step 3: Test Whisper directly on the same file
            print("\n📝 Step 3: Testing Whisper directly...")
            try:
                import whisper
                model = whisper.load_model("base")
                whisper_result = model.transcribe(result, language="en", verbose=False)
                whisper_text = whisper_result["text"].strip()
                print(f"📝 Whisper direct result: '{whisper_text}'")
                print(f"📝 Whisper result length: {len(whisper_text)}")
                
                # Compare results
                if text != whisper_text:
                    print("⚠️ transcribe_audio and Whisper direct results differ!")
                else:
                    print("✅ transcribe_audio and Whisper direct results match")
                    
            except Exception as e:
                print(f"❌ Whisper direct test failed: {e}")
            
            # Step 4: Test voice service with the same file
            print("\n📝 Step 4: Testing voice service manually...")
            try:
                voice_service = VoiceService()
                
                # Manually call the voice service steps
                from app.services.intent_service import intent_service
                from app.repo.mock_db import create_session
                
                session = create_session("debug_session")
                
                # Test intent detection
                if text:
                    intent = intent_service.detect_intent(text)
                    entities = intent_service.extract_entities(text)
                    intent_result = intent_service.route_intent(intent, entities, session)
                    
                    print(f"🎯 Intent: {intent}")
                    print(f"🏷️ Entities: {entities}")
                    print(f"🤖 Intent response: '{intent_result.get('response', 'None')}'")
                    print(f"⚡ Intent action: {intent_result.get('action', 'None')}")
                else:
                    print("⚠️ No text to process")
                    
            except Exception as e:
                print(f"❌ Voice service manual test failed: {e}")
                import traceback
                traceback.print_exc()
            
            # Clean up
            os.unlink(result)
            
        else:
            print("❌ record_audio returned None")
            
    except Exception as e:
        print(f"❌ Step 1 failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_step_by_step()
    print("\n🔍 DEBUG COMPLETE")
