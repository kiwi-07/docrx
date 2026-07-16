# Better Dockerfile — should score higher
FROM python:3.13-slim

LABEL org.opencontainers.image.title="example"

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

USER nobody

HEALTHCHECK CMD curl -f http://localhost:8000/health || exit 1

CMD ["python", "app.py"]
