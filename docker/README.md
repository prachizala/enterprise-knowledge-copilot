# Docker Infrastructure Notes

This directory contains container definitions and orchestration configurations for the Enterprise Knowledge Copilot.

## Services Defined in `docker-compose.yml`:

| Service | Base Image / Build | Port | Role |
| :--- | :--- | :--- | :--- |
| **frontend** | `./frontend/Dockerfile` | 3000 | Next.js 14 Dashboard UI |
| **backend** | `./backend/Dockerfile` | 8000 | FastAPI REST API engine |
| **postgres** | `postgres:16-alpine` | 5432 | Relational store for enterprise documents & auth |
| **neo4j** | `neo4j:5.20-community` | 7474, 7687 | Knowledge Graph with APOC plugins |

## How to Run:

```bash
# Start all containers in background
docker compose up -d

# Check service logs
docker compose logs -f backend

# Stop all containers
docker compose down
```
