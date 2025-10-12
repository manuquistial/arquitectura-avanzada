.PHONY: help dev-up dev-down dev-logs build deploy-infra deploy-opensearch deploy-cert-manager deploy-helm test lint format clean

help: ## Mostrar este mensaje de ayuda
	@echo "Carpeta Ciudadana - Comandos Disponibles:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-25s\033[0m %s\n", $$1, $$2}'

# Desarrollo Local
dev-up: ## Levantar infraestructura de desarrollo (Docker Compose)
	docker-compose up -d

dev-down: ## Detener infraestructura de desarrollo
	docker-compose down

dev-logs: ## Ver logs de desarrollo
	docker-compose logs -f

dev-services: ## Iniciar servicios backend (venv)
	./start-services.sh

dev-stop: ## Detener servicios backend
	./stop-services.sh

# Build
build: ## Construir todas las imágenes Docker
	./build-all.sh

# Deploy Infraestructura
deploy-infra: ## Desplegar infraestructura con Terraform
	cd infra/terraform && terraform init && terraform apply

deploy-opensearch: ## Desplegar OpenSearch en AKS
	./scripts/deploy-opensearch.sh

deploy-cert-manager: ## Desplegar cert-manager en AKS
	./scripts/deploy-cert-manager.sh

deploy-full-stack: ## Desplegar stack completo (infraestructura + aplicación)
	./scripts/deploy-full-stack.sh

create-secrets: ## Crear secrets de Kubernetes desde Terraform outputs
	./scripts/create-k8s-secrets.sh

update-secrets: ## Actualizar secrets existentes desde Terraform
	./scripts/update-secrets-from-terraform.sh $(NAMESPACE)

# Deploy Aplicación
deploy-helm-dev: ## Desplegar aplicación en dev con Helm
	helm upgrade --install carpeta-ciudadana ./deploy/helm/carpeta-ciudadana \
		-f deploy/helm/carpeta-ciudadana/values.yaml \
		-f deploy/helm/values-dev.yaml \
		--create-namespace \
		--namespace carpeta-ciudadana-dev

deploy-helm-prod: ## Desplegar aplicación en prod con Helm
	helm upgrade --install carpeta-ciudadana ./deploy/helm/carpeta-ciudadana \
		-f deploy/helm/carpeta-ciudadana/values.yaml \
		-f deploy/helm/values-prod.yaml \
		--create-namespace \
		--namespace carpeta-ciudadana-prod

# Testing
test: ## Ejecutar tests unitarios
	@echo "Running unit tests..."
	cd services/gateway && poetry run pytest tests/ -v
	cd services/mintic_client && poetry run pytest tests/unit/ -v
	cd services/transfer && poetry run pytest tests/unit/ -v

test-e2e: ## Ejecutar tests E2E con Playwright
	cd tests/e2e && npm test

test-load: ## Ejecutar tests de carga con k6
	k6 run tests/load/k6-load-test.js

# Linting y Format
lint: ## Ejecutar linters
	@echo "Running linters..."
	cd services/gateway && poetry run ruff check .
	cd services/citizen && poetry run ruff check .

format: ## Formatear código
	@echo "Formatting code..."
	cd services/gateway && poetry run ruff format .
	cd services/citizen && poetry run ruff format .

# Kubernetes
k8s-context: ## Obtener credenciales de AKS
	az aks get-credentials --resource-group carpeta-ciudadana-dev-rg --name carpeta-ciudadana-dev

k8s-pods: ## Ver pods en Kubernetes
	kubectl get pods

k8s-services: ## Ver servicios en Kubernetes
	kubectl get services

k8s-ingress: ## Ver Ingress en Kubernetes
	kubectl get ingress

k8s-logs: ## Ver logs de un pod (usar POD=nombre)
	kubectl logs -f $(POD)

k8s-port-forward-frontend: ## Port forward frontend
	kubectl port-forward svc/carpeta-ciudadana-frontend 3000:80

k8s-port-forward-gateway: ## Port forward gateway
	kubectl port-forward svc/carpeta-ciudadana-gateway 8000:8000

# cert-manager
cert-manager-status: ## Ver estado de cert-manager
	kubectl get pods -n cert-manager
	kubectl get clusterissuers

cert-manager-certs: ## Ver certificados
	kubectl get certificates
	kubectl get certificaterequests

cert-manager-logs: ## Ver logs de cert-manager
	kubectl logs -n cert-manager deployment/cert-manager -f

# OpenSearch
opensearch-status: ## Ver estado de OpenSearch
	kubectl get pods -l app.kubernetes.io/name=opensearch
	kubectl get svc -l app.kubernetes.io/name=opensearch

opensearch-port-forward: ## Port forward OpenSearch
	kubectl port-forward svc/opensearch-cluster-master 9200:9200

opensearch-dashboards: ## Port forward OpenSearch Dashboards
	kubectl port-forward svc/opensearch-dashboards 5601:5601

opensearch-logs: ## Ver logs de OpenSearch
	kubectl logs -f -l app.kubernetes.io/name=opensearch

# Backup y Restore
backup-postgres: ## Backup de PostgreSQL
	./scripts/backup/backup-postgres.sh

restore-postgres: ## Restore de PostgreSQL
	./scripts/backup/restore-postgres.sh

backup-secrets: ## Backup de secrets de Kubernetes
	./scripts/secrets/backup-secrets.sh

restore-secrets: ## Restore de secrets de Kubernetes
	./scripts/secrets/restore-secrets.sh

rotate-secrets: ## Rotar secretos
	./scripts/secrets/rotate-secrets.sh

# Monitoring
grafana-port-forward: ## Port forward Grafana
	kubectl port-forward -n monitoring svc/grafana 3000:80

prometheus-port-forward: ## Port forward Prometheus
	kubectl port-forward -n monitoring svc/prometheus 9090:9090

jaeger-port-forward: ## Port forward Jaeger
	kubectl port-forward -n observability svc/jaeger-query 16686:16686

# Clean
clean: ## Limpiar archivos temporales
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	find . -type d -name "node_modules" -exec rm -rf {} +
	find . -type d -name ".next" -exec rm -rf {} +

clean-docker: ## Limpiar imágenes y contenedores Docker
	docker-compose down -v
	docker system prune -af

# Documentación
docs-serve: ## Servir documentación localmente
	@echo "Documentación disponible en:"
	@echo "- GUIA_COMPLETA.md"
	@echo "- docs/ARCHITECTURE.md"
	@echo "- docs/CERT_MANAGER_TLS.md"
	@echo "- docs/OPENSEARCH_DEPLOYMENT.md"
	@echo ""
	@echo "Usa un visualizador Markdown o abre los archivos directamente"

# Info
info: ## Mostrar información del proyecto
	@echo "========================================="
	@echo "Carpeta Ciudadana - Sistema de Microservicios"
	@echo "========================================="
	@echo ""
	@echo "Cloud Provider: Azure"
	@echo "Kubernetes: AKS"
	@echo "Servicios Backend: 12"
	@echo "Frontend: Next.js 14"
	@echo "Backend: FastAPI + Python 3.13"
	@echo ""
	@echo "Infraestructura:"
	@echo "- Terraform (IaC)"
	@echo "- Helm (Deploy)"
	@echo "- cert-manager + Let's Encrypt (TLS)"
	@echo "- OpenSearch (Búsqueda)"
	@echo "- PostgreSQL (Base de datos)"
	@echo "- Redis (Cache)"
	@echo "- Service Bus (Eventos)"
	@echo ""
	@echo "Documentación: make docs-serve"
	@echo "========================================="
