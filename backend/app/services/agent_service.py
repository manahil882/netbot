import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from datetime import datetime, timezone
from typing import Any

from google import genai
from google.genai import types

from app.config import settings
from app.db.vector_store import get_qdrant_client
from app.models.chat import Citation
from app.services.rag_service import list_thread_chunks, retrieve_context

logger = logging.getLogger(__name__)

_client: genai.Client | None = None
_model_blocked_until: dict[str, float] = {}

RAG_EXPLAIN = (
    "RAG (Retrieval-Augmented Generation) looks up relevant passages from your "
    "documents, then the model answers using that context instead of guessing."
)

FALLBACK_ANSWER = (
    "I could not reach the language model just now. Your message was saved — "
    "try again in a moment."
)

_SKIP_HISTORY = "I could not reach the language model"

_EXTRACT_HINTS = (
    "summar",
    "cover",
    "overview",
    "what is this",
    "explain this",
    "whole document",
    "extract",
    "quote",
)

_TASK_HINTS = (
    "mcq",
    "mcqs",
    "multiple choice",
    "multiple-choice",
    "quiz",
    "questions",
    "flashcard",
    "generate",
)


def _named_files(query: str, filenames: list[str]) -> list[str]:
    lowered = query.lower()
    compact_query = "".join(ch for ch in lowered if ch.isalnum())
    hits: list[str] = []
    for name in filenames:
        stem = name.rsplit(".", 1)[0]
        compact_name = "".join(ch for ch in stem.lower() if ch.isalnum())
        if name.lower() in lowered or stem.lower() in lowered:
            hits.append(name)
        elif compact_name and compact_name in compact_query:
            hits.append(name)
    return hits


def _prefer_named_files(query: str, chunks: list[dict]) -> list[dict]:
    names = [str(c.get("source_filename") or "") for c in chunks]
    unique = list(dict.fromkeys(n for n in names if n))
    matched = _named_files(query, unique)
    if not matched:
        return chunks
    return [c for c in chunks if c.get("source_filename") in matched]


def _answer_from_chunks(chunks: list[dict]) -> str:
    grouped: dict[str, list[dict]] = {}
    for chunk in chunks:
        name = str(chunk.get("source_filename") or "document")
        grouped.setdefault(name, []).append(chunk)

    sections: list[str] = []
    for filename, items in grouped.items():
        items.sort(key=lambda c: (int(c.get("page_number") or 0), int(c.get("chunk_index") or 0)))
        lines = [f"## {filename}\n"]
        seen: set[str] = set()
        for chunk in items:
            text = " ".join((chunk.get("text") or "").split())
            if len(text) < 20 or text in seen:
                continue
            seen.add(text)
            page = chunk.get("page_number") or "?"
            lines.append(f"**p.{page}** — {text}")
        if len(lines) > 1:
            sections.append("\n\n".join(lines))
    if not sections:
        return "I found the file, but there was not enough extracted text to summarise."
    return "\n\n".join(sections)


def _wants_extract(message: str) -> bool:
    lowered = message.lower()
    return any(hint in lowered for hint in _EXTRACT_HINTS)


def _wants_task(message: str) -> bool:
    lowered = message.lower()
    return any(hint in lowered for hint in _TASK_HINTS)


def _dedupe_chunks(chunks: list[dict]) -> list[dict]:
    seen: set[str] = set()
    unique: list[dict] = []
    for chunk in chunks:
        key = " ".join((chunk.get("text") or "").split())[:240]
        if len(key) < 20 or key in seen:
            continue
        seen.add(key)
        unique.append(chunk)
    return unique


def _context_block(chunks: list[dict], max_chars: int = 20_000) -> str:
    parts: list[str] = []
    size = 0
    for chunk in _dedupe_chunks(chunks):
        piece = (
            f"[{chunk.get('source_filename', 'doc')} p.{chunk.get('page_number', '?')}] "
            f"{chunk.get('text', '')}"
        )
        if size + len(piece) > max_chars:
            break
        parts.append(piece)
        size += len(piece)
    return "\n\n".join(parts)


