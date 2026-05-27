# ============================================================================
# MSME Saathi — In-Memory Knowledge Base (RAG)
# ============================================================================
# Connects to the local ChromaDB vector store to fetch state-specific
# schemes (e.g. Bihar MSME schemes).
# ============================================================================

import os
import chromadb
from typing import List

# Connect to the local ChromaDB
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "chroma_db")

try:
    client = chromadb.PersistentClient(path=DB_PATH)
    HAS_DB = True
except Exception as e:
    print(f"Warning: Could not connect to ChromaDB at {DB_PATH}: {e}")
    HAS_DB = False


def get_collection():
    """
    Dynamically retrieve or create the ChromaDB collection.
    This avoids stale references when the collection is recreated.
    """
    if not HAS_DB:
        return None
    try:
        return client.get_or_create_collection(name="bihar_msme_schemes")
    except Exception as e:
        print(f"Error fetching/creating ChromaDB collection: {e}")
        return None


def retrieve_context(query: str, k: int = 3) -> str:
    """
    Retrieve the top-k most relevant knowledge base entries for a query
    using ChromaDB's semantic vector search.
    
    Args:
        query: The user's message (English, Hindi, or Hinglish)
        k: Number of top results to return
        
    Returns:
        Formatted context string for injection into the LLM prompt.
    """
    if not HAS_DB:
        return "System Warning: RAG Database is currently offline. Please refer to general knowledge or escalate."

    try:
        collection_ref = get_collection()
        if collection_ref is None:
            return ""

        # Perform semantic search
        results = collection_ref.query(
            query_texts=[query],
            n_results=k
        )
        
        if not results['documents'] or len(results['documents'][0]) == 0:
            return ""
            
        # Format the context
        context_parts = []
        for i, doc in enumerate(results['documents'][0]):
            context_parts.append(f"[Document {i+1}]\n{doc}")
            
        return "\n\n---\n\n".join(context_parts)

    except Exception as e:
        print(f"RAG Retrieval Error: {e}")
        return ""

