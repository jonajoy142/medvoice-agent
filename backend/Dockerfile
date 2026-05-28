FROM python:3.11-slim

ARG INSTALL_WHISPER=false

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VERSION=2.3.2 \
    POETRY_VIRTUALENVS_CREATE=false \
    PIP_NO_CACHE_DIR=1 \
    ENABLE_WHISPER=false \
    ENABLE_LOCAL_STT=false \
    ENABLE_LOCAL_TTS=false \
    PORT=8000

WORKDIR /app

RUN pip install --no-cache-dir "poetry==$POETRY_VERSION"

RUN if [ "$INSTALL_WHISPER" = "true" ]; then \
      apt-get update \
      && apt-get install -y --no-install-recommends ffmpeg libportaudio2 \
      && rm -rf /var/lib/apt/lists/* \
      && pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch torchvision torchaudio \
      && pip install --no-cache-dir openai-whisper==20250625 scipy sounddevice; \
    fi

COPY pyproject.toml poetry.lock ./
RUN poetry install --no-interaction --no-ansi --no-root

COPY app ./app
COPY alembic ./alembic
COPY scripts ./scripts
COPY alembic.ini ./

EXPOSE 8000

CMD ["sh", "-c", "poetry run uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
