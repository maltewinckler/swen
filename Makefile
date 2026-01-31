# SWEN Development Commands
# ==============================
# Run `make help` to see all available commands

.PHONY: help install dev backend frontend ml build test lint secrets clean pre-commit

# Default target
help:
	@echo "SWEN Development Commands"
	@echo "=============================="
	@echo ""
	@echo "Setup:"
	@echo "  make install      - Install all dependencies (backend + frontend + ml)"
	@echo "  make install-backend  - Install Python backend dependencies"
	@echo "  make install-frontend - Install npm dependencies"
	@echo "  make install-ml       - Install ML service dependencies"
	@echo ""
	@echo "Development:"
	@echo "  make dev          - Start both backend and frontend (requires 2 terminals)"
	@echo "  make backend      - Start backend API server (port 8000)"
	@echo "  make frontend     - Start frontend dev server (port 5173)"
	@echo "  make ml           - Start ML service (port 8001)"
	@echo ""
	@echo "Build:"
	@echo "  make build        - Build frontend for production"
	@echo ""
	@echo "Testing:"
	@echo "  make test         - Run all tests"
	@echo "  make test-backend - Run backend tests"
	@echo "  make test-ml      - Run ML service tests"
	@echo "  make test-cov     - Run tests with coverage"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint         - Run all linters"
	@echo "  make lint-backend - Run Python linters (ruff)"
	@echo "  make lint-frontend- Run frontend linter (eslint)"
	@echo "  make format       - Format Python code"
	@echo "  make pre-commit   - Run pre-commit on all files"
	@echo "  make pre-commit-install - Install pre-commit hooks"
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

install: install-backend install-frontend install-ml
	@echo "All dependencies installed"

install-backend:
	@echo "Installing Python backend dependencies..."
	uv sync --package swen-backend

install-frontend:
	@echo "Installing npm dependencies..."
	cd services/frontend && npm install

install-ml:
	@echo "Installing ML service dependencies..."
	uv sync --package swen-ml

# =============================================================================
# Development Servers
# =============================================================================

backend:
	@echo "Starting backend on http://127.0.0.1:8000..."
	uv run --package swen-backend uvicorn swen.presentation.api.app:app --reload --host 127.0.0.1 --port 8000

frontend:
	@echo "Starting frontend on http://localhost:5173..."
	cd services/frontend && npm run dev

ml:
	@echo "Starting ML service on http://127.0.0.1:8001..."
	uv run --package swen-ml uvicorn swen_ml.api.app:create_app --factory --reload --host 127.0.0.1 --port 8001

# Combined dev (prints instructions since we can't easily run both in one terminal)
dev:
	@echo "To run the full development stack, open 3 terminals:"
	@echo ""
	@echo "  Terminal 1: make backend   # API server (port 8000)"
	@echo "  Terminal 2: make frontend  # React app (port 5173)"
	@echo "  Terminal 3: make ml        # ML service (port 8001, optional)"
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

test: test-backend test-ml

test-backend:
	uv run --package swen-backend pytest services/backend/tests/

test-ml:
	uv run --package swen-ml pytest services/ml/tests/

test-cov:
	uv run --package swen-backend pytest services/backend/tests/ --cov=swen --cov-report=html --cov-report=term

# =============================================================================
# Code Quality
# =============================================================================

lint: lint-backend lint-frontend

lint-backend:
	uv run --package swen-backend ruff check services/backend/src/

lint-frontend:
	cd services/frontend && npm run lint

format:
	uv run --package swen-backend ruff format services/backend/src/
	uv run --package swen-backend ruff check --fix services/backend/src/

pre-commit:
	uv run --package swen-backend pre-commit run --all-files

pre-commit-install:
	uv run --package swen-backend pre-commit install

# =============================================================================
# Database
# =============================================================================

db-init:
	@echo "Initializing database tables..."
	uv run --package swen-backend db-init

db-reset:
	@echo "Resetting PostgreSQL databases..."
	uv run --package swen-backend db-reset
	uv run --package swen-ml ml-db-reset

db-reset-force:
	@echo "Resetting PostgreSQL databases (no confirmation)..."
	uv run --package swen-backend db-reset --force
	uv run --package swen-ml ml-db-reset --force

seed-demo:
	@echo "Seeding demo data for screenshots..."
	uv run --package swen-backend seed-demo

# =============================================================================
# Utilities
# =============================================================================

secrets:
	@echo "Generating secrets for config/config.yaml..."
	uv run --package swen-backend swen secrets generate

# =============================================================================
# Cleanup
# =============================================================================

clean:
	@echo "Cleaning build artifacts..."
	rm -rf services/frontend/dist
	rm -rf services/backend/.pytest_cache
	rm -rf services/ml/.pytest_cache
	rm -rf .coverage
	rm -rf htmlcov
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@echo "Cleaned"
