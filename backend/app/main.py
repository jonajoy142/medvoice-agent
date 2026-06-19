from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.routes_voice import router as voice_router
from app.api.v1.routes_saas import router as saas_router
from app.core.config import settings
from app.db.bootstrap import bootstrap_database

app = FastAPI(title=settings.app_name)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(voice_router, prefix="/api/v1")
app.include_router(saas_router, prefix="/api/v1")
app.include_router(saas_router)


@app.on_event("startup")
async def startup_event() -> None:
    """
    Ensure local schema exists for Docker/Postgres and local dev.
    TODO(SUPABASE): switch to migrations-only flow when managed DB is enabled.
    """
    if settings.use_database:
        bootstrap_database()
