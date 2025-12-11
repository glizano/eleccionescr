# Architecture Documentation

## System Overview

EleccionesCR is a RAG (Retrieval-Augmented Generation) system for querying Costa Rica 2026 election government plans. It uses an intelligent agent-based architecture to provide accurate, contextual responses.

## High-Level Architecture

```
┌─────────────┐
│   Browser   │
└──────┬──────┘
       │ HTTP
       ▼
┌─────────────────────────────────────────────────────────────┐
│                        Frontend                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │  Astro + TypeScript                                 │    │
│  │  - Single Page Application                          │    │
│  │  - Markdown rendering                               │    │
│  │  - Session management                               │    │
│  └────────────────────────────────────────────────────┘    │
│                         Nginx                               │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP/REST API
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                     Backend (FastAPI)                        │
│  ┌────────────────────────────────────────────────────┐    │
│  │              Agent Orchestration                    │    │
│  │  ┌──────────────────────────────────────────┐     │    │
│  │  │  LangGraph Agent Workflow                 │     │    │
│  │  │                                           │     │    │
│  │  │  1. Intent Classifier                    │     │    │
│  │  │     ↓                                     │     │    │
│  │  │  2. Party Extractor (conditional)        │     │    │
│  │  │     ↓                                     │     │    │
│  │  │  3. RAG Search (filtered/general)        │     │    │
│  │  │     ↓                                     │     │    │
│  │  │  4. Response Generator                   │     │    │
│  │  └──────────────────────────────────────────┘     │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │              Services Layer                         │    │
│  │  - LLM Provider (Google Gemini / OpenAI)          │    │
│  │  - Embedding Generator                             │    │
│  │  - Vector Search (Qdrant Client)                   │    │
│  │  - Observability (Langfuse)                        │    │
│  └────────────────────────────────────────────────────┘    │
└──────────┬───────────────────────────┬─────────────────────┘
           │                           │
           │ Vector Search             │ Tracing
           ▼                           ▼
┌────────────────────┐      ┌────────────────────┐
│      Qdrant        │      │     Langfuse       │
│  Vector Database   │      │   Observability    │
│                    │      │                    │
│  - Embeddings      │      │  - Trace logs      │
│  - Metadata        │      │  - Metrics         │
│  - Similarity      │      │  - Debugging       │
└────────────────────┘      └────────────────────┘
           ▲
           │
           │ Ingest PDFs
┌──────────┴────────┐
│  Ingest Service   │
│                   │
│  - PDF parsing    │
│  - Chunking       │
│  - Embedding      │
│  - Upsert         │
└───────────────────┘
```

## Component Details

### Frontend (Astro + TypeScript)

**Purpose**: User interface for asking questions and viewing responses

**Key Features**:
- Server-side rendering with Astro
- TypeScript for type safety
- Markdown rendering for formatted responses
- Source citation display
- Session tracking

**Files**:
- `frontend/src/pages/index.astro` - Main page
- `frontend/src/components/ChatInterface.astro` - Chat UI
- `frontend/src/components/SourceCard.astro` - Source display
- `frontend/nginx.conf` - Production web server config

### Backend (FastAPI + LangGraph)

**Purpose**: Intelligent agent system for query processing and response generation

**Key Features**:
- RESTful API with FastAPI
- Agent-based architecture with LangGraph
- Multi-provider LLM support (Google Gemini, OpenAI)
- Vector search with Qdrant
- Observability with Langfuse
- Rate limiting and CORS protection

**Agent Workflow**:

1. **Intent Classification Agent**
   - Analyzes user question
   - Classifies as: specific_party, general_comparison, or unclear
   - Uses LLM with structured output

2. **Party Extraction Agent** (conditional)
   - Runs only if intent is "specific_party"
   - Extracts party abbreviations from question
   - Uses known party list for validation

3. **RAG Search Agent**
   - Generates query embedding
   - Executes vector search with filters
   - Strategy varies by intent:
     - Specific: filtered by party, top 5 chunks
     - General: distributed across parties, top 10 chunks
     - Unclear: unfiltered, top 5 chunks

4. **Response Generation Agent**
   - Builds context from retrieved chunks
   - Generates structured prompt with citations
   - Uses LLM to create natural language response
   - Returns answer with sources and metadata

