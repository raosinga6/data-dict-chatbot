import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import chat, schema

settings = get_settings()
logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Data Dictionary Chatbot API — env=%s", settings.environment)
    yield
    logger.info("Shutting down")


app = FastAPI(
    title="Data Dictionary Chatbot API",
    description="Natural language to SQL for business analysts",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:8501",
        "http://dd_streamlit:8501",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, prefix="/api/v1", tags=["chat"])
app.include_router(schema.router, prefix="/api/v1", tags=["schema"])


@app.get("/health", tags=["ops"])
async def health():
    return {"status": "healthy", "version": "0.1.0", "env": settings.environment}