"""
Example demonstrating the enhanced Langfuse tracing capabilities.

This script shows how traces, spans, generations, and feedback work together.
"""

import os
from unittest.mock import MagicMock

# Set environment variables for testing
os.environ["LANGFUSE_ENABLED"] = "false"  # Disabled for demo
os.environ["GOOGLE_API_KEY"] = "test-key"
os.environ["OPENAI_API_KEY"] = "test-key"


def demo_trace_structure():
    """Demonstrate the hierarchical trace structure."""
    print("=" * 80)
    print("LANGFUSE TRACE STRUCTURE EXAMPLE")
    print("=" * 80)
    print()

    # Mock trace for demonstration
    mock_trace = MagicMock()
    mock_trace.id = "trace-abc123"

    print("📊 TRACE: agent-workflow")
    print("   ID: trace-abc123")
    print("   Session: user-session-456")
    print("   User ID: a1b2c3d4e5f6g7h8 (anonymous hash)")
    print("   Tags: [specific_party, party:PLN, sources:5]")
    print("   Metadata:")
    print("     - llm_provider: google")
    print("     - llm_model: gemini-2.5-flash")
    print("     - question_length: 45")
    print()

    print("   ├─ 🔍 SPAN: classify_intent")
    print("   │    Duration: 234ms")
    print("   │    Input: {question: '¿Qué propone el PLN sobre...?'}")
    print("   │    Output: {intent: 'specific_party'}")
    print("   │")

    print("   ├─ 🔍 SPAN: extract_parties")
    print("   │    Duration: 156ms")
    print("   │    Input: {question: '¿Qué propone el PLN sobre...?'}")
    print("   │    Output: {parties: ['PLN']}")
    print("   │")

    print("   ├─ 🔍 SPAN: rag_search")
    print("   │    Duration: 567ms")
    print("   │    Metadata: {intent: 'specific_party', parties: ['PLN']}")
    print("   │    │")
    print("   │    └─ 🔍 SPAN: rag_search_specific_party")
    print("   │         Duration: 543ms")
    print("   │         Metadata: {party: 'PLN', strategy: 'specific_party', limit: 5}")
    print("   │         Output:")
    print("   │           - num_results: 5")
    print("   │           - avg_score: 0.87")
    print("   │           - scores: [0.92, 0.89, 0.86, 0.84, 0.82]")
    print("   │")

    print("   └─ 🔍 SPAN: generate_response")
    print("        Duration: 2145ms")
    print("        Metadata: {intent: 'specific_party', num_contexts: 5}")
    print("        │")
    print("        └─ 🤖 GENERATION: llm_generation")
    print("             Model: gemini-2.5-flash")
    print("             Provider: google")
    print("             Duration: 2089ms")
    print("             Latency: 2089ms")
    print("             Input: [PROMPT WITH 5 CONTEXTS]")
    print("             Output: 'El PLN propone en educación...'")
    print("             Metadata:")
    print("               - latency_ms: 2089")
    print("               - response_length: 456")
    print("               - prompt_length: 1234")
    print()

    print("   📈 TRACE OUTPUT:")
    print("      - answer_length: 456")
    print("      - sources_count: 5")
    print("      - intent: specific_party")
    print("      - parties_detected: ['PLN']")
    print("      - steps: ['Intent: specific_party', 'Parties: [PLN]', ...]")
    print()


def demo_feedback_flow():
    """Demonstrate the user feedback flow."""
    print("=" * 80)
    print("USER FEEDBACK FLOW EXAMPLE")
    print("=" * 80)
    print()

    print("1️⃣  User asks question:")
    print("   POST /api/ask")
    print("   {")
    print('     "question": "¿Qué propone el PLN sobre educación?",')
    print('     "session_id": "user-session-456"')
    print("   }")
    print()

    print("2️⃣  System responds with trace_id:")
    print("   {")
    print('     "answer": "El PLN propone...",')
    print('     "sources": [...],')
    print('     "trace_id": "trace-abc123",  ⬅️  NEW!')
    print('     "session_id": "user-session-456"')
    print("   }")
    print()

    print("3️⃣  User provides feedback (later):")
    print("   POST /api/feedback")
    print("   {")
    print('     "trace_id": "trace-abc123",')
    print('     "score": 0.9,')
    print('     "comment": "Very helpful answer!"')
    print("   }")
    print()

    print("4️⃣  Feedback stored in Langfuse:")
    print("   📊 Score added to trace-abc123")
    print("   📈 Available for quality analysis")
    print("   🎯 Can filter by score ranges in UI")
    print()


def demo_rag_metrics():
    """Demonstrate RAG search metrics."""
    print("=" * 80)
    print("RAG SEARCH METRICS EXAMPLE")
    print("=" * 80)
    print()

    print("🔍 Strategy: general_comparison")
    print("   Question: 'Comparar propuestas de seguridad'")
    print()
    print("   Metrics captured:")
    print("   ├─ num_results: 40")
    print("   ├─ avg_score: 0.78")
    print("   ├─ parties_covered: 18 out of 20")
    print("   ├─ parties_missing: ['PRSC', 'PRD']")
    print("   └─ party_distribution:")
    print("        PLN: 2 chunks")
    print("        PUSC: 2 chunks")
    print("        PAC: 2 chunks")
    print("        ...")
    print()

    print("   ⚡ Benefits:")
    print("   • Identify parties with poor coverage")
    print("   • Detect when similarity scores are low")
    print("   • Monitor fairness of party representation")
    print("   • Debug why certain parties are missing")
    print()


def demo_tags_filtering():
    """Demonstrate tags for UI filtering."""
    print("=" * 80)
    print("TAGS FOR UI FILTERING EXAMPLE")
    print("=" * 80)
    print()

    print("📌 Available tags on each trace:")
    print()

    print("   Intent tags:")
    print("   • specific_party")
    print("   • party_general_plan")
    print("   • general_comparison")
    print("   • metadata_query")
    print("   • unclear")
    print()

    print("   Party tags:")
    print("   • party:PLN")
    print("   • party:PUSC")
    print("   • party:PAC")
    print("   • ...")
    print()

    print("   Source count tags:")
    print("   • sources:5")
    print("   • sources:10")
    print("   • sources:40")
    print()

    print("   Mode tags:")
    print("   • streaming")
    print()

    print("   🎯 Use cases:")
    print("   • Filter all 'party:PLN' questions to analyze PLN interest")
    print("   • Find 'general_comparison' with low sources to debug")
    print("   • Compare 'streaming' vs regular requests performance")
    print("   • Identify 'unclear' intents to improve classification")
    print()


def main():
    """Run all demonstrations."""
    demo_trace_structure()
    print()
    demo_feedback_flow()
    print()
    demo_rag_metrics()
    print()
    demo_tags_filtering()

    print("=" * 80)
    print("✅ LANGFUSE IMPROVEMENTS SUMMARY")
    print("=" * 80)
    print()
    print("✓ LLM calls tracked with latency and metadata")
    print("✓ Each graph node has its own span for debugging")
    print("✓ RAG searches track quality metrics")
    print("✓ Structured tags enable powerful filtering")
    print("✓ User feedback loop for quality measurement")
    print("✓ Anonymous user IDs for usage analytics")
    print()
    print("📚 See LANGFUSE_IMPROVEMENTS.md for full documentation")
    print()


if __name__ == "__main__":
    main()
