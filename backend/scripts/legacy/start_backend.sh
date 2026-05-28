#!/bin/bash

echo "Starting MedVoice AI Backend..."

# Start the FastAPI backend
echo "Starting FastAPI server on http://localhost:8000"
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
