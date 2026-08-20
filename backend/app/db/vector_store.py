import logging
from pathlib import Path

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

from app.config import settings

logger = logging.getLogger(__name__)

# Populated on first successful connect. Never connect at import time.
qdrant_client: QdrantClient | None = None
_connect_attempted = False

_LOCAL_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "qdrant_local"


def _qdrant_api_key() -> str | None:
    key = (settings.QDRANT_API_KEY or "").strip()
    if not key or key.lower().startswith("mock"):
        return None
    url = settings.QDRANT_URL.lower()
    if url.startswith("http://") and "localhost" in url:
        return None
    return key


def get_qdrant_client() -> QdrantClient | None:
    """Connect to Qdrant Cloud/server, then fall back to on-disk storage.

    Local disk is used when localhost:6333 is down so document upload still works
    without Docker. Do not run uvicorn --reload while using the local store.
    """
    global qdrant_client, _connect_attempted
    if _connect_attempted:
        return qdrant_client
    _connect_attempted = True

    url = (settings.QDRANT_URL or "").strip()
    if url.startswith("http"):
        try:
            logger.info("Connecting to Qdrant at %s", url)
            client = QdrantClient(
                url=url,
                api_key=_qdrant_api_key(),
                timeout=1.0,
                check_compatibility=False,
            )
            client.get_collections()
            qdrant_client = client
            logger.info("Connected to Qdrant.")
            return qdrant_client
        except Exception as exc:
            logger.warning("Remote Qdrant unavailable (%s). Trying local disk.", exc)

    if not settings.QDRANT_FALLBACK_LOCAL:
        logger.warning("Qdrant fallback disabled. RAG retrieval will be empty.")
        qdrant_client = None
        return None

    _LOCAL_PATH.mkdir(parents=True, exist_ok=True)
    try:
        qdrant_client = QdrantClient(path=str(_LOCAL_PATH))
        logger.info("Using local Qdrant at %s", _LOCAL_PATH)
        return qdrant_client
    except Exception as local_error:
        logger.error("Local Qdrant unavailable (%s). RAG disabled.", local_error)
        qdrant_client = None
        return None


def ensure_collection_exists() -> None:
    """Create the documents collection if Qdrant is reachable."""
    client = get_qdrant_client()
    if client is None:
        logger.warning("Skipping Qdrant collection check: no client available.")
        return
    collection_name = settings.QDRANT_COLLECTION_NAME
    try:
        if not client.collection_exists(collection_name):
            logger.info("Qdrant collection '%s' does not exist. Creating...", collection_name)
            client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=384, distance=Distance.COSINE),
            )
            logger.info("Qdrant collection '%s' created successfully.", collection_name)
        else:
            logger.info("Qdrant collection '%s' already exists.", collection_name)
    except Exception as exc:
        logger.error("Error ensuring Qdrant collection exists: %s", exc)
