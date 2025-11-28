from typing import Literal

from pydantic import BaseModel, Field


class ConversationMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class AskRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=500)
    last_messages: list[ConversationMessage] | None = None
    session_id: str | None = None


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
