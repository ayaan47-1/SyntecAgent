# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Context

Internal AI chatbot for Syntec Group providing document-based Q&A using semantic search and GPT-4o. Serves internal BuildUSA/Syntec documentation and future client-facing website chat.

**BuildUSA (BUSA)**: Syntec Group's modular construction project.
- Website: https://syntecgroup.com/
- Blog: https://build.syntecgroup.com/

## Architecture Overview

**Flask + React + ChromaDB** with dual deployment modes (Docker Compose and native).

### Backend (`app2.py` + `agent/` package)
- Port: 5001
- OpenAI GPT-4o for chat; DeepSeek as optional primary (falls back to OpenAI)
- OpenAI `text-embedding-3-small` for semantic search → ChromaDB (`./chroma_db/`)
- Redis for rate limiting/caching (falls back to in-memory)
- Document processing: PDF, CSV, PNG (OCR via DeepInfra), XLSX
- Agentic BIM classification management via `agent/` package (OpenAI function calling)
- Classifications stored in SQLite (`classifications.db`) + synced to ChromaDB

### Frontend (React + Vite)
- Dev port: 5176 (native) or 80 (Docker/Nginx)
- Source mode toggle: Documents (semantic search) vs Internet (direct GPT)
- `SyntecChatWidget.jsx` — embeddable widget
- `ConfirmationModal.jsx` — confirmation gate for destructive agent actions

### Data Flow
1. Documents → text extraction → chunking (1200 chars, 150 overlap) → OpenAI embeddings → ChromaDB
2. User query → embedding → similarity search (top 10 chunks) → GPT-4o context → response with citations
3. Module CRUD: user intent → GPT function calling → `agent/` CRUD → SQLite + ChromaDB sync
   - Non-destructive (get/list/add) → execute immediately
   - Destructive (update/delete) → `ConfirmationModal` → `handle_confirmation()` → execute

### Dual-Mode Operation

```bash
make up              # Docker mode (default): Redis + Backend + Frontend in containers
make up MODE=native  # Native mode: Redis in Docker, Backend/Frontend local with hot-reload
```

## Commands

### Service Management
```bash
make up / make down / make restart / make ps
make backend-restart / make frontend-restart / make redis-restart
make logs / make logs-backend / make logs-frontend
```

### Database & Ingestion
```bash
make db-stats        # ChromaDB statistics
make db-backup       # Timestamped backup
make db-reset        # Clear ChromaDB (with confirmation)
make ingest          # Run ingest_sources.py
```

### Testing
```bash
python -m pytest tests/ -v                           # All tests
python -m pytest tests/test_module_management.py -v  # Module CRUD only
python -m pytest tests/ -k "test_add_module" -v      # Single test by name
python -m pytest tests/ --cov=app2 --cov=agent -v    # With coverage
```

### Frontend
```bash
cd chatbot-frontend && npm run dev    # Dev server :5176
npm run build                         # Production build
npm run lint                          # ESLint
```

## Key Files

**Backend**
- `app2.py` — Flask application: endpoints, embeddings, chat logic, ChromaDB init
- `agent/db.py` — SQLite layer: `get_db()` (thread-local), `init_db()` (schema + JSON migration)
- `agent/crud.py` — CRUD + `list_category(prefix)` via SQLite
- `agent/chromadb_sync.py` — `sync_module_to_chromadb()` / `remove_module_from_chromadb()` + `init()` dependency injection
- `agent/tools.py` — `AGENT_TOOLS`, `AGENT_FUNCTION_MAP`, `DESTRUCTIVE_ACTIONS`
- `agent/routes.py` — Blueprint factory for `/api/modules` REST endpoints
- `agent/chat_handlers.py` — `handle_tool_call()` + `handle_confirmation()`
- `agent/storage.py` — shim that re-exports from `agent/db.py`
- `ingest_sources.py` — bulk ingestion: PDFs, blog posts, website pages, BUSA site
- `classifications.db` — SQLite module database (runtime-created)
- `tests/` — pytest suite (~101 tests across 5 files)

**Infrastructure**
- `Makefile` — dual-mode automation (primary ops tool)
- `docker-compose.yml` / `Dockerfile` / `chatbot-frontend/Dockerfile`

## Critical Implementation Details

### Port Configuration
- Backend: **5001** always. `ingest_sources.py` line 13 must use 5001 (not 5000).
- Frontend: **80** (Docker) or **5176** (native). Redis: **6379**.

### Environment Variables (`.env`)
```
OPENAI_API_KEY=sk-...
PORT=5001
FLASK_ENV=production        # IMPORTANT: controls ChromaDB fail-fast behavior
CORS_ORIGINS=http://localhost,http://localhost:80
REDIS_URL=redis://redis:6379/0
DEEPSEEK_API_KEY=sk-...     # Optional: cheaper primary model
DEEPINFRA_API_KEY=...       # Required for PNG OCR
```

