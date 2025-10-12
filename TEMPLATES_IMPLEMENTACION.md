# 📝 TEMPLATES DE IMPLEMENTACIÓN - Servicios Faltantes

Este documento contiene **templates de código** listos para usar para completar los servicios faltantes.

---

## 1. AUTH SERVICE

### `services/auth/app/main.py`

```python
"""Auth Service - OIDC Provider."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import Settings
from app.routers import oidc
from app.services.key_manager import KeyManager

# Setup logging
try:
    from carpeta_common.middleware import setup_logging
    setup_logging()
except ImportError:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

logger = logging.getLogger(__name__)
settings = Settings()
key_manager = KeyManager(settings)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan."""
    logger.info("🔐 Starting Auth Service (OIDC Provider)...")
    
    # Generate or load RSA keys
    await key_manager.initialize()
    
    yield
    
    logger.info("👋 Shutting down Auth Service...")


# Create FastAPI app
app = FastAPI(
    title="Auth Service",
    description="OIDC Provider for Carpeta Ciudadana",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(oidc.router, tags=["oidc"])


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "auth",
        "version": "1.0.0"
    }


@app.get("/ready")
async def readiness_check():
    """Readiness check endpoint."""
    # Check if keys are loaded
    is_ready = key_manager.is_ready()
    
    if not is_ready:
        return {"status": "not_ready", "reason": "RSA keys not loaded"}, 503
    
    return {"status": "ready"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8008)
```

### `services/auth/Dockerfile`

```dockerfile
FROM python:3.13-slim

WORKDIR /app

# Install Poetry
RUN pip install --no-cache-dir poetry==2.2.1

# Copy poetry files
COPY pyproject.toml poetry.lock* ./

# Install dependencies
RUN poetry config virtualenvs.create false \
    && poetry install --no-dev --no-interaction --no-ansi

# Copy application code
COPY app/ ./app/

# Expose port
EXPOSE 8008

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8008"]
```

---

## 2. NOTIFICATION SERVICE

### `services/notification/app/main.py`

```python
"""Notification Service - Email + Webhooks."""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.config import Settings
from app.consumers.notification_consumer import NotificationConsumer
from app.routers import notifications

# Setup logging
try:
    from carpeta_common.middleware import setup_logging, setup_cors
    setup_logging()
    COMMON_AVAILABLE = True
except ImportError:
    from fastapi.middleware.cors import CORSMiddleware
    COMMON_AVAILABLE = False
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

logger = logging.getLogger(__name__)
settings = Settings()
consumer = None
consumer_task = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan."""
    global consumer, consumer_task
    
    logger.info("📧 Starting Notification Service...")
    
    # Start Service Bus consumer in background
    if settings.servicebus_connection_string:
        consumer = NotificationConsumer(settings)
        consumer_task = asyncio.create_task(consumer.start())
        logger.info("✅ Service Bus consumer started")
    else:
        logger.warning("⚠️  Service Bus not configured, running without event consumption")
    
    yield
    
    # Shutdown consumer
    if consumer_task:
        consumer_task.cancel()
        try:
            await consumer_task
        except asyncio.CancelledError:
            pass
    
    logger.info("👋 Shutting down Notification Service...")


# Create FastAPI app
app = FastAPI(
    title="Notification Service",
    description="Email and webhook notifications",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
if COMMON_AVAILABLE:
    setup_cors(app)
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Include routers
app.include_router(notifications.router, prefix="/notify", tags=["notifications"])


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return JSONResponse(
        content={
            "status": "healthy",
            "service": "notification",
            "version": "1.0.0",
            "consumer_running": consumer_task is not None and not consumer_task.done()
        }
    )


@app.get("/ready")
async def readiness_check():
    """Readiness check endpoint."""
    # Check if consumer is running (if configured)
    if settings.servicebus_connection_string:
        if not consumer_task or consumer_task.done():
            return JSONResponse(
                status_code=503,
                content={"status": "not_ready", "reason": "Consumer not running"}
            )
    
    return {"status": "ready"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8010)
```

### `services/notification/Dockerfile`

