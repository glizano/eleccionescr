"""
LLM Provider abstraction for EleccionesCR.

This module provides a generic interface for LLM providers,
allowing easy switching between different providers like Google Gemini,
OpenAI, etc.
"""

from app.services.llm_providers.factory import get_llm_provider

__all__ = ["get_llm_provider"]
