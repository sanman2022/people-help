import logging

from openai import AsyncOpenAI

from config import (
    OPENAI_API_KEY,
    OPENAI_CHAT_MODEL,
    OPENAI_EMBEDDING_MODEL,
)
from services.supabase_client import get_supabase

logger = logging.getLogger(__name__)

_openai_client: AsyncOpenAI | None = None


def _get_openai() -> AsyncOpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
    return _openai_client


async def get_embedding(text: str) -> list[float]:
    try:
        client = _get_openai()
        r = await client.embeddings.create(input=[text], model=OPENAI_EMBEDDING_MODEL)
        return r.data[0].embedding
    except Exception as e:
        logger.error("Embedding generation failed: %s", e)
        raise


async def search_chunks(query: str, top_k: int = 5) -> list[dict]:
    embedding = await get_embedding(query)
    try:
        sb = get_supabase()
        result = sb.rpc(
            "match_document_chunks",
            {
                "query_embedding": embedding,
                "match_threshold": 0.3,
                "match_count": top_k,
            },
        ).execute()
        return result.data or []
    except Exception as e:
        logger.error("Vector search failed: %s", e)
        return []


async def answer_with_rag(query: str, top_k: int = 5) -> tuple[str, list[dict]]:
    chunks = await search_chunks(query, top_k=top_k)
    if not chunks:
        return (
            "I couldn't find relevant policy or process documents for that question. Try rephrasing or ask your HR team.",
            [],
        )

    context = "\n\n---\n\n".join(
        f"[{i+1}] {c.get('content', '')}" for i, c in enumerate(chunks)
    )
    sources = [
        {"index": i + 1, "content": (c.get("content") or "")[:200]}
        for i, c in enumerate(chunks)
    ]

    try:
        client = _get_openai()
        system = """You answer questions using only the provided context from internal policy/process documents.
Cite sources by number, e.g. [1], [2]. If the context doesn't contain the answer, say so briefly.
Keep answers concise and practical for employees."""

        r = await client.chat.completions.create(
            model=OPENAI_CHAT_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query}"},
            ],
            max_tokens=500,
        )
        answer = (r.choices[0].message.content or "").strip()
        return answer, sources
    except Exception as e:
        logger.error("RAG answer generation failed: %s", e)
        return "Sorry, I'm having trouble generating an answer right now. Please try again.", sources


async def store_question_and_feedback(
    query: str, answer_text: str | None, sources_json: list | None
) -> str:
    try:
        sb = get_supabase()
        row = (
            sb.table("questions")
            .insert(
                {
                    "query": query,
                    "answer_text": answer_text,
                    "sources_json": sources_json or [],
                }
            )
            .execute()
        )
        if row.data and len(row.data) > 0:
            return str(row.data[0]["id"])
    except Exception as e:
        logger.error("Failed to store question: %s", e)
    return ""


async def add_feedback(question_id: str, helpful: bool) -> None:
    try:
        get_supabase().table("feedback").insert(
            {"question_id": question_id, "helpful": helpful}
        ).execute()
    except Exception as e:
        logger.error("Failed to store feedback: %s", e)


def chunk_text(text: str, max_chars: int = 800) -> list[str]:
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    for p in paragraphs:
        if current_len + len(p) > max_chars and current:
            chunks.append("\n\n".join(current))
            current = [p]
            current_len = len(p)
        else:
            current.append(p)
            current_len += len(p)
    if current:
        chunks.append("\n\n".join(current))
    return chunks if chunks else [text[:max_chars]]


async def ingest_document(title: str, content: str, source_url: str | None = None) -> str:
    try:
        sb = get_supabase()
        doc = (
            sb.table("documents")
            .insert({"title": title, "content": content, "source_url": source_url})
            .execute()
        )
        if not doc.data or len(doc.data) == 0:
            return ""
        document_id = str(doc.data[0]["id"])
        chunks = chunk_text(content)
        for i, chunk in enumerate(chunks):
            embedding = await get_embedding(chunk)
            sb.table("document_chunks").insert(
                {
                    "document_id": document_id,
                    "content": chunk,
                    "embedding": embedding,
                    "chunk_index": i,
                }
            ).execute()
        return document_id
    except Exception as e:
        logger.error("Document ingestion failed: %s", e)
        return ""
