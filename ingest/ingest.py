import os
import hashlib
import logging
import uuid
from pathlib import Path

from langchain_core.embeddings import Embeddings
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import OpenAIEmbeddings
from pypdf import PdfReader
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct, Filter, FieldCondition, MatchValue

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", None)
COLLECTION = os.getenv("QDRANT_COLLECTION", "planes_gobierno")
DATA_DIR = Path(os.getenv("DATA_DIR", "data/raw"))

# Embedding configuration
EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "sentence_transformers")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")


# Lazy initialization for embedding provider
_embed_provider = None


def get_embedding_provider() -> Embeddings:
    """Get the configured embedding provider (lazy initialization).
    
    Returns:
        A LangChain Embeddings instance.
    """
    global _embed_provider
    if _embed_provider is not None:
        return _embed_provider

    model_name = EMBEDDING_MODEL

    if EMBEDDING_PROVIDER == "openai":
        # For OpenAI, use a default model if no specific model is configured
        if model_name.startswith("sentence-transformers/"):
            model_name = "text-embedding-3-small"
        if not OPENAI_API_KEY:
            raise ValueError("OpenAI API key is required for OpenAI embedding provider")
        _embed_provider = OpenAIEmbeddings(model=model_name, api_key=OPENAI_API_KEY)
        logger.info(f"Initialized OpenAI embeddings provider with model: {model_name}")
    else:
        # Default to HuggingFace (sentence-transformers)
        _embed_provider = HuggingFaceEmbeddings(model_name=model_name)
        logger.info(f"Initialized HuggingFace embeddings provider with model: {model_name}")

    return _embed_provider


def get_vector_dimension() -> int:
    """Get the vector dimension for the configured embedding provider.
    
    Returns:
        The dimension size of embedding vectors.
    """
    provider = get_embedding_provider()
    # Get dimension by encoding a dummy text
    test_embedding = provider.embed_query("test")
    return len(test_embedding)

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
            vectors_config=VectorParams(size=get_vector_dimension(), distance=Distance.COSINE)
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
    provider = get_embedding_provider()
    embeddings = provider.embed_documents(chunks)
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
        points.append(PointStruct(id=pid, vector=vec, payload=payload))
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
    """Main ingestion function that processes all PDFs in the data directory."""
    # Validate data directory exists
    if not DATA_DIR.exists():
        logger.error(f"Data directory does not exist: {DATA_DIR}")
        logger.info(f"Please create the directory and add PDF files: mkdir -p {DATA_DIR}")
        raise FileNotFoundError(f"Data directory not found: {DATA_DIR}")
    
    # Check for PDF files
    pdf_files = list(DATA_DIR.glob("*.pdf"))
    if not pdf_files:
        logger.warning(f"No PDF files found in {DATA_DIR}")
        logger.info("Please add PDF files to the data directory")
        return
    
    logger.info(f"Found {len(pdf_files)} PDF files to process")
    
    qc = init_qdrant()

    # Auto-scan folder and use filename stem as party name
    mapping = []
    for p in pdf_files:
        # Map known filenames to full names if desired, else use stem
        stem = p.stem
        # Simple heuristic or lookup could go here
        mapping.append((p.name, stem))

    processed = 0
    skipped = 0
    failed = 0

    for fname, partido in mapping:
        p = DATA_DIR / fname
        if not p.exists():
            logger.warning(f"Missing file: {p}")
            failed += 1
            continue
        try:
            result = process_file(qc, p, partido)
            if result:
                processed += 1
            else:
                skipped += 1
        except Exception as e:
            logger.error(f"Failed to process {fname}: {e}", exc_info=True)
            failed += 1

    logger.info("="*50)
    logger.info(f"Ingestion complete: {processed} processed, {skipped} skipped, {failed} failed")
    logger.info("="*50)
