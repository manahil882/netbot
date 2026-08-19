from app.services.gemini import client

# 768-dim output -- must match the `vector(768)` column in document_chunks (see schema.sql)
EMBEDDING_MODEL = "text-embedding-004"


def embed_text(text: str) -> list[float]:
    response = client.models.embed_content(model=EMBEDDING_MODEL, contents=text)
    return response.embeddings[0].values


def embed_texts(texts: list[str]) -> list[list[float]]:
    # google-genai doesn't guarantee a batch embed_content signature across
    # versions -- looping is slower but safe. If you're on a recent SDK
    # version, check whether embed_content accepts a list for `contents`
    # and batch this for speed.
    return [embed_text(t) for t in texts]
