# Arquitectura del Sistema - Carpeta Ciudadana

## Visión General

Sistema de Carpeta Ciudadana implementado como operador en AWS siguiendo arquitectura de microservicios event-driven con patrones CQRS.

## Arquitectura de Microservicios

### Frontend
- **Tecnología**: Next.js 14+ (App Router) con Node.js 22
- **Características**:
  - Login OIDC con Cognito (Authorization Code + PKCE)
  - Subida de documentos con presigned URLs (directo a S3)
  - Búsqueda con OpenSearch
  - Flujo de transferencia P2P
  - UI con Montserrat, inputs con fondo claro

### Backend Services

#### 1. Gateway Service
- **Puerto**: 8000
- **Funciones**:
  - Rate limiting (60 req/min por defecto)
  - Validación de tokens JWT
  - Routing a microservicios
- **Tecnologías**: FastAPI, Redis, SlowAPI

#### 2. Citizen Service
- **Puerto**: 8000
- **Funciones**:
  - Registro y gestión de ciudadanos
  - Validación de identidad
  - Integración con MinTIC Hub
- **Base de datos**: PostgreSQL (RDS)

#### 3. Ingestion Service
- **Puerto**: 8000
- **Funciones**:
  - Generación de URLs pre-firmadas PUT (subida)
  - Generación de URLs pre-firmadas GET (descarga)
  - Confirmación de upload y verificación SHA-256
- **Almacenamiento**: S3

#### 4. Signature Service
- **Puerto**: 8000
- **Funciones**:
  - Firma digital: XAdES, CAdES, PAdES
  - Integración con TSA (Time Stamp Authority)
  - Verificación de firmas
- **Tecnologías**: cryptography, jwcrypto

#### 5. Metadata Service
- **Puerto**: 8000
- **Funciones**:
  - Almacenamiento de metadatos en PostgreSQL
  - Indexación en OpenSearch
  - Búsqueda avanzada
- **Bases de datos**: PostgreSQL, OpenSearch

#### 6. Transfer Service
- **Puerto**: 8000
- **Funciones**:
  - Transferencia P2P entre operadores
  - Gestión de idempotencia
  - Confirmación de transferencias
  - Verificación de integridad (SHA-256)
- **Flujo**:
  1. POST /api/transferCitizen (destino recibe)
  2. Descarga documentos con presigned URLs
  3. POST /api/transferCitizenConfirm (destino confirma)
  4. Origen elimina datos si req_status=1

#### 7. Sharing Service
- **Puerto**: 8000
- **Funciones**:
  - Compartir paquetes de documentos
  - URLs temporales de acceso
  - Control de expiración

#### 8. Notification Service
- **Puerto**: 8000
- **Funciones**:
  - Notificaciones por email
  - Webhooks
  - Eventos de sistema
- **Tecnologías**: SNS, SES

#### 9. MinTIC Client Service
- **Puerto**: 8000
- **Funciones**:
  - Cliente para hub MinTIC con mTLS
  - Endpoints implementados:
    - POST /apis/registerCitizen
    - DELETE /apis/unregisterCitizen
    - PUT /apis/authenticateDocument
    - GET /apis/validateCitizen/{id}
    - POST /apis/registerOperator
    - PUT /apis/registerTransferEndPoint
    - GET /apis/getOperators
- **Seguridad**: OAuth 2.1 client_credentials + mTLS (ACM PCA)

## Patrones de Arquitectura

### CQRS (Command Query Responsibility Segregation)
- **Commands**: Escrituras en PostgreSQL
- **Queries**: Lecturas optimizadas desde OpenSearch

### Event-Driven Architecture
- **Mensajería**: SQS/SNS (compatible con Kafka/MSK futuro)
- **Eventos firmados**: JWS para auditoría
- **Tipos de eventos**:
  - citizen.registered
  - citizen.unregistered
  - document.uploaded
  - document.signed
  - document.authenticated
  - transfer.initiated
  - transfer.confirmed
  - transfer.failed

## Infraestructura AWS

### Compute
- **EKS (Kubernetes)**: Orquestación de microservicios
- **HPA**: Auto-scaling horizontal basado en CPU/memoria

### Storage
- **S3**: Almacenamiento de documentos
- **RDS PostgreSQL**: Metadatos y datos estructurados
- **OpenSearch**: Búsqueda y analytics

### Networking
- **VPC**: Red privada con subnets públicas y privadas
- **ALB**: Application Load Balancer para ingress

