import logging
from pathlib import Path
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from app.config import settings

logger = logging.getLogger(__name__)

# Single client instance that falls back to local disk storage if Qdrant server is offline
qdrant_client = None

try:
    if settings.QDRANT_URL.startswith("http"):
        logger.info(f"Attempting to connect to remote Qdrant at {settings.QDRANT_URL}...")
        # Check connection using a short timeout (2.0s) so it doesn't hang the app startup
        temp_client = QdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY if settings.QDRANT_API_KEY else None,
            timeout=2.0
        )
        # Attempt to get collections to verify connection
        temp_client.get_collections()
        qdrant_client = temp_client
        logger.info("Connected to remote Qdrant server successfully.")
    else:
        logger.info(f"Initializing Qdrant client with location: {settings.QDRANT_URL}")
        qdrant_client = QdrantClient(location=settings.QDRANT_URL)
except Exception as e:
    logger.warning("Could not connect to Qdrant server at %s: %s", settings.QDRANT_URL, e)
    local_path = Path(__file__).parent.parent.parent / "data" / "qdrant_local"
    local_path.mkdir(parents=True, exist_ok=True)
    logger.warning("Falling back to local disk-based Qdrant storage at: %s", local_path)
    try:
        qdrant_client = QdrantClient(path=str(local_path))
    except Exception as local_error:
        logger.error("Local Qdrant unavailable (%s). RAG retrieval will be empty.", local_error)
        qdrant_client = None


def ensure_collection_exists() -> None:
    """Checks if the Qdrant collection exists, and creates it if not.

    The collection is configured with a vector size of 384 (matching BAAI/bge-small-en-v1.5)
    and Cosine distance metric.
    """
    if qdrant_client is None:
        logger.warning("Skipping Qdrant collection check: no client available.")
        return
    collection_name = settings.QDRANT_COLLECTION_NAME
    try:
        if not qdrant_client.collection_exists(collection_name):
            logger.info(f"Qdrant collection '{collection_name}' does not exist. Creating...")
            qdrant_client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=384, distance=Distance.COSINE)
            )
            logger.info(f"Qdrant collection '{collection_name}' created successfully.")
        else:
            logger.info(f"Qdrant collection '{collection_name}' already exists.")
    except Exception as e:
        logger.error(f"Error ensuring Qdrant collection exists: {e}")
        raise e
