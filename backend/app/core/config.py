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
    llm_provider: str = "deterministic"
    llm_fallback_provider: str = "deterministic"
    llm_timeout_seconds: int = 8
    llm_enable_fallback: bool = True
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    groq_api_key: str = ""
    groq_model: str = "llama-3.1-8b-instant"
    openrouter_api_key: str = ""
    openrouter_model: str = "meta-llama/llama-3.1-8b-instruct"
    log_dir: str = "logs"
    log_redact_phi: bool = True
    cors_origins: tuple[str, ...] = (
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://medvoice-agent.vercel.app",
    )
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
    enable_whisper: bool = True
    enable_local_stt: bool = True
    enable_local_tts: bool = True


def get_settings() -> Settings:
    raw_cors = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
    cors_origins = tuple(origin.strip() for origin in raw_cors.split(",") if origin.strip())
    timeout_value = os.getenv("LLM_TIMEOUT_SECONDS") or os.getenv("OLLAMA_TIMEOUT_SECONDS", "8")
    try:
        timeout_seconds = int(timeout_value)
    except ValueError as exc:
        raise ValueError("LLM_TIMEOUT_SECONDS must be an integer") from exc

    return Settings(
        app_name=os.getenv("APP_NAME", "MedVoice AI"),
        environment=os.getenv("ENVIRONMENT", "development"),
        llm_provider=os.getenv("LLM_PROVIDER", "deterministic").strip().lower(),
        llm_fallback_provider=os.getenv("LLM_FALLBACK_PROVIDER", "deterministic").strip().lower(),
        llm_timeout_seconds=timeout_seconds,
        llm_enable_fallback=_as_bool(os.getenv("LLM_ENABLE_FALLBACK"), True),
        ollama_base_url=os.getenv("OLLAMA_BASE_URL") or os.getenv("OLLAMA_URL", "http://localhost:11434"),
        ollama_model=os.getenv("OLLAMA_MODEL", "llama3"),
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        groq_api_key=os.getenv("GROQ_API_KEY", ""),
        groq_model=os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
        openrouter_api_key=os.getenv("OPENROUTER_API_KEY", ""),
        openrouter_model=os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.1-8b-instruct"),
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
        enable_whisper=_as_bool(os.getenv("ENABLE_WHISPER"), True),
        enable_local_stt=_as_bool(os.getenv("ENABLE_LOCAL_STT"), True),
        enable_local_tts=_as_bool(os.getenv("ENABLE_LOCAL_TTS"), True),
    )


settings = get_settings()
