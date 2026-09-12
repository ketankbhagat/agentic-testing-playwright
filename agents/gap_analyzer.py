"""Node 1: RAG-powered gap analysis against knowledge base."""
import re

from langchain_text_splitters import RecursiveCharacterTextSplitter

from agents.llm import PROJECT_ROOT, get_llm, text_of

KNOWLEDGE_DIR = PROJECT_ROOT / "knowledge_base"
N_RESULTS = 8

_vectorstore = None
_chunks = None


def _load_chunks() -> list[tuple[str, str]]:
    """Split every knowledge_base/*.md file into (source, text) chunks."""
    global _chunks
    if _chunks is None:
        splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        _chunks = [
            (path.name, piece)
            for path in sorted(KNOWLEDGE_DIR.glob("*.md"))
            for piece in splitter.split_text(path.read_text(encoding="utf-8"))
        ]
    return _chunks


def _get_vectorstore():
    """Initialize an in-memory ChromaDB collection. Lazy singleton.

    Uses Chroma's built-in default embedding (all-MiniLM-L6-v2, local, no API key).
    """
    global _vectorstore
    if _vectorstore is not None:
        return _vectorstore

    import chromadb
    from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

    client = chromadb.EphemeralClient()
    collection = client.get_or_create_collection(
        "knowledge_base", embedding_function=DefaultEmbeddingFunction()
    )
    chunks = _load_chunks()
    collection.add(
        ids=[f"doc_{i}" for i in range(len(chunks))],
        documents=[text for _, text in chunks],
        metadatas=[{"source": source} for source, _ in chunks],
    )
    _vectorstore = collection
    return _vectorstore


def _keyword_search(query: str, n: int) -> list[str]:
    """Fallback retrieval when ChromaDB's native deps can't load."""
    terms = {t for t in re.findall(r"[a-z]+", query.lower()) if len(t) > 3} | {"missing"}
    ranked = sorted(_load_chunks(), key=lambda c: -sum(c[1].lower().count(t) for t in terms))
    return [f"[{source}]\n{text}" for source, text in ranked[:n]]


def retrieve(query: str, n: int = N_RESULTS) -> tuple[list[str], str]:
    """Return (documents, retrieval_method)."""
    try:
        results = _get_vectorstore().query(query_texts=[query], n_results=n)
        docs = results["documents"][0] if results["documents"] else []
        metas = results["metadatas"][0] if results["metadatas"] else [{}] * len(docs)
        return [f"[{m.get('source', '')}]\n{d}" for d, m in zip(docs, metas)], "chromadb"
    except Exception as e:  # e.g. Smart App Control blocking onnxruntime DLLs
        print(f"⚠️  ChromaDB unavailable ({type(e).__name__}: {e}) — using keyword retrieval")
        return _keyword_search(query, n), "keyword"


def analyze_gaps(state: dict) -> dict:
    """Search knowledge base for existing coverage, identify gaps."""
    requirement = state["requirement"]
    feedback = state.get("gap_feedback", "")
    retrieved_texts, method = retrieve(requirement)

    docs_block = "\n".join(f"--- Doc {i + 1} ---\n{t}" for i, t in enumerate(retrieved_texts))
    prompt = f"""You are a QA gap analyst for the Swag Labs e-commerce app (https://www.saucedemo.com/).

REQUIREMENT: {requirement}

EXISTING KNOWLEDGE BASE (JIRA tickets, schema, API docs, changelog):

{docs_block}

HUMAN FEEDBACK ON A PREVIOUS DRAFT (apply it if present): {feedback or "none"}

Produce a structured gap report:

1. **Existing Coverage**: What JIRA tickets and tests already exist for this flow?
2. **Gaps Found**: What is missing — untested scenarios, undocumented behaviors, edge cases?
3. **Recommended Fixes**: Concrete suggestions to close each gap.
4. **Risk Level**: HIGH / MEDIUM / LOW for each gap.

Be specific. Reference JIRA IDs where relevant. Focus on the login-to-checkout purchase flow.
Call out in particular: JIRA-204 has no end-to-end login-to-checkout test, JIRA-201 has no
locked_out_user test, and direct access to /inventory.html without a session is untested.
"""

    response = get_llm().invoke(prompt)

    return {
        "gap_analysis": text_of(response),
        "retrieved_docs": retrieved_texts,
        "current_node": "gap_analyzer",
        "status": "waiting_human",
        "event_log": state.get("event_log", []) + [
            {"node": "gap_analyzer", "event": "completed",
             "summary": f"Gap analysis ready for review ({len(retrieved_texts)} docs via {method})"}
        ],
    }
