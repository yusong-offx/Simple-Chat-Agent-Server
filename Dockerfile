# syntax=docker/dockerfile:1.7-labs
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps
RUN apt-get update -y && apt-get install -y --no-install-recommends \
    build-essential ca-certificates curl && \
    rm -rf /var/lib/apt/lists/*

# Copy project
COPY pyproject.toml README.md /app/
COPY ai /app/ai
COPY main.py /app/

# Install
RUN pip install --upgrade pip && \
    pip install . && \
    pip cache purge

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
