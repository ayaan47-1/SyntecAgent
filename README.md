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
