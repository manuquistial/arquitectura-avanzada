# 🎯 PLAN DE ACCIÓN - Cumplimiento de Requerimientos

> **Basado en**: `Requerimientos_Proyecto_GovCarpeta.md`  
> **Análisis**: `CUMPLIMIENTO_REQUERIMIENTOS.md`  
> **Fecha**: 12 de Octubre 2025

---

## 📊 RESUMEN DE PRIORIDADES

### 🔴 CRÍTICO (Bloquean funcionalidad core):
- ❌ WORM + Retención de documentos
- ❌ Azure AD B2C (identidad real)
- ❌ transfer-worker + KEDA
- ❌ Key Vault + CSI Secret Store
- ❌ NetworkPolicies
- ⚠️ Orden de transferencia (conflicto)

### 🟠 ALTA (Funcionalidad importante):
- Sistema de usuarios (users, citizen_links)
- Headers M2M completos (X-Nonce, X-Signature)
- PodDisruptionBudgets
- Vistas frontend faltantes
- Nodepools dedicados

### 🟡 MEDIA (Mejoras significativas):
- Accesibilidad WCAG 2.2 AA
- Tests E2E completos
- RLS en PostgreSQL
- Azure Cache for Redis
- Application Insights

### 🟢 BAJA (Nice to have):
- ExternalDNS
- pgBouncer
- Chaos testing
- SBOM generation

---

## 📋 PLAN PASO A PASO (24 FASES)

### FASE 1: DOCUMENTOS WORM + RETENCIÓN 🔴 CRÍTICO

**Tiempo estimado**: 8 horas

#### 1.1 Migración de Base de Datos

**Crear**: `services/ingestion/alembic/versions/XXX_add_worm_retention.py`

```python
"""Add WORM and retention fields.

Revision ID: XXX
"""

from alembic import op
import sqlalchemy as sa


def upgrade():
    # Add columns
    op.add_column('document_metadata',
        sa.Column('state', sa.String(), nullable=False, server_default='UNSIGNED'))
    op.add_column('document_metadata',
        sa.Column('worm_locked', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('document_metadata',
        sa.Column('signed_at', sa.DateTime(), nullable=True))
    op.add_column('document_metadata',
        sa.Column('retention_until', sa.Date(), nullable=True))
    op.add_column('document_metadata',
        sa.Column('hub_signature_ref', sa.String(), nullable=True))
    op.add_column('document_metadata',
        sa.Column('legal_hold', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('document_metadata',
        sa.Column('lifecycle_tier', sa.String(), nullable=False, server_default='Hot'))
    
    # Create WORM enforcement function
    op.execute("""
        CREATE OR REPLACE FUNCTION prevent_worm_update()
        RETURNS TRIGGER AS $$
        BEGIN
            IF OLD.worm_locked = TRUE AND (
                NEW.worm_locked = FALSE OR
                NEW.state != OLD.state OR
                NEW.retention_until != OLD.retention_until OR
                NEW.hub_signature_ref != OLD.hub_signature_ref OR
                NEW.signed_at != OLD.signed_at
            ) THEN
                RAISE EXCEPTION 'Cannot modify WORM-locked document fields';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    # Create trigger
    op.execute("""
        CREATE TRIGGER enforce_worm_immutability
        BEFORE UPDATE ON document_metadata
        FOR EACH ROW
        EXECUTE FUNCTION prevent_worm_update();
    """)


def downgrade():
    op.execute("DROP TRIGGER IF EXISTS enforce_worm_immutability ON document_metadata")
    op.execute("DROP FUNCTION IF EXISTS prevent_worm_update()")
    op.drop_column('document_metadata', 'lifecycle_tier')
    op.drop_column('document_metadata', 'legal_hold')
    op.drop_column('document_metadata', 'hub_signature_ref')
    op.drop_column('document_metadata', 'retention_until')
    op.drop_column('document_metadata', 'signed_at')
    op.drop_column('document_metadata', 'worm_locked')
    op.drop_column('document_metadata', 'state')
```

#### 1.2 Actualizar Models

**Modificar**: `services/ingestion/app/models.py`

```python
from sqlalchemy import String, Boolean, DateTime, Date

class DocumentMetadata(Base):
    __tablename__ = "document_metadata"
    
    # ... campos existentes ...
    
    # WORM and Retention (NUEVO)
    state: Mapped[str] = mapped_column(String, default="UNSIGNED")
    worm_locked: Mapped[bool] = mapped_column(Boolean, default=False)
    signed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    retention_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    hub_signature_ref: Mapped[str | None] = mapped_column(String, nullable=True)
    legal_hold: Mapped[bool] = mapped_column(Boolean, default=False)
    lifecycle_tier: Mapped[str] = mapped_column(String, default="Hot")
```

#### 1.3 Signature Service - Actualizar WORM

**Modificar**: `services/signature/app/routers/signature.py`

```python
from datetime import date, timedelta

@router.post("/sign")
async def sign_document(...):
    # ... código existente ...
    
    # Después de hub authentication exitosa:
    if hub_result.ok:
        # Calcular retention (5 años desde firma)
        retention_date = date.today() + timedelta(days=365*5)
        
        # Actualizar documento a WORM
        await db.execute(
            update(DocumentMetadata)
            .where(DocumentMetadata.id == document_id)
            .values(
                state="SIGNED",
                worm_locked=True,
                signed_at=datetime.utcnow(),
                retention_until=retention_date,
                hub_signature_ref=hub_response.get("signature_ref", "hub-sig-xxx")
            )
        )
        await db.commit()
        
        # Actualizar blob tags
        await storage_client.set_blob_tags(
            blob_name=document.blob_name,
            tags={
                "state": "SIGNED",
                "worm": "true",
                "retentionUntil": retention_date.isoformat()
            }
        )
```

#### 1.4 CronJob Auto-purga UNSIGNED (30 días)

**Crear**: `deploy/kubernetes/cronjob-purge-unsigned.yaml`

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: purge-unsigned-documents
  namespace: carpeta-ciudadana
spec:
  schedule: "0 2 * * *"  # Diario 2am
  concurrencyPolicy: Forbid
  successfulJobsHistoryLimit: 3
  failedJobsHistoryLimit: 3
  jobTemplate:
    spec:
      template:
        spec:
          serviceAccountName: carpeta-ciudadana-sa
          restartPolicy: Never
          containers:
          - name: purge
            image: manuelquistial/carpeta-ingestion:latest
            command: 
            - python
            - -c
            - |
              import asyncio
              from datetime import datetime, timedelta
              from app.database import engine, SessionLocal
              from app.models import DocumentMetadata
              from sqlalchemy import select, delete
              
              async def purge_old_unsigned():
                  async with SessionLocal() as db:
                      cutoff = datetime.utcnow() - timedelta(days=30)
                      
                      # Buscar documentos UNSIGNED > 30 días
                      stmt = select(DocumentMetadata).where(
                          DocumentMetadata.state == "UNSIGNED",
                          DocumentMetadata.created_at < cutoff
                      )
                      result = await db.execute(stmt)
                      old_docs = result.scalars().all()
                      
                      print(f"Found {len(old_docs)} UNSIGNED documents > 30 days old")
                      
                      # Eliminar blobs
                      for doc in old_docs:
                          # TODO: Delete blob from Azure Storage
                          print(f"Deleting blob: {doc.blob_name}")
                      
                      # Eliminar metadata
                      stmt = delete(DocumentMetadata).where(
                          DocumentMetadata.state == "UNSIGNED",
                          DocumentMetadata.created_at < cutoff
                      )
                      await db.execute(stmt)
                      await db.commit()
                      
                      print(f"Purged {len(old_docs)} old unsigned documents")
              
              asyncio.run(purge_old_unsigned())
            envFrom:
            - configMapRef:
                name: app-flags
            - secretRef:
                name: db-secrets
            - secretRef:
                name: azure-storage
