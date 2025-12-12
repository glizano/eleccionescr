#!/usr/bin/env python3
"""
Script to verify quality of ingested chunks in Qdrant.
Uses intelligent sampling to avoid scanning all chunks in production.

Optimizations:
- Samples chunks per party (default 10 per party)
- Fast count estimation
- Configurable via environment variables
"""

import os
from collections import defaultdict
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", None)
COLLECTION = os.getenv("QDRANT_COLLECTION", "planes_gobierno")

# CI mode - fail on critical issues
CI_MODE = os.getenv("CI", "false").lower() == "true"

# Sampling configuration (environment variables)
# Set VERIFY_SAMPLE_SIZE to number of chunks per party to check
# Set VERIFY_FULL_SCAN=true to check all chunks (not recommended for production)
SAMPLE_SIZE = int(os.getenv("VERIFY_SAMPLE_SIZE", "10"))  # Chunks per party
FULL_SCAN = os.getenv("VERIFY_FULL_SCAN", "false").lower() == "true"


def is_text_corrupted(text: str, threshold: float = 0.3) -> bool:
    """Detect if text has too many corrupted/non-printable characters."""
    if not text or len(text) < 20:
        return True

    corrupted_chars = 0
    valid_spanish = set("áéíóúñÁÉÍÓÚÑüÜ¿¡")

    for char in text:
        if not (
            char.isalnum()
            or char.isspace()
            or char in ".,;:!?()[]{}\"'-/\n\r"
            or char in valid_spanish
        ):
            if ord(char) > 127 and char not in valid_spanish:
                corrupted_chars += 1

    corruption_ratio = corrupted_chars / len(text)
    return corruption_ratio > threshold


def analyze_chunk_quality(text: str) -> dict:
    """Analyze quality metrics for a text chunk."""
    words = text.split()

    return {
        "char_count": len(text),
        "word_count": len(words),
        "avg_word_len": sum(len(w) for w in words) / max(len(words), 1),
        "corrupted": is_text_corrupted(text, threshold=0.2),
        "corruption_ratio": sum(
            1 for c in text if ord(c) > 127 and c not in "áéíóúñÁÉÍÓÚÑüÜ¿¡"
        )
        / max(len(text), 1),
    }


def get_collection_info(client: QdrantClient) -> dict:
    """Get collection statistics without loading all points."""
    try:
        collection_info = client.get_collection(COLLECTION)
        return {"points_count": collection_info.points_count, "exists": True}
    except Exception:
        return {"points_count": 0, "exists": False}


def get_parties_list(client: QdrantClient) -> list[str]:
    """Get unique party names from collection (with sampling)."""
    parties = set()

    # Get up to first 1000 points to find all parties
    # This is a reasonable limit for most cases
    offset = None

    while len(parties) < 100:  # Safety limit
        result = client.scroll(
            collection_name=COLLECTION, limit=100, offset=offset, with_payload=True
        )

        points, offset = result

        if not points:
            break

        for point in points:
            partido = point.payload.get("partido", "Unknown")
            if partido:
                parties.add(partido)

        if not offset:
            break

    return sorted(list(parties))


