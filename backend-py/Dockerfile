# Dockerfile for backend-py with uv
FROM python:3.13-slim-bookworm

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# Set working directory
WORKDIR /app

# Install uv for fast dependency installation
COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /usr/local/bin/uv

# Copy dependency files and install
COPY pyproject.toml uv.lock ./
RUN uv export --no-dev --frozen | uv pip install --system -r -

# Copy application code
COPY app/ ./app/
COPY main.py run.py ./

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run the application
CMD ["python", "run.py"]
