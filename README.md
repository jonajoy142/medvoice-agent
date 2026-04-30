# MedVoice AI

Production-quality hospital voice assistant system with structured intent routing and modern UI.

## Features

- **Voice Processing**: Whisper STT with silence detection and error handling
- **Intent Recognition**: Rule-based routing for appointments, availability, patient lookup
- **LLM Integration**: Ollama (llama3) with strict hallucination prevention
- **Database**: In-memory mock database with patients, doctors, appointments
- **Logging**: Complete conversation tracking with structured logs
- **Modern UI**: React + TailwindCSS frontend with voice controls
- **API**: FastAPI backend with async endpoints

## Architecture

```
medVoice-ai/
├── app/
│   ├── core/
│   │   ├── voice_pipeline.py    # Audio recording, STT, TTS
│   │   └── logger.py           # Conversation logging
│   ├── services/
│   │   ├── llm_service.py      # Ollama integration
│   │   ├── intent_service.py   # Intent detection & routing
│   │   └── voice_service.py    # Main voice processing
│   ├── repo/
│   │   └── mock_db.py          # In-memory database
│   └── api/v1/
│       └── routes_voice.py     # FastAPI endpoints
├── frontend/                   # React + Vite + TailwindCSS
└── logs/                      # Conversation logs
```

## Prerequisites

1. **Python 3.11**
2. **Ollama** with llama3 model:
   ```bash
   curl -fsSL https://ollama.ai/install.sh | sh
   ollama pull llama3
   ollama serve
   ```

3. **Node.js 18+** (for frontend)

## Installation

### Backend
```bash
cd medVoice-ai
pip install -e .
```

### Frontend
```bash
cd frontend
npm install
```

## Usage

### Start Backend
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Start Frontend
```bash
cd frontend
npm run dev
```

### Test Voice Interface
```bash
python test.py
```

## API Endpoints

- `POST /api/v1/voice` - Process voice input
- `GET /api/v1/availability` - Check doctor availability
- `POST /api/v1/appointment` - Book appointment
- `GET /api/v1/appointments` - Get appointments
- `GET /api/v1/patient/{opid}` - Get patient info
- `GET /api/v1/health` - System health check

## Sample Interactions

1. **Book Appointment**: "I want to book an appointment with dermatologist"
2. **Check Availability**: "When are doctors available?"
3. **Patient Lookup**: "My OPID is 411326"
4. **General Chat**: "Hello, how are you?"

## Intent System

The system uses rule-based intent detection:
- `greeting` - Hello, hi, etc.
- `book_appointment` - Schedule appointments
- `check_availability` - Doctor schedules
- `patient_lookup` - Find patient by OPID
- `doctor_info` - Doctor information
- `goodbye` - End conversation

## Hallucination Prevention

Strict LLM rules prevent:
- Creating fake patient data
- Modifying OPID numbers
- Inventing doctor names
- Only uses database-provided information

## Frontend Features

- **Voice Controls**: Click-to-speak microphone
- **Voice Selection**: Male/female TTS options
- **Status Indicators**: Listening, processing, speaking
- **Chat Interface**: Real-time conversation display
- **Dark Mode**: Modern, clean UI design

## Performance Optimizations

- Whisper "base" model for faster transcription
- Async API endpoints
- Thread pool execution for voice processing
- Efficient session management
- Minimal LLM token usage

## Development

### Add New Intents
1. Update `intent_service.py` patterns
2. Add routing logic in `route_intent()`
3. Test with voice input

### Add Database Entities
1. Update `mock_db.py` data structures
2. Add corresponding service functions
3. Update API endpoints

## Logging

All conversations are logged to `logs/conversations.log` with:
- Timestamp
- Session ID
- User input
- AI response
- Intent and entities
- Action taken

## Troubleshooting

1. **Ollama Connection**: Ensure `ollama serve` is running
2. **Audio Issues**: Check microphone permissions
3. **Frontend Errors**: Verify backend is running on port 8000
4. **Whisper Warnings**: Suppressed in production mode

## Production Deployment

1. Configure environment variables
2. Set up proper logging rotation
3. Add authentication to API endpoints
4. Configure CORS for production domain
5. Set up monitoring and health checks