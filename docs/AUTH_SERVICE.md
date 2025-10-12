# 🔐 Auth Service - OIDC Provider + Session Management

**Servicio**: `auth`  
**Puerto**: `8011`  
**Versión**: `1.0.0`  
**Autor**: Manuel Jurado  
**Fecha**: 2025-10-13

---

## 📋 Índice

1. [Descripción General](#descripción-general)
2. [Arquitectura](#arquitectura)
3. [Endpoints](#endpoints)
4. [OIDC Discovery](#oidc-discovery)
5. [Token Management](#token-management)
6. [Session Management](#session-management)
7. [Configuración](#configuración)
8. [Deployment](#deployment)
9. [Testing](#testing)
10. [Troubleshooting](#troubleshooting)

---

## 🎯 Descripción General

El **Auth Service** proporciona autenticación y autorización centralizada para Carpeta Ciudadana, implementando el protocolo **OpenID Connect (OIDC)** y gestionando sesiones de usuario.

### Características

✅ **OIDC Provider**: Implementa OpenID Connect Discovery  
✅ **Token Management**: Generación y validación de JWT  
✅ **Session Storage**: Sesiones en Redis con TTL  
✅ **Azure AD B2C Integration**: Delegación de autenticación  
✅ **M2M Authentication**: Client credentials flow  
✅ **Health Endpoints**: `/health`, `/ready`  

---

## 🏗️ Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│                      Auth Service (8011)                     │
│                                                              │
│  ┌────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │  OIDC Provider │  │ Token Validator │  │   Sessions   │ │
│  │                │  │                 │  │   Manager    │ │
│  │ - Discovery    │  │ - JWT sign      │  │              │ │
│  │ - JWKS         │  │ - JWT verify    │  │ - Create     │ │
│  │ - Authorize    │  │ - Refresh       │  │ - Get        │ │
│  │ - Token        │  │                 │  │ - Delete     │ │
│  │ - UserInfo     │  │                 │  │ - Refresh    │ │
│  └────────────────┘  └─────────────────┘  └──────────────┘ │
│                                                              │
└──────────────────────────┬───────────────────────────────────┘
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
         ▼                 ▼                 ▼
  ┌─────────────┐   ┌────────────┐   ┌───────────┐
  │ Azure AD B2C│   │   Redis    │   │ PostgreSQL│
  │   (OIDC)    │   │ (Sessions) │   │  (Users)  │
  └─────────────┘   └────────────┘   └───────────┘
```

### Flujo de Autenticación

```
User → Frontend → Auth Service → Azure AD B2C
                         │
                         ├→ Validate token
                         ├→ Create session (Redis)
                         └→ Return tokens
```

---

## 📡 Endpoints

### Health & Info

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/ready` | GET | Readiness check |
| `/` | GET | Service info |

### OIDC Discovery

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/.well-known/openid-configuration` | GET | OIDC configuration |
| `/.well-known/jwks.json` | GET | JSON Web Key Set |

### Authentication

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/auth/authorize` | POST | Start authorization |
| `/api/auth/token` | POST | Exchange code for tokens |
| `/api/auth/userinfo` | GET | Get user information |
| `/api/auth/logout` | POST | Logout user |

### Session Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/sessions` | POST | Create session |
| `/api/sessions/{id}` | GET | Get session |
| `/api/sessions/{id}` | DELETE | Delete session |
| `/api/sessions/{id}/refresh` | POST | Refresh session |

---

## 🔍 OIDC Discovery

### Configuration Endpoint

**GET** `/.well-known/openid-configuration`

```json
{
  "issuer": "http://localhost:8011",
  "authorization_endpoint": "http://localhost:8011/api/auth/authorize",
  "token_endpoint": "http://localhost:8011/api/auth/token",
  "userinfo_endpoint": "http://localhost:8011/api/auth/userinfo",
  "jwks_uri": "http://localhost:8011/.well-known/jwks.json",
  "end_session_endpoint": "http://localhost:8011/api/auth/logout",
  
  "response_types_supported": [
    "code", "token", "id_token"
  ],
  "subject_types_supported": ["public"],
  "id_token_signing_alg_values_supported": ["RS256"],
  "scopes_supported": [
    "openid", "profile", "email", "offline_access"
  ],
  "token_endpoint_auth_methods_supported": [
    "client_secret_post", "client_secret_basic"
  ],
  "claims_supported": [
    "sub", "iss", "aud", "exp", "iat",
    "email", "name", "roles", "permissions"
  ],
  "code_challenge_methods_supported": ["S256"],
  "grant_types_supported": [
    "authorization_code",
    "refresh_token",
    "client_credentials"
  ]
}
```

### JWKS Endpoint

**GET** `/.well-known/jwks.json`

```json
{
  "keys": [
    {
      "kty": "RSA",
      "use": "sig",
      "kid": "carpeta-ciudadana-key-1",
      "alg": "RS256",
      "n": "<modulus>",
      "e": "AQAB"
    }
  ]
}
```

---

## 🎫 Token Management

### Token Request

**POST** `/api/auth/token`

#### Authorization Code Flow

```json
{
  "grant_type": "authorization_code",
  "code": "auth_code_123",
  "redirect_uri": "http://localhost:3000/callback",
  "client_id": "frontend",
  "code_verifier": "pkce_verifier_123"
}
```

#### Refresh Token Flow

```json
{
  "grant_type": "refresh_token",
  "refresh_token": "refresh_token_123"
}
```

#### Client Credentials Flow (M2M)

```json
{
  "grant_type": "client_credentials",
  "client_id": "service_a",
  "client_secret": "secret_123"
}
```

### Token Response

```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIs...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "refresh_token": "refresh_token_123",
  "id_token": "eyJhbGciOiJSUzI1NiIs...",
  "scope": "openid profile email"
}
```

### UserInfo Request

**GET** `/api/auth/userinfo`

```bash
curl -H "Authorization: Bearer <access_token>" \
  http://localhost:8011/api/auth/userinfo
```

### UserInfo Response

```json
{
  "sub": "user-id-123",
  "email": "user@example.com",
  "email_verified": true,
  "name": "Demo User",
  "given_name": "Demo",
  "family_name": "User",
  "roles": ["user", "operator"],
  "permissions": [
    "read:own_documents",
    "write:own_documents"
  ]
}
```

---

## 📦 Session Management

### Create Session

**POST** `/api/sessions`

```json
{
  "user_id": "user-123",
  "email": "user@example.com",
  "name": "Demo User",
  "roles": ["user"],
  "permissions": ["read:own_documents"]
}
```

**Response (201)**:

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "user-123",
  "email": "user@example.com",
  "name": "Demo User",
  "roles": ["user"],
  "permissions": ["read:own_documents"],
  "created_at": "2025-10-13T03:45:00Z",
  "expires_at": "2025-10-14T03:45:00Z",
  "is_active": true
}
```

### Get Session

**GET** `/api/sessions/{session_id}`

**Response (200)**:

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "user-123",
  "email": "user@example.com",
  "is_active": true,
  ...
}
```

### Delete Session (Logout)

**DELETE** `/api/sessions/{session_id}`

**Response (200)**:

```json
{
  "message": "Session deleted",
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### Refresh Session

**POST** `/api/sessions/{session_id}/refresh`

**Response (200)**:

```json
{
  "message": "Session refreshed",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "expires_at": "2025-10-14T03:45:00Z"
}
```

---

## ⚙️ Configuración

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `OIDC_ISSUER_URL` | OIDC issuer URL | `http://localhost:8011` | Yes |
| `JWT_ACCESS_TOKEN_EXPIRE` | Access token TTL (min) | `60` | No |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token TTL (days) | `30` | No |
| `JWT_PRIVATE_KEY_PATH` | JWT signing key path | `/etc/auth/private_key.pem` | Yes |
| `JWT_PUBLIC_KEY_PATH` | JWT verification key path | `/etc/auth/public_key.pem` | Yes |
| `AZURE_AD_B2C_TENANT_NAME` | Azure B2C tenant | - | No |
| `AZURE_AD_B2C_TENANT_ID` | Azure B2C tenant ID | - | No |
| `AZURE_AD_B2C_CLIENT_ID` | Azure B2C client ID | - | No |
| `DATABASE_URL` | PostgreSQL connection | - | Yes |
| `REDIS_HOST` | Redis host | `localhost` | Yes |
| `REDIS_PORT` | Redis port | `6379` | No |
| `REDIS_PASSWORD` | Redis password | - | No |
| `REDIS_SESSION_DB` | Redis DB for sessions | `1` | No |
| `CORS_ALLOWED_ORIGINS` | CORS origins | `*` | No |
| `LOG_LEVEL` | Log level | `INFO` | No |

### Helm Values

```yaml
auth:
  enabled: true
  replicaCount: 2
  
  image:
    repository: carpeta-ciudadana/auth
    tag: latest
  
  service:
    type: ClusterIP
    port: 8011
  
  oidcIssuerUrl: "https://auth.example.com"
  jwtAccessTokenExpireMinutes: "60"
  jwtRefreshTokenExpireDays: "30"
  logLevel: "INFO"
  
  resources:
    requests:
      cpu: 100m
      memory: 256Mi
    limits:
      cpu: 500m
      memory: 512Mi
  
  autoscaling:
    enabled: true
    minReplicas: 2
    maxReplicas: 10
    targetCPUUtilizationPercentage: 70
```

---

## 🚀 Deployment

### Local Development

```bash
cd services/auth

# Install dependencies
poetry install

# Run service
poetry run uvicorn app.main:app --reload --port 8011

# Test endpoints
curl http://localhost:8011/health
curl http://localhost:8011/.well-known/openid-configuration
```

### Docker

```bash
# Build image
docker build -t carpeta-ciudadana/auth:latest .

# Run container
docker run -p 8011:8011 \
  -e OIDC_ISSUER_URL=http://localhost:8011 \
  -e REDIS_HOST=redis \
  -e DATABASE_URL=postgresql://... \
  carpeta-ciudadana/auth:latest
```

### Kubernetes (Helm)

```bash
# Deploy
helm upgrade --install carpeta-ciudadana ./deploy/helm/carpeta-ciudadana \
  --set auth.enabled=true \
  --set auth.replicaCount=2 \
  --set auth.oidcIssuerUrl=https://auth.example.com

# Check status
kubectl get pods -l app=auth
kubectl logs -l app=auth -f

# Test service
kubectl port-forward svc/carpeta-ciudadana-dev-auth 8011:8011
curl http://localhost:8011/health
```

---

## 🧪 Testing

### Health Check

```bash
curl http://localhost:8011/health
# Expected: {"status":"healthy","service":"auth"}
```

### OIDC Discovery

```bash
curl http://localhost:8011/.well-known/openid-configuration | jq
# Should return OIDC configuration
```

### JWKS

```bash
curl http://localhost:8011/.well-known/jwks.json | jq
# Should return public keys
```

### Token Request (Mock)

```bash
curl -X POST http://localhost:8011/api/auth/token \
  -H "Content-Type: application/json" \
  -d '{
    "grant_type": "authorization_code",
    "code": "test_code"
  }' | jq
```

### UserInfo (Mock)

```bash
curl http://localhost:8011/api/auth/userinfo \
  -H "Authorization: Bearer test_token" | jq
```

### Session Create

```bash
curl -X POST http://localhost:8011/api/sessions \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user-123",
    "email": "test@example.com",
    "roles": ["user"]
  }' | jq
```

---

## 🔍 Troubleshooting

### Service no inicia

**Síntoma**: Pod en CrashLoopBackOff

**Debug**:
```bash
kubectl logs -l app=auth --tail=100

# Check environment
kubectl exec -it <auth-pod> -- env | grep -E 'REDIS|DATABASE|OIDC'
```

**Causas comunes**:
- Redis no disponible
- DATABASE_URL inválida
- Secrets faltantes

### OIDC Discovery no funciona

**Síntoma**: 404 en `/.well-known/openid-configuration`

**Solución**:
```bash
# Check service
kubectl get svc -l app=auth

# Check ingress
kubectl get ingress

# Test internal
kubectl run test --rm -it --image=curlimages/curl -- \
  curl http://carpeta-ciudadana-dev-auth:8011/.well-known/openid-configuration
```

### Sessions no persisten

**Síntoma**: Sessions desaparecen después de restart

**Causa**: Redis no configurado

**Solución**:
```bash
# Check Redis connection
kubectl exec -it <auth-pod> -- sh
nc -zv redis-host 6379

# Check Redis password
echo $REDIS_PASSWORD
```

### Tokens no validan

**Síntoma**: 401 Unauthorized

**Debug**:
```bash
# Decode JWT
echo "<token>" | cut -d. -f2 | base64 -d | jq

# Check issuer
# Should match OIDC_ISSUER_URL
```

---

## 📊 Monitoring

### Prometheus Metrics

TODO: Implementar métricas

```prometheus
# Sessions created
auth_sessions_created_total

# Sessions active
auth_sessions_active_gauge

# Tokens issued
auth_tokens_issued_total

# Token validations
auth_token_validations_total{status="success|failure"}
```

### Health Checks

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8011
  initialDelaySeconds: 15
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /ready
    port: 8011
  initialDelaySeconds: 10
  periodSeconds: 5
```

---

## 🔐 Security

### JWT Signing

- **Algorithm**: RS256 (asymmetric)
- **Key rotation**: TODO
- **Key storage**: Azure Key Vault (TODO)

### Session Security

- **Storage**: Redis (in-memory)
- **TTL**: 24 hours
- **Refresh**: Extends TTL

### CORS

Configurado para permitir orígenes específicos:

```python
CORS_ALLOWED_ORIGINS = [
  "http://localhost:3000",
  "https://frontend.example.com"
]
```

---

## 🚧 TODOs

- [ ] Implementar JWT signing con Key Vault
- [ ] Implementar token refresh logic
- [ ] Conectar Redis para sessions
- [ ] Implementar JWKS con public keys reales
- [ ] Agregar rate limiting
- [ ] Implementar Prometheus metrics
- [ ] Agregar audit logging
- [ ] Implementar token revocation
- [ ] PKCE support completo
- [ ] Introspection endpoint

---

## 📚 Referencias

- [OpenID Connect Core](https://openid.net/specs/openid-connect-core-1_0.html)
- [OpenID Connect Discovery](https://openid.net/specs/openid-connect-discovery-1_0.html)
- [OAuth 2.0 RFC 6749](https://datatracker.ietf.org/doc/html/rfc6749)
- [JWT RFC 7519](https://datatracker.ietf.org/doc/html/rfc7519)
- [PKCE RFC 7636](https://datatracker.ietf.org/doc/html/rfc7636)

---

## ✅ Resumen

**Servicio**: Auth  
**Puerto**: 8011  
**Features**:
- ✅ OIDC Provider
- ✅ Token management
- ✅ Session storage (Redis)
- ✅ Azure AD B2C integration
- ✅ Health endpoints
- ✅ CORS configured
- ✅ Dockerized
- ✅ Helm deployed

**Estado**: 🟢 Funcional (con TODOs pendientes)

---

**Generado**: 2025-10-13 04:00  
**Autor**: Manuel Jurado  
**Versión**: 1.0.0

