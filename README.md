# Syntec Group AI Chatbot

A BIM classification management agent for Syntec Group. Ingests XLSX building classification data and provides an agent-mode chat interface for querying and managing classification codes using semantic search and GPT-4o function calling.

## Overview

- **XLSX Ingestion**: Upload building classification spreadsheets — parsed into SQLite and embedded into ChromaDB for semantic search
- **Agent Chat**: GPT-4o with function calling manages BIM classification codes (add, update, delete, search by code prefix)
- **Semantic Search**: Queries match against ChromaDB embeddings (top 10 results, blog content excluded)
- **Confirmation Gates**: Destructive actions (update/delete) require explicit user confirmation via modal
- **Dual Deployment**: Docker Compose or native mode with hot-reload

### Agent Tools

| Tool | Description |
|------|-------------|
| `get_module` | Look up a classification by name |
| `list_modules` | List all classifications (capped at 50) |
| `list_category` | List codes by prefix, e.g. `04 05 13` (capped at 100) |
| `add_module` | Add a new classification code |
| `update_module` | Update an existing code (requires confirmation) |
| `delete_module` | Delete a code (requires confirmation) |

## Stack

### Backend
- Python 3.12, Flask 3.0
- OpenAI GPT-4o (chat) + `text-embedding-3-small` (embeddings)
- DeepSeek as optional primary model (falls back to OpenAI)
- ChromaDB (vector database)
- SQLite (classifications storage)
- Redis (rate limiting/caching, falls back to in-memory)

### Frontend
- React 19, Vite 7
- Embeddable chat widget (`SyntecChatWidget.jsx`)
- Confirmation modal for destructive agent actions

### Infrastructure
- Docker Compose (Redis + Backend + Frontend)
- Nginx (production frontend)
- Makefile for all operations

## Getting Started

### Prerequisites
- Docker + Docker Compose
- An OpenAI API key
- (Native mode only) Python 3.12 and Node.js 20+

### Setup

```bash
git clone https://github.com/ayaan47-1/SyntecAgent.git
cd SyntecAgent

cp .env.example .env        # then fill in OPENAI_API_KEY
make up                     # Docker mode: Redis + Backend + Frontend
make health-check           # verify the backend is healthy
```

- Frontend: http://localhost (port 80)
- Backend API: http://localhost:5001

For local development with hot-reload:

```bash
make up MODE=native         # Redis in Docker; Backend + Frontend run locally
```

### Common Commands

```bash
make up / make down / make restart / make ps   # lifecycle
make logs                                       # tail all logs
make backend-restart / make frontend-restart    # restart one service
make ingest                                     # bulk-ingest XLSX data
make db-stats / make db-backup / make db-reset   # ChromaDB management
```

## Configuration

Set in `.env` (see `.env.example` for the full template):

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | Chat + embeddings |
| `PORT` | No | Backend port (default `5001`) |
| `FLASK_ENV` | No | `production` makes ChromaDB failures fatal; `development` falls back to in-memory |
| `CORS_ORIGINS` | No | Comma-separated allowed origins |
| `REDIS_URL` | No | Redis connection (falls back to in-memory) |
| `DEEPINFRA_API_KEY` | No | Required only for PNG OCR ingestion |
| `DEEPSEEK_API_KEY` | No | Optional cheaper primary model (falls back to OpenAI) |

## API Endpoints

The backend exposes three core endpoints:

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check (includes `chromadb_in_memory` flag) |
| POST | `/api/ingest` | Ingest classification data (**XLSX only** — other formats return 400) |
| POST | `/api/chat` | Agent-mode chat with function calling |

Plus the module REST API (`/api/modules`, `/api/modules/category/<prefix>`, etc.); destructive `PUT`/`DELETE` require `?confirm=true`.

## Testing

```bash
python -m pytest tests/ -v                       # full suite
python -m pytest tests/ --cov=app2 --cov=agent   # with coverage
```

## Deployment

The app is deployed as a **split frontend/backend**:

- **Frontend** → Vercel (project `syntec-agent`). Build config lives in `vercel.json`: it builds `chatbot-frontend` and serves `dist`. All `/api/*` requests are rewritten to the backend host.
- **Backend** → DigitalOcean droplet running the Docker Compose stack (Redis + Flask backend) on port `5001`. The Vercel rewrite in `vercel.json` points to this host.

To redeploy:

```bash
# Frontend (Vercel) — push to the connected branch, or:
cd chatbot-frontend && vercel --prod

# Backend (droplet) — pull and restart the stack on the server:
git pull && make up
```

> **Note:** ChromaDB and SQLite data live on the backend host and are **not** populated by a fresh deploy. After provisioning a new backend, run `make ingest` (or `POST /api/ingest`) so the knowledge base is non-empty — `GET /api/health` reports `collection_count`.

## Rate Limits

| Endpoint | Limit |
|----------|-------|
| Health check | 10/min |
| Chat | 30/min |
| Document ingestion | 10/hr |
| Global | 200/day, 50/hr |

## Security Features

- Input sanitization (HTML stripping, control character removal)
- Path traversal prevention
- Rate limiting on all endpoints
- Security headers (X-Frame-Options, X-Content-Type-Options, etc.)
- CORS restrictions
- Confirmation gates for destructive operations
- SQLite/ChromaDB atomic writes with rollback on failure

## Troubleshooting

**OpenAI API key error**: Ensure `OPENAI_API_KEY` is set in `.env`

**ChromaDB connection issues**: In production (`FLASK_ENV=production`), ChromaDB failures are fatal. In development, it falls back to in-memory. Check `GET /api/health` for `chromadb_in_memory` status.

**Rate limit errors**: Reduce request frequency or adjust limits in `app2.py`

**Cannot connect to backend**: Verify `VITE_API_URL` points to the correct backend URL (default port 5001)

**CORS errors**: Add your frontend URL to `CORS_ORIGINS` in `.env`

## About Syntec Group

Syntec Group is focused on innovative building solutions through BuildUSA (BUSA), which implements a modular approach to construction.

- Website: https://syntecgroup.com/
- BuildUSA Blog: https://build.syntecgroup.com/

### BuildUSA Overview

BuildUSA is built on the **Prototype Initiative** framework:
- **Research**: Understanding modular building approaches
- **Process**: Developing efficient construction workflows
- **Execution**: Implementing scalable building solutions

## License

[MIT](LICENSE)

## Support

For issues or questions, open an issue on GitHub or check the troubleshooting section above.

---

Built for Syntec Group
