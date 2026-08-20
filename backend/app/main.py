import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db.supabase_client import check_supabase_connection
from app.db.vector_store import ensure_collection_exists
from app.routers import auth, chat, threads, voice

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing system dependencies...")
    try:
        check_supabase_connection()
        logger.info("Supabase connection check succeeded.")
    except Exception as e:
        logger.error("CRITICAL: Supabase connection check failed: %s", e)

    try:
        ensure_collection_exists()
        logger.info("Qdrant collection check/creation succeeded.")
    except Exception as e:
        logger.error("CRITICAL: Qdrant collection verification failed: %s", e)

    yield
    logger.info("Shutting down application...")


app = FastAPI(
    title="AI Voice Chatbot API",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(threads.router)
app.include_router(chat.router)
app.include_router(voice.router)


@app.get("/health", tags=["health"])
async def health() -> dict:
    return {"status": "healthy"}
