#!/bin/bash
set -e

cd "$(dirname "$0")/.."

echo "Starting MedVoice AI backend on http://localhost:8000"
echo "LLM_PROVIDER defaults to deterministic; set LLM_PROVIDER=ollama for local Ollama."

poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