```

#### 1.5 Blob Lifecycle Policy (Terraform)

**Crear**: `infra/terraform/modules/storage/lifecycle.tf`

```hcl
resource "azurerm_storage_management_policy" "document_lifecycle" {
  storage_account_id = azurerm_storage_account.main.id

  rule {
    name    = "move-signed-to-cool-after-90d"
    enabled = true
    
    filters {
      blob_types   = ["blockBlob"]
      prefix_match = ["documents/"]
    }
    
    actions {
      base_blob {
        tier_to_cool_after_days_since_modification_greater_than    = 90
        tier_to_archive_after_days_since_modification_greater_than = 365
      }
    }
  }
  
  rule {
    name    = "delete-unsigned-after-30d"
    enabled = true
    
    filters {
      blob_types   = ["blockBlob"]
      prefix_match = ["documents/"]
      # Note: Necesita blob index tags para filtrar por state=UNSIGNED
    }
    
    actions {
      base_blob {
        delete_after_days_since_modification_greater_than = 30
      }
    }
  }
}

# Enable blob versioning for WORM
resource "azurerm_storage_account" "main" {
  # ... config existente ...
  
  blob_properties {
    versioning_enabled = true
    
    # Immutability policy for WORM
    container_delete_retention_policy {
      days = 7
    }
  }
}
```

#### 1.6 Frontend - Mostrar Retención

**Modificar**: `apps/frontend/src/app/documents/page.tsx`

```typescript
<div className="document-card">
  <h3>{doc.filename}</h3>
  <p>Estado: {doc.state}</p>
  
  {doc.state === 'UNSIGNED' && (
    <div className="retention-warning">
      <WarningIcon />
      <span>
        Documento sin firmar. Se eliminará automáticamente el{' '}
        {new Date(doc.created_at).setDate(
          new Date(doc.created_at).getDate() + 30
        ).toLocaleDateString()}
        {' '}si no se autentica.
      </span>
    </div>
  )}
  
  {doc.state === 'SIGNED' && (
    <div className="retention-info">
      <LockIcon />
      <span>
        Documento firmado (WORM). Retención hasta:{' '}
        {new Date(doc.retention_until).toLocaleDateString()}
        {' '}(protegido por 5 años)
      </span>
    </div>
  )}
</div>
```

**ENTREGABLES**:
- ✅ Migración Alembic
- ✅ Models actualizados
- ✅ Signature service actualiza WORM
- ✅ CronJob purga automática
- ✅ Terraform lifecycle policy
- ✅ Frontend muestra retención

**VERIFICACIÓN**:
```bash
# 1. Ejecutar migración
cd services/ingestion
alembic upgrade head

# 2. Crear documento UNSIGNED
curl -X POST .../documents/upload-url

# 3. Firmar documento
curl -X POST .../signature/sign

# 4. Verificar WORM en DB
psql -c "SELECT id, state, worm_locked, retention_until FROM document_metadata WHERE id='xxx';"

# Esperado:
# state='SIGNED', worm_locked=true, retention_until='2030-10-12'

# 5. Intentar actualizar (debe fallar)
psql -c "UPDATE document_metadata SET state='UNSIGNED' WHERE id='xxx';"
# Error: Cannot modify WORM-locked document
```

---

### FASE 2: AZURE AD B2C (OIDC Real) 🔴 CRÍTICO

**Tiempo estimado**: 12 horas

#### 2.1 Crear Tenant B2C en Azure Portal

```bash
# 1. Azure Portal → Azure AD B2C → Create tenant
# Name: carpeta-ciudadana-b2c
# Domain: carpetaciudadana.onmicrosoft.com

# 2. Create User Flow
# Type: Sign up and sign in
# Name: B2C_1_signupsignin
# Identity providers: Email signup
# User attributes: Given name, Surname, Email

# 3. Register application
# Name: carpeta-ciudadana-frontend
# Reply URLs:
#   - http://localhost:3000/api/auth/callback/azure-ad-b2c (dev)
#   - https://app.carpeta-ciudadana.example.com/api/auth/callback/azure-ad-b2c (prod)
# Get: Client ID, Tenant ID
```

#### 2.2 Instalar NextAuth

**Ejecutar**: en apps/frontend

```bash
cd apps/frontend
npm install next-auth@latest
```

#### 2.3 Configurar NextAuth API Route

**Crear**: `apps/frontend/src/app/api/auth/[...nextauth]/route.ts`

```typescript
import NextAuth, { NextAuthOptions } from "next-auth";
import { JWT } from "next-auth/jwt";

const b2cTenant = process.env.AZURE_AD_B2C_TENANT_NAME;
const b2cPolicy = process.env.AZURE_AD_B2C_PRIMARY_USER_FLOW;
const clientId = process.env.AZURE_AD_B2C_CLIENT_ID;
const clientSecret = process.env.AZURE_AD_B2C_CLIENT_SECRET;

export const authOptions: NextAuthOptions = {
  providers: [
    {
      id: "azure-ad-b2c",
      name: "Azure AD B2C",
      type: "oauth",
      wellKnown: `https://${b2cTenant}.b2clogin.com/${b2cTenant}.onmicrosoft.com/${b2cPolicy}/v2.0/.well-known/openid-configuration`,
      authorization: { params: { scope: "openid profile email offline_access" } },
      clientId: clientId!,
      clientSecret: clientSecret!,
      idToken: true,
      profile(profile) {
        return {
          id: profile.sub,
          name: profile.name,
          email: profile.emails?.[0],
        };
      },
    },
  ],
  session: {
    strategy: "jwt",
    maxAge: 30 * 60, // 30 minutos
  },
  cookies: {
    sessionToken: {
      name: `__Secure-next-auth.session-token`,
      options: {
        httpOnly: true,
        sameSite: 'lax',
        path: '/',
        secure: process.env.NODE_ENV === 'production',
      },
    },
  },
  callbacks: {
    async jwt({ token, account, profile }) {
      if (account) {
        token.accessToken = account.access_token;
        token.idToken = account.id_token;
      }
      return token;
    },
    async session({ session, token }) {
      session.accessToken = token.accessToken as string;
      session.user.id = token.sub!;
      return session;
    },
  },
};

const handler = NextAuth(authOptions);

export { handler as GET, handler as POST };
```

#### 2.4 Actualizar AuthStore (Zustand)

**Modificar**: `apps/frontend/src/store/authStore.ts`

```typescript
import { signIn, signOut, useSession } from 'next-auth/react';

export const useAuthStore = create<AuthState>()(
  (set) => ({
    login: async (email: string, password: string) => {
      // NextAuth maneja el flujo OIDC
      await signIn('azure-ad-b2c', {
        callbackUrl: '/dashboard',
      });
    },
    
    logout: async () => {
      await signOut({ callbackUrl: '/' });
    },
  })
);
```

#### 2.5 Middleware de Rutas Protegidas

**Crear**: `apps/frontend/src/middleware.ts`

```typescript
import { withAuth } from "next-auth/middleware";

export default withAuth({
  callbacks: {
    authorized({ token }) {
      return !!token;
    },
  },
});

export const config = {
  matcher: ['/dashboard/:path*', '/documents/:path*', '/upload/:path*', '/transfer/:path*'],
};
```

#### 2.6 Endpoint Bootstrap User ↔ Citizen

**Crear**: `services/citizen/app/routers/users.py`

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()

@router.post("/bootstrap")
async def bootstrap_user(
    citizen_id: int,
    user_sub: str,  # from JWT
    db: AsyncSession = Depends(get_db)
):
    """
    Link Azure AD B2C user (sub) with citizen_id.
    
    Validates:
    1. Citizen exists in DB
    2. Citizen is registered in hub (validateCitizen)
    3. Creates link in citizen_links table
    """
    # 1. Check citizen exists
    citizen = await db.get(Citizen, citizen_id)
    if not citizen:
        raise HTTPException(404, "Citizen not found")
    
    # 2. Validate in hub
    hub_result = await mintic_client.validate_citizen(citizen_id)
    if not hub_result.ok:
        raise HTTPException(400, f"Citizen not valid in hub: {hub_result.message}")
    
    # 3. Create link
    link = CitizenLink(
        user_sub=user_sub,
        citizen_id=citizen_id,
        linked_at=datetime.utcnow()
    )
    db.add(link)
    await db.commit()
    
    return {"message": "User linked to citizen", "citizen_id": citizen_id}
```

**Migración**: `services/citizen/alembic/versions/XXX_create_users_tables.py`

