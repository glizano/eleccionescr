import os
import hashlib

import uuid
from pathlib import Path
from pypdf import PdfReader
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct, Filter, FieldCondition, MatchValue
from sentence_transformers import SentenceTransformer

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", None)
COLLECTION = os.getenv("QDRANT_COLLECTION", "planes_gobierno")
DATA_DIR = Path(os.getenv("DATA_DIR", "data/raw"))

# Embedding model (local small)
EMBED_MODEL = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
VECTOR_DIM = EMBED_MODEL.get_sentence_embedding_dimension()

# ---------- Helpers ----------
def sha256_file(path: Path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()

def read_pdf_text(path: Path):
    # Intenta extracción directa con pypdf
    try:
        reader = PdfReader(str(path))
        pages = []
        for p in reader.pages:
            text = p.extract_text()
            if text:
                pages.append(text)
        text = "\n".join(pages).strip()
        if text:
            return text
    except Exception as e:
        print("pypdf err:", e)

def chunk_text_words(text, chunk_size=500, overlap=50):
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk = words[i:i+chunk_size]
        chunks.append(" ".join(chunk))
        i += chunk_size - overlap
    return chunks

# ---------- Qdrant client ----------
def init_qdrant():
    if QDRANT_API_KEY:
        qc = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    else:
        qc = QdrantClient(url=QDRANT_URL)
    # crear coleccion si no existe
    try:
        collections = [c.name for c in qc.get_collections().collections]
    except Exception:
        collections = []
    if COLLECTION not in collections:
        qc.create_collection(
            collection_name=COLLECTION,
            vectors_config=VectorParams(size=VECTOR_DIM, distance=Distance.COSINE)
        )
        print("Created collection", COLLECTION)
    return qc

# ---------- Upsert document (delete old + insert new) ----------
def delete_doc_points(qc: QdrantClient, doc_id: str):
    try:
        qc.delete(
            collection_name=COLLECTION,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="doc_id",
                        match=MatchValue(value=doc_id)
                    )
                ]
            )
        )
        print("Deleted previous points for", doc_id)
    except Exception as e:
        print("Delete error:", e)

def upsert_chunks(qc: QdrantClient, chunks, doc_id, filename, partido, file_hash):
    embeddings = EMBED_MODEL.encode(chunks, show_progress_bar=False)
    points = []
    for i, (chunk, vec) in enumerate(zip(chunks, embeddings)):
        pid = str(uuid.uuid4())
        payload = {
            "text": chunk,
            "doc_id": doc_id,
            "filename": filename,
            "partido": partido,
            "chunk_index": i,
            "file_hash": file_hash
        }
        points.append(PointStruct(id=pid, vector=vec.tolist(), payload=payload))
    # upsert in batches
    BATCH = 64
    for i in range(0, len(points), BATCH):
        batch = points[i:i+BATCH]
        qc.upsert(collection_name=COLLECTION, points=batch)

# ---------- Main ingestion flow ----------
def process_file(qc, path: Path, partido: str):
    file_hash = sha256_file(path)
    doc_id = path.stem  # use filename without extension

    # Check if doc exists in Qdrant with same hash
    try:
        result, _ = qc.scroll(
            collection_name=COLLECTION,
            scroll_filter=Filter(
                must=[
                    FieldCondition(key="doc_id", match=MatchValue(value=doc_id))
                ]
            ),
            limit=1,
            with_payload=True
        )
        if result:
            existing_hash = result[0].payload.get("file_hash")
            if existing_hash == file_hash:
                print(f"SKIP {path.name} (no changes)")
                return False
            print(f"Updating {path.name}...")
    except Exception as e:
        print(f"Error checking status for {path.name}: {e}")

    text = read_pdf_text(path)
    if not text or len(text) < 100:
        print("No usable text for", path.name)
        return False

    chunks = chunk_text_words(text, chunk_size=600, overlap=100)
    print(f"{path.name} -> {len(chunks)} chunks")

    # delete old points for this doc_id
    delete_doc_points(qc, doc_id)

    # upsert new chunks
    upsert_chunks(qc, chunks, doc_id, path.name, partido, file_hash)


    print("Ingested", path.name)
    return True

def ingest():
    qc = init_qdrant()

    # Define files and mapping to partido (you should adapt this list)
    # Auto-scan folder and use filename stem as party name
    mapping = []
    for p in DATA_DIR.glob("*.pdf"):
        # Map known filenames to full names if desired, else use stem
        stem = p.stem
        # Simple heuristic or lookup could go here
        mapping.append((p.name, stem))

    for fname, partido in mapping:
        p = DATA_DIR / fname
        if not p.exists():
            print("Missing file", p)
            continue
        process_file(qc, p, partido)

    print("Done.")
