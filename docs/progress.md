# Project progress

## Stack
- Backend: FastAPI + Python 3.11
- UI: Streamlit (port 8501)
- Vector DB: ChromaDB (port 8001, internal 8000)
- Database: PostgreSQL 15 (port 5433 external, 5432 internal)
- Cache: Redis 7
- Deploy: Docker locally, GCP GKE (Day 18+)
- CI/CD: Cloud Build → Artifact Registry (working)
- Repo: data-dict-chatbot

## Completed
- Day 1 ✓ Docker scaffold, FastAPI, Streamlit, CI/CD pipeline
- Day 2 ✓ All containers healthy, 13 tables + 57 columns + 17 joins seeded

## Key decisions
- Streamlit over React (simplicity, same Docker image as backend)
- chromadb depends_on: service_started (not service_healthy — too slow)
- postgres port mapped to 5433 (5432 taken by local postgres)
- cloudbuild.yaml — no GKE steps until Day 18

## Known issues fixed
- ChromaDB healthcheck: /api/v2/heartbeat (not v1)
- backend/streamlit: restart: on-failure + service_started dependency
- docker-compose version: removed (obsolete in Compose v2)