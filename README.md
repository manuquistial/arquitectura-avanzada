# 🗂️ Carpeta Ciudadana - Sistema de Microservicios

> Sistema de Carpeta Ciudadana con arquitectura de microservicios event-driven  
> **Cloud:** Azure (AKS) | **Python** 3.13 | **Node.js** 22 | **FastAPI** + **Next.js**

[![CI/CD](https://github.com/manuquistial/arquitectura-avanzada/actions/workflows/ci.yml/badge.svg)](https://github.com/manuquistial/arquitectura-avanzada/actions)

---

## 📖 Documentación

- **[GUIA_COMPLETA.md](./GUIA_COMPLETA.md)** ⭐ - Guía completa del proyecto
- **[docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md)** - Arquitectura técnica detallada
- **[OBSERVABILITY_GUIDE.md](./OBSERVABILITY_GUIDE.md)** - OpenTelemetry y métricas
- **[RATE_LIMITER_GUIDE.md](./RATE_LIMITER_GUIDE.md)** - Rate limiting avanzado
- **[scripts/secrets/README.md](./scripts/secrets/README.md)** - Rotación de secretos
- **[observability/README.md](./observability/README.md)** - Dashboards y alertas

---

## 🚀 Quick Start

### Desarrollo Local (venv - recomendado)

```bash
# 1. Levantar infraestructura (Postgres, Redis, OpenSearch)
docker-compose up -d

# 2. Iniciar servicios backend y frontend
./start-services.sh

# 3. Abrir en navegador
open http://localhost:3000

# Detener
./stop-services.sh
docker-compose down
```

### Stack Completo en Docker

```bash
# Build todas las imágenes
./build-all.sh

# Levantar stack completo
docker-compose --profile app up -d

# Ver logs
docker-compose logs -f gateway

# Detener
docker-compose down
```

---

## 🏗️ Arquitectura

### Stack Tecnológico

**Frontend:**
- Next.js 14 (App Router)
- TypeScript
- Tailwind CSS
- Fuente: Montserrat

**Backend:**
- FastAPI (Python 3.13)
- PostgreSQL (Azure Database)
- Redis (Azure Cache)
- Azure Blob Storage
- Service Bus (eventos)
- OpenSearch (búsqueda)

**Cloud:**
- Azure Kubernetes Service (AKS)
- Terraform (IaC)
- Helm (deploy)
- GitHub Actions (CI/CD)

### Microservicios (12)

| Servicio | Puerto | Descripción |
|----------|--------|-------------|
| **frontend** | 3000 | Next.js UI |
| **gateway** | 8000 | API Gateway + Rate Limiting |
| **citizen** | 8001 | Gestión ciudadanos |
| **ingestion** | 8002 | Upload/download documentos |
| **metadata** | 8003 | Búsqueda y metadata |
| **transfer** | 8004 | Transferencias P2P |
| **mintic_client** | 8005 | Cliente hub MinTIC |
| **signature** | 8006 | Firma y autenticación |
| **read_models** | 8007 | CQRS read models |
| **auth** | 8008 | OIDC provider |
| **iam** | 8009 | ABAC authorization |
| **notification** | 8010 | Email + webhooks |
| **sharing** | 8011 | Compartición shortlinks |

---

## 🔧 Requisitos

### Local Development

```bash
# Node.js 22
nvm use 22

# Python 3.13
python --version  # 3.13.7

# Poetry 2.2.1
poetry --version

# Docker
docker --version

# Kubernetes tools
kubectl version
helm version
```

### Azure Setup

- Cuenta Azure for Students ($100 créditos)
- Azure CLI instalado y autenticado
- Terraform 1.6+
- kubectl configurado con AKS

---

## 🧪 Testing

```bash
# Unit tests (backend)
cd services/gateway
pytest tests/ -v

# E2E tests (Playwright)
cd tests/e2e
npx playwright test

# Load tests (k6)
cd tests/load
k6 run k6-load-test.js

# Load tests (Locust)
locust -f locustfile.py
```

---

## 🚢 Deployment

### Local

```bash
# Con venv
./start-services.sh

# Con Docker
docker-compose --profile app up -d
```

### Azure (AKS)

```bash
# 1. Deploy infraestructura
cd infra/terraform
terraform init
terraform apply

# 2. Deploy aplicación
cd ../../
helm upgrade --install carpeta-ciudadana \
  deploy/helm/carpeta-ciudadana \
  --namespace carpeta-ciudadana \
  --create-namespace

# 3. Verificar
kubectl get pods -n carpeta-ciudadana
```

### CI/CD (Automático)

GitHub Actions despliega automáticamente en cada push a `master`:
- Lint + tests
- Build Docker images
- Push a Docker Hub
- Deploy a AKS con Helm

---

## 📊 Características Principales

### ✅ Implementado

- [x] 12 microservicios con FastAPI
- [x] Frontend Next.js 14 con TypeScript
- [x] API Gateway con rate limiting avanzado
- [x] Integración con hub MinTIC (GovCarpeta)
- [x] Upload directo a Azure Blob Storage (presigned URLs)
- [x] Búsqueda full-text con OpenSearch
- [x] Transferencias P2P entre operadores
- [x] Compartición de documentos con shortlinks
- [x] Sistema de eventos con Azure Service Bus
- [x] CQRS con read models
- [x] Saga pattern con compensación
- [x] Circuit breakers para resilencia
- [x] OpenTelemetry (traces, metrics, logs)
- [x] Redis para cache, locks, idempotencia
- [x] Rotación automática de secretos (30 días)
- [x] Backups automáticos (PostgreSQL, OpenSearch)
- [x] Dashboards Grafana predefinidos
- [x] Alertas Prometheus configuradas
- [x] Tests E2E con Playwright
- [x] Tests de carga con k6 y Locust
- [x] CI/CD completo con GitHub Actions

### 🔄 Próximas Mejoras

- [ ] OIDC authentication completa (Auth service)
- [ ] ABAC policies en IAM service
- [ ] Azure Key Vault + CSI driver
- [ ] Multi-región con geo-replication
- [ ] CDN para assets estáticos

---

## 🌐 Integración Hub MinTIC

**Hub GovCarpeta:**
- URL: https://govcarpeta-apis-4905ff3c005b.herokuapp.com
- API pública (sin OAuth ni mTLS)

**Endpoints integrados:**
- Register/unregister citizen
- Authenticate document
- Validate citizen
- Register operator
- Get operators list
- Register transfer endpoint

---

## 📈 Observabilidad

**OpenTelemetry instrumentación completa:**
- Trazas distribuidas con `traceparent`
- Métricas: latencia p95, error rate, cache hit/miss, DLQ length
- 4 dashboards Grafana (API Latency, Transfers Saga, Queue Health, Cache Efficiency)
- 11 alertas configuradas (p95>2s, 5xx>1%, DLQ>10, etc.)

**Exporters:**
- Console (stdout) para desarrollo
- Azure Monitor para producción
- Prometheus + Grafana

---

## 🔐 Seguridad

- **Rate Limiting**: Por rol (ciudadano: 60rpm, operador: 200rpm, services: 400rpm)
- **Ban System**: 5 violaciones → ban 120s
- **Allowlist**: IPs hub MinTIC bypass límites
- **Secretos**: Rotación automática cada 30 días
- **Backups**: Encriptados con AES-256-CBC
- **Eventos**: Deduplicación con Redis

---

## 💾 Backup & Recovery

**RPO:** 24 horas  
**RTO:** < 2 horas

- PostgreSQL: Backups diarios (retención 7 días)
- OpenSearch: Snapshots diarios
- Blobs: Replicación LRS nativa de Azure
- Cleanup de huérfanos: Semanal

---

## 📞 Soporte

Para problemas:
1. Ver logs: `docker-compose logs -f {service}`
2. Consultar [GUIA_COMPLETA.md](./GUIA_COMPLETA.md)
3. Revisar [GitHub Actions](https://github.com/manuquistial/arquitectura-avanzada/actions)
4. Verificar [Troubleshooting](./GUIA_COMPLETA.md#troubleshooting)

---

## 🔗 Enlaces

- **Repositorio**: https://github.com/manuquistial/arquitectura-avanzada
- **Docker Hub**: https://hub.docker.com/u/manuelquistial
- **GovCarpeta API**: https://govcarpeta-apis-4905ff3c005b.herokuapp.com

---

**Versión:** 2.0.0  
**Última actualización:** 12 Octubre 2025  
**Autor:** Manuel Jurado (Proyecto Universitario - Arquitectura Avanzada)
