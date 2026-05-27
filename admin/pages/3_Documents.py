import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
import streamlit as st

# Apply custom theme immediately to prevent layout pop/flicker
from admin.theme import apply_custom_theme
apply_custom_theme()

import requests
import pandas as pd
from datetime import datetime
from requests.auth import HTTPBasicAuth

# Enforce authentication
if "authentication_status" not in st.session_state or not st.session_state["authentication_status"]:
    st.error("Please login from the main page first.")
    st.stop()

st.title("📄 Document Manager (ChromaDB)")

DOCS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "documents")
os.makedirs(DOCS_DIR, exist_ok=True)

# Helper function to list files
def get_documents_list():
    files = []
    for f in os.listdir(DOCS_DIR):
        if f.endswith(".txt") or f.endswith(".pdf"):
            fp = os.path.join(DOCS_DIR, f)
            stat = os.stat(fp)
            files.append({
                "filename": f,
                "size_kb": round(stat.st_size / 1024, 2),
                "date_added": datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
            })
    return files

# Trigger full re-ingestion HTTP request
def trigger_ingest():
    try:
        # Use default basic credentials config
        admin_user = os.environ.get("ADMIN_USERNAME", "admin")
        # For security, we assume the password 'admin' is configured as the default
        r = requests.post(
            "http://127.0.0.1:8000/admin/documents/ingest",
            auth=HTTPBasicAuth(admin_user, "admin"),
            timeout=30
        )
        if r.status_code == 200:
            st.success(f"Ingestion successful! Ingested {r.json().get('document_count', 0)} chunks.")
        else:
            st.error(f"Ingestion failed with status code {r.status_code}: {r.text}")
    except Exception as e:
        st.error(f"Failed to connect to the backend API: {e}")

# --- SECTION A: CURRENT DOCUMENTS ---
st.write("### 📂 Ingested Documents")
docs = get_documents_list()

if not docs:
    st.info("No documents found in the data/documents/ directory.")
else:
    df_docs = pd.DataFrame(docs)
    st.dataframe(df_docs, use_container_width=True, hide_index=True)
    
    # Action per file
    for doc in docs:
        filename = doc["filename"]
        col1, col2, col3 = st.columns([6, 1.5, 1.5])
        with col1:
            st.write(f"📄 **{filename}** ({doc['size_kb']} KB)")
        with col2:
            if st.button("Preview", key=f"prev_{filename}"):
                file_path = os.path.join(DOCS_DIR, filename)
                if filename.endswith(".txt"):
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as pf:
                        st.text_area("First 500 characters:", value=pf.read()[:500], height=150)
                else:
                    st.info("PDF preview not supported in text box. Download it to view.")
        with col3:
            if st.button("Remove", key=f"rem_{filename}", type="primary"):
                file_path = os.path.join(DOCS_DIR, filename)
                os.remove(file_path)
                st.warning(f"Removed {filename}. Re-indexing ChromaDB...")
                trigger_ingest()
                st.rerun()

# --- SECTION B: ADD NEW DOCUMENT ---
st.write("### 📤 Upload New Document")
uploaded_file = st.file_uploader("Upload a scheme document (.txt or .pdf)", type=["txt", "pdf"])

if uploaded_file is not None:
    # Save the file
    save_path = os.path.join(DOCS_DIR, uploaded_file.name)
    with open(save_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    st.success(f"Saved {uploaded_file.name} to data/documents/.")
    
    if st.button("Ingest into ChromaDB"):
        with st.spinner("Ingesting and indexing..."):
            trigger_ingest()
        st.rerun()

# --- SECTION C: CHROMADB STATUS ---
st.write("### 📡 ChromaDB Status")
try:
    import sys
    import importlib
    if 'app.knowledge_base' in sys.modules:
        try:
            importlib.reload(sys.modules['app.knowledge_base'])
        except Exception:
            pass
    from app.knowledge_base import get_collection
    collection_ref = get_collection()
    if collection_ref is not None:
        chunk_count = collection_ref.count()
        st.info(f"**Collection Name:** `bihar_msme_schemes`  \n**Total active chunks:** `{chunk_count}`  \n**Embeddings Model:** `Default ChromaDB Sentence-Transformers` ")
    else:
        st.warning("Could not retrieve ChromaDB collection. It might be offline or uninitialized.")
except Exception as e:
    st.error(f"Could not connect to ChromaDB: {e}")

if st.button("Full Re-ingest All Documents"):
    # Confirmation dialog
    st.warning("Are you sure? This will clear the vector store collection and re-index all files.")
    if st.checkbox("Yes, clear and re-ingest all"):
        with st.spinner("Re-indexing..."):
            trigger_ingest()
        st.rerun()
