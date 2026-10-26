# Multi-stage build for ContextFoundry Unified Backend & RAG Engine
FROM python:3.12-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY backend_service/requirements.txt /app/backend_requirements.txt
COPY rag_service/requirements.txt /app/rag_requirements.txt

RUN pip install --no-cache-dir --user -r /app/backend_requirements.txt && \
    pip install --no-cache-dir --user -r /app/rag_requirements.txt

# Final Runtime Image
FROM python:3.12-slim

WORKDIR /app

RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/backend_service/data && \
    chown -R appuser:appuser /app

COPY --from=builder /root/.local /home/appuser/.local
ENV PATH=/home/appuser/.local/bin:$PATH
ENV PYTHONPATH=/app

COPY --chown=appuser:appuser backend_service/ /app/backend_service/
COPY --chown=appuser:appuser rag_service/ /app/rag_service/

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health')" || exit 1

CMD ["python", "-m", "uvicorn", "backend_service.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
