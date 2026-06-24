# Build stage - compile dependencies
FROM python:3.13-slim as builder

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Build lockfile and sync dependencies
RUN uv pip compile pyproject.toml -o requirements.txt && \
    uv pip install -r requirements.txt --target /app/venv


# Runtime stage - minimal production image
FROM python:3.13-slim

WORKDIR /app

# Copy Python environment from builder
COPY --from=builder /app/venv /usr/local/lib/python3.13/site-packages

# Copy application code
COPY . .

# Non-root user for security
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8080/health')" || exit 1

# Expose port (Cloud Run expects 8080)
EXPOSE 8080

# Start application
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]