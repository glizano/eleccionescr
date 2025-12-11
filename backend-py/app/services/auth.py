"""Authentication service for API key validation."""

import logging
from typing import Annotated

from fastapi import Header, HTTPException, status

from app.config import settings

logger = logging.getLogger(__name__)


def verify_api_key(x_api_key: Annotated[str | None, Header()] = None) -> None:
    """
    Verify API key from request header.

    Args:
        x_api_key: API key from X-API-Key header

    Raises:
        HTTPException: If authentication is required but API key is invalid or missing
    """
    # If authentication is not required, allow all requests
    if not settings.require_auth:
        return

    # If authentication is required but no API key is configured, log error
    if not settings.api_key:
        logger.error("Authentication is required but no API key is configured")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server configuration error",
        )

    # Check if API key is provided
    if not x_api_key:
        logger.warning("Request rejected: Missing API key")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Provide X-API-Key header",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Verify API key
    if x_api_key != settings.api_key:
        logger.warning("Request rejected: Invalid API key")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    logger.debug("API key validated successfully")