```python
def upgrade():
    # users table
    op.create_table('users',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('sub', sa.String(), unique=True, nullable=False),  # B2C sub
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('name', sa.String()),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )
    
    # user_roles table
    op.create_table('user_roles',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id')),
        sa.Column('role', sa.String(), nullable=False),  # citizen, operator_admin, admin
        sa.Column('granted_at', sa.DateTime(), server_default=sa.func.now()),
    )
    
    # citizen_links table
    op.create_table('citizen_links',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_sub', sa.String(), sa.ForeignKey('users.sub')),
        sa.Column('citizen_id', sa.BigInteger(), sa.ForeignKey('citizens.id')),
        sa.Column('linked_at', sa.DateTime(), server_default=sa.func.now()),
        sa.UniqueConstraint('user_sub', 'citizen_id'),
    )
```

**ENTREGABLES**:
- ✅ Azure AD B2C tenant creado
- ✅ NextAuth instalado
- ✅ API route configurado
- ✅ Middleware de rutas protegidas
- ✅ Cookie HTTPOnly+Secure
- ✅ Endpoint /api/users/bootstrap
- ✅ Tablas users, user_roles, citizen_links

**VERIFICACIÓN**:
```bash
# 1. Navegar a http://localhost:3000/login
# 2. Click "Iniciar Sesión"
# 3. Redirige a Azure AD B2C
# 4. Completa signup/signin
# 5. Redirige a /dashboard con sesión
# 6. Verificar cookie (debe ser HTTPOnly)
# 7. Vincular con citizen: POST /api/users/bootstrap
```

---

### FASE 3: transfer-worker + KEDA 🔴 CRÍTICO

**Tiempo estimado**: 10 horas

#### 3.1 Instalar KEDA (Terraform)

**Añadir**: `infra/terraform/modules/keda/main.tf`

```hcl
resource "helm_release" "keda" {
  name       = "keda"
  repository = "https://kedacore.github.io/charts"
  chart      = "keda"
  version    = "2.12.0"
  namespace  = "keda"
  create_namespace = true
  
  set {
    name  = "resources.operator.limits.cpu"
    value = "1"
  }
  
  set {
    name  = "resources.operator.limits.memory"
    value = "1Gi"
  }
  
  set {
    name  = "resources.metricServer.limits.cpu"
    value = "1"
  }
}

output "keda_installed" {
  value = true
}
```

**Añadir a**: `infra/terraform/main.tf`

```hcl
module "keda" {
  source = "./modules/keda"
  
  depends_on = [module.aks]
}
```

#### 3.2 Crear transfer-worker Service

**Crear**: `services/transfer_worker/` (nuevo servicio)

```
services/transfer_worker/
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── worker.py
│   ├── tasks.py
│   └── main.py
├── Dockerfile
├── pyproject.toml
└── tests/
```

**`app/worker.py`**:

```python
"""Transfer worker - Procesa transferencias asíncronamente."""

import asyncio
import logging
from azure.servicebus.aio import ServiceBusClient
from azure.servicebus import ServiceBusMessage

from app.config import Settings
from app.tasks import process_transfer_request, process_cleanup_request

logger = logging.getLogger(__name__)
settings = Settings()


class TransferWorker:
    """Worker que consume colas de Service Bus."""
    
    def __init__(self):
        self.servicebus_client = ServiceBusClient.from_connection_string(
            settings.servicebus_connection_string
        )
    
    async def start(self):
        """Inicia consumidores de colas."""
        logger.info("🚀 Starting Transfer Worker...")
        
        # Consumir en paralelo
        await asyncio.gather(
            self.consume_transfer_requests(),
            self.consume_cleanup_requests(),
        )
    
    async def consume_transfer_requests(self):
        """Consume cola transfer.requested."""
        async with self.servicebus_client:
            receiver = self.servicebus_client.get_queue_receiver("transfer-requested")
            async with receiver:
                while True:
                    messages = await receiver.receive_messages(max_message_count=10, max_wait_time=60)
                    
                    for msg in messages:
                        try:
                            logger.info(f"Processing transfer request: {msg.message_id}")
                            
                            # Procesar transferencia
                            await process_transfer_request(msg.body)
                            
                            # Complete message
                            await receiver.complete_message(msg)
                            logger.info(f"✅ Transfer processed: {msg.message_id}")
                            
                        except Exception as e:
                            logger.error(f"Error processing transfer: {e}")
                            # Dead letter
                            await receiver.dead_letter_message(msg, reason=str(e))
    
    async def consume_cleanup_requests(self):
        """Consume cola cleanup.requested."""
        async with self.servicebus_client:
            receiver = self.servicebus_client.get_queue_receiver("cleanup-requested")
            async with receiver:
                while True:
                    messages = await receiver.receive_messages(max_message_count=10, max_wait_time=60)
                    
                    for msg in messages:
                        try:
                            await process_cleanup_request(msg.body)
                            await receiver.complete_message(msg)
                        except Exception as e:
                            logger.error(f"Error in cleanup: {e}")
                            await receiver.dead_letter_message(msg, reason=str(e))
```

**`app/main.py`**:

```python
"""Main entry point for transfer worker."""

import asyncio
import logging

from app.worker import TransferWorker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Run worker."""
    worker = TransferWorker()
    await worker.start()


if __name__ == "__main__":
    asyncio.run(main())
```

**`Dockerfile`**:

```dockerfile
FROM python:3.13-slim

WORKDIR /app

RUN pip install --no-cache-dir poetry==2.2.1

COPY pyproject.toml poetry.lock* ./
RUN poetry config virtualenvs.create false \
    && poetry install --no-dev --no-interaction

COPY app/ ./app/

# Worker no expone puerto HTTP
CMD ["python", "-m", "app.main"]
```

#### 3.3 ScaledObject para KEDA

**Crear**: `deploy/helm/carpeta-ciudadana/templates/scaledobject-transfer-worker.yaml`

```yaml
{{- if .Values.transferWorker.enabled -}}
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: {{ include "carpeta-ciudadana.fullname" . }}-transfer-worker
  namespace: {{ .Release.Namespace }}
spec:
  scaleTargetRef:
    name: {{ include "carpeta-ciudadana.fullname" . }}-transfer-worker
  pollingInterval: 30
  cooldownPeriod: 300
  minReplicaCount: 0  # Scale-to-zero
  maxReplicaCount: 10
  triggers:
  - type: azure-servicebus
    metadata:
      queueName: transfer-requested
      namespace: {{ .Values.serviceBus.namespace }}
      queueLength: "5"  # 1 replica por cada 5 mensajes
      connectionFromEnv: SERVICEBUS_CONNECTION_STRING
  - type: azure-servicebus
    metadata:
      queueName: cleanup-requested
      namespace: {{ .Values.serviceBus.namespace }}
      queueLength: "5"
      connectionFromEnv: SERVICEBUS_CONNECTION_STRING
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "carpeta-ciudadana.fullname" . }}-transfer-worker
spec:
  replicas: 0  # KEDA controlará esto
  selector:
    matchLabels:
      app: transfer-worker
  template:
    metadata:
      labels:
        app: transfer-worker
    spec:
      serviceAccountName: {{ include "carpeta-ciudadana.serviceAccountName" . }}
      containers:
      - name: worker
        image: "{{ .Values.global.imageRegistry }}/{{ .Values.transferWorker.image.repository }}:{{ .Values.transferWorker.image.tag }}"
        envFrom:
        - configMapRef:
            name: {{ include "carpeta-ciudadana.fullname" . }}-app-flags
        - secretRef:
            name: db-secrets
        - secretRef:
            name: sb-secrets
        resources:
          {{- toYaml .Values.transferWorker.resources | nindent 10 }}
{{- end }}
```

#### 3.4 Actualizar values.yaml

```yaml
# Añadir configuración del worker
transferWorker:
  enabled: true
  image:
    repository: carpeta-transfer-worker
    tag: latest
  resources:
    requests:
      memory: "256Mi"
      cpu: "200m"
    limits:
      memory: "512Mi"
      cpu: "1000m"
  
  # Spot nodes (cost optimization)
  nodeSelector:
    kubernetes.io/os: linux
    agentpool: workers  # Spot nodepool
  
  tolerations:
  - key: "kubernetes.azure.com/scalesetpriority"
    operator: "Equal"
    value: "spot"
    effect: "NoSchedule"
```

