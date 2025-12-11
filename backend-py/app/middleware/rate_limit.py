"""
Simple in-memory rate limiting middleware.

For production, consider using Redis-based rate limiting
with libraries like slowapi or fastapi-limiter.
"""

import logging
import time
from collections import defaultdict
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple in-memory rate limiting middleware.
    
    Note: This is a basic implementation suitable for single-instance deployments.
    For production with multiple instances, use Redis-based rate limiting.
    """

    def __init__(self, app, requests_per_minute: int = 20):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests: dict[str, list[float]] = defaultdict(list)
        self.cleanup_interval = 60  # Clean up old entries every 60 seconds
        self.last_cleanup = time.time()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for health check and docs
        if request.url.path in ["/health", "/docs", "/openapi.json"]:
            return await call_next(request)

        # Get client identifier (IP address)
        client_ip = request.client.host if request.client else "unknown"

        # Clean up old entries periodically
        current_time = time.time()
        if current_time - self.last_cleanup > self.cleanup_interval:
            self._cleanup_old_entries(current_time)
            self.last_cleanup = current_time

        # Get recent requests for this client
        recent_requests = self.requests[client_ip]

        # Remove requests older than 1 minute
        cutoff_time = current_time - 60
        recent_requests = [req_time for req_time in recent_requests if req_time > cutoff_time]
        self.requests[client_ip] = recent_requests

        # Check if rate limit exceeded
        if len(recent_requests) >= self.requests_per_minute:
            logger.warning(f"Rate limit exceeded for {client_ip}")
            return Response(
                content="Rate limit exceeded. Please try again later.",
                status_code=429,
                headers={"Retry-After": "60"},
            )

        # Add current request
        recent_requests.append(current_time)

        # Process request
        response = await call_next(request)
        return response

    def _cleanup_old_entries(self, current_time: float):
        """Remove old entries to prevent memory growth."""
        cutoff_time = current_time - 120  # Keep last 2 minutes
        keys_to_delete = []

        for client_ip, requests in self.requests.items():
            # Remove old requests
            recent = [req_time for req_time in requests if req_time > cutoff_time]
            if recent:
                self.requests[client_ip] = recent
            else:
                keys_to_delete.append(client_ip)

        # Delete empty entries
        for key in keys_to_delete:
            del self.requests[key]

        if keys_to_delete:
            logger.debug(f"Cleaned up {len(keys_to_delete)} rate limit entries")
