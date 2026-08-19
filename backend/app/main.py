import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.db.supabase_client import check_supabase_connection
from app.db.vector_store import ensure_collection_exists
from app.routers import threads

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handles startup check connections to Supabase and Qdrant."""
    logger.info("Initializing system dependencies...")
    
    # 1. Check Supabase connection
    try:
        check_supabase_connection()
        logger.info("Supabase connection check succeeded.")
    except Exception as e:
        logger.error(f"CRITICAL: Supabase connection check failed: {e}")
        # We catch but log so the app runner gets clear failure reasons

    # 2. Check Qdrant collection
    try:
        ensure_collection_exists()
        logger.info("Qdrant collection check/creation succeeded.")
    except Exception as e:
        logger.error(f"CRITICAL: Qdrant collection verification failed: {e}")

    yield
    logger.info("Shutting down application...")

app = FastAPI(
    title="AI Voice Chatbot API",
    version="0.1.0",
    lifespan=lifespan
)

# Register RAG/DB Layer Routers
app.include_router(threads.router)

# TODO(teammate): Include auth router (/register, /login, face recognition)
# TODO(teammate): Include chat/agent router (/chat with guardrails/agent tool calling)
# TODO(teammate): Include voice router (/transcribe, /speak)

@app.get("/health", tags=["health"])
async def health() -> dict:
    """Trivial health check endpoint."""
    return {"status": "healthy"}
