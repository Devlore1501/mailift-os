# Mailift Planner — build unico per Railway (o qualsiasi host Docker).
# Stage 1: build del frontend React/Vite (dist/ statico)
# Stage 2: backend FastAPI che serve API + frontend costruito, un solo servizio/URL.

FROM node:20-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app

COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./
COPY --from=frontend /app/frontend/dist ./frontend_dist

ENV PLANNER_DATA_DIR=/data
ENV PLANNER_FRONTEND_DIST=/app/frontend_dist
ENV PYTHONUNBUFFERED=1

EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