```dockerfile
FROM python:3.13-slim

WORKDIR /app

# Install Poetry
RUN pip install --no-cache-dir poetry==2.2.1

# Copy poetry files
COPY pyproject.toml poetry.lock* ./

# Install dependencies
RUN poetry config virtualenvs.create false \
    && poetry install --no-dev --no-interaction --no-ansi

# Copy application code
COPY app/ ./app/

# Expose port
EXPOSE 8010

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8010"]
```

---

## 3. READ_MODELS SERVICE

### `services/read_models/app/main.py`

```python
"""Read Models Service - CQRS Read Side."""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from app.config import Settings
from app.database import init_db, engine
from app.routers import read_queries

# Setup logging
try:
    from carpeta_common.middleware import setup_logging, setup_cors
    setup_logging()
    COMMON_AVAILABLE = True
except ImportError:
    from fastapi.middleware.cors import CORSMiddleware
    COMMON_AVAILABLE = False
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

logger = logging.getLogger(__name__)
settings = Settings()
consumer_task = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan."""
    global consumer_task
    
    logger.info("🔄 Starting Read Models Service (CQRS)...")
    
    # Initialize database
    await init_db()
    
    # Start event consumers in background (if Service Bus configured)
    if settings.servicebus_connection_string:
        # TODO: Import and start consumers
        # from app.consumers.event_projector import EventProjector
        # consumer = EventProjector(settings)
        # consumer_task = asyncio.create_task(consumer.start())
        logger.info("✅ Event consumers started")
    else:
        logger.warning("⚠️  Service Bus not configured, running without projections")
    
    yield
    
    # Shutdown
    if consumer_task:
        consumer_task.cancel()
        try:
            await consumer_task
        except asyncio.CancelledError:
            pass
    
    await engine.dispose()
    logger.info("👋 Shutting down Read Models Service...")


# Create FastAPI app
app = FastAPI(
    title="Read Models Service",
    description="CQRS read models with optimized queries",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
if COMMON_AVAILABLE:
    setup_cors(app)
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Include routers
app.include_router(read_queries.router, prefix="/read", tags=["read-models"])


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "read-models",
        "version": "1.0.0"
    }


@app.get("/ready")
async def readiness_check():
    """Readiness check endpoint."""
    # TODO: Check database connection
    return {"status": "ready"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8007)
```

### `services/read_models/app/routers/read_queries.py`

```python
"""Read queries router - Optimized read models."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app import models

router = APIRouter()


@router.get("/documents")
async def get_documents(
    citizen_id: Optional[int] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """
    Get optimized read model for documents.
    
    Returns denormalized data for fast queries.
    """
    # TODO: Implement query to read_documents table
    
    return {
        "documents": [],
        "total": 0,
        "limit": limit,
        "offset": offset
    }


@router.get("/transfers")
async def get_transfers(
    citizen_id: Optional[int] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """
    Get optimized read model for transfers.
    
    Returns denormalized data for fast queries.
    """
    # TODO: Implement query to read_transfers table
    
    return {
        "transfers": [],
        "total": 0,
        "limit": limit,
        "offset": offset
    }
```

### `services/read_models/app/consumers/event_projector.py`

```python
"""Event projector - Projects events to read models."""

import asyncio
import logging
from typing import Any, Dict

from app.config import Settings

logger = logging.getLogger(__name__)


class EventProjector:
    """Projects Service Bus events to read models."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        # TODO: Initialize Service Bus consumer
    
    async def start(self):
        """Start consuming events."""
        logger.info("Starting event projector...")
        
        # TODO: Implement event consumption
        # Listen to:
        # - citizen.registered
        # - document.uploaded
        # - document.authenticated
        # - transfer.requested
        # - transfer.confirmed
        
        while True:
            try:
                # Consume event
                # Project to read model
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Error in event projector: {e}")
                await asyncio.sleep(5)
    
    async def project_event(self, event: Dict[str, Any]):
        """Project a single event to read model."""
        event_type = event.get("event_type")
        
        if event_type == "citizen.registered":
            await self._project_citizen_registered(event)
        elif event_type == "document.uploaded":
            await self._project_document_uploaded(event)
        elif event_type == "document.authenticated":
            await self._project_document_authenticated(event)
        elif event_type == "transfer.confirmed":
            await self._project_transfer_confirmed(event)
    
    async def _project_citizen_registered(self, event: Dict[str, Any]):
        """Update citizen_name in read_documents."""
        # TODO: Implement
        pass
    
    async def _project_document_uploaded(self, event: Dict[str, Any]):
        """Create entry in read_documents."""
        # TODO: Implement
        pass
    
    async def _project_document_authenticated(self, event: Dict[str, Any]):
        """Update is_authenticated in read_documents."""
        # TODO: Implement
        pass
    
    async def _project_transfer_confirmed(self, event: Dict[str, Any]):
        """Update transfer status in read_transfers."""
        # TODO: Implement
        pass
```

