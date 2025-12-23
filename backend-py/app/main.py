import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.agents.graph import run_agent
from app.config import settings
from app.models import AgentTrace, AskRequest, AskResponse, FeedbackRequest, Source
from app.services.langfuse_service import shutdown_langfuse
from app.utils.logging import sanitize_for_log

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
        logger.info(f"[API] Question received: {sanitize_for_log(ask_request.question[:100])}...")

        # Build conversation history from last messages if provided
        conversation_history = None
        if ask_request.last_messages:
            # Take last 2-3 exchanges for context
            recent_messages = ask_request.last_messages[-4:]  # Last 2 Q&A pairs
            history_parts = []
            for msg in recent_messages:
                role = "Usuario" if msg.role == "user" else "Asistente"
                history_parts.append(f"{role}: {msg.content[:200]}")
            conversation_history = "\n".join(history_parts)
            logger.info(f"[API] Using conversation history with {len(recent_messages)} messages")

        # Run agent workflow with session_id for Langfuse tracing
        result = run_agent(
            ask_request.question,
            session_id=ask_request.session_id,
            conversation_history=conversation_history,
        )

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
            trace_id=result.get("trace_id"),
        )

        logger.info("[API] Response generated successfully")
        return response

    except Exception as e:
        logger.error(f"[API] Error: {sanitize_for_log(str(e))}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}") from e


@app.get("/api/parties")
@limiter.limit(f"{settings.max_requests_per_minute}/minute")
async def list_parties(request: Request):
    """List known political parties with metadata"""
    from app.party_metadata import PARTIES_METADATA

    return {"parties": PARTIES_METADATA}


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


@app.post("/api/ask/stream")
@limiter.limit(f"{settings.max_requests_per_minute}/minute")
@limiter.limit(f"{settings.max_requests_per_hour}/hour")
@limiter.limit(f"{settings.max_requests_per_day}/day")
async def ask_stream(ask_request: AskRequest, request: Request):
    """
    Streaming RAG endpoint - returns answer progressively via Server-Sent Events

    Same rate limits as /api/ask endpoint.
    """

    async def generate_stream():
        try:
            logger.info(
                f"[API Stream] Question received: {sanitize_for_log(ask_request.question[:100])}..."
            )

            # Build conversation history
            conversation_history = None
            if ask_request.last_messages:
                recent_messages = ask_request.last_messages[-4:]
                history_parts = []
                for msg in recent_messages:
                    role = "Usuario" if msg.role == "user" else "Asistente"
                    history_parts.append(f"{role}: {msg.content[:200]}")
                conversation_history = "\n".join(history_parts)
                logger.info(
                    f"[API Stream] Using conversation history with {len(recent_messages)} messages"
                )

            # Send initial metadata event
            yield f"data: {json.dumps({'type': 'start', 'session_id': ask_request.session_id})}\n\n"

            # Run agent workflow with streaming
            from app.agents.graph import run_agent_stream

            async for chunk in run_agent_stream(
                ask_request.question,
                session_id=ask_request.session_id,
                conversation_history=conversation_history,
            ):
                if chunk["type"] == "token":
                    # Stream text tokens
                    yield f"data: {json.dumps({'type': 'token', 'content': chunk['content']})}\n\n"
                elif chunk["type"] == "metadata":
                    # Send sources and trace at the end
                    yield f"data: {json.dumps({'type': 'metadata', **chunk['data']})}\n\n"

            # Send done event
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as e:
            logger.error(f"[API Stream] Error: {sanitize_for_log(str(e))}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(generate_stream(), media_type="text/event-stream")


@app.post("/api/feedback")
@limiter.limit(f"{settings.max_requests_per_minute}/minute")
async def submit_feedback(feedback: FeedbackRequest, request: Request):
    """
    Submit user feedback for a specific trace.

    This helps track real-world quality and user satisfaction.

    Args:
        feedback: FeedbackRequest with trace_id, score, and optional comment

    Returns:
        Success status
    """
    try:
        from app.services.langfuse_service import score_trace

        logger.info(
            f"[API] Feedback received for trace {sanitize_for_log(feedback.trace_id)}: "
            f"score={feedback.score}, comment={sanitize_for_log(feedback.comment[:50]) if feedback.comment else 'None'}"
        )

        # Score the trace in Langfuse
        success = score_trace(
            trace_id=feedback.trace_id,
            name="user_feedback",
            value=feedback.score,
            comment=feedback.comment,
        )

        if not success:
            logger.warning(f"[API] Failed to score trace {sanitize_for_log(feedback.trace_id)}")
            return {
                "success": False,
                "message": "Langfuse is not enabled or scoring failed",
            }

        return {
            "success": True,
            "message": "Feedback received successfully",
        }

    except Exception as e:
        logger.error(f"[API] Error submitting feedback: {sanitize_for_log(str(e))}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error submitting feedback: {str(e)}") from e
