# Makefile for SMS Campaign Generation API

.PHONY: help install install-dev run test lint format clean docker-build docker-run docker-stop

# Default target
help:
	@echo "Available commands:"
	@echo "  install      - Install production dependencies"
	@echo "  install-dev  - Install development dependencies"
	@echo "  run          - Run the API server"
	@echo "  test         - Run tests"
	@echo "  lint         - Run linting"
	@echo "  format       - Format code"
	@echo "  clean        - Clean Python cache"
	@echo "  docker-build - Build Docker image"
	@echo "  docker-run   - Run with Docker Compose"
	@echo "  docker-stop  - Stop Docker Compose"
	@echo "  seed-db      - Seed template database"
	@echo "  health       - Check API health"

# Installation
install:
	pip install -r requirements-prod.txt

install-dev:
	pip install -r requirements.txt

# Running
run:
	python -m src.main

run-dev:
	python -m src.main --reload

# Testing
test:
	pytest tests/ -v

test-coverage:
	pytest tests/ --cov=src --cov-report=html

# Code quality
lint:
	flake8 src/ tests/
	pylint src/
	mypy src/

format:
	black src/ tests/
	isort src/ tests/

format-check:
	black --check src/ tests/
	isort --check-only src/ tests/

# Cleanup
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name "*.egg" -exec rm -rf {} +
	find . -type d -name "*.dist-info" -exec rm -rf {} +

# Docker
docker-build:
	docker build -t sms-campaign-api .

docker-run:
	docker-compose up -d

docker-stop:
	docker-compose down

docker-logs:
	docker-compose logs -f api

docker-shell:
	docker-compose exec api bash

# Database and templates
seed-db:
	curl -X POST http://localhost:8000/api/v1/campaigns/templates/seed \
		-H "Authorization: Bearer dev-key" \
		-H "Content-Type: application/json"

# Health checks
health:
	curl -f http://localhost:8000/health || echo "API not running"

docs:
	@echo "Opening API documentation..."
	@echo "Swagger UI: http://localhost:8000/docs"
	@echo "ReDoc: http://localhost:8000/redoc"

# Development workflow
dev: install-dev run

# Production deployment
deploy: docker-build docker-run

# Quick test after deployment
test-deploy: health seed-db docs

# Version management
version:
	@python -c "import sys; print(f'Python {sys.version}')"

# Environment check
check-env:
	@echo "Checking environment variables..."
	@echo "OPENAI_API_KEY: $${OPENAI_API_KEY:+SET}"
	@echo "GROQ_API_KEY: $${GROQ_API_KEY:+SET}"
	@echo "OPENROUTER_API_KEY: $${OPENROUTER_API_KEY:+SET}"
	@echo "QDRANT_URL: $${QDRANT_URL:-NOT_SET}"
	@echo "COHERE_API_KEY: $${COHERE_API_KEY:+SET}"