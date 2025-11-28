from functools import lru_cache

from sentence_transformers import SentenceTransformer

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


@lru_cache(maxsize=1)
def get_embedding_model():
    """Load embedding model (cached)"""
    return SentenceTransformer(MODEL_NAME)


def generate_embedding(text: str) -> list[float]:
    """Generate embedding for text"""
    model = get_embedding_model()
    embedding = model.encode([text], show_progress_bar=False)[0]
    return embedding.tolist()