**Directory Structure**:
```
backend-py/
├── app/
│   ├── agents/           # Agent workflow definitions
│   │   ├── classifier.py # Intent & party extraction
│   │   └── graph.py      # LangGraph workflow
│   ├── services/         # Core services
│   │   ├── llm_providers/# LLM abstraction layer
│   │   ├── embeddings.py # Embedding generation
│   │   ├── qdrant.py     # Vector search
│   │   └── langfuse_service.py # Observability
│   ├── middleware/       # HTTP middleware
│   │   └── rate_limit.py # Rate limiting
│   ├── config.py         # Configuration management
│   ├── models.py         # Pydantic models
│   └── main.py           # FastAPI application
└── tests/                # Test suite
```

### Ingest Service

**Purpose**: Process PDF documents and populate vector database

**Key Features**:
- PDF text extraction with pypdf
- Configurable chunking (600 words, 100 overlap)
- Multi-provider embeddings (HuggingFace, OpenAI)
- Incremental updates (hash-based change detection)
- Batch processing for efficiency

**Process Flow**:
1. Scan data directory for PDF files
2. Calculate file hash to detect changes
3. Extract text from PDF
4. Split into overlapping chunks
5. Generate embeddings for each chunk
6. Upsert to Qdrant with metadata

**Files**:
- `ingest/ingest.py` - Main processing logic
- `ingest/main.py` - Entry point
- `ingest/data/` - Source PDF directory

### Vector Database (Qdrant)

**Purpose**: Store and search document embeddings

**Configuration**:
- Vector size: 384 (for all-MiniLM-L6-v2) or 1536 (for OpenAI)
- Distance metric: Cosine similarity
- Collection: `planes_gobierno`

**Metadata Schema**:
```python
{
  "text": str,           # Chunk text content
  "doc_id": str,         # Document identifier
  "filename": str,       # Source filename
  "partido": str,        # Political party
  "chunk_index": int,    # Chunk position
  "file_hash": str,      # SHA256 hash for change detection
}
```

### Observability (Langfuse)

**Purpose**: LLM tracing, monitoring, and debugging

**Key Features**:
- Request tracing
- Token usage tracking
- Latency monitoring
- Error tracking
- Session management

**Integration Points**:
- Agent workflow tracing
- LLM call instrumentation
- Embedding generation tracking

## Data Flow

### Query Processing Flow

```
1. User submits question
   ↓
2. Frontend sends POST /api/ask
   ↓
3. Backend receives request
   ↓
4. Rate limiting check
   ↓
5. Agent workflow starts
   │
   ├─→ Classify intent (LLM call)
   │
   ├─→ Extract parties if needed (LLM call)
   │
   ├─→ Generate query embedding
   │
   ├─→ Search Qdrant (vector similarity)
   │
   ├─→ Build context from results
   │
   └─→ Generate response (LLM call)
       ↓
6. Return response with sources
   ↓
7. Frontend displays answer
   ↓
8. User views sources
```

### Ingest Flow

```
1. Place PDFs in data/ directory
   ↓
2. Run ingest service
   ↓
3. For each PDF:
   │
   ├─→ Calculate file hash
   │
   ├─→ Check if already processed
   │
   ├─→ Extract text
   │
   ├─→ Split into chunks
   │
   ├─→ Generate embeddings (batch)
   │
   ├─→ Delete old entries (if exists)
   │
   └─→ Upsert new entries to Qdrant
       ↓
4. Qdrant indexes vectors
   ↓
5. Ready for queries
```

## Deployment Architecture

### Development (Docker Compose)

```
┌─────────────────────────────────────────────────────┐
│                   Docker Host                        │
│                                                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐         │
│  │ Frontend │  │ Backend  │  │  Qdrant  │         │
│  │  :80     │  │  :8000   │  │  :6333   │         │
│  └──────────┘  └──────────┘  └──────────┘         │
│                                                      │
│  ┌──────────┐  ┌────────────┐                      │
│  │ Langfuse │  │ Langfuse   │                      │
│  │  :3000   │  │ Postgres   │                      │
│  └──────────┘  └────────────┘                      │
│                                                      │
│  ┌──────────┐                                       │
│  │  Ingest  │  (runs once, exits)                  │
│  └──────────┘                                       │
└─────────────────────────────────────────────────────┘
```

### Production (Recommended)

