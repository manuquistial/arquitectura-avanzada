# 🗂️ Carpeta Ciudadana - Sistema de Microservicios

> Sistema de Carpeta Ciudadana con arquitectura de microservicios event-driven  
> **Cloud:** Azure (AKS) | **Python** 3.13 | **Node.js** 22 | **FastAPI** + **Next.js**

[![CI/CD](https://github.com/manuquistial/arquitectura-avanzada/actions/workflows/ci.yml/badge.svg)](https://github.com/manuquistial/arquitectura-avanzada/actions)

---

## 📖 Documentación Principal

### 📚 Guías Esenciales

1. **[GUIA_COMPLETA.md](./GUIA_COMPLETA.md)** ⭐
   - Guía completa del proyecto con todos los detalles
   - Quick start y desarrollo local
   - Despliegue, testing y troubleshooting
   - CI/CD, secrets, backup y operaciones

2. **[docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md)** 🏗️
   - Arquitectura técnica detallada del sistema
   - Descripción completa de los 12 microservicios
   - Patrones de diseño implementados (CQRS, Saga, Circuit Breaker)
   - Flujos de datos, diagramas e infraestructura Azure

### 🛠️ Recursos Adicionales
- **[Makefile](./Makefile)** - Todos los comandos de automatización disponibles
- **[scripts/](./scripts/)** - Scripts de operación y deployment
- **[observability/](./observability/)** - Dashboards Grafana y alertas Prometheus
- **[deploy/helm/](./deploy/helm/)** - Charts de Helm para Kubernetes

---

## 🚀 Quick Start

### Desarrollo Local

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

### Despliegue Completo Automatizado

```bash
# 1. Configurar credenciales
cp infra/terraform/terraform.tfvars.example infra/terraform/terraform.tfvars
# Editar terraform.tfvars con tus valores

# 2. Desplegar TODO (infraestructura + aplicación)
make deploy-full-stack

# O paso a paso:
make deploy-infra        # Terraform
make create-secrets      # Secrets K8s
make deploy-helm-dev     # Helm
```

---

## 🏗️ Arquitectura

### Microservicios (12)

| Servicio | Puerto | Descripción |
|----------|--------|-------------|
| **frontend** | 3000 | Next.js UI |
| **gateway** | 8000 | API Gateway + Rate Limiting |
| **citizen** | 8001 | Gestión ciudadanos |
| **ingestion** | 8002 | Upload/download documentos (SAS) |
| **metadata** | 8003 | Búsqueda y metadata (OpenSearch) |
| **transfer** | 8004 | Transferencias P2P (Saga) |
| **mintic_client** | 8005 | Cliente hub MinTIC (CB + RL) |
| **signature** | 8006 | Firma y autenticación |
| **read_models** | 8007 | CQRS read models |
| **auth** | 8008 | OIDC provider |
| **notification** | 8010 | Email + webhooks |
| **sharing** | 8011 | Compartición shortlinks |

### Stack Tecnológico

**Backend:** FastAPI (Python 3.13) + PostgreSQL + Redis + Azure Blob Storage + Service Bus + OpenSearch  
**Frontend:** Next.js 14 (App Router) + TypeScript + Tailwind CSS  
**Cloud:** Azure Kubernetes Service (AKS) + Terraform (IaC) + Helm (deploy)  
**Observabilidad:** OpenTelemetry + Prometheus + Grafana

---

## 🎯 Características

### Seguridad
✅ Managed Identity + User Delegation SAS  
✅ PostgreSQL Firewall restrictivo  
✅ TLS automático (cert-manager + Let's Encrypt)  
✅ Sanitización y headers de seguridad  

### Resiliencia
✅ Circuit Breaker configurable por endpoint  
✅ Rate Limiting multinivel (Ingress, Gateway, Hub)  
✅ Dead Letter Queue con retry exponencial  
✅ Health Checks (liveness + readiness)  

### Observabilidad
✅ OpenTelemetry (traces, metrics, logs)  
✅ Dashboards predefinidos (Latency, DLQ, Cache, Hub)  
✅ Alertas Prometheus configuradas  
✅ Logs correlacionados con trace_id  

---

## 📦 Comandos Útiles

```bash
# Desarrollo
make dev-up              # Levanta infra + servicios
make dev-down            # Para todo
make test                # Tests unitarios
make lint                # Linters

# Despliegue
make deploy-full-stack   # Stack completo
make deploy-infra        # Solo Terraform
make deploy-helm-dev     # Solo Helm (dev)

# Monitoreo
make k8s-pods            # Ver pods
make prometheus-port-forward
make opensearch-dashboards

# Operaciones
make backup-postgres     # Backup PostgreSQL
make rotate-secrets      # Rotar secretos
make clean               # Limpiar temporales
```

---

## 📚 Para Más Información

- **Arquitectura detallada:** Ver [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md)
- **Guía completa de uso:** Ver [GUIA_COMPLETA.md](./GUIA_COMPLETA.md)
- **Dashboards y alertas:** Ver [observability/](./observability/)
- **Scripts de operación:** Ver [scripts/](./scripts/)

---

## 🎓 Proyecto Universitario

Sistema desarrollado como proyecto de arquitectura avanzada, optimizado para Azure for Students ($100 créditos).

**Costo estimado:** ~$35/mes en desarrollo  
**Tiempo de uso:** 2-5 meses con créditos gratuitos

---

**Estado:** ✅ PRODUCTION READY  
**Última actualización:** 2025-10-12  
**Autor:** Manuel Jurado - Universidad EAFIT

**Deployment rápido:** `make deploy-full-stack`
