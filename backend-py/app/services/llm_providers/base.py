"""
Base LLM Provider using LangChain abstractions.
"""

from langchain_core.language_models import BaseChatModel


class LLMProvider:
    """Wrapper for LangChain chat models."""

    def __init__(self, chat_model: BaseChatModel):
        """
        Initialize the provider with a LangChain chat model.

        Args:
            chat_model: A LangChain BaseChatModel instance.
        """
        self._chat_model = chat_model

    def generate_text(self, prompt: str) -> str:
        """
        Generate text from a prompt.

        Args:
            prompt: The input prompt to generate text from.

        Returns:
            The generated text response.
        """
        try:
            response = self._chat_model.invoke(prompt)
            return response.content
        except Exception as e:
            return f"Error al generar respuesta: {str(e)}"

    @property
    def model_name(self) -> str:
        """Return the name of the model being used."""
        return getattr(self._chat_model, "model_name", str(type(self._chat_model).__name__))
