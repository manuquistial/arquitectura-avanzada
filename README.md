# Carpeta Ciudadana - Operador AWS

Sistema de Carpeta Ciudadana implementado como operador en AWS con arquitectura de microservicios event-driven siguiendo patrones CQRS.

## Arquitectura

- **Frontend**: Next.js 14+ (App Router) con Node.js 22
- **Backend**: FastAPI microservicios
- **Autenticación**: 
  - Usuarios: AWS Cognito OIDC (Authorization Code + PKCE)
  - B2B: OAuth 2.1 client_credentials + mTLS (ACM PCA)
- **Infraestructura AWS**:
  - EKS (Kubernetes)
  - RDS PostgreSQL (metadatos)
  - S3 (documentos)
  - OpenSearch (búsqueda)
  - SQS/SNS (eventos)
  - ACM PCA (mTLS)
  - Cognito (autenticación)
- **Observabilidad**: OpenTelemetry (trazas, métricas, logs)

## Estructura del Proyecto

```
.
├── apps/
│   └── frontend/          # Next.js App Router
├── services/
│   ├── gateway/           # API Gateway, rate limiting
│   ├── iam/              # OIDC/ABAC
│   ├── citizen/          # Gestión de ciudadanos
│   ├── ingestion/        # Ingesta de documentos
│   ├── signature/        # Firma digital (XAdES/CAdES/PAdES)
│   ├── metadata/         # Metadatos de documentos
│   ├── transfer/         # Transferencia P2P
│   ├── sharing/          # Compartir documentos
│   ├── notification/     # Notificaciones
│   └── mintic_client/    # Cliente hub MinTIC
├── infra/
│   └── terraform/        # IaC para AWS
├── deploy/
│   └── helm/             # Charts de Kubernetes
├── docs/
│   ├── openapi/          # Especificaciones OpenAPI
│   └── asyncapi/         # Especificaciones AsyncAPI
└── Makefile              # Comandos de desarrollo

```

## Microservicios

### Gateway Service
- Rate limiting
- Validación de tokens JWT
- Routing a microservicios

### IAM Service
- Gestión OIDC
- ABAC (Attribute-Based Access Control)
- Emisión de tokens B2B

### Citizen Service
- Registro de ciudadanos
- Afiliación a operador
- Validación de ciudadanos

### Ingestion Service
- Ingesta de documentos
- Generación de URLs pre-firmadas (PUT)
- Validación de metadatos

### Signature Service
- Firma digital: XAdES, CAdES, PAdES
- Integración con TSA (Time Stamp Authority)
- Verificación de firmas

### Metadata Service
- Almacenamiento de metadatos en PostgreSQL
- Indexación en OpenSearch
- Búsqueda avanzada

### Transfer Service
- Transferencia P2P entre operadores
- Gestión de idempotencia
- Confirmación de transferencias

### Sharing Service
- Compartir paquetes de documentos
- URLs de descarga pre-firmadas (GET)
- Control de acceso temporal

### Notification Service
- Notificaciones por email
- Webhooks
- Eventos de sistema

### MinTIC Client Service
- Integración con hub MinTIC
- Registro de ciudadanos/operadores
- Autenticación de documentos

## Integración Hub MinTIC

### Endpoints Implementados

- `POST /apis/registerCitizen` - Registrar ciudadano en MinTIC
- `DELETE /apis/unregisterCitizen` - Desafiliar ciudadano
- `PUT /apis/authenticateDocument` - Autenticar documento
- `GET /apis/validateCitizen/{id}` - Validar ciudadano
- `POST /apis/registerOperator` - Registrar operador
- `PUT /apis/registerTransferEndPoint` - Registrar endpoint de transferencia
- `GET /apis/getOperators` - Obtener operadores

## P2P Transfer

### Flujo de Transferencia

1. Operador origen inicia transferencia
2. Operador destino recibe: `POST /api/transferCitizen`
3. Destino descarga documentos con URLs pre-firmadas
4. Destino confirma: `POST /api/transferCitizenConfirm`
5. Origen elimina datos tras confirmación exitosa

## Frontend

### Funcionalidades

- Login OIDC con Cognito
- Registro y afiliación de ciudadanos
- Subida de documentos (presigned PUT directo a S3)
- Bandeja de documentos
- Búsqueda en OpenSearch
- Compartir paquetes
- Flujo de transferencia entre operadores

## Desarrollo

### Requisitos

- Node.js 22+
- Python 3.11+
- Docker & Docker Compose
- Terraform
- kubectl & Helm
- AWS CLI

### Comandos

```bash
# Desarrollo local
make dev-up          # Levantar servicios locales
make dev-down        # Detener servicios

# Testing
make test            # Ejecutar todos los tests
make test-unit       # Tests unitarios
make test-contract   # Tests de contrato
make test-e2e        # Tests E2E

# Linting
make lint            # Linter
make format          # Formatear código

# Build
make build           # Build de todos los servicios
make docker-build    # Build imágenes Docker

# Deploy
make deploy-dev      # Deploy a desarrollo
make deploy-staging  # Deploy a staging
make deploy-prod     # Deploy a producción
```

## Seguridad

- **Autenticación usuarios**: OIDC Authorization Code + PKCE
- **Autenticación B2B**: OAuth 2.1 client_credentials + mTLS
- **Documentos**: URLs pre-firmadas con expiración
- **Eventos**: Firmados con JWS
- **Auditoría**: OpenTelemetry completo
- **Integridad**: SHA-256 para documentos

## Observabilidad

- **Trazas**: OpenTelemetry traces
- **Métricas**: OpenTelemetry metrics
- **Logs**: OpenTelemetry logs
- **Eventos auditables**: Firmados con JWS

## Despliegue

### EKS (Kubernetes)

- Helm charts para cada servicio
- HPA (Horizontal Pod Autoscaler)
- Service Mesh (Istio opcional)
- Ingress con ALB

### CI/CD

- GitHub Actions
- Build automático de imágenes
- Tests automáticos
- Deploy automático por ambiente

## Licencia

Propiedad de [Tu Organización]

