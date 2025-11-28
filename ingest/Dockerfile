# Multi-stage Dockerfile for ingest service with uv
FROM ghcr.io/astral-sh/uv:0.5.11-python3.13-bookworm as builder

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml .

# Create virtual environment and install dependencies with uv
RUN uv venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN uv sync --no-dev

# Production stage
FROM python:3.13-bookworm

# Set environment variables
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Copy application code
COPY . /app/

# Run the ingest script
CMD ["python", "main.py"]
