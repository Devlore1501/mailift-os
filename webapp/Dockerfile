# Autofatture webapp: frontend React buildato + backend FastAPI in un'unica
# immagine. Build dalla root del repo (servono tools/ e webapp/):
#
#   docker build -f webapp/Dockerfile -t autofatture .
#
# Dati persistenti (DB, estratti, PDF fornitori, token) su un volume in /data.

FROM node:22-slim AS frontend
WORKDIR /web
COPY webapp/frontend/package.json webapp/frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY webapp/frontend/ ./
RUN npm run build

FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app

COPY webapp/backend/requirements.txt webapp/backend/requirements.txt
RUN pip install -r webapp/backend/requirements.txt

# Solo i tools che la webapp importa, non l'intera cartella.
COPY tools/parse_bank_statement.py tools/classify_transactions.py \
     tools/autofatture_prep.py tools/run_autofatture.py tools/fic_client.py \
     tools/send_autofatture_sdi.py tools/verify_suppliers_from_email.py \
     tools/gmail_client.py tools/
COPY webapp/backend/app webapp/backend/app
COPY --from=frontend /web/dist webapp/frontend/dist

# I tools scrivono in <repo>/.tmp (PDF fornitori) e leggono <repo>/tokens:
# li faccio puntare al volume.
RUN useradd --create-home --uid 10001 app \
 && mkdir -p /data \
 && chown app:app /data \
 && ln -s /data/tmp /app/.tmp \
 && ln -s /data/tokens /app/tokens

ENV WEBAPP_DATA_DIR=/data/webapp \
    MAILIFT_ENV_PATH=/data/mailift.env \
    GMAIL_TOKEN_PERSONAL=/data/tokens/gmail_personal.json \
    GMAIL_TOKEN_BUSINESS=/data/tokens/gmail_business.json \
    WEBAPP_COOKIE_SECURE=true \
    PORT=8000

USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
  CMD python -c "import os,urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ[\"PORT\"]}/api/healthz', timeout=4)"

# Un solo worker: job in background e cache sono in memoria del processo.
CMD ["sh", "-c", "mkdir -p /data/tmp /data/tokens /data/webapp && exec uvicorn app.main:app --app-dir webapp/backend --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*'"]
