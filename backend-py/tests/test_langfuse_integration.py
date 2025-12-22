"""
Integration tests for enhanced Langfuse tracing.
"""

from unittest.mock import MagicMock, patch


def test_langfuse_span_context_manager():
    """Test that langfuse_span works correctly."""
    from app.services.langfuse_service import langfuse_span

    # Test with None trace (disabled Langfuse)
    with langfuse_span(None, "test-span") as span:
        assert span is None

    # Test with mock trace
    mock_trace = MagicMock()
    mock_span = MagicMock()
    mock_trace.span.return_value = mock_span

    with langfuse_span(mock_trace, "test-span", metadata={"key": "value"}) as span:
        assert span == mock_span

    # Verify span was created with correct parameters
    mock_trace.span.assert_called_once()
    call_kwargs = mock_trace.span.call_args[1]
    assert call_kwargs["name"] == "test-span"
    assert call_kwargs["metadata"] == {"key": "value"}

    # Verify span.end() was called
    mock_span.end.assert_called_once()


def test_create_event():
    """Test that create_event works correctly."""
    from app.services.langfuse_service import create_event

    # Test with None trace
    result = create_event(None, "test-event")
    assert result is None

    # Test with mock trace
    mock_trace = MagicMock()
    mock_event = MagicMock()
    mock_trace.event.return_value = mock_event

    result = create_event(
        mock_trace,
        "test-event",
        metadata={"key": "value"},
        input_data={"input": "test"},
        output_data={"output": "result"},
        level="DEBUG",
    )

    assert result == mock_event
    mock_trace.event.assert_called_once()
    call_kwargs = mock_trace.event.call_args[1]
    assert call_kwargs["name"] == "test-event"
    assert call_kwargs["metadata"] == {"key": "value"}
    assert call_kwargs["input"] == {"input": "test"}
    assert call_kwargs["output"] == {"output": "result"}
    assert call_kwargs["level"] == "DEBUG"


def test_score_trace():
    """Test that score_trace works correctly."""
    from app.services.langfuse_service import get_langfuse_client, score_trace

    # Clear cache
    get_langfuse_client.cache_clear()

    # Test with disabled Langfuse
    with patch("app.services.langfuse_service.settings") as mock_settings:
        mock_settings.langfuse_enabled = False
        mock_settings.langfuse_public_key = ""
        mock_settings.langfuse_secret_key = ""

        result = score_trace("test-trace-id", "user_feedback", 0.8)
        assert result is False


def test_llm_generate_text_creates_generation():
    """Test that generate_text creates a Langfuse generation."""
    from unittest.mock import ANY

    with patch("app.services.llm.get_llm") as mock_get_llm:
        with patch("app.services.llm.get_llm_circuit_breaker") as mock_cb:
            with patch("app.services.llm._invoke_llm_with_timeout") as mock_invoke:
                # Setup mocks
                mock_llm = MagicMock()
                mock_llm.model_name = "gpt-4"
                mock_get_llm.return_value = mock_llm

                mock_circuit_breaker = MagicMock()
                mock_circuit_breaker.call = lambda func, callable_func: callable_func()
                mock_cb.return_value = mock_circuit_breaker

                # Mock the invoke to return response
                mock_invoke.return_value = "Test response"

                # Create mock trace with generation
                mock_trace = MagicMock()
                mock_generation = MagicMock()
                mock_trace.generation.return_value = mock_generation

                from app.services.llm import generate_text

                # Call with trace
                result = generate_text("Test prompt", langfuse_trace=mock_trace)

                assert result == "Test response"

                # Verify generation was created
                mock_trace.generation.assert_called_once()
                call_kwargs = mock_trace.generation.call_args[1]
                assert call_kwargs["name"] == "llm_generation"
                assert call_kwargs["model"] == "gpt-4"
                assert call_kwargs["input"] == "Test prompt"

                # Verify generation.end was called with output
                mock_generation.end.assert_called_once()
                end_kwargs = mock_generation.end.call_args[1]
                assert end_kwargs["output"] == "Test response"
                assert "latency_ms" in end_kwargs["metadata"]


def test_feedback_request_model():
    """Test FeedbackRequest model validation."""
    from app.models import FeedbackRequest

    # Valid feedback
    feedback = FeedbackRequest(trace_id="test-id", score=0.5, comment="Good")
    assert feedback.trace_id == "test-id"
    assert feedback.score == 0.5
    assert feedback.comment == "Good"

    # Score validation (should be 0-1)
    try:
        FeedbackRequest(trace_id="test-id", score=1.5)
        assert False, "Should have raised validation error"
    except Exception:
        pass  # Expected

    # Optional comment
    feedback = FeedbackRequest(trace_id="test-id", score=0.8)
    assert feedback.comment is None


def test_ask_response_includes_trace_id():
    """Test that AskResponse includes trace_id."""
    from app.models import AskResponse, AgentTrace

    response = AskResponse(
        answer="Test answer",
        sources=[],
        cached=False,
        agent_trace=AgentTrace(
            intent="test", parties_detected=[], chunks_retrieved=0, steps=[]
        ),
        session_id="test-session",
        trace_id="test-trace-id",
    )

    assert response.trace_id == "test-trace-id"
    assert response.session_id == "test-session"
