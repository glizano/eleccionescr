import os
import hashlib
import logging
import re
import uuid
from pathlib import Path

from langchain_core.embeddings import Embeddings
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import OpenAIEmbeddings
from pypdf import PdfReader
import pdfplumber
from qdrant_client import QdrantClient
from qdrant_client.models import (
    VectorParams,
    Distance,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    PayloadSchemaType,
)

logger = logging.getLogger(__name__)

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", None)
COLLECTION = os.getenv("QDRANT_COLLECTION", "planes_gobierno")
DATA_DIR = Path(os.getenv("DATA_DIR", "data/raw"))
RECREATE_COLLECTION = os.getenv("RECREATE_COLLECTION", "false").lower() == "true"

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

def is_text_corrupted(text: str, threshold: float = 0.3) -> bool:
    """Detect if text has too many corrupted/non-printable characters.
    
    Args:
        text: Text to validate
        threshold: Max ratio of corrupted chars allowed (default 30%)
    
    Returns:
        True if text appears corrupted
    """
    if not text or len(text) < 20:
        return True
    
    # Count non-ASCII printable characters (excluding common Spanish chars)
    corrupted_chars = 0
    valid_spanish = set('áéíóúñÁÉÍÓÚÑüÜ¿¡')
    
    for char in text:
        # Allow: alphanumeric, whitespace, punctuation, valid Spanish chars
        if not (char.isalnum() or char.isspace() or 
                char in '.,;:!?()[]{}"\'-/\n\r' or 
                char in valid_spanish):
            # Check if it's a weird Unicode character
            if ord(char) > 127 and char not in valid_spanish:
                corrupted_chars += 1
    
    corruption_ratio = corrupted_chars / len(text)
    return corruption_ratio > threshold

def clean_text(text: str) -> str:
    """Clean and normalize extracted text.
    
    Args:
        text: Raw text from PDF
    
    Returns:
        Cleaned text
    """
    if not text:
        return ""
    
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove null bytes and other control characters
    text = text.replace('\x00', '')
    
    # Fix common encoding issues (Spanish-specific)
    replacements = {
        'Ã¡': 'á', 'Ã©': 'é', 'Ã­': 'í', 'Ã³': 'ó', 'Ãº': 'ú',
        'Ã±': 'ñ', 'Ã': 'Ñ', 'Ã¼': 'ü',
    }
    for wrong, correct in replacements.items():
        text = text.replace(wrong, correct)
    
    return text.strip()

