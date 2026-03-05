"""ChromaDB synchronization for module documents.

Uses late-binding init() so the collection and embedding function
are injected from app2.py after creation, avoiding circular imports.
"""

import re
import logging

logger = logging.getLogger(__name__)

# Injected at startup via init()
_collection = None
_get_embedding = None


def init(collection, get_embedding_cached):
    """Call once at app startup to inject dependencies."""
    global _collection, _get_embedding
    _collection = collection
    _get_embedding = get_embedding_cached


def _sanitize_module_id(module_name: str) -> str:
    """Create a deterministic ChromaDB document ID from module name."""
    return "module_" + re.sub(r"[^a-zA-Z0-9]", "_", module_name.lower()).strip("_")


def sync_module_to_chromadb(module_name: str, code: str, description: str) -> None:
    """Add or update a module document in ChromaDB for semantic search.

    Raises on failure so callers can roll back SQLite transactions.
    """
    doc_id = _sanitize_module_id(module_name)
    doc_text = f"Module: {module_name}\nCode: {code}\nDescription: {description}"
    embedding = _get_embedding(doc_text)
    metadata = {
        "source": "Module Database",
        "source_type": "module",
        "module_name": module_name,
        "module_code": code,
        "chunk_index": 0,
    }
    _collection.upsert(
        ids=[doc_id],
        documents=[doc_text],
        embeddings=[embedding],
        metadatas=[metadata],
    )
    logger.info(f"Synced module '{module_name}' to ChromaDB (id={doc_id})")


def remove_module_from_chromadb(module_name: str) -> None:
    """Remove a module document from ChromaDB.

    Raises on failure so callers can roll back SQLite transactions.
    """
    doc_id = _sanitize_module_id(module_name)
    _collection.delete(ids=[doc_id])
    logger.info(f"Removed module '{module_name}' from ChromaDB (id={doc_id})")