def _local_fallback(user_message: str, chunks: list[dict] | None = None) -> str:
    if chunks and _wants_extract(user_message) and not _wants_task(user_message):
        return _answer_from_chunks(chunks)
    lowered = user_message.lower()
    if "rag" in lowered or "retrieval-augmented" in lowered:
        return RAG_EXPLAIN
    if chunks:
        names = sorted({str(c.get("source_filename") or "document") for c in chunks})
        files = ", ".join(names)
        return (
            f"I have your file ({files}) in this chat, but I could not reach the language "
            "model to answer that request. Try again in a moment — I will use the document "
            "as source material instead of pasting it."
        )
    return FALLBACK_ANSWER


def get_gemini_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(
            api_key=settings.GEMINI_API_KEY.strip(),
            http_options=types.HttpOptions(
                timeout=50_000,
                retry_options=types.HttpRetryOptions(attempts=1),
            ),
        )
    return _client


TOOL_DECLARATIONS = [
    types.FunctionDeclaration(
        name="search_documents",
        description="Search the knowledge base for relevant document chunks.",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "query": types.Schema(type=types.Type.STRING, description="Search query"),
                "top_k": types.Schema(type=types.Type.INTEGER, description="Max chunks to return"),
            },
            required=["query"],
        ),
    ),
    types.FunctionDeclaration(
        name="get_current_datetime",
        description="Return the current UTC date and time.",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={},
        ),
    ),
]


def _run_tool(
    name: str, args: dict[str, Any], user_id: str | None = None, thread_id: str | None = None
) -> tuple[str, list[Citation], str | None]:
    if name == "search_documents":
        query = args.get("query", "")
        top_k = int(args.get("top_k", 5))
        chunks = retrieve_context(query, top_k=top_k, user_id=user_id, thread_id=thread_id)
        citations = [
            Citation(
                source_filename=c.get("source_filename", ""),
                page_number=int(c.get("page_number", 0)),
                chunk_index=int(c.get("chunk_index", 0)),
                score=float(c.get("score", 0)),
                excerpt=(c.get("text", "") or "")[:240],
            )
            for c in chunks
        ]
        return json.dumps(chunks, default=str), citations, "search_documents"

    if name == "get_current_datetime":
        now = datetime.now(timezone.utc).isoformat()
        return json.dumps({"utc": now}), [], "get_current_datetime"

    return json.dumps({"error": f"Unknown tool: {name}"}), [], None


def _format_history(messages: list[dict]) -> list[types.Content]:
    contents: list[types.Content] = []
    for msg in messages[-8:]:
        text = msg.get("content") or ""
        if _SKIP_HISTORY in text:
            continue
        # Skip previous extractive dumps so they do not poison the next answer.
        if msg.get("role") != "user" and (
            len(text) > 3500 or text.lstrip().startswith("## ")
        ):
            continue
        role = "user" if msg["role"] == "user" else "model"
        contents.append(
            types.Content(role=role, parts=[types.Part.from_text(text=text)])
        )
    return contents


def _citations_from_chunks(chunks: list[dict]) -> list[Citation]:
    return [
        Citation(
            source_filename=c.get("source_filename", ""),
            page_number=int(c.get("page_number", 0)),
            chunk_index=int(c.get("chunk_index", 0)),
            score=float(c.get("score", 0)),
            excerpt=(c.get("text", "") or "")[:240],
        )
        for c in chunks
    ]


