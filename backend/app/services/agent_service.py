import json
import logging
from datetime import datetime, timezone
from typing import Any

from google import genai
from google.genai import types

from app.config import settings
from app.models.chat import Citation
from app.services.rag_service import retrieve_context

logger = logging.getLogger(__name__)

_client: genai.Client | None = None


def get_gemini_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=settings.GEMINI_API_KEY)
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
        parameters=types.Schema(type=types.Type.OBJECT, properties={}),
    ),
]


def _run_tool(name: str, args: dict[str, Any]) -> tuple[str, list[Citation], str | None]:
    if name == "search_documents":
        query = args.get("query", "")
        top_k = int(args.get("top_k", 5))
        chunks = retrieve_context(query, top_k=top_k)
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
    for msg in messages[-12:]:
        role = "user" if msg["role"] == "user" else "model"
        contents.append(
            types.Content(role=role, parts=[types.Part.from_text(text=msg["content"])])
        )
    return contents


def generate_chat_reply(user_message: str, history: list[dict]) -> tuple[str, list[Citation], list[str]]:
    client = get_gemini_client()
    rag_chunks = retrieve_context(user_message, top_k=5)
    rag_block = "\n\n".join(
        f"[{c.get('source_filename', 'doc')} p.{c.get('page_number', '?')}] {c.get('text', '')}"
        for c in rag_chunks
    )
    system = (
        "You are Netbot, a grounded enterprise assistant. "
        "Prefer retrieved document context. Cite sources when used. "
        "Use tools when document search or current time is needed.\n\n"
        f"Retrieved context:\n{rag_block or '(none)'}"
    )

    contents = [types.Content(role="user", parts=[types.Part.from_text(text=system)])]
    contents.extend(_format_history(history))
    contents.append(types.Content(role="user", parts=[types.Part.from_text(text=user_message)]))

    tools_used: list[str] = []
    all_citations: list[Citation] = [
        Citation(
            source_filename=c.get("source_filename", ""),
            page_number=int(c.get("page_number", 0)),
            chunk_index=int(c.get("chunk_index", 0)),
            score=float(c.get("score", 0)),
            excerpt=(c.get("text", "") or "")[:240],
        )
        for c in rag_chunks
    ]

    config = types.GenerateContentConfig(
        tools=[types.Tool(function_declarations=TOOL_DECLARATIONS)],
        temperature=0.3,
    )

    for _ in range(4):
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=contents,
            config=config,
        )

        candidate = response.candidates[0] if response.candidates else None
        if not candidate or not candidate.content or not candidate.content.parts:
            break

        function_calls = [p.function_call for p in candidate.content.parts if p.function_call]
        if not function_calls:
            text = response.text or "I could not generate a response."
            return text.strip(), all_citations, tools_used

        contents.append(candidate.content)
        tool_response_parts: list[types.Part] = []
        for call in function_calls:
            args = dict(call.args or {})
            result, citations, tool_name = _run_tool(call.name or "", args)
            if tool_name:
                tools_used.append(tool_name)
            all_citations.extend(citations)
            tool_response_parts.append(
                types.Part.from_function_response(name=call.name or "tool", response={"result": result})
            )
        contents.append(types.Content(role="user", parts=tool_response_parts))

    return "I could not complete the request.", all_citations, tools_used
