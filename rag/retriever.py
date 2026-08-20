"""
rag/retriever.py — CrisisPredictor
Chunks crisis_causal_chain.md by factor headers, builds a FAISS index,
and exposes a retrieval function used by the LLM scoring node.
Matches GoldBot's rag/retriever.py pattern.
"""

import os
import re
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from dotenv import load_dotenv

load_dotenv()

RAG_DOC_PATH = os.path.join(os.path.dirname(__file__), "crisis_causal_chain.md")
INDEX_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "faiss_index")

embeddings = OpenAIEmbeddings(model="text-embedding-3-small")


def chunk_by_factor(md_text: str) -> list[Document]:
    """Split the causal chain doc into one chunk per '## FACTOR:' section."""
    sections = re.split(r"(?=^## FACTOR:)", md_text, flags=re.MULTILINE)
    docs = []
    for section in sections:
        section = section.strip()
        if not section.startswith("## FACTOR:"):
            continue
        title_match = re.match(r"## FACTOR:\s*(.+)", section)
        factor_name = title_match.group(1).strip() if title_match else "Unknown"
        docs.append(Document(page_content=section, metadata={"factor": factor_name}))
    return docs


def build_index(force_rebuild: bool = False):
    """Build (or load cached) FAISS index from the causal chain document."""
    if not force_rebuild and os.path.exists(os.path.join(INDEX_DIR, "index.faiss")):
        return FAISS.load_local(INDEX_DIR, embeddings, allow_dangerous_deserialization=True)

    with open(RAG_DOC_PATH, "r", encoding="utf-8") as f:
        md_text = f.read()

    docs = chunk_by_factor(md_text)
    print(f"Chunked into {len(docs)} factor sections")

    vectorstore = FAISS.from_documents(docs, embeddings)
    os.makedirs(INDEX_DIR, exist_ok=True)
    vectorstore.save_local(INDEX_DIR)
    return vectorstore


_vectorstore = None


def get_vectorstore():
    global _vectorstore
    if _vectorstore is None:
        _vectorstore = build_index()
    return _vectorstore


def retrieve_factor_context(factor_query: str, k: int = 1) -> str:
    """Retrieve the most relevant factor section(s) for a given factor name/query."""
    vs = get_vectorstore()
    results = vs.similarity_search(factor_query, k=k)
    return "\n\n".join(doc.page_content for doc in results)


if __name__ == "__main__":
    # Build index and test retrieval
    vs = build_index(force_rebuild=True)
    print("\n--- Test retrieval: 'yield curve' ---")
    print(retrieve_factor_context("yield curve"))
    print("\n--- Test retrieval: 'geopolitical risk' ---")
    print(retrieve_factor_context("geopolitical risk"))