def generate_chat_reply(
    user_message: str,
    history: list[dict],
    user_id: str | None = None,
    thread_id: str | None = None,
) -> tuple[str, list[Citation], list[str]]:
    rag_chunks: list[dict] = []
    qdrant = get_qdrant_client()
    summarize = _wants_extract(user_message)
    task = _wants_task(user_message)
    if qdrant is not None:
        thread_chunks: list[dict] = []
        if user_id and thread_id:
            thread_chunks = list_thread_chunks(user_id, thread_id)
        filenames = list(
            dict.fromkeys(
                str(c.get("source_filename") or "")
                for c in thread_chunks
                if c.get("source_filename")
            )
        )
        matched_names = _named_files(user_message, filenames)
        scoped = (
            [c for c in thread_chunks if c.get("source_filename") in matched_names]
            if matched_names
            else thread_chunks
        )
        if not thread_chunks:
            rag_chunks = []
        elif task or summarize:
            rag_chunks = scoped or thread_chunks
        else:
            rag_chunks = retrieve_context(
                user_message, top_k=12, user_id=user_id, thread_id=thread_id
            )
            if matched_names:
                rag_chunks = _prefer_named_files(user_message, rag_chunks) or scoped
    else:
        logger.warning("Skipping RAG retrieval: Qdrant is unavailable.")

    all_citations = _citations_from_chunks(rag_chunks)
    tools_used: list[str] = []

    rag_block = _context_block(rag_chunks)
    system = (
        "You are Netbot, a grounded assistant. "
        "The last user message has SOURCE MATERIAL from their uploaded files, then their REQUEST. "
        "SOURCE MATERIAL is reference only — never dump or reprint it as the answer. "
        "Always fulfill the REQUEST using that source. "
        "If they ask for MCQs, a quiz, or N questions: write exactly that many items "
        "using this Markdown layout, with a real newline after every line "
        "(never join questions with --- or put them on one line):\n"
        "1. Question text\n"
        "- A. option\n"
        "- B. option\n"
        "- C. option\n"
        "- D. option\n"
        "**Correct answer:** B\n"
        "Do not use # headings, --- rules, or underscore emphasis. "
        "If they ask for a summary or explanation, write it in your own words and cite the filename. "
        "If SOURCE MATERIAL is (none), answer from general knowledge and say no file is attached in this chat. "
        "Format with Markdown. Do not use LaTeX."
    )
    user_payload = (
        f"SOURCE MATERIAL:\n{rag_block or '(none)'}\n\n"
        f"REQUEST:\n{user_message}"
    )

    contents = list(_format_history(history))
    contents.append(types.Content(role="user", parts=[types.Part.from_text(text=user_payload)]))

    config = types.GenerateContentConfig(
        temperature=0.4 if task else 0.3,
        system_instruction=system,
        max_output_tokens=8192,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )

    def _generate() -> tuple[str, list[Citation], list[str]]:
        client = get_gemini_client()
        local_citations = list(all_citations)
        last_error: Exception | None = None
        now = time.time()
        for model_name in settings.gemini_model_list:
            if _model_blocked_until.get(model_name, 0) > now:
                continue
            try:
                logger.info("Calling Gemini model %s", model_name)
                response = client.models.generate_content(
                    model=model_name,
                    contents=contents,
                    config=config,
                )
                text = (response.text or "").strip()
                if text:
                    return text, local_citations, tools_used
            except Exception as exc:
                last_error = exc
                message = str(exc)
                logger.error("Gemini model %s failed: %s", model_name, exc)
                if "429" in message or "RESOURCE_EXHAUSTED" in message:
                    _model_blocked_until[model_name] = time.time() + 45
                    continue
                if "404" in message or "NOT_FOUND" in message:
                    _model_blocked_until[model_name] = time.time() + 3600
                    continue
                raise
        if last_error:
            raise last_error
        raise RuntimeError("No Gemini model was available.")

    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(_generate).result(timeout=50)
    except FutureTimeout:
        logger.error("Gemini timed out")
        return _local_fallback(user_message, rag_chunks), all_citations, tools_used
    except Exception as exc:
        logger.error("Gemini chat failed: %s", exc)
        return _local_fallback(user_message, rag_chunks), all_citations, tools_used
