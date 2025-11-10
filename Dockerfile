# --- STAGE 1: Builder (use slim to reduce base image size) ---
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /app

# Copy only requirements first for caching
COPY requirements.txt .

# Install into a vendor folder to avoid leaving build artifacts in system site-packages
RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev build-essential \
    && python -m pip install --upgrade pip \
    && pip install --no-cache-dir --upgrade -r requirements.txt --target=/app/vendor \
    && apt-get purge -y --auto-remove gcc build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy project files (large caches excluded via .dockerignore)
COPY . .

# Collect static (optional) — don't fail build on platforms without static config
RUN python manage.py collectstatic --noinput || true


# --- STAGE 2: Production Runtime ---
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Copy only the installed Python packages and app code from builder
COPY --from=builder /app/vendor /usr/local/lib/python3.11/site-packages
COPY --from=builder /app /app

# Expose port and run gunicorn (point to your actual wsgi module)
EXPOSE 8000

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "hair_project.wsgi:application"]