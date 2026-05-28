"""
Centralized runtime configuration for MedVoice.
"""

from __future__ import annotations

from dataclasses import dataclass
import os


def _as_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    app_name: str = "MedVoice AI"
    environment: str = "development"
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "llama3"
    ollama_timeout_seconds: int = 30
    log_dir: str = "logs"
    log_redact_phi: bool = True
    cors_origins: tuple[str, ...] = ("http://localhost:3000", "http://127.0.0.1:3000")
    require_api_key: bool = False
    api_key: str = ""
    use_database: bool = False
    database_url: str = "postgresql+psycopg://medvoice:medvoice@localhost:55432/medvoice"
    postgres_user: str = "medvoice"
    postgres_password: str = "medvoice"
    postgres_db: str = "medvoice"
    postgres_port: int = 55432
    postgres_host: str = "localhost"
    supabase_url: str = ""
    supabase_key: str = ""
    voice_provider: str = "local"
    sarvam_api_key: str = ""
    sarvam_tts_model: str = ""
    sarvam_stt_model: str = ""
    sarvam_tts_url: str = "https://api.sarvam.ai/v1/tts"
    sarvam_stt_url: str = "https://api.sarvam.ai/v1/stt"
    sarvam_timeout_seconds: int = 12
    provider_retry_count: int = 1
    default_language: str = "en-IN"
    default_voice_persona: str = "female_warm_indian"
    enable_streaming_audio: bool = True


def get_settings() -> Settings:
    raw_cors = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
    cors_origins = tuple(origin.strip() for origin in raw_cors.split(",") if origin.strip())
    timeout_value = os.getenv("OLLAMA_TIMEOUT_SECONDS", "30")
    try:
        timeout_seconds = int(timeout_value)
    except ValueError as exc:
        raise ValueError("OLLAMA_TIMEOUT_SECONDS must be an integer") from exc

    return Settings(
        app_name=os.getenv("APP_NAME", "MedVoice AI"),
        environment=os.getenv("ENVIRONMENT", "development"),
        ollama_url=os.getenv("OLLAMA_URL", "http://localhost:11434"),
        ollama_model=os.getenv("OLLAMA_MODEL", "llama3"),
        ollama_timeout_seconds=timeout_seconds,
        log_dir=os.getenv("LOG_DIR", "logs"),
        log_redact_phi=_as_bool(os.getenv("LOG_REDACT_PHI"), True),
        cors_origins=cors_origins or ("http://localhost:3000", "http://127.0.0.1:3000"),
        require_api_key=_as_bool(os.getenv("REQUIRE_API_KEY"), False),
        api_key=os.getenv("MEDVOICE_API_KEY", ""),
        use_database=_as_bool(os.getenv("USE_DATABASE"), False),
        database_url=os.getenv(
            "DATABASE_URL",
            "postgresql+psycopg://medvoice:medvoice@localhost:55432/medvoice",
        ),
        postgres_user=os.getenv("POSTGRES_USER", "medvoice"),
        postgres_password=os.getenv("POSTGRES_PASSWORD", "medvoice"),
        postgres_db=os.getenv("POSTGRES_DB", "medvoice"),
        postgres_port=int(os.getenv("POSTGRES_PORT", "55432")),
        postgres_host=os.getenv("POSTGRES_HOST", "localhost"),
        supabase_url=os.getenv("SUPABASE_URL", ""),
        supabase_key=os.getenv("SUPABASE_KEY", ""),
        voice_provider=os.getenv("VOICE_PROVIDER", "local"),
        sarvam_api_key=os.getenv("SARVAM_API_KEY", ""),
        sarvam_tts_model=os.getenv("SARVAM_TTS_MODEL", ""),
        sarvam_stt_model=os.getenv("SARVAM_STT_MODEL", ""),
        sarvam_tts_url=os.getenv("SARVAM_TTS_URL", "https://api.sarvam.ai/v1/tts"),
        sarvam_stt_url=os.getenv("SARVAM_STT_URL", "https://api.sarvam.ai/v1/stt"),
        sarvam_timeout_seconds=int(os.getenv("SARVAM_TIMEOUT_SECONDS", "12")),
        provider_retry_count=int(os.getenv("PROVIDER_RETRY_COUNT", "1")),
        default_language=os.getenv("DEFAULT_LANGUAGE", "en-IN"),
        default_voice_persona=os.getenv("DEFAULT_VOICE_PERSONA", "female_warm_indian"),
        enable_streaming_audio=_as_bool(os.getenv("ENABLE_STREAMING_AUDIO"), True),
    )


settings = get_settings()
