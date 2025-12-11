from typing import Literal

from pydantic import BaseModel, Field


class ConversationMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class AskRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=3,
        max_length=500,
        description="User's question about government plans",
        examples=["¿Qué propone el PLN sobre educación?"]
    )
    last_messages: list[ConversationMessage] | None = Field(
        None,
        description="Previous conversation messages for context",
        max_items=10
    )
    session_id: str | None = Field(
        None,
        description="Session ID for tracking conversation history",
        max_length=100
    )


class Source(BaseModel):
    partido: str
    filename: str
    text: str
    doc_id: str
    chunk_index: int
    score: float


class AgentTrace(BaseModel):
    """Trace information from agent execution"""

    intent: str
    parties_detected: list[str]
    chunks_retrieved: int
    steps: list[str]


class AskResponse(BaseModel):
    answer: str
    sources: list[Source]
    cached: bool = False
    agent_trace: AgentTrace | None = None
    session_id: str | None = None
