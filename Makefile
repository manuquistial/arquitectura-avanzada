.PHONY: help dev-up dev-down test test-unit test-contract test-e2e lint format build docker-build deploy-dev deploy-staging deploy-prod

help:
	@echo "Carpeta Ciudadana - Makefile Commands"
	@echo "====================================="
	@echo "dev-up          - Start local development environment"
	@echo "dev-down        - Stop local development environment"
	@echo "test            - Run all tests"
	@echo "test-unit       - Run unit tests"
	@echo "test-contract   - Run contract tests"
	@echo "test-e2e        - Run E2E tests"
	@echo "lint            - Run linters"
	@echo "format          - Format code"
	@echo "build           - Build all services"
	@echo "docker-build    - Build Docker images"
	@echo "deploy-dev      - Deploy to development"
	@echo "deploy-staging  - Deploy to staging"
	@echo "deploy-prod     - Deploy to production"

dev-up:
	@echo "Starting local development environment..."
	docker-compose up -d
	@echo "Services available at:"
	@echo "  Frontend: http://localhost:3000"
	@echo "  Gateway: http://localhost:8000"
	@echo "  OpenSearch: http://localhost:9200"
	@echo "  PostgreSQL: localhost:5432"

dev-down:
	@echo "Stopping local development environment..."
	docker-compose down

test:
	@echo "Running all tests..."
	$(MAKE) test-unit
	$(MAKE) test-contract
	$(MAKE) test-e2e

test-unit:
	@echo "Running unit tests..."
	cd services/gateway && poetry run pytest tests/unit
	cd services/citizen && poetry run pytest tests/unit
	cd services/ingestion && poetry run pytest tests/unit
	cd services/signature && poetry run pytest tests/unit
	cd services/metadata && poetry run pytest tests/unit
	cd services/transfer && poetry run pytest tests/unit
	cd services/sharing && poetry run pytest tests/unit
	cd services/notification && poetry run pytest tests/unit
	cd services/mintic_client && poetry run pytest tests/unit
	cd apps/frontend && npm run test:unit

test-contract:
	@echo "Running contract tests..."
	cd services/gateway && poetry run pytest tests/contract
	cd services/mintic_client && poetry run pytest tests/contract

test-e2e:
	@echo "Running E2E tests..."
	cd apps/frontend && npm run test:e2e

lint:
	@echo "Running linters..."
	cd services/gateway && poetry run ruff check .
	cd services/citizen && poetry run ruff check .
	cd services/ingestion && poetry run ruff check .
	cd services/signature && poetry run ruff check .
	cd services/metadata && poetry run ruff check .
	cd services/transfer && poetry run ruff check .
	cd services/sharing && poetry run ruff check .
	cd services/notification && poetry run ruff check .
	cd services/mintic_client && poetry run ruff check .
	cd apps/frontend && npm run lint

format:
	@echo "Formatting code..."
	cd services/gateway && poetry run ruff format .
	cd services/citizen && poetry run ruff format .
	cd services/ingestion && poetry run ruff format .
	cd services/signature && poetry run ruff format .
	cd services/metadata && poetry run ruff format .
	cd services/transfer && poetry run ruff format .
	cd services/sharing && poetry run ruff format .
	cd services/notification && poetry run ruff format .
	cd services/mintic_client && poetry run ruff format .
	cd apps/frontend && npm run format

build:
	@echo "Building all services..."
	cd apps/frontend && npm run build

docker-build:
	@echo "Building Docker images..."
	docker build -t carpeta-ciudadana/frontend:latest -f apps/frontend/Dockerfile apps/frontend
	docker build -t carpeta-ciudadana/gateway:latest -f services/gateway/Dockerfile services/gateway
	docker build -t carpeta-ciudadana/citizen:latest -f services/citizen/Dockerfile services/citizen
	docker build -t carpeta-ciudadana/ingestion:latest -f services/ingestion/Dockerfile services/ingestion
	docker build -t carpeta-ciudadana/signature:latest -f services/signature/Dockerfile services/signature
	docker build -t carpeta-ciudadana/metadata:latest -f services/metadata/Dockerfile services/metadata
	docker build -t carpeta-ciudadana/transfer:latest -f services/transfer/Dockerfile services/transfer
	docker build -t carpeta-ciudadana/sharing:latest -f services/sharing/Dockerfile services/sharing
	docker build -t carpeta-ciudadana/notification:latest -f services/notification/Dockerfile services/notification
	docker build -t carpeta-ciudadana/mintic_client:latest -f services/mintic_client/Dockerfile services/mintic_client

deploy-dev:
	@echo "Deploying to development..."
	kubectl config use-context dev
	helm upgrade --install carpeta-ciudadana deploy/helm/carpeta-ciudadana -f deploy/helm/carpeta-ciudadana/values-dev.yaml --namespace carpeta-ciudadana-dev --create-namespace

deploy-staging:
	@echo "Deploying to staging..."
	kubectl config use-context staging
	helm upgrade --install carpeta-ciudadana deploy/helm/carpeta-ciudadana -f deploy/helm/carpeta-ciudadana/values-staging.yaml --namespace carpeta-ciudadana-staging --create-namespace

deploy-prod:
	@echo "Deploying to production..."
	@read -p "Are you sure you want to deploy to PRODUCTION? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		kubectl config use-context prod; \
		helm upgrade --install carpeta-ciudadana deploy/helm/carpeta-ciudadana -f deploy/helm/carpeta-ciudadana/values-prod.yaml --namespace carpeta-ciudadana-prod --create-namespace; \
	else \
		echo "Deployment cancelled."; \
	fi

