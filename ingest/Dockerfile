# Dockerfile for ingest service with uv
FROM python:3.13-slim-bookworm

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Install uv for fast dependency installation
COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /usr/local/bin/uv

# Copy dependency files and install
COPY pyproject.toml uv.lock ./
RUN uv export --no-dev --frozen | uv pip install --system -r -

# Copy application code
COPY *.py ./
COPY data/ ./data/

# Run the ingest script
CMD ["python", "main.py"]