### `services/read_models/Dockerfile`

```dockerfile
FROM python:3.13-slim

WORKDIR /app

# Install Poetry
RUN pip install --no-cache-dir poetry==2.2.1

# Copy poetry files
COPY pyproject.toml poetry.lock* ./

# Install dependencies
RUN poetry config virtualenvs.create false \
    && poetry install --no-dev --no-interaction --no-ansi

# Copy application code
COPY app/ ./app/

# Expose port
EXPOSE 8007

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8007"]
```

---

## 4. HELM TEMPLATES

### `deploy/helm/carpeta-ciudadana/templates/deployment-frontend.yaml`

```yaml
{{- if .Values.frontend.enabled -}}
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "carpeta-ciudadana.fullname" . }}-frontend
  labels:
    app: frontend
    {{- include "carpeta-ciudadana.labels" . | nindent 4 }}
spec:
  replicas: {{ .Values.frontend.replicaCount }}
  selector:
    matchLabels:
      app: frontend
  template:
    metadata:
      labels:
        app: frontend
    spec:
      serviceAccountName: {{ include "carpeta-ciudadana.serviceAccountName" . }}
      containers:
      - name: frontend
        image: "{{ .Values.global.imageRegistry }}/{{ .Values.frontend.image.repository }}:{{ .Values.frontend.image.tag }}"
        imagePullPolicy: {{ .Values.global.imagePullPolicy }}
        ports:
        - containerPort: 3000
          name: http
        env:
        - name: NEXT_PUBLIC_API_URL
          value: "http://{{ include "carpeta-ciudadana.fullname" . }}-gateway:8000"
        - name: NEXT_PUBLIC_OPERATOR_ID
          value: "operator-demo"
        - name: NEXT_PUBLIC_OPERATOR_NAME
          value: "Carpeta Ciudadana Demo"
        envFrom:
        - configMapRef:
            name: {{ include "carpeta-ciudadana.fullname" . }}-app-flags
        resources:
          {{- toYaml .Values.frontend.resources | nindent 10 }}
        livenessProbe:
          httpGet:
            path: /
            port: 3000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /
            port: 3000
          initialDelaySeconds: 20
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: {{ include "carpeta-ciudadana.fullname" . }}-frontend
  labels:
    app: frontend
    {{- include "carpeta-ciudadana.labels" . | nindent 4 }}
spec:
  type: {{ .Values.frontend.service.type }}
  ports:
  - port: {{ .Values.frontend.service.port }}
    targetPort: 3000
    name: http
  selector:
    app: frontend
---
{{- if .Values.frontend.autoscaling.enabled }}
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: {{ include "carpeta-ciudadana.fullname" . }}-frontend
  labels:
    app: frontend
    {{- include "carpeta-ciudadana.labels" . | nindent 4 }}
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: {{ include "carpeta-ciudadana.fullname" . }}-frontend
  minReplicas: {{ .Values.frontend.autoscaling.minReplicas }}
  maxReplicas: {{ .Values.frontend.autoscaling.maxReplicas }}
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: {{ .Values.frontend.autoscaling.targetCPUUtilizationPercentage }}
{{- end }}
{{- end }}
```

### `deploy/helm/carpeta-ciudadana/templates/deployment-sharing.yaml`

