import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.agents.graph import run_agent
from app.config import settings
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
    logger.info(
        f"Rate limiting enabled: {settings.max_requests_per_minute}/min, "
        f"{settings.max_requests_per_hour}/hour, {settings.max_requests_per_day}/day"
    )
    logger.info("Public API - No authentication required")
    yield
    # Shutdown
    logger.info("Shutting down Langfuse client...")
    shutdown_langfuse()


# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

# Create FastAPI app
app = FastAPI(
    title="EleccionesCR 2026 - Agent-based RAG API",
    description="Intelligent agent system for Costa Rica 2026 election plans",
    version="2.0.0",
    lifespan=lifespan,
)

# Add rate limiter state and exception handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok", "version": "2.0.0"}


@app.post("/api/ask", response_model=AskResponse)
@limiter.limit(f"{settings.max_requests_per_minute}/minute")
@limiter.limit(f"{settings.max_requests_per_hour}/hour")
@limiter.limit(f"{settings.max_requests_per_day}/day")
async def ask(ask_request: AskRequest, request: Request):
    """
    Main RAG endpoint with intelligent agent routing

    The agent system will:
    1. Classify intent (specific party vs general)
    2. Extract party names if applicable
    3. Execute filtered or broad RAG search
    4. Generate response with citations

    Rate limited to protect against excessive LLM costs:
    - Per minute: {settings.max_requests_per_minute}
    - Per hour: {settings.max_requests_per_hour}
    - Per day: {settings.max_requests_per_day}

    Public endpoint - no authentication required.
    """
    try:
        logger.info(f"[API] Question received: {ask_request.question[:100]}...")

        # Run agent workflow with session_id for Langfuse tracing
        result = run_agent(ask_request.question, session_id=ask_request.session_id)

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
            session_id=ask_request.session_id,
        )

        logger.info("[API] Response generated successfully")
        return response

    except Exception as e:
        logger.error(f"[API] Error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}") from e


@app.get("/api/parties")
@limiter.limit(f"{settings.max_requests_per_minute}/minute")
async def list_parties(request: Request):
    """List known political parties"""
    from app.agents.classifier import KNOWN_PARTIES

    return {"parties": KNOWN_PARTIES}


@app.get("/api/config")
async def get_config():
    """Get public API configuration including rate limits"""
    return {
        "rate_limits": {
            "per_minute": settings.max_requests_per_minute,
            "per_hour": settings.max_requests_per_hour,
            "per_day": settings.max_requests_per_day,
        }
    }
