FROM python:3.12-slim

# ── System dependencies ───────────────────────────────────────────────────────
# LibreOffice (headless) converts PPTX → PDF with full Unicode/multilingual support.
# Noto fonts cover every script: Devanagari, CJK, Arabic, Latin extended, etc.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libreoffice-core \
        libreoffice-impress \
        fonts-noto-core \
        fonts-noto-cjk \
        fonts-noto-color-emoji \
        fonts-noto-extra \
        # Required by matplotlib / Pillow at runtime
        libglib2.0-0 \
        libgl1 \
    && rm -rf /var/lib/apt/lists/*

# ── Working directory ─────────────────────────────────────────────────────────
WORKDIR /app

# ── Python dependencies (cached layer) ────────────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Application code ──────────────────────────────────────────────────────────
COPY . .

# ── Persistent storage directories ───────────────────────────────────────────
RUN mkdir -p /app/reports /app/uploads /app/static

# ── Port (Railway injects PORT env var) ──────────────────────────────────────
EXPOSE ${PORT:-8000}

# ── Health-check (used by Railway + docker-compose) ───────────────────────────
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://localhost:{os.environ.get(\"PORT\",\"8000\")}/health')" || exit 1

# ── Start server ──────────────────────────────────────────────────────────────
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
