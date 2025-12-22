# Langfuse Tracing Improvements

## Overview
This document describes the comprehensive improvements made to Langfuse tracing for better observability, debugging, and analytics of the EleccionesCR RAG system.

## Implemented Features

### ✅ HIGH PRIORITY (COMPLETED)

#### 1. LLM Call Tracking (Costs, Tokens, Latency)
- **Generation Events**: Every LLM call now creates a Langfuse generation event with:
  - Model name (e.g., "gemini-2.5-flash", "gpt-4o-mini")
  - Input prompt and output text
  - Latency in milliseconds
  - Provider metadata (Google or OpenAI)
  - Error tracking with status messages and levels
- **Streaming Support**: Streaming LLM calls are also tracked with full text capture
- **Location**: `app/services/llm.py` - `generate_text()` and `generate_text_stream()`

#### 2. Graph Node Spans (Debugging Workflow)
Each node in the LangGraph workflow now has its own span:
- **classify_intent_node**: Tracks intent classification
- **extract_parties_node**: Tracks party extraction
- **rag_search_node**: Tracks RAG search execution with sub-spans
- **generate_response_node**: Tracks final response generation
- **metadata_query_node**: Tracks direct metadata queries

Each span includes:
- Input data (question, context)
- Output data (results, metrics)
- Metadata (node name, configuration)
- **Location**: `app/agents/graph.py`

#### 3. RAG Search Tracking (Quality of Retrieval)
Each retrieval strategy now has dedicated spans with metrics:
- **search_specific_party**: Single party focused search
- **search_general_party_plan**: Comprehensive party overview
- **search_general_comparison**: Multi-party comparison
- **search_default**: General search

Metrics tracked:
- Number of results
- Average relevance score
- Score distribution
- Party coverage and distribution
- Missing parties (for comparison queries)
- **Location**: `app/agents/retrieval.py`

### ✅ MEDIUM PRIORITY (COMPLETED)

#### 4. Tags and Structured Metadata
Traces now include structured tags for easy filtering in Langfuse UI:
- **Intent tags**: `specific_party`, `general_comparison`, `metadata_query`, etc.
- **Party tags**: `party:PLN`, `party:PUSC`, etc. (for detected parties)
- **Source tags**: `sources:5`, `sources:10`, etc. (number of sources)
- **Mode tags**: `streaming` (for streaming requests)

Metadata includes:
- LLM provider and model name
- Configuration settings (timeouts, limits)
- Question length and conversation history status
- **Location**: `app/agents/graph.py` - `run_agent()` and `run_agent_stream()`

#### 5. User Feedback Loop
New feedback endpoint for tracking real-world quality:
- **Endpoint**: `POST /api/feedback`
- **Request Model**: `FeedbackRequest`
  - `trace_id`: ID of the trace to score
  - `score`: 0-1 feedback score
  - `comment`: Optional feedback text
- **Response includes trace_id**: All API responses include `trace_id` for feedback tracking
- **Langfuse Integration**: Feedback is stored as scores in Langfuse
- **Location**: `app/main.py`, `app/models.py`

### ✅ LOW PRIORITY (COMPLETED)

#### 6. Anonymous User ID
- **Implementation**: Hash of session_id (SHA256, first 16 chars)
- **Purpose**: Track recurring users without PII
- **Analytics**: Enables user journey analysis in Langfuse
- **Location**: `app/agents/graph.py` - `run_agent()` and `run_agent_stream()`

## New Helper Functions

### `app/services/langfuse_service.py`

1. **`langfuse_span()`**: Context manager for creating spans
   ```python
   with langfuse_span(trace, "operation-name", metadata={...}) as span:
       # Your code here
       pass
   ```

2. **`create_event()`**: Create discrete events for tracking
   ```python
   event = create_event(trace, "event-name", input_data={...}, output_data={...})
   ```

3. **`score_trace()`**: Submit user feedback scores
   ```python
   success = score_trace(trace_id, "user_feedback", 0.8, "Great answer!")
   ```

4. **Enhanced `create_generation()`**: Now supports usage metrics
   ```python
   generation = create_generation(
       trace, "llm-call", "gpt-4", "prompt", "output",
       usage={"prompt_tokens": 100, "completion_tokens": 50}
   )
   ```

## Usage Examples

### Tracking a Complete Request
```python
from app.agents.graph import run_agent

# Run agent with session_id for tracking
result = run_agent(
    question="¿Qué propone el PLN sobre educación?",
    session_id="user-session-123"
)

# Result includes trace_id for feedback
print(result["trace_id"])
```

### Submitting User Feedback
```python
import httpx

response = httpx.post(
    "http://localhost:8000/api/feedback",
    json={
        "trace_id": "langfuse-trace-id-here",
        "score": 0.9,
        "comment": "Very helpful answer!"
    }
)
```

### Viewing Traces in Langfuse UI
1. Navigate to your Langfuse dashboard
2. Filter by:
   - **Tags**: `specific_party`, `party:PLN`, `streaming`
   - **Session ID**: Track user conversations
   - **User ID**: Anonymous user tracking
   - **Time range**: Analyze specific periods
3. View detailed traces with:
   - Complete workflow execution path
   - LLM generation details (latency, tokens)
   - RAG search metrics (scores, coverage)
   - Error information (if any)

## Metrics Available

### LLM Metrics
- Latency (ms)
- Response length
- Prompt length
- Model name
- Provider

### RAG Metrics
- Number of chunks retrieved
- Average relevance score
- Score distribution (top 5 scores)
- Party coverage (in comparison queries)
- Party distribution (chunks per party)

### Workflow Metrics
- Total execution steps
- Intent classification result
- Parties detected
- Number of sources in response
- Error tracking with levels

## Testing

### Test Coverage
- `tests/test_langfuse.py`: Original Langfuse service tests
- `tests/test_langfuse_integration.py`: New integration tests for:
  - Span creation and management
  - Event creation
  - Generation tracking
  - Feedback model validation
  - Trace ID propagation

### Running Tests
```bash
cd backend-py
python -m pytest tests/test_langfuse*.py -v
```

## Configuration

All Langfuse settings are in `app/config.py`:
```python
langfuse_public_key: str = ""
langfuse_secret_key: str = ""
langfuse_host: str = "https://cloud.langfuse.com"
langfuse_enabled: bool = False
```

Set via environment variables:
```bash
LANGFUSE_ENABLED=true
LANGFUSE_PUBLIC_KEY=pk-xxx
LANGFUSE_SECRET_KEY=sk-xxx
LANGFUSE_HOST=https://cloud.langfuse.com  # or self-hosted URL
```

## Backward Compatibility

All changes are backward compatible:
- ✅ Works without Langfuse enabled (all functions return None/False gracefully)
- ✅ Existing API contracts unchanged
- ✅ No breaking changes to request/response models (trace_id is optional)
- ✅ All existing tests pass

## Benefits

1. **Better Debugging**: Detailed spans show exactly which node is slow or failing
2. **Cost Tracking**: LLM generation events help track token usage and costs
3. **Quality Monitoring**: RAG metrics reveal retrieval quality issues
4. **User Analytics**: Anonymous user IDs and session tracking for usage patterns
5. **Feedback Loop**: Real user feedback scores to measure actual quality
6. **Easy Filtering**: Structured tags make it easy to find specific traces in UI

## Future Enhancements

Possible future additions:
- Token usage tracking (requires LangChain callback support)
- Cost estimation based on model pricing
- A/B testing support with trace tags
- Custom dashboards in Langfuse
- Automated alerts for quality degradation
