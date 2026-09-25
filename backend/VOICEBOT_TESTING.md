# Exotel VoiceBot E2E Testing Guide

## Prerequisites

### Exotel Account Setup
1. **Enable AgentStream**: Contact Exotel support (hello@exotel.com) to enable AgentStream/VoiceBot on your account
2. **Get Credentials**:
   - Account SID (e.g., `ACxxxxxxxxxxxxxxxxxxxxxxxx`)
   - API Token (e.g., `xxxxxxxxxxxxxxxxxxxxxxxx`)
   - Virtual Number (Exophone)
3. **IP Whitelisting**: Request Exotel's IP ranges and whitelist your server's public IP

### Environment Variables
Add these to your `backend/.env`:
```env
TELEPHONY_PROVIDER=exotel
TELEPHONY_ACCOUNT_SID=your_account_sid
TELEPHONY_AUTH_TOKEN=your_api_token
TELEPHONY_PHONE_NUMBER=your_exophone_number
TELEPHONY_BASE_URL=https://api.in.exotel.com/v1/Accounts
```

### Server Requirements
- **Public WebSocket URL**: Your server must be accessible from the internet (use ngrok for local testing)
- **SSL/TLS**: Exotel requires `wss://` (secure WebSocket)
- **Port**: Ensure your firewall allows inbound connections on the WebSocket port

## Local Testing with ngrok

### 1. Start ngrok
```bash
ngrok http 8000
```
Copy the HTTPS URL (e.g., `https://abc123.ngrok.io`)

### 2. Start Backend Server
```bash
cd backend
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Configure Exotel WebSocket URL
Your WebSocket URL will be:
```
wss://abc123.ngrok.io/api/v1/voice/stream
```

## Testing Methods

### Method 1: Exotel Dashboard (Recommended)
1. Log into Exotel Dashboard (my.exotel.com)
2. Navigate to your Exophone settings
3. Create a new call flow:
   - Add **VoiceBot Applet**
   - Set **WebSocket URL**: `wss://your-domain.com/api/v1/voice/stream`
   - Set **Stream Type**: `bidirectional`
   - Set **Sample Rate**: `8000` (default) or `16000`
4. Save and publish the call flow
5. Call your Exophone from a phone
6. Monitor backend logs for WebSocket connection

### Method 2: Exotel Legs API (Programmatic)
Use the updated telephony provider to start a VoiceBot stream:

```python
from app.telephony.factory import get_telephony_provider
from app.telephony.base import VoiceBotStreamRequest

provider = get_telephony_provider()
request = VoiceBotStreamRequest(
    to_number="+919876543210",  # Customer's phone number
    websocket_url="wss://your-domain.com/api/v1/voice/stream",
    caller_id="+918047491899",  # Your Exophone
    record=True,
    time_limit=300,  # 5 minutes
    custom_parameters={"agent_id": "demo_agent"},
    status_callback_url="https://your-domain.com/api/v1/webhooks/exotel"
)

result = provider.start_voicebot_stream(request)
print(f"Call started: {result.provider_call_id}")
```

### Method 3: Manual WebSocket Testing
Use a WebSocket client to test the endpoint directly:

```bash
wscat -c wss://your-domain.com/api/v1/voice/stream
```

Expected messages from server:
- On connection: Server accepts connection
- Send this JSON to simulate Exotel start event:
```json
{
  "event": "start",
  "sequence_number": "1",
  "stream_sid": "MZxxxxxxxxxxxxxxxxxxxxxxxx",
  "start": {
    "stream_sid": "MZxxxxxxxxxxxxxxxxxxxxxxxx",
    "call_sid": "CAxxxxxxxxxxxxxxxxxxxxxxxx",
    "account_sid": "ACxxxxxxxxxxxxxxxxxxxxxxxx",
    "from": "+919876543210",
    "to": "+918047491899",
    "custom_parameters": {},
    "media_format": {
      "encoding": "audio/x-raw",
      "sample_rate": "8000",
      "bit_rate": "16"
    }
  }
}
```

## Expected Behavior

### Current Implementation (Echo Test)
1. **Call starts** → Exotel connects to WebSocket
2. **Server receives `start` event** → Logs call metadata
3. **Server receives `media` events** → Decodes base64 audio
4. **Server echoes back audio** → Sends same audio back to caller
5. **Caller hears their own voice** → Confirms bidirectional audio works

### Log Output
```
INFO: WebSocket connection accepted
INFO: Stream started: stream_sid=MZxxxxxxxx, call_sid=CAxxxxxxxx, from=+919876543210, to=+918047491899, media_format={'encoding': 'audio/x-raw', 'sample_rate': '8000', 'bit_rate': '16'}
DEBUG: Received message: media
DEBUG: Received media chunk 1, timestamp=100, size=3200 bytes
INFO: Call ended
```

## Troubleshooting

### Connection Issues
- **WebSocket connection fails**: Check ngrok is running, verify SSL certificate
- **Exotel cannot connect**: Verify IP whitelisting, check firewall rules
- **Connection drops**: Check server logs for errors, verify stable internet connection

### Audio Issues
- **No audio heard**: Verify audio format matches Exotel configuration (PCM vs mulaw)
- **Distorted audio**: Check sample rate mismatch (8000 vs 16000 Hz)
- **One-way audio**: Verify stream type is `bidirectional` in Exotel config

### Authentication Issues
- **401 Unauthorized**: Verify TELEPHONY_ACCOUNT_SID and TELEPHONY_AUTH_TOKEN
- **403 Forbidden**: Check IP whitelisting status with Exotel

## Next Steps After Echo Test

Once echo test passes, implement:
1. **STT Integration**: Replace echo with Sarvam/OpenAI STT
2. **LLM Processing**: Send transcribed text to LLM
3. **TTS Response**: Convert LLM response to audio
4. **Interruption Handling**: Detect user speech during AI response
5. **Conversation State**: Maintain state across turns

## Security Notes

- **Never commit credentials** to git
- **Use environment variables** for all secrets
- **Enable Basic Auth** on WebSocket URL in production
- **Validate caller numbers** before processing
- **Rate limit** WebSocket connections per tenant

## Performance Targets

- **WebSocket connection**: < 500ms
- **Audio round-trip**: < 100ms (echo test)
- **First AI response**: < 1s (after STT/LLM/TTS)
- **Normal response**: ~1-2s

## Monitoring

Add these metrics to your monitoring:
- WebSocket connection success rate
- Average audio latency
- Call duration distribution
- Error rates by event type
- Concurrent connection count