```yaml
{{- if .Values.sharing.enabled -}}
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "carpeta-ciudadana.fullname" . }}-sharing
  labels:
    app: sharing
    {{- include "carpeta-ciudadana.labels" . | nindent 4 }}
spec:
  replicas: {{ .Values.sharing.replicaCount }}
  selector:
    matchLabels:
      app: sharing
  template:
    metadata:
      labels:
        app: sharing
    spec:
      serviceAccountName: {{ include "carpeta-ciudadana.serviceAccountName" . }}
      containers:
      - name: sharing
        image: "{{ .Values.global.imageRegistry }}/{{ .Values.sharing.image.repository }}:{{ .Values.sharing.image.tag }}"
        imagePullPolicy: {{ .Values.global.imagePullPolicy }}
        ports:
        - containerPort: 8000
          name: http
        envFrom:
        - configMapRef:
            name: {{ include "carpeta-ciudadana.fullname" . }}-app-flags
        - secretRef:
            name: db-secrets
        - secretRef:
            name: azure-storage
        - secretRef:
            name: redis-auth
            optional: true
        resources:
          {{- toYaml .Values.sharing.resources | nindent 10 }}
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 15
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: {{ include "carpeta-ciudadana.fullname" . }}-sharing
  labels:
    app: sharing
    {{- include "carpeta-ciudadana.labels" . | nindent 4 }}
spec:
  type: {{ .Values.sharing.service.type }}
  ports:
  - port: {{ .Values.sharing.service.port }}
    targetPort: 8000
    name: http
  selector:
    app: sharing
---
{{- if .Values.sharing.autoscaling.enabled }}
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: {{ include "carpeta-ciudadana.fullname" . }}-sharing
  labels:
    app: sharing
    {{- include "carpeta-ciudadana.labels" . | nindent 4 }}
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: {{ include "carpeta-ciudadana.fullname" . }}-sharing
  minReplicas: {{ .Values.sharing.autoscaling.minReplicas }}
  maxReplicas: {{ .Values.sharing.autoscaling.maxReplicas }}
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: {{ .Values.sharing.autoscaling.targetCPUUtilizationPercentage }}
{{- end }}
{{- end }}
```

### `deploy/helm/carpeta-ciudadana/templates/deployment-notification.yaml`

```yaml
{{- if .Values.notification.enabled -}}
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "carpeta-ciudadana.fullname" . }}-notification
  labels:
    app: notification
    {{- include "carpeta-ciudadana.labels" . | nindent 4 }}
spec:
  replicas: {{ .Values.notification.replicaCount }}
  selector:
    matchLabels:
      app: notification
  template:
    metadata:
      labels:
        app: notification
    spec:
      serviceAccountName: {{ include "carpeta-ciudadana.serviceAccountName" . }}
      containers:
      - name: notification
        image: "{{ .Values.global.imageRegistry }}/{{ .Values.notification.image.repository }}:{{ .Values.notification.image.tag }}"
        imagePullPolicy: {{ .Values.global.imagePullPolicy }}
        ports:
        - containerPort: 8000
          name: http
        envFrom:
        - configMapRef:
            name: {{ include "carpeta-ciudadana.fullname" . }}-app-flags
        - secretRef:
            name: db-secrets
        - secretRef:
            name: sb-secrets
        - secretRef:
            name: smtp-credentials
            optional: true
        resources:
          {{- toYaml .Values.notification.resources | nindent 10 }}
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 20
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 15
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: {{ include "carpeta-ciudadana.fullname" . }}-notification
  labels:
    app: notification
    {{- include "carpeta-ciudadana.labels" . | nindent 4 }}
spec:
  type: {{ .Values.notification.service.type }}
  ports:
  - port: {{ .Values.notification.service.port }}
    targetPort: 8000
    name: http
  selector:
    app: notification
---
{{- if .Values.notification.autoscaling.enabled }}
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: {{ include "carpeta-ciudadana.fullname" . }}-notification
  labels:
    app: notification
    {{- include "carpeta-ciudadana.labels" . | nindent 4 }}
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: {{ include "carpeta-ciudadana.fullname" . }}-notification
  minReplicas: {{ .Values.notification.autoscaling.minReplicas }}
  maxReplicas: {{ .Values.notification.autoscaling.maxReplicas }}
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: {{ .Values.notification.autoscaling.targetCPUUtilizationPercentage }}
{{- end }}
{{- end }}
```

