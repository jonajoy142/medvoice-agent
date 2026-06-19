"""
Centralized runtime configuration for MedVoice.

External integrations must be configured through environment variables. Empty
secret values are allowed at boot so local development and tests can run, but
provider implementations fail fast when a required credential is missing.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Literal


LLMProviderName = Literal["deterministic", "openai", "anthropic", "ollama", "groq", "openrouter"]
TelephonyProviderName = Literal["exotel", "twilio", "plivo"]


def _load_env_files() -> None:
    for path in (Path(__file__).resolve().parents[2] / ".env", Path(__file__).resolve().parents[3] / ".env"):
        if not path.exists():
            continue
        for raw_line in path.read_text().splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


_load_env_files()


def _as_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _as_float(value: str | None, default: float) -> float:
    if value is None or value == "":
        return default
    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(f"Expected float value, got {value!r}") from exc


def _as_int(value: str | None, default: int) -> int:
    if value is None or value == "":
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"Expected integer value, got {value!r}") from exc


@dataclass(frozen=True)
class Settings:
    app_name: str = "MedVoice AI"
    environment: str = "development"

    # Security / auth
    jwt_secret: str = ""
    require_api_key: bool = False
    api_key: str = ""
    cors_origins: tuple[str, ...] = (
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    )

    # Data plane
    use_database: bool = False
    database_url: str = ""
    redis_url: str = "redis://localhost:6379/0"
    postgres_user: str = "medvoice"
    postgres_password: str = "medvoice"
    postgres_db: str = "medvoice"
    postgres_port: int = 55432
    postgres_host: str = "localhost"

    # Supabase
    supabase_url: str = ""
    supabase_service_role_key: str = ""
    supabase_anon_key: str = ""
    supabase_key: str = ""
    supabase_storage_bucket: str = "knowledge-base"

    # LLM
    llm_provider: str = "openai"
    llm_fallback_provider: str = "deterministic"
    llm_timeout_seconds: int = 8
    llm_enable_fallback: bool = True
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    openai_stt_model: str = "gpt-4o-mini-transcribe"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-3-5-sonnet-latest"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3"
    groq_api_key: str = ""
    groq_model: str = "llama-3.1-8b-instant"
    openrouter_api_key: str = ""
    openrouter_model: str = "meta-llama/llama-3.1-8b-instruct"

    # Voice providers
    voice_provider: str = "sarvam"
    sarvam_api_key: str = ""
    sarvam_stt_endpoint: str = ""
    sarvam_tts_endpoint: str = ""
    sarvam_stt_model: str = ""
    sarvam_tts_model: str = ""
    sarvam_timeout_seconds: int = 12
    provider_retry_count: int = 1
    default_language: str = "en-IN"
    default_voice_persona: str = "female_warm_indian"
    enable_streaming_audio: bool = True
    enable_whisper: bool = False
    enable_local_stt: bool = False
    enable_local_tts: bool = False

    # Telephony
    telephony_provider: str = "exotel"
    telephony_account_sid: str = ""
    telephony_auth_token: str = ""
    telephony_phone_number: str = ""
    telephony_base_url: str = "https://api.exotel.com/v1/Accounts"

    # Guardrails / quality thresholds
    low_confidence_threshold: float = 0.72
    rag_confidence_threshold: float = 0.68
    emergency_escalation_number: str = ""
    human_handoff_number: str = ""

    # Logging
    log_dir: str = "logs"
    log_redact_phi: bool = True


_DEFAULT_DATABASE_URL = "postgresql+psycopg://medvoice:medvoice@localhost:55432/medvoice"


def _database_url() -> str:
    raw = os.getenv("DATABASE_URL", "").strip()
    if raw:
        return _normalize_postgres_url(raw)
    host = os.getenv("SUPABASE_HOST", "").strip()
    if not host:
        return _DEFAULT_DATABASE_URL
    port = os.getenv("SUPABASE_PORT") or os.getenv("SUPBASE_PORT") or "5432"
    db = os.getenv("SUPABASE_DB") or "postgres"
    user = os.getenv("SUPABASE_USER") or "postgres"
    password = os.getenv("SUPABASE_PASSWORD") or os.getenv("SUPABASE_PSWD") or os.getenv("SUPBASE_PSWD") or ""
    return _normalize_postgres_url(f"postgresql://{user}:{password}@{host}:{port}/{db}")


def _supabase_url() -> str:
    raw = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
    if raw:
        return raw
    host = os.getenv("SUPABASE_HOST", "").strip().rstrip("/")
    if not host:
        return ""
    if host.startswith(("http://", "https://")):
        return host
    host = host.removeprefix("db.")
    if "supabase.co" in host:
        return f"https://{host}"
    scheme = "http" if host.startswith(("localhost", "127.0.0.1", "::1")) else "https"
    port = (os.getenv("SUPABASE_API_PORT") or os.getenv("SUPABASE_URL_PORT") or os.getenv("SUPABASE_PORT") or "").strip()
    if port and ":" not in host:
        return f"{scheme}://{host}:{port}"
    return f"{scheme}://{host}"


def _normalize_postgres_url(value: str) -> str:
    if value.startswith("postgresql://"):
        return value.replace("postgresql://", "postgresql+psycopg://", 1)
    if value.startswith("postgres://"):
        return value.replace("postgres://", "postgresql+psycopg://", 1)
    return value


def get_settings() -> Settings:
    raw_cors = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173,https://medvoice-agent.vercel.app",
    )
    cors_origins = tuple(origin.strip() for origin in raw_cors.split(",") if origin.strip())

    supabase_service_key = (
        os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        or os.getenv("SUPABASE_SERVICE_KEY")
        or os.getenv("SUPABASE_SECRET_KEY")
        or ""
    )
    legacy_supabase_key = os.getenv("SUPABASE_KEY", "")

    return Settings(
        app_name=os.getenv("APP_NAME", "MedVoice AI"),
        environment=os.getenv("ENVIRONMENT", "development"),
        jwt_secret=os.getenv("JWT_SECRET", ""),
        require_api_key=_as_bool(os.getenv("REQUIRE_API_KEY"), False),
        api_key=os.getenv("MEDVOICE_API_KEY", ""),
        cors_origins=cors_origins,
        use_database=_as_bool(os.getenv("USE_DATABASE"), bool(os.getenv("DATABASE_URL") or os.getenv("SUPABASE_HOST"))),
        database_url=_database_url(),
        redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        postgres_user=os.getenv("POSTGRES_USER", "medvoice"),
        postgres_password=os.getenv("POSTGRES_PASSWORD", "medvoice"),
        postgres_db=os.getenv("POSTGRES_DB", "medvoice"),
        postgres_port=_as_int(os.getenv("POSTGRES_PORT"), 55432),
        postgres_host=os.getenv("POSTGRES_HOST", "localhost"),
        supabase_url=_supabase_url(),
        supabase_service_role_key=supabase_service_key,
        supabase_anon_key=os.getenv("SUPABASE_ANON_KEY", ""),
        supabase_key=supabase_service_key or legacy_supabase_key,
        supabase_storage_bucket=os.getenv("SUPABASE_STORAGE_BUCKET", "knowledge-base"),
        llm_provider=os.getenv("LLM_PROVIDER", "openai").strip().lower(),
        llm_fallback_provider=os.getenv("LLM_FALLBACK_PROVIDER", "deterministic").strip().lower(),
        llm_timeout_seconds=_as_int(os.getenv("LLM_TIMEOUT_SECONDS") or os.getenv("OLLAMA_TIMEOUT_SECONDS"), 8),
        llm_enable_fallback=_as_bool(os.getenv("LLM_ENABLE_FALLBACK"), True),
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        openai_embedding_model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
        openai_stt_model=os.getenv("OPENAI_STT_MODEL", "gpt-4o-mini-transcribe"),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
        anthropic_model=os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-latest"),
        ollama_base_url=os.getenv("OLLAMA_BASE_URL") or os.getenv("OLLAMA_URL", "http://localhost:11434"),
        ollama_model=os.getenv("OLLAMA_MODEL", "llama3"),
        groq_api_key=os.getenv("GROQ_API_KEY", ""),
        groq_model=os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
        openrouter_api_key=os.getenv("OPENROUTER_API_KEY", ""),
        openrouter_model=os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.1-8b-instruct"),
        voice_provider=os.getenv("VOICE_PROVIDER", "sarvam").strip().lower(),
        sarvam_api_key=os.getenv("SARVAM_API_KEY", ""),
        sarvam_stt_endpoint=os.getenv("SARVAM_STT_ENDPOINT") or os.getenv("SARVAM_STT_URL", ""),
        sarvam_tts_endpoint=os.getenv("SARVAM_TTS_ENDPOINT") or os.getenv("SARVAM_TTS_URL", ""),
        sarvam_stt_model=os.getenv("SARVAM_STT_MODEL", ""),
        sarvam_tts_model=os.getenv("SARVAM_TTS_MODEL", ""),
        sarvam_timeout_seconds=_as_int(os.getenv("SARVAM_TIMEOUT_SECONDS"), 12),
        provider_retry_count=_as_int(os.getenv("PROVIDER_RETRY_COUNT"), 1),
        default_language=os.getenv("DEFAULT_LANGUAGE", "en-IN"),
        default_voice_persona=os.getenv("DEFAULT_VOICE_PERSONA", "female_warm_indian"),
        enable_streaming_audio=_as_bool(os.getenv("ENABLE_STREAMING_AUDIO"), True),
        enable_whisper=_as_bool(os.getenv("ENABLE_WHISPER"), False),
        enable_local_stt=_as_bool(os.getenv("ENABLE_LOCAL_STT"), False),
        enable_local_tts=_as_bool(os.getenv("ENABLE_LOCAL_TTS"), False),
        telephony_provider=os.getenv("TELEPHONY_PROVIDER", "exotel").strip().lower(),
        telephony_account_sid=os.getenv("TELEPHONY_ACCOUNT_SID", ""),
        telephony_auth_token=os.getenv("TELEPHONY_AUTH_TOKEN", ""),
        telephony_phone_number=os.getenv("TELEPHONY_PHONE_NUMBER", ""),
        telephony_base_url=os.getenv("TELEPHONY_BASE_URL", "https://api.exotel.com/v1/Accounts"),
        low_confidence_threshold=_as_float(os.getenv("LOW_CONFIDENCE_THRESHOLD"), 0.72),
        rag_confidence_threshold=_as_float(os.getenv("RAG_CONFIDENCE_THRESHOLD"), 0.68),
        emergency_escalation_number=os.getenv("EMERGENCY_ESCALATION_NUMBER", ""),
        human_handoff_number=os.getenv("HUMAN_HANDOFF_NUMBER", ""),
        log_dir=os.getenv("LOG_DIR", "logs"),
        log_redact_phi=_as_bool(os.getenv("LOG_REDACT_PHI"), True),
    )


settings = get_settings()