### ChromaDB Initialization
`app2.py` attempts `chromadb.PersistentClient`. On failure:
- **If `FLASK_ENV=production` (default)**: raises `RuntimeError` immediately — no silent fallback
- **If `FLASK_ENV=development`**: falls back to in-memory, sets `app.config["CHROMADB_IN_MEMORY"] = True`

`GET /api/health` includes `"chromadb_in_memory": bool` in its response.

### SQLite Classifications Schema
```sql
classifications: id, code TEXT UNIQUE, name TEXT NOT NULL, description,
                 sheet, category, source ('xlsx'|'agent'), created_at, updated_at
```
- `source='xlsx'`: imported from XLSX ingestion
- `source='agent'`: added via chat/REST API
- Category derived from code prefix (everything before the last `.`)
- XLSX ingestion upserts rows; `init_db()` migrates from `modules_db.json` if present

### Agent Package Architecture

**Dependency injection** (avoids circular imports):
```python
# app2.py startup order:
init_classifications_db()                          # SQLite schema + JSON migration
init_agent_chromadb(collection, get_embedding_cached)
modules_bp = create_modules_blueprint(limiter, sanitize_input)
app.register_blueprint(modules_bp)
```

**Import hierarchy** (no circular deps):
```
agent/db.py           ← stdlib only
agent/chromadb_sync.py ← late-bound deps via init()
agent/crud.py          ← db + chromadb_sync
agent/tools.py         ← crud
agent/routes.py        ← crud (Blueprint factory)
agent/chat_handlers.py ← tools + crud
agent/storage.py       ← re-exports agent/db.py
```

### Agent Tools

| Tool | Destructive? |
|------|-------------|
| `get_module` | No |
| `list_modules` | No (capped at 50 rows) |
| `list_category(prefix)` | No (capped at 100 rows; use over list_modules for BIM prefix queries) |
| `add_module` | No |
| `update_module` | **Yes** — requires confirmation |
| `delete_module` | **Yes** — requires confirmation |

### SQLite/ChromaDB Atomicity
All write ops (`add`, `update`, `delete`) in `crud.py` follow this pattern:
1. Execute SQL (no commit)
2. Sync to ChromaDB (raises on failure — no swallowed exceptions)
3. `conn.commit()` only if sync succeeded; `conn.rollback()` on any exception

`chromadb_sync.py` functions propagate exceptions — callers handle rollback.

### REST API Modules Endpoints

| Method | Endpoint | Notes |
|--------|----------|-------|
| GET | `/api/modules` | |
| GET | `/api/modules/<name>` | |
| GET | `/api/modules/category/<prefix>` | LIKE-escaped prefix |
| POST | `/api/modules` | |
| PUT | `/api/modules/<name>?confirm=true` | **Requires `?confirm=true`** → 409 without it |
| DELETE | `/api/modules/<name>?confirm=true` | **Requires `?confirm=true`** → 409 without it |

409 response includes `"pending_action"` payload for frontend to display confirmation UI.

### Document Formats
Supported: **PDF, CSV, PNG** (OCR), **XLSX** (upserts into `classifications.db`)
Rejected (400): DOCX, PPTX, TXT

XLSX ingestion: column B → code, C → name, D → description; sheet name stored; category derived from code prefix.

### Caching
- OpenAI embeddings cached 24h (by content hash)
- API responses cached 5 minutes
- Redis preferred; in-memory fallback

## Testing

**Test files:**
- `tests/test_document_processing.py` — file extraction, PNG OCR
- `tests/test_api_endpoints.py` — API integration + health endpoint flags
- `tests/test_module_management.py` — module CRUD, REST API, atomicity, wildcard escaping
- `tests/test_chat_handlers.py` — `handle_tool_call()`, `handle_confirmation()`, malformed JSON
- `tests/test_xlsx_ingestion.py` — XLSX parsing, upsert, category derivation

**Test isolation pattern** (SQLite):
```python
@pytest.fixture
def temp_modules_db(tmp_path):
    with patch("agent.db._DB_PATH", str(tmp_path / "test.db")):
        # clear thread-local, init schema, yield, cleanup
```
Patch target is `agent.db._DB_PATH` (not `agent.storage.MODULES_DB_PATH`).

**ChromaDB mock pattern:**
```python
@patch("agent.chromadb_sync._collection")
@patch("agent.chromadb_sync._get_embedding", return_value=[0.1] * 1536)
```

## Adding New Document Sources

1. Place files in `./data/`
2. For new website URLs, update `ingest_sources.py`:
   - Blog posts: WordPress API section (~line 158)
   - Website pages: `syntec_urls` list (~line 221)
3. `make ingest` → `make db-stats`

## Data Persistence

- ChromaDB: `./chroma_db/` (backup: `make db-backup`)
- SQLite: `classifications.db` (project root)
- Redis: `redis_data` Docker volume
- All persist across `make down/up`; only `make clean` removes volumes