#### 3.5 Añadir a CI/CD

**Modificar**: `.github/workflows/ci.yml`

```yaml
matrix:
  service:
    - ...existentes...
    - transfer_worker  # ← AÑADIR
```

#### 3.6 Crear Spot Nodepool (Terraform)

```hcl
# infra/terraform/modules/aks/main.tf
resource "azurerm_kubernetes_cluster_node_pool" "workers" {
  name                  = "workers"
  kubernetes_cluster_id = azurerm_kubernetes_cluster.main.id
  vm_size              = "Standard_D2s_v3"
  node_count           = 1
  enable_auto_scaling  = true
  min_count            = 0  # Scale-to-zero
  max_count            = 10
  
  priority             = "Spot"  # Spot instances
  eviction_policy      = "Delete"
  spot_max_price       = -1  # Pay market price
  
  node_labels = {
    "workload-type" = "workers"
    "agentpool"     = "workers"
  }
  
  node_taints = [
    "kubernetes.azure.com/scalesetpriority=spot:NoSchedule"
  ]
}
```

**ENTREGABLES**:
- ✅ KEDA instalado en AKS
- ✅ transfer-worker service creado
- ✅ ScaledObject configurado
- ✅ Spot nodepool para workers
- ✅ Scale-to-zero functional
- ✅ Procesa transfer.requested, cleanup.requested

**VERIFICACIÓN**:
```bash
# 1. Verificar KEDA instalado
kubectl get pods -n keda

# 2. Sin mensajes en cola
kubectl get scaledobject -n carpeta-ciudadana
# Esperado: READY=True, ACTIVE=False, MIN=0, MAX=10, TRIGGERS=2

kubectl get deployments transfer-worker -n carpeta-ciudadana
# Esperado: READY=0/0 (scale-to-zero)

# 3. Publicar mensaje a cola
az servicebus queue send \
  --namespace ... \
  --name transfer-requested \
  --messages ...

# 4. Verificar scaling automático
kubectl get pods -l app=transfer-worker -n carpeta-ciudadana
# Esperado: 1 pod creado automáticamente

# 5. Esperar procesamiento
# Pod debe procesar y volver a 0 replicas
```

---

### FASE 3: KEY VAULT + CSI SECRET STORE 🔴 CRÍTICO

**Tiempo estimado**: 6 horas

#### 3.1 Crear Key Vault (Terraform)

**Añadir**: `infra/terraform/modules/keyvault/`

```hcl
# main.tf
resource "azurerm_key_vault" "main" {
  name                = "${var.project_name}-${var.environment}-kv"
  location            = var.azure_region
  resource_group_name = var.resource_group_name
  tenant_id           = data.azurerm_client_config.current.tenant_id
  sku_name            = "standard"
  
  enabled_for_disk_encryption = true
  purge_protection_enabled    = true
  
  network_acls {
    bypass         = "AzureServices"
    default_action = "Deny"
    
    # Allow from AKS subnet
    virtual_network_subnet_ids = [var.aks_subnet_id]
  }
}

# Workload Identity for pods
resource "azurerm_user_assigned_identity" "kv_reader" {
  name                = "${var.project_name}-kv-reader"
  location            = var.azure_region
  resource_group_name = var.resource_group_name
}

# Federated credential for K8s ServiceAccount
resource "azurerm_federated_identity_credential" "kv_reader" {
  name                = "kv-reader-fed-cred"
  resource_group_name = var.resource_group_name
  parent_id           = azurerm_user_assigned_identity.kv_reader.id
  audience            = ["api://AzureADTokenExchange"]
  issuer              = azurerm_kubernetes_cluster.main.oidc_issuer_url
  subject             = "system:serviceaccount:carpeta-ciudadana:carpeta-ciudadana-sa"
}

# Access policy
resource "azurerm_key_vault_access_policy" "kv_reader" {
  key_vault_id = azurerm_key_vault.main.id
  tenant_id    = data.azurerm_client_config.current.tenant_id
  object_id    = azurerm_user_assigned_identity.kv_reader.principal_id
  
  secret_permissions = ["Get", "List"]
}

# Secrets
resource "azurerm_key_vault_secret" "postgres_conn" {
  name         = "POSTGRES-CONNECTION-STRING"
  value        = "postgresql://${var.db_username}:${var.db_password}@${azurerm_postgresql_flexible_server.main.fqdn}/carpeta_ciudadana"
  key_vault_id = azurerm_key_vault.main.id
}

resource "azurerm_key_vault_secret" "servicebus_conn" {
  name         = "SERVICEBUS-CONNECTION-STRING"
  value        = azurerm_servicebus_namespace.main.default_primary_connection_string
  key_vault_id = azurerm_key_vault.main.id
}

resource "azurerm_key_vault_secret" "redis_conn" {
  name         = "REDIS-CONNECTION-STRING"
  value        = var.redis_connection_string
  key_vault_id = azurerm_key_vault.main.id
}
```

#### 3.2 Instalar CSI Secret Store Driver (Terraform)

```hcl
# infra/terraform/modules/aks/main.tf
resource "azurerm_kubernetes_cluster" "main" {
  # ... config existente ...
  
  # Habilitar workload identity
  oidc_issuer_enabled       = true
  workload_identity_enabled = true
  
  key_vault_secrets_provider {
    secret_rotation_enabled = true
    secret_rotation_interval = "2m"
  }
}

# Helm release para CSI driver (si no está incluido en AKS)
resource "helm_release" "csi_secrets_store" {
  name       = "csi-secrets-store"
  repository = "https://kubernetes-sigs.github.io/secrets-store-csi-driver/charts"
  chart      = "secrets-store-csi-driver"
  version    = "1.3.4"
  namespace  = "kube-system"
  
  set {
    name  = "syncSecret.enabled"
    value = "true"
  }
}

# Azure provider
resource "helm_release" "csi_secrets_store_azure" {
  name       = "csi-secrets-store-provider-azure"
  repository = "https://azure.github.io/secrets-store-csi-driver-provider-azure/charts"
  chart      = "csi-secrets-store-provider-azure"
  version    = "1.4.1"
  namespace  = "kube-system"
  
  depends_on = [helm_release.csi_secrets_store]
}
```

#### 3.3 SecretProviderClass (Helm)

**Crear**: `deploy/helm/carpeta-ciudadana/templates/secretproviderclass.yaml`

```yaml
apiVersion: secrets-store.csi.x-k8s.io/v1
kind: SecretProviderClass
metadata:
  name: {{ include "carpeta-ciudadana.fullname" . }}-azure-kv
  namespace: {{ .Release.Namespace }}
spec:
  provider: azure
  secretObjects:
  - secretName: kv-secrets
    type: Opaque
    data:
    - objectName: POSTGRES-CONNECTION-STRING
      key: DATABASE_URL
    - objectName: SERVICEBUS-CONNECTION-STRING
      key: SERVICEBUS_CONNECTION_STRING
    - objectName: REDIS-CONNECTION-STRING
      key: REDIS_CONNECTION_STRING
  parameters:
    usePodIdentity: "false"
    useVMManagedIdentity: "false"
    clientID: {{ .Values.keyVault.workloadIdentityClientId }}
    keyvaultName: {{ .Values.keyVault.name }}
    cloudName: ""
    tenantId: {{ .Values.keyVault.tenantId }}
    objects: |
      array:
        - |
          objectName: POSTGRES-CONNECTION-STRING
          objectType: secret
        - |
          objectName: SERVICEBUS-CONNECTION-STRING
          objectType: secret
        - |
          objectName: REDIS-CONNECTION-STRING
          objectType: secret
        - |
          objectName: ACS-CONNECTION-STRING
          objectType: secret
        - |
          objectName: HMAC-JWS-KEY
          objectType: secret
```

#### 3.4 Actualizar ServiceAccount

**Modificar**: `deploy/helm/carpeta-ciudadana/templates/serviceaccount.yaml`