```
Internet
   │
   ▼
┌─────────────────┐
│  Load Balancer  │
│   (SSL/TLS)     │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌─────────┐ ┌─────────┐
│Frontend │ │Frontend │  (Multiple instances)
│ Pod 1   │ │ Pod 2   │
└────┬────┘ └────┬────┘
     │           │
     └─────┬─────┘
           │
           ▼
    ┌──────────────┐
    │  API Gateway │
    │ (Rate limit) │
    └──────┬───────┘
           │
      ┌────┴────┐
      │         │
      ▼         ▼
  ┌─────────┐ ┌─────────┐
  │Backend  │ │Backend  │  (Stateless, scalable)
  │ Pod 1   │ │ Pod 2   │
  └────┬────┘ └────┬────┘
       │           │
       └─────┬─────┘
             │
        ┌────┴────┐
        │         │
        ▼         ▼
   ┌─────────┐ ┌──────────┐
   │ Qdrant  │ │ Langfuse │  (Managed or clustered)
   │ Cluster │ │ Cluster  │
   └─────────┘ └──────────┘
```

## Security Architecture

### Authentication & Authorization

- **Current**: No built-in authentication (designed for internal use)
- **Recommended for production**: Add API keys or OAuth2 at reverse proxy level

### Rate Limiting

- **Development**: In-memory rate limiting (20 requests/minute)
- **Production**: Consider Redis-based rate limiting for distributed systems

### Input Validation

- Request validation with Pydantic models
- Question length limits (3-500 characters)
- Sanitization of LLM inputs

### Network Security

- CORS configuration (restrictable by origin)
- Security headers (X-Frame-Options, CSP, etc.)
- HTTPS termination at load balancer

### Secrets Management

- Environment variables for all secrets
- No secrets in code or version control
- API key validation at startup

## Scalability Considerations

### Horizontal Scaling

**Frontend**: Fully stateless, can scale infinitely

**Backend**: Stateless (except in-memory rate limiting), horizontally scalable
- Replace in-memory rate limiting with Redis for multi-instance deployments
- Use session affinity if needed

**Qdrant**: Supports clustering for high-volume scenarios

### Performance Optimization

1. **Caching**: Add response cache (Redis) for common queries
2. **Embedding cache**: Cache embeddings for common queries
3. **LLM optimization**: Use streaming responses for better UX
4. **Vector search**: Optimize Qdrant settings for your data size
5. **Batch processing**: Process multiple requests in parallel

### Monitoring

**Metrics to track**:
- Request latency (p50, p95, p99)
- LLM token usage
- Vector search latency
- Error rates
- Rate limit hits

**Tools**:
- Langfuse for LLM observability
- Prometheus + Grafana for system metrics
- Log aggregation (ELK, Loki)

## Technology Stack

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| Frontend | Astro | 5.x | Static site generator |
| Frontend Server | Nginx | latest | Web server |
| Backend | FastAPI | 0.115+ | API framework |
| Backend Runtime | Python | 3.11+ | Runtime |
| Agent Framework | LangGraph | 0.2+ | Agent orchestration |
| LLM Integration | LangChain | 0.3+ | LLM abstraction |
| Vector DB | Qdrant | latest | Vector storage |
| Observability | Langfuse | 2.x | LLM tracing |
| LLM Provider | Google Gemini | 2.5-flash | Text generation |
| LLM Provider | OpenAI | GPT-4o-mini | Text generation (alt) |
| Embeddings | HuggingFace | all-MiniLM-L6-v2 | Default embeddings |
| Embeddings | OpenAI | text-embedding-3-small | Alternative embeddings |

## Environment Variables

See [.env.example](.env.example) for complete configuration documentation.

Key variables:
- `LLM_PROVIDER`: google or openai
- `GOOGLE_API_KEY` / `OPENAI_API_KEY`: LLM credentials
- `EMBEDDING_PROVIDER`: sentence_transformers or openai
- `QDRANT_URL`: Vector database connection
- `CORS_ORIGINS`: Allowed frontend origins
- `ENVIRONMENT`: development or production

## Additional Resources

- [README.md](README.md) - Quick start guide
- [CONTRIBUTING.md](CONTRIBUTING.md) - Development workflow
- [SECURITY.md](SECURITY.md) - Security policy
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Common issues
- [Backend README](backend-py/README.md) - Backend details
- [Frontend README](frontend/README.md) - Frontend details
- [Ingest README](ingest/README.md) - Data ingestion

---

Last updated: December 2024
