# =============================================================================
# Jersey Ice Cream Demand Intelligence Platform — Makefile
# =============================================================================
# Developer commands for local development, testing, and deployment.
#
# Usage:
#   make help          — Show all available commands
#   make dev           — Start full development stack
#   make test          — Run all tests
#   make migrate       — Run database migrations
# =============================================================================

.PHONY: help dev dev-down dev-logs test test-unit test-integration lint format \
        migrate migrate-create db-reset docker-build docker-push \
        backend-shell db-shell redis-cli clean

# ─── Variables ───────────────────────────────────────────────────────────────

COMPOSE         := docker compose
COMPOSE_FILE    := docker-compose.yml
BACKEND_SERVICE := backend
DB_SERVICE      := postgres
REDIS_SERVICE   := redis

# Python
PYTHON          := python3
PYTEST          := pytest
RUFF            := ruff
BLACK           := black
ALEMBIC         := alembic

# Node
NPM             := npm
NEXT            := npx next

# ─── Help ────────────────────────────────────────────────────────────────────

help: ## Show this help message
	@echo ""
	@echo "  Jersey Ice Cream Platform — Developer Commands"
	@echo "  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""

# ─── Development ─────────────────────────────────────────────────────────────

dev: ## Start full development stack (all services)
	$(COMPOSE) -f $(COMPOSE_FILE) up --build -d
	@echo ""
	@echo "  ✅ Development stack is running"
	@echo "  ─────────────────────────────────"
	@echo "  Backend API:    http://localhost:8000"
	@echo "  API Docs:       http://localhost:8000/docs"
	@echo "  Frontend:       http://localhost:3000"
	@echo "  MinIO Console:  http://localhost:9001"
	@echo "  Kafka UI:       http://localhost:8080"
	@echo "  Grafana:        http://localhost:3001"
	@echo ""

dev-down: ## Stop development stack
	$(COMPOSE) -f $(COMPOSE_FILE) down

dev-logs: ## Tail logs from all services
	$(COMPOSE) -f $(COMPOSE_FILE) logs -f

dev-logs-backend: ## Tail backend logs only
	$(COMPOSE) -f $(COMPOSE_FILE) logs -f $(BACKEND_SERVICE)

# ─── Testing ─────────────────────────────────────────────────────────────────

test: ## Run all tests
	cd backend && $(PYTEST) tests/ -v --tb=short --cov=app --cov-report=term-missing

test-unit: ## Run unit tests only
	cd backend && $(PYTEST) tests/unit/ -v --tb=short

test-integration: ## Run integration tests (requires running services)
	cd backend && $(PYTEST) tests/integration/ -v --tb=short

test-frontend: ## Run frontend tests
	cd frontend && $(NPM) test

test-e2e: ## Run end-to-end tests
	cd backend && $(PYTEST) tests/e2e/ -v --tb=short

# ─── Code Quality ────────────────────────────────────────────────────────────

lint: ## Run all linters
	cd backend && $(RUFF) check app/ tests/
	cd frontend && $(NPM) run lint

format: ## Format all code
	cd backend && $(RUFF) format app/ tests/
	cd backend && $(RUFF) check --fix app/ tests/
	cd frontend && $(NPM) run format 2>/dev/null || true

security-scan: ## Run security scanners
	cd backend && bandit -r app/ -c pyproject.toml
	cd frontend && $(NPM) audit --production

type-check: ## Run type checkers
	cd backend && mypy app/
	cd frontend && $(NPM) run type-check 2>/dev/null || npx tsc --noEmit

# ─── Database ────────────────────────────────────────────────────────────────

migrate: ## Run database migrations to head
	cd backend && $(ALEMBIC) upgrade head

migrate-create: ## Create a new migration (usage: make migrate-create MSG="add_users_table")
	cd backend && $(ALEMBIC) revision --autogenerate -m "$(MSG)"

migrate-down: ## Downgrade one migration
	cd backend && $(ALEMBIC) downgrade -1

migrate-history: ## Show migration history
	cd backend && $(ALEMBIC) history --verbose

db-reset: ## Reset database (WARNING: destroys all data)
	@echo "⚠️  This will destroy all data. Press Ctrl+C to cancel."
	@sleep 3
	$(COMPOSE) -f $(COMPOSE_FILE) stop $(DB_SERVICE)
	$(COMPOSE) -f $(COMPOSE_FILE) rm -f $(DB_SERVICE)
	docker volume rm jersey_icecream_solution_pgdata 2>/dev/null || true
	$(COMPOSE) -f $(COMPOSE_FILE) up -d $(DB_SERVICE)
	@echo "Waiting for PostgreSQL to start..."
	@sleep 5
	cd backend && $(ALEMBIC) upgrade head
	@echo "✅ Database reset complete"

# ─── Docker ──────────────────────────────────────────────────────────────────

docker-build: ## Build all Docker images
	$(COMPOSE) -f $(COMPOSE_FILE) build

docker-build-backend: ## Build backend Docker image only
	docker build -t jersey-backend:latest ./backend

docker-build-frontend: ## Build frontend Docker image only
	docker build -t jersey-frontend:latest ./frontend

docker-build-ai: ## Build AI pipeline Docker image
	docker build -t jersey-ai:latest ./ai

# ─── Shell Access ────────────────────────────────────────────────────────────

backend-shell: ## Open a shell in the backend container
	$(COMPOSE) -f $(COMPOSE_FILE) exec $(BACKEND_SERVICE) /bin/bash

db-shell: ## Open psql shell
	$(COMPOSE) -f $(COMPOSE_FILE) exec $(DB_SERVICE) psql -U jersey -d jersey_platform

redis-cli: ## Open Redis CLI
	$(COMPOSE) -f $(COMPOSE_FILE) exec $(REDIS_SERVICE) redis-cli

# ─── AI Pipeline ─────────────────────────────────────────────────────────────

ai-train-yolo: ## Train YOLO model for cart photo analysis
	cd ai && $(PYTHON) -m models.yolo.train

ai-train-forecast: ## Train demand forecasting models
	cd ai && $(PYTHON) -m models.forecasting.xgboost_model

ai-evaluate: ## Evaluate all AI models
	cd ai && $(PYTHON) -m pipelines.evaluation_pipeline

# ─── Cleanup ─────────────────────────────────────────────────────────────────

clean: ## Remove all generated files and caches
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name node_modules -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .next -exec rm -rf {} + 2>/dev/null || true
	rm -rf backend/.coverage backend/htmlcov
	@echo "✅ Cleaned"