def sample_chunks_per_party(
    client: QdrantClient, partido: str, sample_size: int
) -> list:
    """Get a sample of chunks from a specific party.

    Uses scroll with filter to efficiently sample chunks without loading all.
    """
    chunks = []
    offset = None
    chunk_count = 0

    while len(chunks) < sample_size:
        result = client.scroll(
            collection_name=COLLECTION,
            limit=100,
            offset=offset,
            scroll_filter=Filter(
                must=[FieldCondition(key="partido", match=MatchValue(value=partido))]
            ),
            with_payload=True,
        )

        points, offset = result

        if not points:
            break

        for point in points:
            if len(chunks) >= sample_size:
                break
            chunk_count += 1
            # Sample every Nth chunk to spread across the party's data
            if (
                chunk_count % max(1, chunk_count // sample_size) == 0
                or len(chunks) < sample_size
            ):
                text = point.payload.get("text", "")
                if text:
                    chunks.append(text)

        if not offset or len(chunks) >= sample_size:
            break

    return chunks


def main():
    print("🔍 Analyzing chunk quality in Qdrant...\n")

    # Connect to Qdrant
    if QDRANT_API_KEY:
        client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    else:
        client = QdrantClient(url=QDRANT_URL)

    # Check collection exists
    collection_info = get_collection_info(client)
    if not collection_info["exists"]:
        print(f"❌ Collection '{COLLECTION}' not found!")
        return 1

    total_chunks = collection_info["points_count"]
    print(f"📊 Collection info: {total_chunks:,} total chunks")

    if FULL_SCAN:
        print("⚠️  FULL SCAN MODE: Checking all chunks (slow for production!)\n")
    else:
        print(f"📌 SAMPLING MODE: Checking {SAMPLE_SIZE} chunks per party\n")
        print("💡 To scan all chunks, set VERIFY_FULL_SCAN=true\n")

    # Get unique parties
    print("Discovering parties...")
    parties = get_parties_list(client)
    print(f"Found {len(parties)} parties: {', '.join(parties)}\n")

    party_stats = defaultdict(
        lambda: {
            "total_chunks": 0,
            "sampled_chunks": 0,
            "corrupted_chunks": 0,
            "corruption_ratios": [],
        }
    )

    total_sampled = 0

    # Analyze samples
    for partido in parties:
        if FULL_SCAN:
            # Full scan mode - get all chunks (slow)
            chunks = []
            offset = None
            while True:
                result = client.scroll(
                    collection_name=COLLECTION,
                    limit=100,
                    offset=offset,
                    scroll_filter=Filter(
                        must=[
                            FieldCondition(
                                key="partido", match=MatchValue(value=partido)
                            )
                        ]
                    ),
                    with_payload=True,
                )

                points, offset = result
                if not points:
                    break

                for point in points:
                    text = point.payload.get("text", "")
                    if text:
                        chunks.append(text)

                if not offset:
                    break
        else:
            # Sample mode - get only sample_size chunks (fast)
            chunks = sample_chunks_per_party(client, partido, SAMPLE_SIZE)

        stats = party_stats[partido]
        stats["sampled_chunks"] = len(chunks)
        total_sampled += len(chunks)

        for text in chunks:
            metrics = analyze_chunk_quality(text)
            stats["corruption_ratios"].append(metrics["corruption_ratio"])

            if metrics["corrupted"]:
                stats["corrupted_chunks"] += 1

    print(f"✅ Analyzed {total_sampled} chunks from {len(parties)} parties")
    if not FULL_SCAN:
        print(
            f"   ({SAMPLE_SIZE} samples per party, ~{len(parties) * SAMPLE_SIZE} total)\n"
        )
    else:
        print("   (FULL SCAN)\n")

    print("=" * 90)
    print(
        f"{'PARTIDO':<10} {'TOTAL':<8} {'SAMPLED':<10} {'CORRUPTED':<12} {'AVG CORRUPT %':<15} {'STATUS':<10}"
    )
    print("=" * 90)

    # Sort by corruption rate (worst first)
    sorted_parties = sorted(
        party_stats.items(),
        key=lambda x: x[1]["corrupted_chunks"] / max(x[1]["sampled_chunks"], 1),
        reverse=True,
    )

    critical_parties = []

    for partido, stats in sorted_parties:
        sampled = stats["sampled_chunks"]
        corrupted = stats["corrupted_chunks"]
        corruption_pct = (corrupted / sampled * 100) if sampled > 0 else 0
        avg_corruption = (
            sum(stats["corruption_ratios"]) / len(stats["corruption_ratios"]) * 100
            if stats["corruption_ratios"]
            else 0
        )

        if corruption_pct > 50:
            status = "🔴 CRITICAL"
            critical_parties.append(partido)
        elif corruption_pct > 10:
            status = "🟡 WARNING"
        else:
            status = "🟢 OK"

        # Estimate total based on sample (if not full scan)
        total_estimate = (
            f"~{total_chunks // len(parties)}" if not FULL_SCAN else str(sampled)
        )

        print(
            f"{partido:<10} {total_estimate:<8} {sampled:<10} {corrupted:<12} {avg_corruption:<15.1f} {status:<10}"
        )

    print("=" * 90)

    if critical_parties:
        print(f"\n⚠️  CRITICAL ISSUES DETECTED in: {', '.join(critical_parties)}")
        print("\n📋 Recommended actions:")
        print(
            "1. Run FULL SCAN to confirm: VERIFY_FULL_SCAN=true python verify_quality.py"
        )
        print("2. Review the source PDFs for these parties")
        print("3. Try alternative PDF extraction tools (OCR if scanned)")
        print("4. Manually clean the PDFs or request better versions")
        print("5. Re-run ingestion after fixing: python main.py")

        # Show sample corrupted text
        if critical_parties:
            print(f"\n📄 Sample corrupted text from {critical_parties[0]}:")
            sample_chunks = sample_chunks_per_party(client, critical_parties[0], 1)
            if sample_chunks:
                for chunk in sample_chunks:
                    if is_text_corrupted(chunk):
                        print(f"   {chunk[:300]}...")
                        break

        # Exit with error code in CI mode
        if CI_MODE:
            print("\n❌ Exiting with error code 1 due to critical quality issues")
            return 1

        return 0
    else:
        print("\n✅ All sampled parties have good text quality!")
        if not FULL_SCAN:
            print(
                "   (Based on sampling - run VERIFY_FULL_SCAN=true for complete verification)"
            )
        return 0
