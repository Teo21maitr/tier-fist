# syntax=docker/dockerfile:1

# --- Étape 1 : build du frontend --------------------------------------------
FROM node:22-alpine AS frontend

WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# --- Étape 2 : image de production ------------------------------------------
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ ./backend/
COPY --from=frontend /build/dist ./frontend/dist

# Les médias vivent sur un volume Railway persistant monté sur /data/media :
# un redéploiement ne doit effacer ni la base ni les images uploadées.
ENV MEDIA_ROOT=/data/media
RUN mkdir -p /data/media

WORKDIR /app/backend

# collectstatic tourne au build : il ne dépend pas de la base de données.
RUN DJANGO_SECRET_KEY=build-only DJANGO_DEBUG=False \
    DATABASE_DB=postgres://user:pass@localhost:5432/db \
    python manage.py collectstatic --noinput

EXPOSE 8000

# Au démarrage : migrations puis serveur. L'ordre est important et reproductible.
CMD ["sh", "-c", "python manage.py migrate --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers ${WEB_CONCURRENCY:-3} --timeout 60 --access-logfile - --error-logfile -"]
