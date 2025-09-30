# syntax=docker/dockerfile:1
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
	PYTHONUNBUFFERED=1

WORKDIR /app

# System deps for building and lxml runtime (safeguard if wheels unavailable)
RUN apt-get update \
	&& apt-get install -y --no-install-recommends build-essential libxml2-dev libxslt1-dev \
	&& rm -rf /var/lib/apt/lists/*

# Install dependencies first (better caching)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY app ./app
COPY templates ./templates
COPY README.md .

EXPOSE 8000

# Respect PORT env var used by many PaaS (Render/Heroku). Default 8000.
CMD ["bash", "-lc", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]