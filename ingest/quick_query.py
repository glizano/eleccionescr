# quick_query.py
import os
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

EMBED_MODEL = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
VECTOR_DIM = EMBED_MODEL.get_sentence_embedding_dimension()

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
qc = QdrantClient(url=QDRANT_URL)

query = "que propuestas incluye el plan de gobierno del PLP?"
query_vec = EMBED_MODEL.encode([query], show_progress_bar=False)[0]
resp = qc.query_points(collection_name="planes_gobierno", query=query_vec, limit=5)
print([p.payload for p in resp.points])