### Security
- **Cognito**: Autenticación OIDC para usuarios
- **IAM**: Roles con IRSA (IAM Roles for Service Accounts)
- **ACM PCA**: Certificate Authority para mTLS B2B
- **Secrets Manager**: Gestión de secretos

### Messaging
- **SQS**: Colas de eventos
- **SNS**: Notificaciones pub/sub
- **DLQ**: Dead Letter Queue para eventos fallidos

### Observability
- **OpenTelemetry**: Trazas, métricas y logs
- **CloudWatch**: Logs centralizados
- **X-Ray**: Distributed tracing

## Seguridad

### Autenticación y Autorización

#### Usuarios (B2C)
- **Cognito OIDC**: Authorization Code + PKCE
- **JWT**: Tokens con expiración
- **MFA**: Multi-factor authentication (opcional)

#### B2B (Operador-a-Operador)
- **OAuth 2.1**: client_credentials flow
- **mTLS**: Mutual TLS con certificados de ACM PCA
- **Renovación automática**: Certificados rotados

### Integridad y Auditoría
- **SHA-256**: Hash de documentos
- **JWS**: Firma de eventos para auditoría
- **OpenTelemetry**: Trazabilidad completa

### URLs Pre-firmadas
- **PUT**: Para subida (1 hora de expiración)
- **GET**: Para descarga (1 hora de expiración)
- **Directas a S3**: Sin pasar binarios por servicios

## Despliegue

### Kubernetes (EKS)
- **Namespace**: carpeta-ciudadana-{env}
- **Helm Charts**: Gestión de deployments
- **HPA**: Min 2, Max 10 pods por servicio
- **Rolling Updates**: Zero-downtime deployments

### CI/CD (GitHub Actions)
1. **Lint y Tests**: Automáticos en PR
2. **Build**: Imágenes Docker a ECR
3. **Deploy**: Helm upgrade en EKS
4. **Security Scan**: Trivy para vulnerabilidades

### Ambientes
- **dev**: Desarrollo
- **staging**: Pre-producción
- **prod**: Producción

## Flujos Principales

### 1. Subida de Documento
```
Usuario → Frontend → Ingestion Service → S3 (presigned PUT)
                   ↓
              PostgreSQL + OpenSearch
                   ↓
              SNS/SQS (document.uploaded)
```

### 2. Transferencia P2P
```
Operador A → Transfer Service A → POST /transferCitizen → Operador B
                                                          ↓
                                          Descarga con presigned GET
                                                          ↓
                                      POST /transferCitizenConfirm
                                                          ↓
                                  A elimina si req_status=1
```

### 3. Autenticación MinTIC
```
Service → MinTIC Client → mTLS → MinTIC Hub
                                  ↓
                              Response 201/500/501
```

## Monitoreo y Observabilidad

### OpenTelemetry
- **Traces**: Seguimiento de requests
- **Metrics**: CPU, memoria, latencia
- **Logs**: Estructurados en JSON

### Métricas Clave
- Tasa de subida de documentos
- Latencia de transferencias P2P
- Tasa de éxito/error MinTIC
- Tiempo de búsqueda OpenSearch

## Escalabilidad

### Horizontal Scaling
- **HPA**: Basado en CPU (70%) y memoria (80%)
- **Min replicas**: 2
- **Max replicas**: 10-20 (según servicio)

### Vertical Scaling
- **EKS nodes**: t3.medium - t3.xlarge
- **RDS**: db.t3.medium - db.r5.large
- **OpenSearch**: t3.medium.search - r5.large.search

## Costos Estimados (AWS)

### Mensual (ambiente prod)
- **EKS**: $150 (cluster) + $300 (nodes t3.medium x3)
- **RDS**: $200 (db.t3.medium)
- **S3**: $50 (1TB storage + requests)
- **OpenSearch**: $300 (2 nodes t3.medium.search)
- **Data Transfer**: $100
- **CloudWatch/X-Ray**: $50
- **Total**: ~$1,150/mes

## Roadmap

### Fase 1 (Actual)
- ✅ Microservicios core
- ✅ Integración MinTIC
- ✅ Transferencia P2P
- ✅ Frontend básico

### Fase 2
- Firma digital completa (XAdES/CAdES/PAdES)
- Integración con TSA
- Blockchain para auditoría
- Mobile app (React Native)

### Fase 3
- IA para clasificación de documentos
- OCR automático
- Analytics avanzado
- Multi-región (DR)

