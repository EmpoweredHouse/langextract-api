FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY app.py /app/app.py
COPY models.py /app/models.py

# Defaults; override at runtime
ENV MODEL_ID=gemini-2.5-flash
ENV ARTIFACTS_DIR=/artifacts

# Non-root + writable artifacts
RUN useradd -u 10001 -m appuser && mkdir -p /artifacts && chown -R appuser:appuser /artifacts
USER appuser

EXPOSE 8080
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