def read_pdf_text(path: Path) -> str | None:
    """Extract text from PDF using multiple strategies with validation.
    
    Tries multiple extraction methods in order:
    1. pdfplumber (best for text PDFs with good encoding)
    2. pypdf (fallback)
    3. pypdf with different encoding strategies
    
    Args:
        path: Path to PDF file
    
    Returns:
        Extracted text or None if all strategies fail
    """
    filename = path.name
    
    # Strategy 1: pdfplumber (handles encoding better)
    try:
        logger.info(f"[{filename}] Trying pdfplumber extraction...")
        with pdfplumber.open(path) as pdf:
            pages = []
            for i, page in enumerate(pdf.pages):
                text = page.extract_text()
                if text:
                    pages.append(text)
            
            if pages:
                full_text = "\n".join(pages)
                full_text = clean_text(full_text)
                
                # Validate text quality
                if is_text_corrupted(full_text):
                    logger.warning(f"[{filename}] pdfplumber: Text appears corrupted, trying next method...")
                else:
                    logger.info(f"[{filename}] ✓ pdfplumber: Extracted {len(full_text)} chars, {len(pages)} pages")
                    return full_text
    except Exception as e:
        logger.warning(f"[{filename}] pdfplumber failed: {e}")
    
    # Strategy 2: pypdf standard
    try:
        logger.info(f"[{filename}] Trying pypdf standard extraction...")
        reader = PdfReader(str(path))
        pages = []
        for p in reader.pages:
            text = p.extract_text()
            if text:
                pages.append(text)
        
        if pages:
            full_text = "\n".join(pages)
            full_text = clean_text(full_text)
            
            if is_text_corrupted(full_text):
                logger.warning(f"[{filename}] pypdf: Text appears corrupted, trying next method...")
            else:
                logger.info(f"[{filename}] ✓ pypdf: Extracted {len(full_text)} chars, {len(pages)} pages")
                return full_text
    except Exception as e:
        logger.warning(f"[{filename}] pypdf failed: {e}")
    
    # Strategy 3: pypdf with layout mode
    try:
        logger.info(f"[{filename}] Trying pypdf with layout mode...")
        reader = PdfReader(str(path))
        pages = []
        for p in reader.pages:
            # Try extracting with layout preservation
            text = p.extract_text(extraction_mode="layout")
            if text:
                pages.append(text)
        
        if pages:
            full_text = "\n".join(pages)
            full_text = clean_text(full_text)
            
            if not is_text_corrupted(full_text):
                logger.info(f"[{filename}] ✓ pypdf layout: Extracted {len(full_text)} chars")
                return full_text
            else:
                logger.error(f"[{filename}] ✗ All strategies produced corrupted text")
    except Exception as e:
        logger.warning(f"[{filename}] pypdf layout mode failed: {e}")
    
    logger.error(f"[{filename}] ✗ ALL EXTRACTION STRATEGIES FAILED")
    return None

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
    
    # Get existing collections
    try:
        collections = [c.name for c in qc.get_collections().collections]
    except Exception:
        collections = []
    
    # Handle recreate mode
    if RECREATE_COLLECTION and COLLECTION in collections:
        logger.warning(f"🔄 RECREATE MODE: Deleting existing collection '{COLLECTION}'...")
        try:
            qc.delete_collection(collection_name=COLLECTION)
            logger.info(f"✅ Deleted collection '{COLLECTION}'")
            collections.remove(COLLECTION)
        except Exception as e:
            logger.error(f"❌ Failed to delete collection: {e}")
            raise
    
    # Create collection if it doesn't exist
    if COLLECTION not in collections:
        logger.info(f"📦 Creating collection '{COLLECTION}'...")
        qc.create_collection(
            collection_name=COLLECTION,
            vectors_config=VectorParams(size=get_vector_dimension(), distance=Distance.COSINE)
        )
        logger.info(f"✅ Created collection '{COLLECTION}'")
        
        # Create payload indexes for filtering
        qc.create_payload_index(
            collection_name=COLLECTION,
            field_name="doc_id",
            field_schema=PayloadSchemaType.KEYWORD
        )
        qc.create_payload_index(
            collection_name=COLLECTION,
            field_name="partido",
            field_schema=PayloadSchemaType.KEYWORD
        )
        logger.info(f"✅ Created payload indexes for doc_id and partido")
    else:
        # If collection exists, ensure indexes are created (for existing collections)
        logger.info(f"📦 Using existing collection '{COLLECTION}'")
        try:
            qc.create_payload_index(
                collection_name=COLLECTION,
                field_name="doc_id",
                field_schema=PayloadSchemaType.KEYWORD
            )
        except Exception as e:
            # Index might already exist, that's ok
            if "already exists" not in str(e).lower():
                logger.warning(f"Note: Could not create doc_id index: {e}")
        
        try:
            qc.create_payload_index(
                collection_name=COLLECTION,
                field_name="partido",
                field_schema=PayloadSchemaType.KEYWORD
            )
        except Exception as e:
            # Index might already exist, that's ok
            if "already exists" not in str(e).lower():
                logger.warning(f"Note: Could not create partido index: {e}")
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
        logger.error(f"[{path.name}] ✗ No usable text extracted (length: {len(text) if text else 0})")
        return False
    
    # Final validation after extraction
    if is_text_corrupted(text, threshold=0.2):
        logger.error(f"[{path.name}] ✗ CRITICAL: Extracted text is corrupted. Manual review required!")
        logger.error(f"[{path.name}] Text preview: {text[:300]}")
        # Still process but log warning
        print(f"\n⚠️  WARNING: {path.name} has corrupted text. Results will be poor!\n")
    
    # Log text quality metrics
    avg_word_len = sum(len(w) for w in text.split()) / max(len(text.split()), 1)
    logger.info(f"[{path.name}] Text quality: {len(text)} chars, {len(text.split())} words, avg word len: {avg_word_len:.1f}")

    chunks = chunk_text_words(text, chunk_size=600, overlap=100)
    logger.info(f"[{path.name}] Created {len(chunks)} chunks")

    # delete old points for this doc_id
    delete_doc_points(qc, doc_id)

    # upsert new chunks
    upsert_chunks(qc, chunks, doc_id, path.name, partido, file_hash)


    print("Ingested", path.name)
    return True

def ingest():
    # Log mode info
    if RECREATE_COLLECTION:
        logger.warning("🔄 RECREATE MODE ENABLED: Will delete and recreate collection from scratch")
    else:
        logger.info("📝 Incremental mode: Will update only changed files")
    
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
            logger.error(f"Missing file: {p}")
            continue
        process_file(qc, p, partido)

    logger.info("✅ Ingestion completed successfully!")
