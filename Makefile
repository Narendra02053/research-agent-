.PHONY: help install test lint format up down build

help:
	@echo "Available commands:"
	@echo "  make install  - Install all dependencies (backend & frontend)"
	@echo "  make test     - Run backend and frontend tests"
	@echo "  make lint     - Run linters"
	@echo "  make format   - Run code formatters"
	@echo "  make up       - Start the full stack with docker-compose"
	@echo "  make down     - Stop the full stack"
	@echo "  make build    - Rebuild docker images"

install:
	cd backend && pip install -r requirements.txt && pip install -r requirements-dev.txt
	cd frontend && npm install

test:
	cd backend && pytest
	# cd frontend && npm test # when configured

lint:
	cd backend && flake8 app tests
	cd frontend && npm run lint

format:
	cd backend && black app tests && isort app tests

up:
	docker-compose up -d

down:
	docker-compose down

build:
	docker-compose build
