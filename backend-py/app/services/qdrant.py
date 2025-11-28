from functools import lru_cache

from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchValue

from app.config import settings


@lru_cache(maxsize=1)
def get_qdrant_client():
    """Get Qdrant client (cached)"""
    if settings.qdrant_api_key:
        return QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)
    return QdrantClient(url=settings.qdrant_url)


def search_qdrant(query_vector: list[float], partido_filter: str | None = None, limit: int = 5):
    """Search for relevant chunks in Qdrant"""
    client = get_qdrant_client()

    search_params = {
        "collection_name": settings.qdrant_collection,
        "query": query_vector,
        "limit": limit,
    }

    # Add partido filter if specified
    if partido_filter:
        search_params["query_filter"] = Filter(
            must=[FieldCondition(key="partido", match=MatchValue(value=partido_filter))]
        )

    results = client.query_points(**search_params)
    return results.points
