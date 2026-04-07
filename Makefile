.PHONY: help setup install-backend install-frontend test test-unit test-property lint format clean docker-up docker-down docker-prod-up docker-prod-down docker-prod-logs

help:
	@echo "VibeAnalytix Development Commands"
	@echo "=================================="
	@echo "setup              - Complete project setup"
	@echo "install-backend    - Install backend dependencies"
	@echo "install-frontend   - Install frontend dependencies"
	@echo "test               - Run all tests"
	@echo "test-unit          - Run unit tests"
	@echo "test-property      - Run property-based tests"
	@echo "lint               - Lint backend code"
	@echo "format             - Format backend code"
	@echo "clean              - Clean build artifacts and cache"
	@echo "docker-up          - Start Docker Compose services"
	@echo "docker-down        - Stop Docker Compose services"
	@echo "docker-logs        - View Docker logs"
	@echo "docker-prod-up     - Start production Docker Compose stack"
	@echo "docker-prod-down   - Stop production Docker Compose stack"
	@echo "docker-prod-logs   - View production stack logs"
	@echo "dev-backend        - Run backend dev server"
	@echo "dev-frontend       - Run frontend dev server"
	@echo "dev-worker         - Run Celery worker"
	@echo "dev-beat           - Run Celery beat scheduler"

setup: install-backend install-frontend
	@echo "Setup complete! Run 'make dev-backend' and 'make dev-frontend' to start"

install-backend:
	cd backend && pip install -e .

install-frontend:
	cd frontend && npm install

test:
	pytest tests/ -v

test-unit:
	pytest tests/unit/ -v

test-property:
	pytest tests/property/ -v

test-cov:
	pytest tests/ --cov=app --cov-report=html

lint:
	black --check app/
	ruff app/

format:
	black app/
	ruff --fix app/

clean:
	find . -type f -name '*.pyc' -delete
	find . -type d -name '__pycache__' -delete
	rm -rf build/ dist/ *.egg-info .pytest_cache/ .mypy_cache/ htmlcov/

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

docker-prod-up:
	docker compose -f docker-compose.prod.yml up -d --build

docker-prod-down:
	docker compose -f docker-compose.prod.yml down

docker-prod-logs:
	docker compose -f docker-compose.prod.yml logs -f

docker-restart:
	docker-compose restart

dev-backend:
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend:
	cd frontend && npm run dev

dev-worker:
	cd backend && celery -A app.celery_app worker --loglevel=info

dev-beat:
	cd backend && celery -A app.celery_app beat --loglevel=info

# Database setup
db-create:
	createdb vibeanalytix_db

db-drop:
	dropdb vibeanalytix_db

db-reset: db-drop db-create

# Docker database commands
docker-db-shell:
	docker-compose exec postgres psql -U postgres -d vibeanalytix_db

docker-redis-shell:
	docker-compose exec redis redis-cli

# Development shortcuts
check: format lint test
	@echo "✓ All checks passed!"

.DEFAULT_GOAL := help