```yaml
{{- if .Values.serviceAccount.create -}}
apiVersion: v1
kind: ServiceAccount
metadata:
  name: {{ include "carpeta-ciudadana.serviceAccountName" . }}
  namespace: {{ .Release.Namespace }}
  annotations:
    azure.workload.identity/client-id: {{ .Values.keyVault.workloadIdentityClientId }}  # ← AÑADIR
  labels:
    {{- include "carpeta-ciudadana.labels" . | nindent 4 }}
    azure.workload.identity/use: "true"  # ← AÑADIR
{{- end }}
```

#### 3.5 Montar Secrets en Deployments

**Modificar**: Todos los `deployment-*.yaml`

```yaml
spec:
  template:
    metadata:
      labels:
        azure.workload.identity/use: "true"  # ← AÑADIR
    spec:
      serviceAccountName: {{ include "carpeta-ciudadana.serviceAccountName" . }}
      
      volumes:  # ← AÑADIR
      - name: secrets-store
        csi:
          driver: secrets-store.csi.k8s.io
          readOnly: true
          volumeAttributes:
            secretProviderClass: {{ include "carpeta-ciudadana.fullname" . }}-azure-kv
      
      containers:
      - name: gateway
        # ... config existente ...
        
        volumeMounts:  # ← AÑADIR
        - name: secrets-store
          mountPath: "/mnt/secrets-store"
          readOnly: true
        
        envFrom:
        - secretRef:
            name: kv-secrets  # Secrets sinced desde CSI
```

**ENTREGABLES**:
- ✅ Key Vault creado
- ✅ Workload Identity configurado
- ✅ CSI Secret Store instalado
- ✅ SecretProviderClass creado
- ✅ Secrets montados en pods

**VERIFICACIÓN**:
```bash
# 1. Verificar Key Vault
az keyvault show --name carpeta-ciudadana-dev-kv

# 2. Verificar CSI driver
kubectl get pods -n kube-system | grep csi-secrets

# 3. Verificar SecretProviderClass
kubectl get secretproviderclass -n carpeta-ciudadana

# 4. Deploy pod y verificar montaje
kubectl exec -it <pod> -n carpeta-ciudadana -- ls /mnt/secrets-store
# Esperado: POSTGRES-CONNECTION-STRING, SERVICEBUS-CONNECTION-STRING, ...

# 5. Verificar secret creado por CSI
kubectl get secret kv-secrets -n carpeta-ciudadana
# Esperado: Opaque con keys DATABASE_URL, SERVICEBUS_CONNECTION_STRING
```

---

### FASE 4: HEADERS M2M COMPLETOS (Transferencias) 🔴 CRÍTICO

**Tiempo estimado**: 4 horas

#### 4.1 Generar Nonce y Timestamp

**Modificar**: `services/transfer/app/routers/transfer_initiate.py` (origen)

```python
import secrets
from datetime import datetime

@router.post("/initiate-transfer")
async def initiate_transfer(...):
    # Generate nonce (replay protection)
    nonce = secrets.token_urlsafe(32)
    timestamp = datetime.utcnow().isoformat()
    
    # Generate HMAC signature
    hmac_key = os.getenv("HMAC_JWS_KEY")  # From Key Vault
    payload = f"{citizen_id}|{nonce}|{timestamp}|{json.dumps(url_documents)}"
    signature = hmac.new(
        hmac_key.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    
    # Headers
    headers = {
        "Authorization": f"Bearer {m2m_jwt_token}",
        "Idempotency-Key": str(uuid4()),
        "X-Trace-Id": trace_id,
        "X-Nonce": nonce,
        "X-Timestamp": timestamp,
        "X-Signature": signature,
    }
    
    # Call destination operator
    response = await httpx.post(
        f"{destination_url}/api/transferCitizen",
        json={...},
        headers=headers
    )
```

#### 4.2 Validar Headers (destino)

**Modificar**: `services/transfer/app/routers/transfer.py`

```python
from fastapi import Header
from datetime import datetime, timedelta
import hmac
import hashlib

@router.post("/transferCitizen")
async def transfer_citizen(
    request: TransferCitizenRequest,
    authorization: str = Header(...),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    trace_id: str = Header(..., alias="X-Trace-Id"),
    nonce: str = Header(..., alias="X-Nonce"),
    timestamp: str = Header(..., alias="X-Timestamp"),
    signature: str = Header(..., alias="X-Signature"),
):
    # 1. Verify JWT
    token = await verify_b2b_token(authorization)
    
    # 2. Verify timestamp (max 5 min old)
    request_time = datetime.fromisoformat(timestamp)
    if datetime.utcnow() - request_time > timedelta(minutes=5):
        raise HTTPException(401, "Request expired (timestamp too old)")
    
    # 3. Verify nonce is unique (Redis)
    nonce_key = f"nonce:{nonce}"
    if await redis.exists(nonce_key):
        raise HTTPException(401, "Nonce already used (replay attack)")
    await redis.setex(nonce_key, 600, "1")  # Store for 10 min
    
    # 4. Verify HMAC signature
    hmac_key = os.getenv("HMAC_JWS_KEY")
    payload = f"{request.id}|{nonce}|{timestamp}|{json.dumps(request.urlDocuments)}"
    expected_sig = hmac.new(
        hmac_key.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    
    if signature != expected_sig:
        raise HTTPException(401, "Invalid signature")
    
    # 5. Proceed with transfer
    # ...
```

#### 4.3 mTLS (opcional, production)

**Configurar**: NGINX Ingress con mutual TLS

```yaml
# deploy/helm/carpeta-ciudadana/templates/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: {{ include "carpeta-ciudadana.fullname" . }}-transfer
  annotations:
    nginx.ingress.kubernetes.io/auth-tls-verify-client: "on"
    nginx.ingress.kubernetes.io/auth-tls-secret: "carpeta-ciudadana/client-ca-cert"
    nginx.ingress.kubernetes.io/auth-tls-verify-depth: "1"
spec:
  rules:
  - host: transfer.carpeta-ciudadana.example.com
    http:
      paths:
      - path: /api/transferCitizen
        backend:
          service:
            name: carpeta-ciudadana-transfer
            port:
              number: 8000
```

**ENTREGABLES**:
- ✅ X-Nonce validation
- ✅ X-Timestamp validation (5 min window)
- ✅ X-Signature HMAC verification
- ✅ Replay protection con Redis
- ✅ mTLS configurado (opcional)

---

### FASE 4: NETWORKPOLICIES 🔴 CRÍTICO

**Tiempo estimado**: 3 horas

**Crear**: `deploy/helm/carpeta-ciudadana/templates/networkpolicy-*.yaml`

Crear una NetworkPolicy por cada servicio:

```yaml
# networkpolicy-gateway.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: {{ include "carpeta-ciudadana.fullname" . }}-gateway
spec:
  podSelector:
    matchLabels:
      app: gateway
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx  # Solo desde ingress
    ports:
    - protocol: TCP
      port: 8000
  egress:
  # Allow to internal services
  - to:
    - podSelector:
        matchLabels:
          app: citizen
    ports:
    - protocol: TCP
      port: 8000
  - to:
    - podSelector:
        matchLabels:
          app: ingestion
    ports:
    - protocol: TCP
      port: 8000
  - to:
    - podSelector:
        matchLabels:
          app: metadata
    ports:
    - protocol: TCP
      port: 8000
  # ... otros servicios
  
  # Allow to PostgreSQL
  - to:
    - namespaceSelector: {}
      podSelector: {}
    ports:
    - protocol: TCP
      port: 5432
  
  # Allow to Redis
  - to:
    ports:
    - protocol: TCP
      port: 6379
  
  # Allow to external (hub MinTIC)
  - to:
    - namespaceSelector: {}
      podSelector: {}
    ports:
    - protocol: TCP
      port: 443
  
  # Allow DNS
  - to:
    - namespaceSelector:
        matchLabels:
          name: kube-system
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
```

Repetir para cada servicio con reglas específicas.

---

### FASE 5: POD DISRUPTION BUDGETS 🟠 ALTA

**Tiempo estimado**: 2 horas

**Crear**: `deploy/helm/carpeta-ciudadana/templates/pdb-*.yaml`

