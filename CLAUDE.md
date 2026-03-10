# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Context

BIM Classification Agent for Syntec Group — XLSX ingestion + agent-mode chat for managing building classification codes. Uses semantic search and GPT-4o function calling.

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
- XLSX-only ingestion → SQLite classifications + ChromaDB embeddings
- Agentic BIM classification management via `agent/` package (OpenAI function calling)
- Only 3 endpoints: `/api/health`, `/api/ingest` (XLSX only), `/api/chat`

### Frontend (React + Vite)
- Dev port: 5176 (native) or 80 (Docker/Nginx)
- `SyntecChatWidget.jsx` — embeddable widget
- `ConfirmationModal.jsx` — confirmation gate for destructive agent actions

### Data Flow
1. XLSX files → `_upsert_xlsx_to_sqlite()` → SQLite `classifications` table + sheet text → ChromaDB embeddings
2. User query → embedding → ChromaDB similarity search (top 10, excludes blogs) → GPT-4o with agent tools
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
python -m pytest tests/ -v                           # All tests (71 tests across 4 files)
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
- `app2.py` — Flask app: 3 endpoints (health, ingest, chat), XLSX parsing, ChromaDB init, agent wiring
- `agent/db.py` — SQLite layer: `get_db()` (thread-local), `init_db()` (schema + JSON migration)
- `agent/crud.py` — CRUD + `list_category(prefix)` via SQLite
- `agent/chromadb_sync.py` — `sync_module_to_chromadb()` / `remove_module_from_chromadb()` + `init()` dependency injection
- `agent/tools.py` — `AGENT_TOOLS`, `AGENT_FUNCTION_MAP`, `DESTRUCTIVE_ACTIONS`
- `agent/routes.py` — Blueprint factory for `/api/modules` REST endpoints
- `agent/chat_handlers.py` — `handle_tool_call()` + `handle_confirmation()`
- `agent/storage.py` — shim that re-exports from `agent/db.py`
- `ingest_sources.py` — bulk ingestion: PDFs, blog posts, website pages, BUSA site
- `classifications.db` — SQLite module database (runtime-created)

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

### XLSX Ingestion (`/api/ingest`)
Only XLSX files are accepted — PDF, CSV, PNG, and all other formats return 400.

`_upsert_xlsx_to_sqlite()` handles multiple sheet formats via parser dispatch:
- `_parse_uniformat` — CSI/UniFormat codes (e.g., `04 05 13.A1`)
- `_parse_families` — family/type sheets
- `_parse_bim_filename` — BIM filename convention sheets
- `_parse_variable_data` — generic fallback

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

### Caching
- OpenAI embeddings cached 24h (by content hash)
- API responses cached 5 minutes
- Redis preferred; in-memory fallback

## Testing

**Test files (71 tests across 4 files):**
- `tests/test_api_endpoints.py` — XLSX-only ingest validation + health endpoint `chromadb_in_memory` flag
- `tests/test_module_management.py` — module CRUD, REST API, atomicity rollback, wildcard escaping, confirmation gate
- `tests/test_chat_handlers.py` — `handle_tool_call()`, `handle_confirmation()`, malformed JSON, tool chaining, safety cap
- `tests/test_xlsx_ingestion.py` — XLSX parsing (normalized + original formats), upsert, category derivation

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

1. Place XLSX files in `./data/`
2. For new website URLs, update `ingest_sources.py`:
   - Blog posts: WordPress API section (~line 158)
   - Website pages: `syntec_urls` list (~line 221)
3. `make ingest` → `make db-stats`

## Data Persistence

- ChromaDB: `./chroma_db/` (backup: `make db-backup`)
- SQLite: `classifications.db` (project root)
- Redis: `redis_data` Docker volume
- All persist across `make down/up`; only `make clean` removes volumes
