import uuid

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from google.genai import types

from app.services.gemini import client
from app.services.supabase import supabase
from app.services.text_extraction import extract_text
from app.services.chunking import chunk_text
from app.services.embeddings import embed_text, embed_texts
from app.dependencies import get_current_user

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    user=Depends(get_current_user),
):
    """Ingest a document into the RAG index: store the raw file, extract
    text, chunk it, embed each chunk, and persist the vectors."""
    file_bytes = await file.read()

    storage_path = f"{user['user_id']}/{uuid.uuid4()}_{file.filename}"
    supabase.storage.from_("documents").upload(
        storage_path,
        file_bytes,
        {"content-type": file.content_type or "application/octet-stream"},
    )

    doc_res = (
        supabase.table("documents")
        .insert(
            {
                "user_id": user["user_id"],
                "filename": file.filename,
                "storage_path": storage_path,
                "status": "processing",
            }
        )
        .execute()
    )
    if not doc_res.data:
        raise HTTPException(status_code=500, detail="Failed to create document record")

    document_id = doc_res.data[0]["id"]

    text = extract_text(file_bytes, file.filename, file.content_type)
    chunks = chunk_text(text)

    if not chunks:
        supabase.table("documents").update({"status": "failed"}).eq("id", document_id).execute()
        raise HTTPException(status_code=400, detail="Could not extract any text from this document")

    embeddings = embed_texts(chunks)
    rows = [
        {
            "document_id": document_id,
            "user_id": user["user_id"],
            "chunk_index": i,
            "content": chunk,
            "embedding": embedding,
        }
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings))
    ]
    supabase.table("document_chunks").insert(rows).execute()
    supabase.table("documents").update({"status": "ready"}).eq("id", document_id).execute()

    return {
        "document_id": document_id,
        "filename": file.filename,
        "chunks_indexed": len(chunks),
        "status": "ready",
    }


@router.post("/{document_id}/ask")
async def ask_document(
    document_id: str,
    question: str = Form(...),
    user=Depends(get_current_user),
):
    """Real RAG: embed the question, retrieve the closest chunks via pgvector,
    and ground the Gemini answer in only that retrieved context."""
    doc = (
        supabase.table("documents")
        .select("id")
        .eq("id", document_id)
        .eq("user_id", user["user_id"])
        .single()
        .execute()
    )
    if not doc.data:
        raise HTTPException(status_code=404, detail="Document not found")

    query_embedding = embed_text(question)

    matches = supabase.rpc(
        "match_document_chunks",
        {
            "query_embedding": query_embedding,
            "match_document_id": document_id,
            "match_user_id": user["user_id"],
            "match_count": 5,
        },
    ).execute()

    chunks = matches.data or []
    if not chunks:
        raise HTTPException(status_code=404, detail="No relevant content found in this document")

    context = "\n\n---\n\n".join(c["content"] for c in chunks)
    prompt = (
        "Answer the question using ONLY the context below. "
        "If the answer isn't in the context, say you don't know.\n\n"
        f"Context:\n{context}\n\nQuestion: {question}"
    )

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[types.Content(role="user", parts=[types.Part.from_text(text=prompt)])],
    )

    return {
        "answer": response.text,
        "sources": [
            {"chunk_index": c["chunk_index"], "similarity": c["similarity"]} for c in chunks
        ],
    }


@router.get("/")
async def list_documents(user=Depends(get_current_user)):
    res = (
        supabase.table("documents")
        .select("id, filename, status, created_at")
        .eq("user_id", user["user_id"])
        .order("created_at", desc=True)
        .execute()
    )
    return res.data


@router.post("/explain")
async def upload_and_explain(
    file: UploadFile = File(...),
    prompt: str = Form("Explain this document in detail."),
    user=Depends(get_current_user),
):
    """Quick one-shot explanation -- doesn't touch the RAG index, just for
    'give me a summary right now' without persisting/chunking anything."""
    file_bytes = await file.read()
    part = types.Part.from_bytes(data=file_bytes, mime_type=file.content_type or "application/pdf")

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[part, prompt],
    )

    return {"filename": file.filename, "explanation": response.text}