```yaml
# pdb-gateway.yaml
{{- if .Values.gateway.enabled }}
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: {{ include "carpeta-ciudadana.fullname" . }}-gateway
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: gateway
{{- end }}

# pdb-citizen.yaml
{{- if .Values.citizen.enabled }}
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: {{ include "carpeta-ciudadana.fullname" . }}-citizen
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app: citizen
{{- end }}
```

Crear PDB para cada servicio crítico.

---

### FASE 6: CORREGIR ORDEN DE TRANSFERENCIA 🔴 DECISIÓN REQUERIDA

**Tiempo estimado**: 4 horas (+ decisión arquitectónica)

#### CONFLICTO:

**REQUERIMIENTO**:
```
1. unregister en hub
2. POST transferCitizen
3. Esperar confirm
4. Cleanup SOLO si success
```

**IMPLEMENTACIÓN ACTUAL**:
```
1. POST transferCitizen
2. Esperar confirm
3. Delete local
4. unregister hub
```

#### OPCIONES:

**Opción A**: Seguir REQUERIMIENTO (más riesgoso)

```python
# services/transfer/app/routers/transfer_initiate.py

@router.post("/initiate-transfer")
async def initiate_transfer(...):
    # 1. unregister en hub PRIMERO
    logger.info(f"Step 1: Unregistering citizen {citizen_id} from hub")
    unregister_result = await mintic_client.unregister_citizen({
        "id": citizen_id,
        "operatorId": operator_id,
        "operatorName": operator_name
    })
    
    if not unregister_result.ok:
        raise HTTPException(500, f"Failed to unregister from hub: {unregister_result.message}")
    
    # 2. POST transferCitizen a destino
    logger.info(f"Step 2: Transferring to destination {destination_url}")
    response = await httpx.post(
        f"{destination_url}/api/transferCitizen",
        json={...},
        headers={...}
    )
    
    # 3. Esperar confirmación (async, via callback)
    # ... almacenar transfer con status=PENDING
    
    # 4. En confirmación (POST /transferCitizenConfirm):
    if req_status == 1:
        # SUCCESS - cleanup
        await delete_citizen_data(citizen_id)
        await delete_documents(citizen_id)
    else:
        # FAILED - ¿qué hacer?
        # Ciudadano ya está unregistered del hub
        # Datos aún están en origen
        # ⚠️ PROBLEMA: Inconsistencia
        logger.error(f"Transfer failed but citizen already unregistered from hub!")
```

**RIESGO**: Si destino falla, ciudadano está unregistered pero datos aún en origen → **INCONSISTENCIA**

**Opción B**: Mantener IMPLEMENTACIÓN ACTUAL (más segura) + JUSTIFICAR

```markdown
# DESVIACIÓN JUSTIFICADA

**Requerimiento**: unregister → transfer → confirm → cleanup
**Implementado**: transfer → confirm → cleanup → unregister

**Justificación**:
El orden implementado EVITA PÉRDIDA DE DATOS:
- Si destino falla ANTES de confirmación → Datos permanecen en origen
- Ciudadano permanece registrado en hub
- Puede reintentar transferencia

El orden requerido PUEDE CAUSAR PÉRDIDA DE DATOS:
- Si unregister OK pero destino falla → Ciudadano pierde acceso
- Datos quedan huérfanos en origen
- Hub no sabe dónde está el ciudadano

**Decisión**: Mantener orden actual por seguridad de datos
**Estado**: DESVIACIÓN DOCUMENTADA - Requiere aprobación stakeholder
```

**Opción C**: Implementar SAGA completo con compensación

```python
# Implementar compensación si falla:
try:
    # 1. unregister hub
    unregister_result = await unregister_from_hub()
    
    # 2. transfer a destino
    transfer_result = await transfer_to_destination()
    
    # 3. Si falla, COMPENSATE (re-register en hub)
    if not transfer_result.ok:
        await compensate_reregister_in_hub()
        raise
    
except Exception as e:
    # Rollback completo
    logger.error(f"Transfer failed, compensating...")
```

**ACCIÓN REQUERIDA**: **DECISIÓN del usuario**

1. ¿Seguir requerimiento al pie de la letra? → Opción A (riesgoso)
2. ¿Mantener implementación actual? → Opción B (documentar desviación)
3. ¿Implementar SAGA con compensación? → Opción C (complejo)

---

### FASE 7: SISTEMA DE USUARIOS 🟠 ALTA

**Tiempo estimado**: 6 horas

#### 7.1 Crear Tablas

**Migración**: `services/citizen/alembic/versions/XXX_create_users_system.py`

```python
def upgrade():
    # users table
    op.create_table('users',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('sub', sa.String(), unique=True, nullable=False, index=True),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('name', sa.String()),
        sa.Column('phone', sa.String()),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), onupdate=sa.func.now()),
    )
    
    # user_roles table
    op.create_table('user_roles',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE')),
        sa.Column('role', sa.String(), nullable=False),
        sa.Column('granted_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('granted_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Index('idx_user_roles', 'user_id', 'role'),
    )
    
    # citizen_links table
    op.create_table('citizen_links',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_sub', sa.String(), sa.ForeignKey('users.sub', ondelete='CASCADE')),
        sa.Column('citizen_id', sa.BigInteger(), sa.ForeignKey('citizens.id', ondelete='CASCADE')),
        sa.Column('linked_at', sa.DateTime(), server_default=sa.func.now()),
        sa.UniqueConstraint('user_sub', 'citizen_id', name='uq_user_citizen'),
        sa.Index('idx_user_sub', 'user_sub'),
        sa.Index('idx_citizen_id', 'citizen_id'),
    )
```

#### 7.2 Crear Models

**Añadir**: `services/citizen/app/models.py`

```python
class User(Base):
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sub: Mapped[str] = mapped_column(String, unique=True, index=True)
    email: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str | None] = mapped_column(String)
    phone: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    
    # Relationships
    roles = relationship("UserRole", back_populates="user")
    citizen_links = relationship("CitizenLink", back_populates="user")


class UserRole(Base):
    __tablename__ = "user_roles"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    role: Mapped[str] = mapped_column(String)  # citizen, operator_admin, admin
    granted_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    
    user = relationship("User", back_populates="roles")


class CitizenLink(Base):
    __tablename__ = "citizen_links"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_sub: Mapped[str] = mapped_column(ForeignKey("users.sub"))
    citizen_id: Mapped[int] = mapped_column(ForeignKey("citizens.id"))
    linked_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    
    user = relationship("User")
    citizen = relationship("Citizen")
```

#### 7.3 Endpoint Bootstrap

Ver FASE 2.6 (ya incluido)

**ENTREGABLES**:
- ✅ Tablas users, user_roles, citizen_links
- ✅ Models SQLAlchemy
- ✅ Endpoint /api/users/bootstrap
- ✅ Validación con hub (validateCitizen)

---

### FASE 8: ACCESIBILIDAD WCAG 2.2 AA 🟡 MEDIA

**Tiempo estimado**: 12 horas

#### 8.1 Instalar herramientas

```bash
cd apps/frontend
npm install --save-dev @axe-core/react jest-axe
npm install @radix-ui/react-accessible-icon
npm install @radix-ui/react-visually-hidden
```

#### 8.2 Añadir axe en tests

**Crear**: `apps/frontend/src/__tests__/accessibility.test.tsx`

```typescript
import { axe, toHaveNoViolations } from 'jest-axe';
expect.extend(toHaveNoViolations);

describe('Accessibility', () => {
  it('should not have accessibility violations on dashboard', async () => {
    const { container } = render(<DashboardPage />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
```

#### 8.3 Skip to Content

**Añadir**: `apps/frontend/src/app/layout.tsx`

```typescript
export default function RootLayout({ children }) {
  return (
    <html lang="es">
      <body>
        <a href="#main-content" className="skip-link">
          Saltar al contenido principal
        </a>
        
        <Header />
        
        <main id="main-content" tabIndex={-1}>
          {children}
        </main>
      </body>
    </html>
  );
}
```

**CSS**: `apps/frontend/src/app/globals.css`

