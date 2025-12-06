"""
Base LLM Provider interface.

All LLM providers must implement this interface.
"""

from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def generate_text(self, prompt: str) -> str:
        """
        Generate text from a prompt.

        Args:
            prompt: The input prompt to generate text from.

        Returns:
            The generated text response.
        """
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the name of the model being used."""
        pass
