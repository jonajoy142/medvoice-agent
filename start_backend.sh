#!/bin/bash

echo "Starting MedVoice AI Backend..."

# Check if Ollama is running
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "Warning: Ollama is not running. Please start with: ollama serve"
    echo "Then pull llama3 model: ollama pull llama3"
fi

# Start the FastAPI backend
echo "Starting FastAPI server on http://localhost:8000"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
