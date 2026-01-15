# SWEN Development Commands
# ==============================
# Run `make help` to see all available commands

.PHONY: help install dev backend frontend build test lint secrets clean

# Default target
help:
	@echo "SWEN Development Commands"
	@echo "=============================="
	@echo ""
	@echo "Setup:"
	@echo "  make install      - Install all dependencies (backend + frontend)"
	@echo "  make install-backend  - Install Python dependencies"
	@echo "  make install-frontend - Install npm dependencies"
	@echo ""
	@echo "Development:"
	@echo "  make dev          - Start both backend and frontend (requires 2 terminals)"
	@echo "  make backend      - Start backend API server (port 8000)"
	@echo "  make frontend     - Start frontend dev server (port 5173)"
	@echo "  make ollama       - Start Ollama server for AI features"
	@echo ""
	@echo "Build:"
	@echo "  make build        - Build frontend for production"
	@echo ""
	@echo "Testing:"
	@echo "  make test         - Run all tests"
	@echo "  make test-unit    - Run unit tests only"
	@echo "  make test-cov     - Run tests with coverage"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint         - Run all linters"
	@echo "  make lint-backend - Run Python linters (ruff)"
	@echo "  make lint-frontend- Run frontend linter (eslint)"
	@echo "  make format       - Format Python code"
	@echo ""
	@echo "Database:"
	@echo "  make db-init      - Initialize/create database tables"
	@echo "  make db-reset     - Reset database (WARNING: deletes data)"
	@echo "  make seed-demo    - Create demo user with sample transactions"
	@echo ""
	@echo "Utilities:"
	@echo "  make secrets      - Generate encryption key and JWT secret"
	@echo "  make clean        - Remove build artifacts"

# =============================================================================
# Setup
# =============================================================================

install: install-backend install-frontend
	@echo "All dependencies installed"

install-backend:
	@echo "Installing Python dependencies..."
	cd services/backend && poetry install

install-frontend:
	@echo "Installing npm dependencies..."
	cd services/frontend && npm install

# =============================================================================
# Development Servers
# =============================================================================

backend:
	@echo "Starting backend on http://127.0.0.1:8000..."
	cd services/backend && poetry run uvicorn swen.presentation.api.app:app --reload --host 127.0.0.1 --port 8000

frontend:
	@echo "Starting frontend on http://localhost:5173..."
	cd services/frontend && npm run dev

ollama:
	@echo "Starting Ollama server..."
	ollama serve

# Combined dev (prints instructions since we can't easily run both in one terminal)
dev:
	@echo "To run the full development stack, open 3 terminals:"
	@echo ""
	@echo "  Terminal 1: make ollama    # AI features (optional)"
	@echo "  Terminal 2: make backend   # API server"
	@echo "  Terminal 3: make frontend  # React app"
	@echo ""
	@echo "Or use tmux/screen to run all in one terminal."

# =============================================================================
# Build
# =============================================================================

build:
	@echo "Building frontend for production..."
	cd services/frontend && npm run build

# =============================================================================
# Testing
# =============================================================================

test:
	cd services/backend && poetry run pytest

test-unit:
	cd services/backend && poetry run pytest tests/unit/ -v

test-cov:
	cd services/backend && poetry run pytest --cov=swen --cov-report=html --cov-report=term

# =============================================================================
# Code Quality
# =============================================================================

lint: lint-backend lint-frontend

lint-backend:
	cd services/backend && poetry run ruff check src/

lint-frontend:
	cd services/frontend && npm run lint

format:
	cd services/backend && poetry run ruff format src/
	cd services/backend && poetry run ruff check --fix src/

# =============================================================================
# Database
# =============================================================================

db-init:
	@echo "Initializing database tables..."
	cd services/backend && poetry run db-init

db-reset:
	@echo "Resetting PostgreSQL database..."
	cd services/backend && poetry run db-reset

db-reset-force:
	@echo "Resetting PostgreSQL database (no confirmation)..."
	cd services/backend && poetry run db-reset --force

seed-demo:
	@echo "Seeding demo data for screenshots..."
	cd services/backend && poetry run seed-demo

# =============================================================================
# Utilities
# =============================================================================

secrets:
	@echo "Generating secrets for config/config.yaml..."
	cd services/backend && poetry run swen secrets generate

# =============================================================================
# Cleanup
# =============================================================================

clean:
	@echo "Cleaning build artifacts..."
	rm -rf services/frontend/dist
	rm -rf services/backend/.pytest_cache
	rm -rf .coverage
	rm -rf htmlcov
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@echo "Cleaned"