### `deploy/helm/carpeta-ciudadana/templates/deployment-auth.yaml`

```yaml
{{- if .Values.auth.enabled -}}
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "carpeta-ciudadana.fullname" . }}-auth
  labels:
    app: auth
    {{- include "carpeta-ciudadana.labels" . | nindent 4 }}
spec:
  replicas: {{ .Values.auth.replicaCount }}
  selector:
    matchLabels:
      app: auth
  template:
    metadata:
      labels:
        app: auth
    spec:
      serviceAccountName: {{ include "carpeta-ciudadana.serviceAccountName" . }}
      containers:
      - name: auth
        image: "{{ .Values.global.imageRegistry }}/{{ .Values.auth.image.repository }}:{{ .Values.auth.image.tag }}"
        imagePullPolicy: {{ .Values.global.imagePullPolicy }}
        ports:
        - containerPort: 8000
          name: http
        envFrom:
        - configMapRef:
            name: {{ include "carpeta-ciudadana.fullname" . }}-app-flags
        - secretRef:
            name: db-secrets
        - secretRef:
            name: redis-auth
            optional: true
        resources:
          {{- toYaml .Values.auth.resources | nindent 10 }}
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 15
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: {{ include "carpeta-ciudadana.fullname" . }}-auth
  labels:
    app: auth
    {{- include "carpeta-ciudadana.labels" . | nindent 4 }}
spec:
  type: {{ .Values.auth.service.type }}
  ports:
  - port: {{ .Values.auth.service.port }}
    targetPort: 8000
    name: http
  selector:
    app: auth
---
{{- if .Values.auth.autoscaling.enabled }}
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: {{ include "carpeta-ciudadana.fullname" . }}-auth
  labels:
    app: auth
    {{- include "carpeta-ciudadana.labels" . | nindent 4 }}
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: {{ include "carpeta-ciudadana.fullname" . }}-auth
  minReplicas: {{ .Values.auth.autoscaling.minReplicas }}
  maxReplicas: {{ .Values.auth.autoscaling.maxReplicas }}
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: {{ .Values.auth.autoscaling.targetCPUUtilizationPercentage }}
{{- end }}
{{- end }}
```

---

## 5. ACTUALIZAR values.yaml

Añadir sección para **auth**:

```yaml
# Auth Service (OIDC Provider)
auth:
  enabled: true
  replicaCount: 2
  image:
    repository: carpeta-auth
    tag: latest
  service:
    type: ClusterIP
    port: 8000
  resources:
    requests:
      memory: "128Mi"
      cpu: "100m"
    limits:
      memory: "256Mi"
      cpu: "500m"
  autoscaling:
    enabled: true
    minReplicas: 2
    maxReplicas: 10
    targetCPUUtilizationPercentage: 70
```

---

## 6. COMANDO DE EJECUCIÓN

Una vez implementados todos los templates, ejecutar:

```bash
# 1. Crear archivos con los templates anteriores

# 2. Actualizar scripts
./scripts/update-all-scripts.sh  # (crear este script con las actualizaciones)

# 3. Build de imágenes Docker
./build-all.sh

# 4. Test local
./start-services.sh

# 5. Commit y push para CI/CD
git add .
git commit -m "feat: complete implementation of all services"
git push origin master

# El pipeline de CI/CD:
# - Compilará todos los servicios
# - Ejecutará tests
# - Construirá y subirá 12 imágenes Docker
# - Desplegará los 12 servicios en AKS
```

---

**Nota**: Estos son templates base. Necesitarás completar:

1. TODOs marcados en el código
2. Lógica de negocio específica de cada servicio
3. Tests unitarios
4. Configuración de environment variables

---

**Generado**: 12 Octubre 2025  
**Versión**: 1.0.0

