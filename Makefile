# ============================================================================
# AI Chatbot - Dual-Mode Makefile (Docker Compose + Native Development)
# ============================================================================

# MODE selection: docker (default) or native
MODE ?= docker

# ANSI color codes
GREEN := \033[0;32m
YELLOW := \033[1;33m
RED := \033[0;31m
BLUE := \033[0;34m
CYAN := \033[0;36m
NC := \033[0m

# Project settings
BACKUP_DIR := ./backups
TIMESTAMP := $(shell date +%Y%m%d_%H%M%S)
COMPOSE := docker compose
PYTHON := python3
VENV_PYTHON := venv/bin/python3
VENV_PIP := venv/bin/pip3
FRONTEND_DIR := chatbot-frontend

# Mode-specific settings
ifeq ($(MODE),docker)
    MODE_NAME := Docker Compose
    BACKEND_URL := http://localhost:5001
    FRONTEND_URL := http://localhost:80
else ifeq ($(MODE),native)
    MODE_NAME := Native/Local
    BACKEND_URL := http://localhost:5001
    FRONTEND_URL := http://localhost:5176
else
    $(error Invalid MODE=$(MODE). Use MODE=docker or MODE=native)
endif

# ============================================================================
# Default Target
# ============================================================================
.DEFAULT_GOAL := help

# ============================================================================
# Help System
# ============================================================================
.PHONY: help
help:
	@echo "$(BLUE)╔════════════════════════════════════════════════════╗$(NC)"
	@echo "$(BLUE)║     AI Chatbot - Management Makefile              ║$(NC)"
	@echo "$(BLUE)╚════════════════════════════════════════════════════╝$(NC)"
	@echo ""
	@echo "$(CYAN)Current MODE: $(MODE_NAME)$(NC)"
	@echo "$(CYAN)Change mode: make up MODE=docker  or  make up MODE=native$(NC)"
	@echo ""
	@echo "$(GREEN)Service Management:$(NC)"
	@echo "  make up/start        - Start all services"
	@echo "  make down/stop       - Stop all services"
	@echo "  make restart         - Restart all services"
	@echo "  make build           - Build Docker images (docker mode only)"
	@echo "  make rebuild         - Rebuild (no cache, docker mode only)"
	@echo "  make ps/status       - Show running containers/processes"
	@echo ""
	@echo "$(GREEN)Individual Service Control:$(NC)"
	@echo "  make backend-start   - Start backend only"
	@echo "  make backend-stop    - Stop backend only"
	@echo "  make backend-restart - Restart backend only"
	@echo "  make backend-build   - Build backend image (docker mode)"
	@echo "  make backend-rebuild - Rebuild backend (no cache, docker mode)"
	@echo "  make frontend-start  - Start frontend only"
	@echo "  make frontend-stop   - Stop frontend only"
	@echo "  make frontend-restart - Restart frontend only"
	@echo "  make frontend-build  - Build frontend image (docker mode)"
	@echo "  make frontend-rebuild - Rebuild frontend (no cache, docker mode)"
	@echo "  make redis-start     - Start redis only"
	@echo "  make redis-stop      - Stop redis only"
	@echo "  make redis-restart   - Restart redis only"
	@echo ""
	@echo "$(GREEN)Logs:$(NC)"
	@echo "  make logs            - Show all logs"
	@echo "  make logs-backend    - Backend logs only"
	@echo "  make logs-frontend   - Frontend logs only"
	@echo "  make logs-redis      - Redis logs only"
	@echo ""
	@echo "$(GREEN)Database Management:$(NC)"
	@echo "  make db-reset        - Reset ChromaDB (with confirmation)"
	@echo "  make db-backup       - Backup ChromaDB to timestamped archive"
	@echo "  make db-restore BACKUP=<file> - Restore from backup"
	@echo "  make db-stats        - Show database statistics"
	@echo "  make db-size         - Show database size"
	@echo "  make db-list-backups - List available backups"
	@echo "  make ingest          - Run document ingestion script"
	@echo ""
	@echo "$(GREEN)Utilities:$(NC)"
	@echo "  make shell-backend   - Open backend shell"
	@echo "  make shell-frontend  - Open frontend shell (docker mode only)"
	@echo "  make clean           - Remove containers/volumes"
	@echo "  make health-check    - Check service health"
	@echo "  make show-mode       - Display current mode details"

# ============================================================================
# Mode Display
# ============================================================================
.PHONY: show-mode
show-mode:
	@echo "$(CYAN)═══════════════════════════════════════$(NC)"
	@echo "$(CYAN)Current MODE: $(MODE_NAME)$(NC)"
	@echo "$(CYAN)Backend URL: $(BACKEND_URL)$(NC)"
	@echo "$(CYAN)Frontend URL: $(FRONTEND_URL)$(NC)"
	@echo "$(CYAN)═══════════════════════════════════════$(NC)"

# ============================================================================
# Service Management - All Services
# ============================================================================
.PHONY: up start
up start: show-mode
ifeq ($(MODE),docker)
	@echo "$(BLUE)[Docker] Starting all services...$(NC)"
	@$(COMPOSE) up -d
	@sleep 3
	@echo "$(GREEN)✓ Services started in Docker mode$(NC)"
	@$(COMPOSE) ps
else
	@echo "$(BLUE)[Native] Starting all services...$(NC)"
	@$(MAKE) _native-redis-start
	@$(MAKE) _native-backend-start
	@$(MAKE) _native-frontend-start
	@echo "$(GREEN)✓ Services started in native mode$(NC)"
	@echo "$(CYAN)Backend: $(BACKEND_URL)$(NC)"
	@echo "$(CYAN)Frontend: $(FRONTEND_URL)$(NC)"
endif

.PHONY: down stop
down stop: show-mode
ifeq ($(MODE),docker)
	@echo "$(BLUE)[Docker] Stopping all services...$(NC)"
	@$(COMPOSE) down
	@echo "$(GREEN)✓ Services stopped$(NC)"
else
	@echo "$(BLUE)[Native] Stopping all services...$(NC)"
	@$(MAKE) _native-frontend-stop
	@$(MAKE) _native-backend-stop
	@$(MAKE) _native-redis-stop
	@echo "$(GREEN)✓ Services stopped$(NC)"
endif

.PHONY: restart
restart: show-mode
	@echo "$(BLUE)Restarting all services...$(NC)"
	@$(MAKE) down MODE=$(MODE)
	@sleep 1
	@$(MAKE) up MODE=$(MODE)

.PHONY: build
build:
ifeq ($(MODE),docker)
	@echo "$(BLUE)[Docker] Building images...$(NC)"
	@$(COMPOSE) build
	@echo "$(GREEN)✓ Build complete$(NC)"
else
	@echo "$(YELLOW)⚠ Build target only available in Docker mode$(NC)"
	@echo "In native mode, dependencies are installed automatically on startup"
endif

.PHONY: rebuild
rebuild:
ifeq ($(MODE),docker)
	@echo "$(BLUE)[Docker] Rebuilding images (no cache)...$(NC)"
	@$(COMPOSE) build --no-cache
	@echo "$(GREEN)✓ Rebuild complete$(NC)"
else
	@echo "$(YELLOW)⚠ Rebuild target only available in Docker mode$(NC)"
endif

.PHONY: ps status
ps status:
ifeq ($(MODE),docker)
	@$(COMPOSE) ps
else
	@echo "$(CYAN)Native Mode - Running Processes:$(NC)"
	@echo ""
	@echo "$(BLUE)Backend:$(NC)"
	@if [ -f /tmp/backend.pid ] && kill -0 $$(cat /tmp/backend.pid) 2>/dev/null; then \
		echo "  $(GREEN)✓ Running (PID: $$(cat /tmp/backend.pid))$(NC)"; \
	else \
		echo "  $(RED)✗ Not running$(NC)"; \
	fi
	@echo ""
	@echo "$(BLUE)Frontend:$(NC)"
	@if [ -f /tmp/frontend.pid ] && kill -0 $$(cat /tmp/frontend.pid) 2>/dev/null; then \
		echo "  $(GREEN)✓ Running (PID: $$(cat /tmp/frontend.pid))$(NC)"; \
	else \
		echo "  $(RED)✗ Not running$(NC)"; \
	fi
	@echo ""
	@echo "$(BLUE)Redis:$(NC)"
	@if docker ps | grep -q syntec-ai-redis; then \
		echo "  $(GREEN)✓ Running (Docker container)$(NC)"; \
	else \
		echo "  $(RED)✗ Not running$(NC)"; \
	fi
endif

# ============================================================================
# Native Mode Helpers (Internal Targets)
# ============================================================================
.PHONY: _native-redis-start
_native-redis-start:
	@echo "$(BLUE)  Starting Redis container...$(NC)"
	@docker run -d --name syntec-ai-redis -p 6379:6379 redis:7-alpine 2>/dev/null || \
		docker start syntec-ai-redis 2>/dev/null || true
	@sleep 1
	@echo "$(GREEN)  ✓ Redis started$(NC)"

.PHONY: _native-backend-start
_native-backend-start:
	@echo "$(BLUE)  Starting backend (venv/Python)...$(NC)"
	@if [ ! -d "venv" ]; then \
		echo "$(YELLOW)  ⚠ venv not found, creating...$(NC)"; \
		$(PYTHON) -m venv venv; \
		echo "$(BLUE)  Installing dependencies...$(NC)"; \
		$(VENV_PIP) install -r requirements.txt; \
	fi
	@$(VENV_PYTHON) app2.py > /tmp/backend.log 2>&1 & echo $$! > /tmp/backend.pid
	@sleep 2
	@echo "$(GREEN)  ✓ Backend started (PID: $$(cat /tmp/backend.pid))$(NC)"
	@echo "$(CYAN)    Logs: tail -f /tmp/backend.log$(NC)"

.PHONY: _native-frontend-start
_native-frontend-start:
	@echo "$(BLUE)  Starting frontend (Vite dev server)...$(NC)"
	@if [ ! -d "$(FRONTEND_DIR)/node_modules" ]; then \
		echo "$(YELLOW)  ⚠ node_modules not found, installing...$(NC)"; \
		cd $(FRONTEND_DIR) && npm install; \
	fi
	@cd $(FRONTEND_DIR) && npm run dev > /tmp/frontend.log 2>&1 & echo $$! > /tmp/frontend.pid
	@sleep 2
	@echo "$(GREEN)  ✓ Frontend started (PID: $$(cat /tmp/frontend.pid))$(NC)"
	@echo "$(CYAN)    Logs: tail -f /tmp/frontend.log$(NC)"

.PHONY: _native-backend-stop
_native-backend-stop:
	@echo "$(BLUE)  Stopping backend...$(NC)"
	@if [ -f /tmp/backend.pid ]; then \
		kill $$(cat /tmp/backend.pid) 2>/dev/null || true; \
		rm /tmp/backend.pid; \
	fi
	@pkill -f "python.*app2.py" 2>/dev/null || true
	@echo "$(GREEN)  ✓ Backend stopped$(NC)"

.PHONY: _native-frontend-stop
_native-frontend-stop:
	@echo "$(BLUE)  Stopping frontend...$(NC)"
	@if [ -f /tmp/frontend.pid ]; then \
		kill $$(cat /tmp/frontend.pid) 2>/dev/null || true; \
		rm /tmp/frontend.pid; \
	fi
	@pkill -f "vite" 2>/dev/null || true
	@echo "$(GREEN)  ✓ Frontend stopped$(NC)"

.PHONY: _native-redis-stop
_native-redis-stop:
	@echo "$(BLUE)  Stopping Redis...$(NC)"
	@docker stop syntec-ai-redis 2>/dev/null || true
	@echo "$(GREEN)  ✓ Redis stopped$(NC)"

# ============================================================================
# Individual Service Control - Backend
# ============================================================================
.PHONY: backend-start backend-up
backend-start backend-up:
ifeq ($(MODE),docker)
	@echo "$(BLUE)[Docker] Starting backend service...$(NC)"
	@$(COMPOSE) up -d backend
	@echo "$(GREEN)✓ Backend started$(NC)"
else
	@$(MAKE) _native-backend-start
endif

.PHONY: backend-stop backend-down
backend-stop backend-down:
ifeq ($(MODE),docker)
	@echo "$(BLUE)[Docker] Stopping backend service...$(NC)"
	@$(COMPOSE) stop backend
	@echo "$(GREEN)✓ Backend stopped$(NC)"
else
	@$(MAKE) _native-backend-stop
endif

.PHONY: backend-restart
backend-restart:
ifeq ($(MODE),docker)
	@echo "$(BLUE)[Docker] Restarting backend service...$(NC)"
	@$(COMPOSE) restart backend
	@echo "$(GREEN)✓ Backend restarted$(NC)"
else
	@$(MAKE) backend-stop MODE=$(MODE)
	@sleep 1
	@$(MAKE) backend-start MODE=$(MODE)
endif

.PHONY: backend-build
backend-build:
ifeq ($(MODE),docker)
	@echo "$(BLUE)[Docker] Building backend image...$(NC)"
	@$(COMPOSE) build backend
	@echo "$(GREEN)✓ Backend built$(NC)"
else
	@echo "$(YELLOW)⚠ Build target only available in Docker mode$(NC)"
endif

.PHONY: backend-rebuild
backend-rebuild:
ifeq ($(MODE),docker)
	@echo "$(BLUE)[Docker] Rebuilding backend image (no cache)...$(NC)"
	@$(COMPOSE) build --no-cache backend
	@echo "$(GREEN)✓ Backend rebuilt$(NC)"
else
	@echo "$(YELLOW)⚠ Rebuild target only available in Docker mode$(NC)"
endif

# ============================================================================
# Individual Service Control - Frontend
# ============================================================================
.PHONY: frontend-start frontend-up
frontend-start frontend-up:
ifeq ($(MODE),docker)
	@echo "$(BLUE)[Docker] Starting frontend service...$(NC)"
	@$(COMPOSE) up -d frontend
	@echo "$(GREEN)✓ Frontend started$(NC)"
else
	@$(MAKE) _native-frontend-start
endif

.PHONY: frontend-stop frontend-down
frontend-stop frontend-down:
ifeq ($(MODE),docker)
	@echo "$(BLUE)[Docker] Stopping frontend service...$(NC)"
	@$(COMPOSE) stop frontend
	@echo "$(GREEN)✓ Frontend stopped$(NC)"
else
	@$(MAKE) _native-frontend-stop
endif

.PHONY: frontend-restart
frontend-restart:
ifeq ($(MODE),docker)
	@echo "$(BLUE)[Docker] Restarting frontend service...$(NC)"
	@$(COMPOSE) restart frontend
	@echo "$(GREEN)✓ Frontend restarted$(NC)"
else
	@$(MAKE) frontend-stop MODE=$(MODE)
	@sleep 1
	@$(MAKE) frontend-start MODE=$(MODE)
endif

.PHONY: frontend-build
frontend-build:
ifeq ($(MODE),docker)
	@echo "$(BLUE)[Docker] Building frontend image...$(NC)"
	@$(COMPOSE) build frontend
	@echo "$(GREEN)✓ Frontend built$(NC)"
else
	@echo "$(YELLOW)⚠ Build target only available in Docker mode$(NC)"
endif

.PHONY: frontend-rebuild
frontend-rebuild:
ifeq ($(MODE),docker)
	@echo "$(BLUE)[Docker] Rebuilding frontend image (no cache)...$(NC)"
	@$(COMPOSE) build --no-cache frontend
	@echo "$(GREEN)✓ Frontend rebuilt$(NC)"
else
	@echo "$(YELLOW)⚠ Rebuild target only available in Docker mode$(NC)"
endif

# ============================================================================
# Individual Service Control - Redis
# ============================================================================
.PHONY: redis-start redis-up
redis-start redis-up:
ifeq ($(MODE),docker)
	@echo "$(BLUE)[Docker] Starting redis service...$(NC)"
	@$(COMPOSE) up -d redis
	@echo "$(GREEN)✓ Redis started$(NC)"
else
	@$(MAKE) _native-redis-start
endif

.PHONY: redis-stop redis-down
redis-stop redis-down:
ifeq ($(MODE),docker)
	@echo "$(BLUE)[Docker] Stopping redis service...$(NC)"
	@$(COMPOSE) stop redis
	@echo "$(YELLOW)⚠ Warning: Backend depends on Redis$(NC)"
	@echo "$(GREEN)✓ Redis stopped$(NC)"
else
	@$(MAKE) _native-redis-stop
	@echo "$(YELLOW)⚠ Warning: Backend depends on Redis$(NC)"
endif

.PHONY: redis-restart
redis-restart:
ifeq ($(MODE),docker)
	@echo "$(BLUE)[Docker] Restarting redis service...$(NC)"
	@$(COMPOSE) restart redis
	@echo "$(GREEN)✓ Redis restarted$(NC)"
else
	@$(MAKE) redis-stop MODE=$(MODE)
	@sleep 1
	@$(MAKE) redis-start MODE=$(MODE)
endif

# ============================================================================
# Logs
# ============================================================================
.PHONY: logs
logs:
ifeq ($(MODE),docker)
	@$(COMPOSE) logs -f --tail=100
else
	@echo "$(CYAN)Native Mode - Viewing logs (Ctrl+C to exit)$(NC)"
	@echo "$(BLUE)Backend log: /tmp/backend.log$(NC)"
	@echo "$(BLUE)Frontend log: /tmp/frontend.log$(NC)"
	@echo ""
	@tail -f /tmp/backend.log /tmp/frontend.log 2>/dev/null || \
		echo "$(YELLOW)⚠ No log files found. Start services first.$(NC)"
endif

.PHONY: logs-backend
logs-backend:
ifeq ($(MODE),docker)
	@$(COMPOSE) logs -f --tail=100 backend
else
	@echo "$(CYAN)Viewing backend log (Ctrl+C to exit)$(NC)"
	@tail -f /tmp/backend.log 2>/dev/null || \
		echo "$(YELLOW)⚠ Backend log not found. Start backend first.$(NC)"
endif

.PHONY: logs-frontend
logs-frontend:
ifeq ($(MODE),docker)
	@$(COMPOSE) logs -f --tail=100 frontend
else
	@echo "$(CYAN)Viewing frontend log (Ctrl+C to exit)$(NC)"
	@tail -f /tmp/frontend.log 2>/dev/null || \
		echo "$(YELLOW)⚠ Frontend log not found. Start frontend first.$(NC)"
endif

.PHONY: logs-redis
logs-redis:
ifeq ($(MODE),docker)
	@$(COMPOSE) logs -f --tail=100 redis
else
	@echo "$(CYAN)Viewing Redis container logs (Ctrl+C to exit)$(NC)"
	@docker logs -f syntec-ai-redis 2>/dev/null || \
		echo "$(YELLOW)⚠ Redis container not running$(NC)"
endif

# ============================================================================
# Database Management
# ============================================================================
.PHONY: db-reset
db-reset:
	@echo "$(YELLOW)⚠ WARNING: This will delete the entire ChromaDB database!$(NC)"
	@read -p "Type 'yes' to continue: " confirm; \
	if [ "$$confirm" = "yes" ]; then \
		echo "$(BLUE)Stopping services...$(NC)"; \
		$(MAKE) down MODE=$(MODE); \
		echo "$(BLUE)Deleting chroma_db directory...$(NC)"; \
		rm -rf ./chroma_db; \
		echo "$(BLUE)Restarting services...$(NC)"; \
		$(MAKE) up MODE=$(MODE); \
		echo "$(GREEN)✓ Database reset complete$(NC)"; \
	else \
		echo "$(RED)✗ Cancelled$(NC)"; \
	fi

.PHONY: db-backup
db-backup: | $(BACKUP_DIR)
	@echo "$(BLUE)Creating backup: chroma_db_$(TIMESTAMP).tar.gz$(NC)"
	@tar -czf $(BACKUP_DIR)/chroma_db_$(TIMESTAMP).tar.gz ./chroma_db 2>/dev/null || \
		(echo "$(YELLOW)⚠ chroma_db directory not found or empty$(NC)" && exit 1)
	@echo "$(GREEN)✓ Backup created$(NC)"
	@du -h $(BACKUP_DIR)/chroma_db_$(TIMESTAMP).tar.gz

$(BACKUP_DIR):
	@mkdir -p $(BACKUP_DIR)

.PHONY: db-restore
db-restore:
	@if [ -z "$(BACKUP)" ]; then \
		echo "$(RED)✗ Error: BACKUP parameter required$(NC)"; \
		echo "Usage: make db-restore BACKUP=chroma_db_20260105_120000.tar.gz"; \
		exit 1; \
	fi
	@if [ ! -f "$(BACKUP_DIR)/$(BACKUP)" ]; then \
		echo "$(RED)✗ Error: Backup not found: $(BACKUP_DIR)/$(BACKUP)$(NC)"; \
		echo "Available backups:"; \
		ls -lh $(BACKUP_DIR)/*.tar.gz 2>/dev/null || echo "  (none)"; \
		exit 1; \
	fi
	@echo "$(YELLOW)⚠ This will overwrite the current database$(NC)"
	@read -p "Continue? Type 'yes': " confirm; \
	if [ "$$confirm" = "yes" ]; then \
		echo "$(BLUE)Stopping services...$(NC)"; \
		$(MAKE) down MODE=$(MODE); \
		echo "$(BLUE)Removing old database...$(NC)"; \
		rm -rf ./chroma_db; \
		echo "$(BLUE)Extracting backup...$(NC)"; \
		tar -xzf $(BACKUP_DIR)/$(BACKUP); \
		echo "$(BLUE)Restarting services...$(NC)"; \
		$(MAKE) up MODE=$(MODE); \
		echo "$(GREEN)✓ Database restored from $(BACKUP)$(NC)"; \
	else \
		echo "$(RED)✗ Cancelled$(NC)"; \
	fi

.PHONY: db-stats
db-stats:
	@echo "$(BLUE)Fetching database statistics...$(NC)"
	@curl -s http://localhost:5001/api/stats | $(PYTHON) -m json.tool || \
		echo "$(RED)✗ Error: Backend not responding. Run 'make up' first$(NC)"

.PHONY: db-size
db-size:
	@echo "$(BLUE)ChromaDB directory size:$(NC)"
	@du -sh ./chroma_db 2>/dev/null || echo "$(YELLOW)⚠ chroma_db directory not found$(NC)"
	@echo ""
	@echo "$(BLUE)Breakdown:$(NC)"
	@du -sh ./chroma_db/* 2>/dev/null || true

.PHONY: db-list-backups
db-list-backups:
	@echo "$(BLUE)Available backups in $(BACKUP_DIR):$(NC)"
	@ls -lht $(BACKUP_DIR)/*.tar.gz 2>/dev/null || echo "$(YELLOW)⚠ No backups found$(NC)"

# ============================================================================
# Ingestion 
# ============================================================================
.PHONY: ingest
ingest:
	@echo "$(BLUE)Running ingestion script...$(NC)"
	@if [ "$(MODE)" = "docker" ]; then \
		if ! docker ps | grep -q syntec-ai-backend; then \
			echo "$(RED)✗ Error: Backend container not running. Run 'make up' first$(NC)"; \
			exit 1; \
		fi; \
	else \
		if [ ! -f /tmp/backend.pid ] || ! kill -0 $$(cat /tmp/backend.pid) 2>/dev/null; then \
			echo "$(RED)✗ Error: Backend not running. Run 'make up MODE=native' first$(NC)"; \
			exit 1; \
		fi; \
	fi
	@$(PYTHON) ingest_sources.py

# ============================================================================
# Shell Access
# ============================================================================
.PHONY: shell-backend
shell-backend:
ifeq ($(MODE),docker)
	@echo "$(BLUE)Opening bash shell in backend container...$(NC)"
	@docker exec -it syntec-ai-backend /bin/bash
else
	@echo "$(BLUE)Opening Python shell in venv...$(NC)"
	@$(VENV_PYTHON)
endif

.PHONY: shell-frontend
shell-frontend:
ifeq ($(MODE),docker)
	@echo "$(BLUE)Opening shell in frontend container...$(NC)"
	@docker exec -it syntec-ai-frontend /bin/sh
else
	@echo "$(YELLOW)⚠ Shell access not available in native mode$(NC)"
	@echo "Frontend is running with Vite dev server. Check logs with: make logs-frontend"
endif

# ============================================================================
# Cleanup
# ============================================================================
.PHONY: clean
clean:
ifeq ($(MODE),docker)
	@echo "$(YELLOW)Cleaning up Docker resources...$(NC)"
	@$(COMPOSE) down -v
	@docker system prune -f
	@echo "$(GREEN)✓ Cleanup complete$(NC)"
else
	@echo "$(YELLOW)Cleaning up native mode resources...$(NC)"
	@$(MAKE) down MODE=native
	@docker rm -f syntec-ai-redis 2>/dev/null || true
	@rm -f /tmp/backend.pid /tmp/frontend.pid
	@rm -f /tmp/backend.log /tmp/frontend.log
	@echo "$(GREEN)✓ Cleanup complete$(NC)"
endif

.PHONY: clean-all
clean-all:
ifeq ($(MODE),docker)
	@echo "$(YELLOW)Removing all Docker resources (images, containers, volumes)...$(NC)"
	@$(COMPOSE) down --rmi all -v
	@echo "$(GREEN)✓ Complete cleanup done$(NC)"
else
	@$(MAKE) clean MODE=native
	@echo "$(BLUE)Removing venv and node_modules...$(NC)"
	@rm -rf venv
	@rm -rf $(FRONTEND_DIR)/node_modules
	@echo "$(GREEN)✓ Complete cleanup done$(NC)"
endif

# ============================================================================
# Health Check
# ============================================================================
.PHONY: health-check
health-check:
	@echo "$(CYAN)═══════════════════════════════════════$(NC)"
	@echo "$(CYAN)Health Check - $(MODE_NAME)$(NC)"
	@echo "$(CYAN)═══════════════════════════════════════$(NC)"
	@echo ""
ifeq ($(MODE),docker)
	@echo "$(BLUE)Checking Docker containers...$(NC)"
	@for service in backend frontend redis; do \
		if docker ps --filter "name=syntec-ai-$$service" --filter "status=running" | grep -q syntec-ai-$$service; then \
			echo "  $(GREEN)✓ $$service is running$(NC)"; \
		else \
			echo "  $(RED)✗ $$service is not running$(NC)"; \
		fi; \
	done
else
	@echo "$(BLUE)Checking native processes...$(NC)"
	@if [ -f /tmp/backend.pid ] && kill -0 $$(cat /tmp/backend.pid) 2>/dev/null; then \
		echo "  $(GREEN)✓ Backend is running (PID: $$(cat /tmp/backend.pid))$(NC)"; \
	else \
		echo "  $(RED)✗ Backend is not running$(NC)"; \
	fi
	@if [ -f /tmp/frontend.pid ] && kill -0 $$(cat /tmp/frontend.pid) 2>/dev/null; then \
		echo "  $(GREEN)✓ Frontend is running (PID: $$(cat /tmp/frontend.pid))$(NC)"; \
	else \
		echo "  $(RED)✗ Frontend is not running$(NC)"; \
	fi
	@if docker ps | grep -q syntec-ai-redis; then \
		echo "  $(GREEN)✓ Redis is running (Docker container)$(NC)"; \
	else \
		echo "  $(RED)✗ Redis is not running$(NC)"; \
	fi
endif
	@echo ""
	@echo "$(BLUE)Checking backend API...$(NC)"
	@curl -s http://localhost:5001/api/health >/dev/null 2>&1 && \
		echo "  $(GREEN)✓ Backend API is healthy$(NC)" || \
		echo "  $(RED)✗ Backend API is not responding$(NC)"

# ============================================================================
# Phony Targets Declaration
# ============================================================================
.PHONY: help up start down stop restart build rebuild ps status show-mode \
        backend-start backend-up backend-stop backend-down backend-restart \
        backend-build backend-rebuild \
        frontend-start frontend-up frontend-stop frontend-down frontend-restart \
        frontend-build frontend-rebuild \
        redis-start redis-up redis-stop redis-down redis-restart \
        logs logs-backend logs-frontend logs-redis \
        db-reset db-backup db-restore db-stats db-size db-list-backups \
        ingest shell-backend shell-frontend clean clean-all health-check \
        _native-redis-start _native-backend-start _native-frontend-start \
        _native-redis-stop _native-backend-stop _native-frontend-stop
