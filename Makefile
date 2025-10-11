.PHONY: help dev-up dev-down dev-docker test test-unit test-contract test-e2e lint format build docker-build deploy-dev deploy-staging deploy-prod clean

help:
	@echo "Carpeta Ciudadana - Makefile Commands"
	@echo "======================================"
	@echo ""
	@echo "🏗️  Development:"
	@echo "  dev-up          - Start infra + services (venv)"
	@echo "  dev-down        - Stop all services"
	@echo "  dev-docker      - Run full stack with Docker"
	@echo ""
	@echo "🧪 Testing:"
	@echo "  test            - Run all tests"
	@echo "  test-unit       - Run unit tests"
	@echo "  test-contract   - Run contract tests"
	@echo "  test-e2e        - Run E2E tests"
	@echo ""
	@echo "🔍 Quality:"
	@echo "  lint            - Run linters"
	@echo "  format          - Format code"
	@echo ""
	@echo "🐳 Build:"
	@echo "  build           - Build frontend"
	@echo "  docker-build    - Build all Docker images"
	@echo ""
	@echo "☁️  Deploy:"
	@echo "  deploy-dev      - Deploy to development (AKS)"
	@echo "  deploy-staging  - Deploy to staging"
	@echo "  deploy-prod     - Deploy to production"
	@echo ""
	@echo "🧹 Cleanup:"
	@echo "  clean           - Clean build artifacts"

dev-up:
	@echo "Starting local development environment (infra + services)..."
	docker-compose up -d
	./start-services.sh

dev-down:
	@echo "Stopping local development environment..."
	./stop-services.sh
	docker-compose down

dev-docker:
	@echo "Running full stack with Docker..."
	@echo "Building images first..."
	./build-all.sh
	@echo "Starting containers..."
	export TAG=local && docker-compose --profile app up -d
	@echo "Stack running at http://localhost:3000"

test:
	@echo "Running all tests..."
	$(MAKE) test-unit
	$(MAKE) test-contract
	$(MAKE) test-e2e

test-unit:
	@echo "Running unit tests..."
	@echo "Backend services..."
	cd services/gateway && poetry run pytest tests/unit || true
	cd services/citizen && poetry run pytest tests/unit || true
	cd services/ingestion && poetry run pytest tests/unit || true
	cd services/metadata && poetry run pytest tests/unit || true
	cd services/transfer && poetry run pytest tests/unit || true
	cd services/mintic_client && poetry run pytest tests/unit || true
	@echo "Frontend tests..."
	cd apps/frontend && npm run test || true
	@echo "✅ Unit tests completed"

test-contract:
	@echo "Running contract tests..."
	cd services/gateway && poetry run pytest tests/contract
	cd services/mintic_client && poetry run pytest tests/contract

test-e2e:
	@echo "Running E2E tests..."
	cd apps/frontend && npm run test:e2e

lint:
	@echo "Running linters..."
	@echo "Backend services..."
	cd services/gateway && poetry run ruff check . || true
	cd services/citizen && poetry run ruff check . || true
	cd services/ingestion && poetry run ruff check . || true
	cd services/metadata && poetry run ruff check . || true
	cd services/transfer && poetry run ruff check . || true
	cd services/mintic_client && poetry run ruff check . || true
	@echo "Frontend..."
	cd apps/frontend && npm run lint || true
	@echo "✅ Linting completed"

format:
	@echo "Formatting code..."
	@echo "Backend services..."
	cd services/gateway && poetry run ruff format . || true
	cd services/citizen && poetry run ruff format . || true
	cd services/ingestion && poetry run ruff format . || true
	cd services/metadata && poetry run ruff format . || true
	cd services/transfer && poetry run ruff format . || true
	cd services/mintic_client && poetry run ruff format . || true
	@echo "Frontend..."
	cd apps/frontend && npm run format || echo "No format script configured"
	@echo "✅ Formatting completed"

build:
	@echo "Building all services..."
	cd apps/frontend && npm run build

docker-build:
	@echo "Building Docker images..."
	./build-all.sh

clean:
	@echo "Cleaning build artifacts..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	cd apps/frontend && rm -rf .next out 2>/dev/null || true
	@echo "✅ Cleanup completed"

deploy-dev:
	@echo "Deploying to development (AKS)..."
	@echo "Using current kubectl context..."
	helm upgrade --install carpeta-ciudadana \
		deploy/helm/carpeta-ciudadana \
		--namespace carpeta-ciudadana \
		--create-namespace \
		--wait \
		--timeout 10m
	@echo "✅ Deployment completed"
	@echo "Get services: kubectl get svc -n carpeta-ciudadana"

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

