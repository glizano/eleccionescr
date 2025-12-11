import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from app.agents.graph import run_agent
from app.models import AgentTrace, AskRequest, AskResponse, Source
from app.services.langfuse_service import shutdown_langfuse

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager"""
    # Startup
    logger.info("Application starting up...")
    
    # Validate required configuration
    from app.config import settings
    
    # Check LLM API keys
    if settings.llm_provider == "google" and not settings.google_api_key:
        logger.error("GOOGLE_API_KEY is required when LLM_PROVIDER=google")
        raise ValueError("Missing GOOGLE_API_KEY environment variable")
    elif settings.llm_provider == "openai" and not settings.openai_api_key:
        logger.error("OPENAI_API_KEY is required when LLM_PROVIDER=openai")
        raise ValueError("Missing OPENAI_API_KEY environment variable")
    
    # Check embedding API keys if using OpenAI embeddings
    if settings.embedding_provider == "openai" and not settings.openai_api_key:
        logger.error("OPENAI_API_KEY is required when EMBEDDING_PROVIDER=openai")
        raise ValueError("Missing OPENAI_API_KEY for embeddings")
    
    logger.info(f"✅ Configuration validated: LLM={settings.llm_provider}, Embeddings={settings.embedding_provider}")
    
    # Test Qdrant connection
    try:
        from app.services.qdrant import get_qdrant_client
        client = get_qdrant_client()
        collections = client.get_collections()
        logger.info(f"✅ Qdrant connection successful: {len(collections.collections)} collections")
    except Exception as e:
        logger.warning(f"⚠️  Qdrant connection check failed: {e}")
        logger.warning("The API will start but RAG queries may fail")
    
    yield
    # Shutdown
    logger.info("Shutting down Langfuse client...")
    shutdown_langfuse()


# Create FastAPI app
app = FastAPI(
    title="EleccionesCR 2026 - Agent-based RAG API",
    description="Intelligent agent system for Costa Rica 2026 election plans",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS Configuration
from app.config import settings

# Parse CORS origins from configuration
cors_origins = settings.cors_origins.split(",") if settings.cors_origins != "*" else ["*"]

if settings.environment == "production" and "*" in cors_origins:
    logger.warning("⚠️  CORS is configured to allow all origins in production. Consider restricting this.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok", "version": "2.0.0"}


@app.post("/api/ask", response_model=AskResponse)
async def ask(request: AskRequest, req: Request):
    """
    Main RAG endpoint with intelligent agent routing

    The agent system will:
    1. Classify intent (specific party vs general)
    2. Extract party names if applicable
    3. Execute filtered or broad RAG search
    4. Generate response with citations
    """
    try:
        logger.info(f"[API] Question received: {request.question[:100]}...")

        # Run agent workflow with session_id for Langfuse tracing
        result = run_agent(request.question, session_id=request.session_id)

        # Build response
        response = AskResponse(
            answer=result["answer"],
            sources=[Source(**s) for s in result["sources"]],
            cached=False,
            agent_trace=AgentTrace(
                intent=result["intent"],
                parties_detected=result["parties"],
                chunks_retrieved=len(result["contexts"]),
                steps=result["steps"],
            ),
            session_id=request.session_id,
        )

        logger.info("[API] Response generated successfully")
        return response

    except Exception as e:
        logger.error(f"[API] Error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}") from e


@app.get("/api/parties")
async def list_parties():
    """List known political parties"""
    from app.agents.classifier import KNOWN_PARTIES

    return {"parties": KNOWN_PARTIES}