```css
.skip-link {
  position: absolute;
  top: -40px;
  left: 0;
  background: #000;
  color: #fff;
  padding: 8px;
  z-index: 100;
}

.skip-link:focus {
  top: 0;
}
```

#### 8.4 ARIA Labels

Revisar todos los formularios:

```typescript
// Antes (sin label):
<input type="text" placeholder="Cédula" />

// Después (con ARIA):
<input 
  type="text" 
  placeholder="Cédula"
  aria-label="Número de cédula"
  aria-required="true"
  aria-describedby="cedula-help"
/>
<span id="cedula-help" className="sr-only">
  Ingrese su número de cédula de 10 dígitos
</span>
```

#### 8.5 Focus Management

```typescript
// En modal/drawer:
import { useRef, useEffect } from 'react';

function Modal({ isOpen, onClose }) {
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  
  useEffect(() => {
    if (isOpen) {
      closeButtonRef.current?.focus();
    }
  }, [isOpen]);
  
  return (
    <dialog open={isOpen} aria-modal="true" aria-labelledby="modal-title">
      <h2 id="modal-title">Título del Modal</h2>
      <button ref={closeButtonRef} onClick={onClose}>
        Cerrar
      </button>
    </dialog>
  );
}
```

#### 8.6 Contrast Checker

```bash
# Verificar contraste de colores
npm install --save-dev eslint-plugin-jsx-a11y

# Ejecutar
npm run lint
```

#### 8.7 Tablas Responsive (cards en móvil)

```typescript
// apps/frontend/src/app/documents/DocumentsTable.tsx
export function DocumentsTable({ documents }) {
  return (
    <>
      {/* Desktop: tabla */}
      <table className="hidden md:table">
        <thead>...</thead>
        <tbody>
          {documents.map(doc => (
            <tr key={doc.id}>...</tr>
          ))}
        </tbody>
      </table>
      
      {/* Mobile: cards */}
      <div className="md:hidden space-y-4">
        {documents.map(doc => (
          <div key={doc.id} className="card p-4 border rounded">
            <h3 className="font-bold">{doc.filename}</h3>
            <p><span className="text-gray-600">Estado:</span> {doc.state}</p>
            <p><span className="text-gray-600">Tamaño:</span> {formatBytes(doc.size)}</p>
            <p><span className="text-gray-600">Fecha:</span> {formatDate(doc.created_at)}</p>
            <button className="btn-primary mt-2 w-full">Ver Detalles</button>
          </div>
        ))}
      </div>
    </>
  );
}
```

#### 8.8 prefers-reduced-motion

```css
/* apps/frontend/src/app/globals.css */
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
```

#### 8.9 CI - axe Audit

**Añadir**: `.github/workflows/ci.yml`

```yaml
frontend-test:
  steps:
    # ... steps existentes ...
    
    - name: Run accessibility audit
      run: |
        cd apps/frontend
        npm run test:a11y
    
    - name: Upload axe results
      if: always()
      uses: actions/upload-artifact@v3
      with:
        name: axe-results
        path: apps/frontend/axe-results/
```

**Añadir**: `apps/frontend/package.json`

```json
{
  "scripts": {
    "test:a11y": "jest --testMatch='**/*.a11y.test.tsx'",
  }
}
```

**ENTREGABLES**:
- ✅ Skip to content
- ✅ ARIA labels completos
- ✅ Focus management
- ✅ Contrast validation
- ✅ Tablas responsive
- ✅ prefers-reduced-motion
- ✅ axe en CI

---

### FASE 9: VISTAS FRONTEND FALTANTES 🟠 ALTA

**Tiempo estimado**: 16 horas

#### Vistas a crear:

1. **Centro de Notificaciones** (4h)
   ```typescript
   // apps/frontend/src/app/notifications/page.tsx
   - Lista de notificaciones
   - Marcar como leído
   - Filtros (todas, leídas, no leídas)
   ```

2. **Preferencias de Notificación** (3h)
   ```typescript
   // apps/frontend/src/app/notifications/preferences/page.tsx
   - Toggle Email/SMS por tipo de evento
   - Guardar en /api/notifications/preferences
   ```

3. **Visor PDF inline** (4h)
   ```typescript
   // apps/frontend/src/components/PDFViewer.tsx
   - React-PDF o PDF.js
   - Navegación de páginas
   - Zoom
   - Descarga
   ```

4. **Timeline en Dashboard** (3h)
   ```typescript
   // apps/frontend/src/app/dashboard/Timeline.tsx
   - Eventos recientes (registro, uploads, firmas, transfers)
   - Con iconos y timestamps
   ```

5. **Asistente de Transferencia** (2h)
   ```typescript
   // apps/frontend/src/app/transfer/TransferWizard.tsx
   - Paso 1: Selección operador destino
   - Paso 2: Revisión de documentos
   - Paso 3: Confirmación
   - Paso 4: Tracking con estados
   ```

---

### FASE 10: AUDIT EVENTS 🟡 MEDIA

**Tiempo estimado**: 4 horas

#### 10.1 Crear Tabla

**Migración**: `services/citizen/alembic/versions/XXX_create_audit_events.py`

```python
def upgrade():
    op.create_table('audit_events',
        sa.Column('id', sa.BigInteger(), primary_key=True),
        sa.Column('timestamp', sa.DateTime(), server_default=sa.func.now(), index=True),
        sa.Column('user_sub', sa.String(), index=True),
        sa.Column('citizen_id', sa.BigInteger(), index=True),
        sa.Column('event_type', sa.String(), nullable=False, index=True),
        sa.Column('resource_type', sa.String()),
        sa.Column('resource_id', sa.String()),
        sa.Column('action', sa.String()),  # CREATE, READ, UPDATE, DELETE
        sa.Column('ip_address', sa.String()),
        sa.Column('user_agent', sa.String()),
        sa.Column('trace_id', sa.String(), index=True),
        sa.Column('status', sa.String()),  # SUCCESS, FAILED
        sa.Column('metadata', sa.JSON()),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )
    
    # Partition by date (optional, para volumen alto)
    # op.execute("SELECT create_hypertable('audit_events', 'timestamp');")  # TimescaleDB
```

#### 10.2 Middleware de Auditoría

**Crear**: `services/common/carpeta_common/audit.py`

```python
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

async def log_audit_event(
    db: AsyncSession,
    request: Request,
    user_sub: str | None,
    event_type: str,
    resource_type: str | None = None,
    resource_id: str | None = None,
    action: str | None = None,
    status: str = "SUCCESS",
    metadata: dict | None = None,
):
    """Log audit event."""
    event = AuditEvent(
        user_sub=user_sub,
        event_type=event_type,
        resource_type=resource_type,
        resource_id=resource_id,
        action=action,
        ip_address=request.client.host,
        user_agent=request.headers.get("User-Agent"),
        trace_id=request.headers.get("traceparent"),
        status=status,
        metadata=metadata
    )
    db.add(event)
    await db.commit()
```

#### 10.3 Usar en Endpoints Críticos

```python
# En signature service
@router.post("/sign")
async def sign_document(...):
    try:
        # ... lógica de firma ...
        
        await log_audit_event(
            db=db,
            request=request,
            user_sub=current_user.sub,
            event_type="document.signed",
            resource_type="document",
            resource_id=document_id,
            action="SIGN",
            status="SUCCESS",
            metadata={"hub_ref": hub_signature_ref}
        )
    except Exception as e:
        await log_audit_event(
            db=db,
            request=request,
            user_sub=current_user.sub,
            event_type="document.signed",
            resource_type="document",
            resource_id=document_id,
            action="SIGN",
            status="FAILED",
            metadata={"error": str(e)}
        )
        raise
```

---

### FASE 11: OUTBOX PATTERN (Notificaciones) 🟠 ALTA

**Tiempo estimado**: 5 horas

#### 11.1 Crear Tabla

```sql
CREATE TABLE notification_outbox (
    id BIGSERIAL PRIMARY KEY,
    event_id UUID UNIQUE NOT NULL,
    event_type VARCHAR NOT NULL,
    aggreggate_id VARCHAR NOT NULL,  -- citizen_id, document_id, etc
    payload JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    processed_at TIMESTAMP,
    status VARCHAR DEFAULT 'PENDING',  -- PENDING, SENT, FAILED
    retry_count INTEGER DEFAULT 0,
    last_error TEXT
);

CREATE INDEX idx_outbox_status ON notification_outbox(status, created_at);
```

