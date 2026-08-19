# AI Voice Chatbot Backend — RAG & Supabase DB Layer

This is the document RAG and Supabase DB layer for our AI voice chatbot.

---

## 1. Setup & Environment Variables

Copy `backend/.env.example` to `backend/.env` and populate the actual connection details:

* `SUPABASE_URL`: Your Supabase project URL (e.g., `https://xxxxx.supabase.co`).
* `SUPABASE_KEY`: Your Supabase **service role API key** (do not expose this frontend-side).
* `QDRANT_URL`: Qdrant instance URL (e.g., `http://localhost:6333` or cloud instance).
* `QDRANT_API_KEY`: API key for Qdrant (optional if running locally without auth).
* `QDRANT_COLLECTION_NAME`: Qdrant collection name (defaults to `chatbot_docs`).

---

## 2. Database Schema setup

Run the SQL script `backend/scripts/schema.sql` inside the **Supabase SQL Editor** to initialize the following tables and schemas:
1. `users`: Stores user credentials (`id`, `name`, `email`, `hashed_password`).
2. `threads`: Stores chat threads (`id`, `user_id`, `title`, `created_at`, `updated_at`).
3. `messages`: Stores chat messages (`id`, `thread_id`, `role`, `content`, `created_at`).

Indices are automatically generated on foreign keys to optimize retrieval performance.

---

## 3. Document RAG Ingestion

To add new reference materials for the chatbot:
1. Put PDF files inside `backend/data/raw/`.
2. Run the ingestion script:
   ```bash
   python backend/scripts/ingest_docs.py
   ```

* How it works: The script parses the PDFs page-by-page, breaks the text into chunks of 800 characters (overlap 150), generates embeddings locally via `fastembed` (using `BAAI/bge-small-en-v1.5`), and pushes them to Qdrant.
* Deduplication: It uses a deterministic point ID based on a hash of the filename and chunk index. Re-running the script will overwrite existing chunks rather than duplicating them.

---

## 4. Importable Services for the Chat Flow

Teammates working on `/chat` can import the context retrieval function directly:

```python
from app.services.rag_service import retrieve_context

# Retrieve top 3 relevant chunks
context_chunks = retrieve_context("What is our refund policy?", top_k=3)
for chunk in context_chunks:
    print(f"Content: {chunk['text']}")
    print(f"Source PDF: {chunk['source_filename']} (Page {chunk['page_number']})")
```

---

## 5. Running Tests

To run the unit test suite locally without hitting external services:
```bash
pytest backend/tests/
```
