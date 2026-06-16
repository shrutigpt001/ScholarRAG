from dotenv import load_dotenv
load_dotenv()

import os
import io
import anthropic
import pdfplumber
from langchain_huggingface import HuggingFaceEmbeddings
from qdrant_client import QdrantClient

QDRANT_PATH = os.path.join(os.path.dirname(__file__), "..", "qdrant_local", "qdrant_local")
COLLECTION  = "papers"
MODEL_NAME  = "all-MiniLM-L6-v2"

SYSTEM_PROMPT = """You are ScholarRAG, an expert AI research assistant with deep knowledge of academic literature.

When answering questions, always:
- Start with a clear, direct answer in 1-2 sentences
- Use **bold** for key terms and concepts
- Use bullet points or numbered lists for multiple findings or steps
- Cite papers inline using the format: *Paper Title (Year)*
- End with a brief "**Key Takeaway**" summarizing the main insight

Keep responses focused and professional. Do not repeat the question. Do not use unnecessary filler phrases."""

_embeddings = None
_qdrant     = None
_client     = None

_memories: dict[str, list] = {}


def init():
    global _embeddings, _qdrant, _client

    _embeddings = HuggingFaceEmbeddings(model_name=MODEL_NAME)
    _qdrant     = QdrantClient(path=QDRANT_PATH)
    _client     = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


def _extract_pdf_text(pdf_bytes: bytes) -> str:
    text_parts = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                text_parts.append(t)
    return "\n\n".join(text_parts)


def _search(query_text: str, k: int = 5):
    vector = _embeddings.embed_query(query_text)
    return _qdrant.query_points(
        collection_name=COLLECTION,
        query=vector,
        limit=k,
    ).points


def _get_memory(session_id: str) -> list:
    if session_id not in _memories:
        _memories[session_id] = []
    return _memories[session_id]


def clear_memory(session_id: str):
    if session_id in _memories:
        del _memories[session_id]


def _github_links(payload: dict) -> list[str]:
    repos = payload.get("github_repos", [])
    if repos and isinstance(repos, list):
        return [r["url"] if isinstance(r, dict) else r for r in repos if r]
    single = payload.get("repo_url", "")
    return [single] if single else []


def _classify_query(question: str) -> str:
    resp = _client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=10,
        messages=[{
            "role": "user",
            "content": (
                f"Classify this query as exactly one word — either 'research' or 'conversational'.\n\n"
                f"- 'research': asks about papers, topics, concepts, code, authors, findings\n"
                f"- 'conversational': greetings, meta-questions about the assistant, thanks, small talk\n\n"
                f"Query: {question}\n\nAnswer:"
            ),
        }],
    )
    label = resp.content[0].text.strip().lower()
    return "research" if "research" in label else "conversational"


def query_rag(question: str, session_id: str, pdf_bytes: bytes = None) -> dict:
    history = _get_memory(session_id)
    intent  = _classify_query(question)
    sources = []

    if intent == "research":
        pdf_text     = _extract_pdf_text(pdf_bytes) if pdf_bytes else None
        search_query = f"{question} {pdf_text[:1500]}" if pdf_text else question

        SCORE_THRESHOLD = 0.30

        candidates = _search(search_query, k=10)
        filtered   = [r for r in candidates if r.score >= SCORE_THRESHOLD]
        filtered.sort(key=lambda r: (not bool(_github_links(r.payload)), -r.score))
        results      = filtered[:5]
        context_hits = results[:2]

        context_parts = []
        for r in context_hits:
            p     = r.payload
            lines = [f"Title: {p.get('title', '')}"]
            year  = (p.get("published") or "")[:4]
            if year:
                lines.append(f"Year: {year}")
            lines.append(f"Abstract: {p.get('summary', '')}")
            github = _github_links(p)
            if github:
                lines.append(f"Implementation (GitHub): {', '.join(github)}")
            context_parts.append("\n".join(lines))

        top_with_code = next((r for r in results if _github_links(r.payload)), None)
        code_note = ""
        if top_with_code:
            p     = top_with_code.payload
            repos = _github_links(p)
            code_note = (
                f"\n\nBest paper with code: \"{p.get('title', '')}\" — "
                f"GitHub: {', '.join(repos)}"
                f"\nAlways mention this implementation link explicitly in your answer."
            )

        qdrant_context = "\n\n---\n\n".join(context_parts) + code_note

        if pdf_text:
            user_msg = (
                f"The user has uploaded a PDF. Here is its full text:\n\n{pdf_text}\n\n"
                f"---\n\nHere are similar papers from the knowledge base:\n{qdrant_context}\n\n"
                f"Question: {question}"
            )
        else:
            user_msg = f"Context from research papers:\n{qdrant_context}\n\nQuestion: {question}"

        for r in results:
            p = r.payload
            sources.append({
                "title":           p.get("title", ""),
                "arxiv_id":        p.get("arxiv_id", ""),
                "authors":         p.get("authors", []),
                "published":       p.get("published", ""),
                "pdf_url":         p.get("pdf_url", ""),
                "category":        p.get("category", ""),
                "summary":         (p.get("summary", "")[:200] + "...") if p.get("summary") else "",
                "github_repos":    _github_links(p),
                "has_code":        len(_github_links(p)) > 0,
                "citations":       p.get("citations", 0),
                "score":           round(r.score, 3),
                "journal":         p.get("journal", ""),
                "doi":             p.get("doi", ""),
                "fields_of_study": p.get("fields_of_study", []),
            })
    else:
        user_msg = question

    messages = list(history)
    messages.append({"role": "user", "content": user_msg})

    response = _client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
        messages=messages,
    )

    answer = response.content[0].text

    history.append({"role": "user",      "content": question})
    history.append({"role": "assistant", "content": answer})

    return {"answer": answer, "sources": sources}
