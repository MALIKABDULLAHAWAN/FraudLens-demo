# ── Stage 1: Build frontend ──────────────────────────────────────────────────
FROM node:22-alpine AS frontend-builder

WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci --silent

COPY frontend/ ./
RUN npm run build

# ── Stage 2: Python backend + serve static ────────────────────────────────────
FROM python:3.11-slim AS runtime

# Install system deps needed by some Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/ ./backend/
COPY scripts/ ./scripts/
COPY artifacts/ ./artifacts/

# Create data directories
RUN mkdir -p data/raw data/processed

# Copy built frontend from previous stage
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Create a non-root user for security
RUN useradd -m -u 1000 fraudlens && chown -R fraudlens /app
USER fraudlens

# Port exposed (override via PORT env var)
ENV PORT=8000
EXPOSE 8000

# Health check for container orchestration
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:${PORT}/health')"

# Startup: auto-generate & train if model missing, then launch uvicorn
CMD ["sh", "-c", "python -c \"import os; os.path.exists('artifacts/xgb_model.joblib') or os.system('python scripts/generate_data.py && python scripts/train.py && python scripts/precompute_demo.py')\" && uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT} --workers 1"]
