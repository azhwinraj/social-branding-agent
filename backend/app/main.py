import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api.routes import router
from app.db.session import engine, SessionLocal
from app.db.models import Base
from app.scheduler.jobs import scheduler, reload_pending


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Set provider API keys before any LiteLLM call
    if settings.groq_api_key:
        os.environ["GROQ_API_KEY"] = settings.groq_api_key
    if settings.anthropic_api_key:
        os.environ["ANTHROPIC_API_KEY"] = settings.anthropic_api_key
    if settings.gemini_api_key:
        os.environ["GEMINI_API_KEY"] = settings.gemini_api_key
    if settings.tavily_api_key:
        os.environ["TAVILY_API_KEY"] = settings.tavily_api_key

    # Set LangSmith env vars before anything imports langchain internals
    if settings.langchain_api_key:
        os.environ["LANGCHAIN_API_KEY"] = settings.langchain_api_key
        os.environ["LANGCHAIN_TRACING_V2"] = settings.langchain_tracing_v2
        os.environ["LANGCHAIN_PROJECT"] = settings.langchain_project

    # Create tables if they don't exist (Alembic handles migrations in prod)
    Base.metadata.create_all(bind=engine)

    # Start scheduler and reload any pending jobs from the DB
    scheduler.start()
    reload_pending(SessionLocal)

    yield

    scheduler.shutdown(wait=False)


app = FastAPI(title="Social Branding Agent", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")
