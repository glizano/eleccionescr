import os
import hashlib
import logging
from abc import ABC, abstractmethod

import uuid
from pathlib import Path
from pypdf import PdfReader
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct, Filter, FieldCondition, MatchValue

logger = logging.getLogger(__name__)

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", None)
COLLECTION = os.getenv("QDRANT_COLLECTION", "planes_gobierno")
DATA_DIR = Path(os.getenv("DATA_DIR", "data/raw"))

# Embedding configuration
EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "sentence_transformers")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")


# ---------- Embedding Providers ----------
class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers"""

    @abstractmethod
    def get_embedding_dimension(self) -> int:
        """Return the dimension of the embedding vectors"""
        pass

    @abstractmethod
    def encode(self, texts: list[str]) -> list[list[float]]:
        """Encode a list of texts into embeddings"""
        pass


class SentenceTransformersProvider(EmbeddingProvider):
    """Embedding provider using sentence-transformers library"""

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        from sentence_transformers import SentenceTransformer

        self.model_name = model_name
        self.model = SentenceTransformer(model_name)
        logger.info(f"Loaded SentenceTransformers model: {model_name}")

    def get_embedding_dimension(self) -> int:
        return self.model.get_sentence_embedding_dimension()

    def encode(self, texts: list[str]) -> list[list[float]]:
        embeddings = self.model.encode(texts, show_progress_bar=False)
        return [embedding.tolist() for embedding in embeddings]


class OpenAIProvider(EmbeddingProvider):
    """Embedding provider using OpenAI API"""

    # Map of model names to their embedding dimensions
    MODEL_DIMENSIONS = {
        "text-embedding-3-small": 1536,
        "text-embedding-3-large": 3072,
        "text-embedding-ada-002": 1536,
    }

    def __init__(self, model_name: str = "text-embedding-3-small", api_key: str | None = None):
        from openai import OpenAI

        self.model_name = model_name
        # Handle both None and empty string cases
        resolved_api_key = api_key if api_key else OPENAI_API_KEY
        if not resolved_api_key:
            raise ValueError("OpenAI API key is required for OpenAI embedding provider")
        self.client = OpenAI(api_key=resolved_api_key)
        logger.info(f"Initialized OpenAI embedding provider with model: {model_name}")

    def get_embedding_dimension(self) -> int:
        return self.MODEL_DIMENSIONS.get(self.model_name, 1536)

    def encode(self, texts: list[str]) -> list[list[float]]:
        # OpenAI recommends replacing newlines for better results
        cleaned_texts = [text.replace("\n", " ") for text in texts]
        response = self.client.embeddings.create(input=cleaned_texts, model=self.model_name)
        return [data.embedding for data in response.data]


# Lazy initialization for embedding provider
_embed_provider = None
_vector_dim = None


def get_embedding_provider() -> EmbeddingProvider:
    """Get the configured embedding provider (lazy initialization)"""
    global _embed_provider
    if _embed_provider is not None:
        return _embed_provider

    model_name = EMBEDDING_MODEL

    if EMBEDDING_PROVIDER == "openai":
        # For OpenAI, use a default model if no specific model is configured
        # or the configured model doesn't match OpenAI format
        if model_name.startswith("sentence-transformers/"):
            model_name = "text-embedding-3-small"
        _embed_provider = OpenAIProvider(model_name=model_name)
    else:
        # Default to sentence-transformers
        _embed_provider = SentenceTransformersProvider(model_name=model_name)

    return _embed_provider


def get_vector_dimension() -> int:
    """Get the vector dimension for the configured embedding provider"""
    global _vector_dim
    if _vector_dim is not None:
        return _vector_dim
    _vector_dim = get_embedding_provider().get_embedding_dimension()
    return _vector_dim

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
    embeddings = provider.encode(chunks)
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