#### 11.2 Insertar en Transacción

```python
# En signature service, MISMA transacción:
async with db.begin():
    # 1. Actualizar documento
    await db.execute(update(DocumentMetadata).where(...).values(...))
    
    # 2. Insertar en outbox (transaccional)
    outbox_event = NotificationOutbox(
        event_id=uuid4(),
        event_type="document.signed",
        aggregate_id=document_id,
        payload={
            "citizen_id": citizen_id,
            "document_id": document_id,
            "signed_at": datetime.utcnow().isoformat()
        },
        status="PENDING"
    )
    db.add(outbox_event)
    
    await db.commit()  # Atómico
```

#### 11.3 Outbox Processor

```python
# services/notification/app/outbox_processor.py

async def process_outbox():
    """Background task que procesa outbox."""
    while True:
        async with SessionLocal() as db:
            # Fetch pending
            stmt = select(NotificationOutbox).where(
                NotificationOutbox.status == "PENDING",
                NotificationOutbox.retry_count < 3
            ).limit(100)
            
            result = await db.execute(stmt)
            events = result.scalars().all()
            
            for event in events:
                try:
                    # Enviar notificación
                    await send_notification(event.payload)
                    
                    # Marcar como enviado
                    event.status = "SENT"
                    event.processed_at = datetime.utcnow()
                    
                except Exception as e:
                    event.retry_count += 1
                    event.last_error = str(e)
                    
                    if event.retry_count >= 3:
                        event.status = "FAILED"
                
                await db.commit()
        
        await asyncio.sleep(5)  # Poll cada 5s
```

---

### FASE 12: AZURE COMMUNICATION SERVICES 🟡 MEDIA

**Tiempo estimado**: 6 horas

#### 12.1 Crear ACS Resource (Terraform)

```hcl
# infra/terraform/modules/communication/main.tf
resource "azurerm_communication_service" "main" {
  name                = "${var.project_name}-${var.environment}-acs"
  resource_group_name = var.resource_group_name
  data_location       = "UnitedStates"
}

resource "azurerm_email_communication_service" "main" {
  name                = "${var.project_name}-${var.environment}-email"
  resource_group_name = var.resource_group_name
  data_location       = "UnitedStates"
}

output "acs_connection_string" {
  value     = azurerm_communication_service.main.primary_connection_string
  sensitive = true
}
```

#### 12.2 Actualizar Notification Service

**Modificar**: `services/notification/app/services/notifier.py`

```python
from azure.communication.email import EmailClient

class ACSEmailService:
    """Azure Communication Services Email."""
    
    def __init__(self, connection_string: str, from_email: str):
        self.client = EmailClient.from_connection_string(connection_string)
        self.from_email = from_email
    
    async def send_email(self, to: str, subject: str, html: str):
        """Send email via ACS."""
        message = {
            "senderAddress": self.from_email,
            "recipients": {
                "to": [{"address": to}]
            },
            "content": {
                "subject": subject,
                "html": html
            }
        }
        
        poller = self.client.begin_send(message)
        result = poller.result()
        
        return result.status == "Succeeded"
```

---

### FASE 13: RLS (ROW LEVEL SECURITY) 🟡 MEDIA

**Tiempo estimado**: 6 horas

#### 13.1 Habilitar RLS

```sql
-- Enable RLS en tablas críticas
ALTER TABLE citizens ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_metadata ENABLE ROW LEVEL SECURITY;
ALTER TABLE transfers ENABLE ROW LEVEL SECURITY;

-- Policy: Users solo ven sus propios datos
CREATE POLICY citizen_isolation_policy ON citizens
    FOR ALL
    TO PUBLIC
    USING (
        -- Solo si el user está vinculado a ese citizen
        id IN (
            SELECT citizen_id 
            FROM citizen_links 
            WHERE user_sub = current_setting('app.current_user_sub')::text
        )
        OR
        -- O si el user es operator_admin
        current_setting('app.current_user_role')::text = 'operator_admin'
    );

-- Policy: Documents solo del citizen
CREATE POLICY document_isolation_policy ON document_metadata
    FOR ALL
    TO PUBLIC
    USING (
        citizen_id IN (
            SELECT citizen_id 
            FROM citizen_links 
            WHERE user_sub = current_setting('app.current_user_sub')::text
        )
        OR
        current_setting('app.current_user_role')::text IN ('operator_admin', 'admin')
    );
```

#### 13.2 Set Session Variables

```python
# En cada request, después de autenticar:
await db.execute(
    text("SET LOCAL app.current_user_sub = :sub"),
    {"sub": current_user.sub}
)
await db.execute(
    text("SET LOCAL app.current_user_role = :role"),
    {"role": current_user.role}
)

# Ahora RLS se aplica automáticamente
citizens = await db.execute(select(Citizen))  # Solo ve los que puede
```

---

## 📈 RESUMEN DE FASES

| Fase | Nombre | Prioridad | Tiempo | Acumulado |
|------|--------|-----------|--------|-----------|
| 1 | WORM + Retención | 🔴 Crítico | 8h | 8h |
| 2 | Azure AD B2C | 🔴 Crítico | 12h | 20h |
| 3 | transfer-worker + KEDA | 🔴 Crítico | 10h | 30h |
| 4 | Key Vault + CSI | 🔴 Crítico | 6h | 36h |
| 5 | NetworkPolicies | 🔴 Crítico | 3h | 39h |
| 6 | PodDisruptionBudgets | 🟠 Alta | 2h | 41h |
| 7 | Orden Transferencia | 🔴 Decisión | 4h | 45h |
| 8 | Sistema Usuarios | 🟠 Alta | 6h | 51h |
| 9 | Headers M2M | 🔴 Crítico | 4h | 55h |
| 10 | Accesibilidad WCAG | 🟡 Media | 12h | 67h |
| 11 | Vistas Frontend | 🟠 Alta | 16h | 83h |
| 12 | Audit Events | 🟡 Media | 4h | 87h |
| 13 | Outbox Pattern | 🟠 Alta | 5h | 92h |
| 14 | Azure Comm Services | 🟡 Media | 6h | 98h |
| 15 | RLS PostgreSQL | 🟡 Media | 6h | 104h |

**Fases adicionales** (16-24): Ver documento extendido

**TIEMPO TOTAL ESTIMADO**: **~150 horas** (3-4 semanas a tiempo completo)

---

## 🎯 RECOMENDACIÓN FINAL

### ESTRATEGIA SUGERIDA:

#### Enfoque 1: CUMPLIMIENTO ESTRICTO (producción real)
- Implementar TODAS las fases
- Tiempo: 150 horas
- Resultado: Sistema production-ready completo

#### Enfoque 2: MVP MEJORADO (proyecto académico)
- Implementar solo fases CRÍTICAS (1-9)
- Tiempo: 55 horas
- Resultado: Core funcional, features avanzadas documentadas

#### Enfoque 3: DEMO FUNCIONAL (presentación)
- Completar servicios básicos (auth, notification, read_models)
- Añadir WORM (Fase 1)
- Añadir AD B2C mock mejorado (2-3h)
- Total: 15-20 horas
- Resultado: Demo end-to-end funcional

---

## 📞 PRÓXIMOS PASOS

1. **LEER**:
   - `CUMPLIMIENTO_REQUERIMIENTOS.md` (análisis detallado)
   - Este documento (plan de acción)

2. **DECIDIR** enfoque:
   - ¿Cumplimiento estricto?
   - ¿MVP mejorado?
   - ¿Demo funcional?

3. **DECIDIR** sobre orden de transferencia:
   - ¿Seguir requerimiento? (Opción A)
   - ¿Mantener actual? (Opción B)
   - ¿SAGA completo? (Opción C)

4. **EJECUTAR**:
   - Comenzar por Fase 1 (WORM) - crítico y standalone
   - Continuar según prioridades

---

**Generado**: 12 de Octubre 2025  
**Basado en**: Requerimientos_Proyecto_GovCarpeta.md  
**Versión**: 1.0.0

