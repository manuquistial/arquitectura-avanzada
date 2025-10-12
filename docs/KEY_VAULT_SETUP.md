# 🔐 Azure Key Vault + CSI Secret Store Driver Setup

**Fecha**: 2025-10-13  
**Versión**: 1.0  
**Autor**: Manuel Jurado

Guía completa para configurar Azure Key Vault con Secrets Store CSI Driver para gestión segura de secretos.

---

## 📋 Índice

1. [Descripción General](#descripción-general)
2. [Arquitectura](#arquitectura)
3. [Instalación Terraform](#instalación-terraform)
4. [Configuración Helm](#configuración-helm)
5. [Uso en Deployments](#uso-en-deployments)
6. [Secret Rotation](#secret-rotation)
7. [Migración desde K8s Secrets](#migración-desde-k8s-secrets)
8. [Testing](#testing)
9. [Troubleshooting](#troubleshooting)

---

## 🎯 Descripción General

Azure Key Vault + CSI Secret Store Driver permite:

✅ **Centralizar secrets**: Todos en Key Vault, no en K8s  
✅ **Auto-rotation**: Secrets se actualizan automáticamente  
✅ **Workload Identity**: Sin passwords, usa Azure AD  
✅ **Auditoría**: Todos los accesos logueados  
✅ **RBAC**: Control granular de acceso  
✅ **Soft delete**: Protección contra eliminación accidental  

---

## 🏗️ Arquitectura

```
┌─────────────────────────────────────────────────┐
│  Azure Key Vault                                │
│  ├── postgres-host                              │
│  ├── postgres-password                          │
│  ├── servicebus-connection-string               │
│  ├── m2m-secret-key                             │
│  └── ... (10+ secrets)                          │
└────────────────┬────────────────────────────────┘
                 │
                 │ RBAC: Key Vault Secrets User
                 ▼
┌─────────────────────────────────────────────────┐
│  AKS Managed Identity (Workload Identity)      │
│  Client ID: xxxxxxxxx-xxxx-xxxx                 │
└────────────────┬────────────────────────────────┘
                 │
                 │ Federated credential
                 ▼
┌─────────────────────────────────────────────────┐
│  ServiceAccount: carpeta-ciudadana-sa           │
│  Annotations:                                   │
│    azure.workload.identity/client-id            │
└────────────────┬────────────────────────────────┘
                 │
                 │ Pod uses
                 ▼
┌─────────────────────────────────────────────────┐
│  Pod (e.g., gateway)                            │
│  ├── Volume: CSI Driver                         │
│  │   └── SecretProviderClass                    │
│  └── VolumeMount: /mnt/secrets-store            │
│      ├── POSTGRES_PASSWORD                      │
│      ├── M2M_SECRET_KEY                         │
│      └── ... (as files)                         │
└─────────────────────────────────────────────────┘
```

---

## 🔧 Instalación Terraform

### Paso 1: Configurar Variables

Editar `terraform.tfvars`:

```hcl
# Key Vault
keyvault_sku = "standard"
keyvault_enable_public_access = true  # false for production
keyvault_purge_protection = false  # true for production
keyvault_soft_delete_days = 7

# M2M Secret (generate with: openssl rand -hex 32)
m2m_secret_key = "your-m2m-secret-key-here"

# Azure AD B2C (if configured)
azure_b2c_tenant_id = "your-tenant-id"
azure_b2c_client_id = "your-client-id"
azure_b2c_client_secret = "your-client-secret"

# CSI Driver
csi_enable_rotation = true
csi_rotation_interval = "2m"
```

### Paso 2: Apply Terraform

```bash
cd infra/terraform

# Initialize
terraform init

# Plan
terraform plan

# Apply
terraform apply

# Get outputs
terraform output key_vault_name
terraform output key_vault_uri
```

### Paso 3: Verificar Key Vault

```bash
# List secrets
az keyvault secret list \
  --vault-name carpeta-ciudadana-dev-kv \
  --query "[].name"

# Get secret value
az keyvault secret show \
  --vault-name carpeta-ciudadana-dev-kv \
  --name postgres-password \
  --query "value" -o tsv
```

---

## ⚙️ Configuración Helm

### Paso 1: Obtener Workload Identity Client ID

```bash
# From Terraform output
CLIENT_ID=$(terraform output -raw aks_identity_client_id)
TENANT_ID=$(terraform output -raw tenant_id)
KV_NAME=$(terraform output -raw key_vault_name)

echo "Client ID: $CLIENT_ID"
echo "Tenant ID: $TENANT_ID"
echo "Key Vault: $KV_NAME"
```

### Paso 2: Actualizar values.yaml

```yaml
global:
  useWorkloadIdentity: true
  
  workloadIdentity:
    enabled: true
    clientId: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
    tenantId: "yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy"
  
  keyVault:
    enabled: true
    name: "carpeta-ciudadana-dev-kv"
    tenantId: "yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy"
    clientId: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
    syncToK8sSecrets: true
```

### Paso 3: Deploy con Helm

```bash
helm upgrade --install carpeta-ciudadana deploy/helm/carpeta-ciudadana \
  --namespace carpeta-ciudadana-dev \
  --create-namespace \
  --set global.keyVault.enabled=true \
  --set global.keyVault.name=$KV_NAME \
  --set global.workloadIdentity.clientId=$CLIENT_ID \
  --set global.workloadIdentity.tenantId=$TENANT_ID \
  --wait \
  --timeout 10m
```

---

## 📦 Uso en Deployments

### Opción 1: Mount como archivos (Recomendado)

```yaml
spec:
  containers:
  - name: myapp
    volumeMounts:
    - name: secrets-store
      mountPath: "/mnt/secrets-store"
      readOnly: true
    
    env:
    # Read secret from mounted file
    - name: POSTGRES_PASSWORD
      value: "/mnt/secrets-store/POSTGRES_PASSWORD"
  
  volumes:
  - name: secrets-store
    csi:
      driver: secrets-store.csi.k8s.io
      readOnly: true
      volumeAttributes:
        secretProviderClass: "carpeta-ciudadana-secrets"
```

### Opción 2: Sync a K8s Secrets (Backward Compatibility)

```yaml
# SecretProviderClass con syncToK8sSecrets
secretObjects:
- secretName: db-secrets-kv
  type: Opaque
  data:
  - objectName: POSTGRES_PASSWORD
    key: POSTGRES_PASSWORD

# Deployment usa el secret sincronizado
envFrom:
- secretRef:
    name: db-secrets-kv
```

### Ejemplo Completo (Gateway)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: gateway
spec:
  template:
    spec:
      serviceAccountName: carpeta-ciudadana-sa
      
      containers:
      - name: gateway
        envFrom:
        # Secrets from Key Vault (synced to K8s)
        - secretRef:
            name: db-secrets-kv
        - secretRef:
            name: m2m-auth-kv
        
        volumeMounts:
        - name: secrets-store
          mountPath: "/mnt/secrets-store"
          readOnly: true
      
      volumes:
      - name: secrets-store
        csi:
          driver: secrets-store.csi.k8s.io
          readOnly: true
          volumeAttributes:
            secretProviderClass: carpeta-ciudadana-secrets
```

---

## 🔄 Secret Rotation

### Configuración

CSI Driver automáticamente refresca secrets cada 2 minutos (configurable):

```yaml
# values.yaml
global:
  keyVault:
    enabled: true
    rotationInterval: "2m"  # Poll Key Vault every 2 minutes
```

### Flujo de Rotation

```
1. CSI Driver polls Key Vault every 2 minutes
2. Detecta cambio en secret version
3. Actualiza archivo en /mnt/secrets-store
4. Si syncToK8sSecrets, actualiza K8s secret
5. App lee nuevo valor (si usa file-based config)
```

### Trigger App Reload

**Opción 1**: Reloader (stakater/reloader)

```yaml
# Deployment annotation
metadata:
  annotations:
    reloader.stakater.com/auto: "true"

# Reloader detecta cambios en secrets y reinicia pods
```

**Opción 2**: Manual restart

```bash
kubectl rollout restart deployment/gateway -n carpeta-ciudadana-dev
```

**Opción 3**: File watcher en app

```python
import os
import time

def watch_secret_file(filepath: str):
    last_mtime = os.path.getmtime(filepath)
    
    while True:
        time.sleep(60)
        current_mtime = os.path.getmtime(filepath)
        
        if current_mtime != last_mtime:
            logger.info(f"Secret file changed: {filepath}")
            # Reload config
            reload_config()
            last_mtime = current_mtime
```

---

## 🔀 Migración desde K8s Secrets

### Paso 1: Backup Existing Secrets

```bash
# Backup all secrets
kubectl get secrets -n carpeta-ciudadana-dev -o yaml > secrets-backup.yaml

# Backup specific secret
kubectl get secret db-secrets -n carpeta-ciudadana-dev -o yaml > db-secrets-backup.yaml
```

### Paso 2: Extract Secret Values

```bash
# Get base64 decoded value
kubectl get secret db-secrets -n carpeta-ciudadana-dev \
  -o jsonpath='{.data.POSTGRES_PASSWORD}' | base64 -d

# Export all secrets to env file
kubectl get secret db-secrets -n carpeta-ciudadana-dev -o json \
  | jq -r '.data | to_entries[] | "\(.key)=\(.value | @base64d)"' \
  > db-secrets.env
```

### Paso 3: Create Secrets in Key Vault

```bash
# From env file
while IFS='=' read -r key value; do
  az keyvault secret set \
    --vault-name carpeta-ciudadana-dev-kv \
    --name "${key,,}"  # lowercase \
    --value "$value"
done < db-secrets.env

# Or manually
az keyvault secret set \
  --vault-name carpeta-ciudadana-dev-kv \
  --name postgres-password \
  --value "your-password"
```

### Paso 4: Enable Key Vault in Helm

```bash
helm upgrade --install carpeta-ciudadana deploy/helm/carpeta-ciudadana \
  --set global.keyVault.enabled=true \
  --set global.keyVault.name=carpeta-ciudadana-dev-kv \
  --set global.workloadIdentity.clientId=$CLIENT_ID \
  --namespace carpeta-ciudadana-dev
```

### Paso 5: Verify Secrets Mounted

```bash
# Check pod has CSI volume
kubectl describe pod gateway-xxxx -n carpeta-ciudadana-dev | grep -A5 "Volumes:"

# Check secrets mounted
kubectl exec -it gateway-xxxx -n carpeta-ciudadana-dev -- ls -la /mnt/secrets-store

# Check secret value
kubectl exec -it gateway-xxxx -n carpeta-ciudadana-dev -- cat /mnt/secrets-store/POSTGRES_PASSWORD
```

### Paso 6: Delete Old Secrets (Optional)

```bash
# After verification
kubectl delete secret db-secrets -n carpeta-ciudadana-dev
kubectl delete secret sb-secrets -n carpeta-ciudadana-dev
kubectl delete secret m2m-auth -n carpeta-ciudadana-dev
```

---

## 🧪 Testing

### Test 1: Secret Montaje

```bash
# Deploy test pod
kubectl run test-secrets \
  --image=busybox \
  --serviceaccount=carpeta-ciudadana-sa \
  --namespace=carpeta-ciudadana-dev \
  --overrides='{
    "spec": {
      "containers": [{
        "name": "test",
        "image": "busybox",
        "command": ["sleep", "3600"],
        "volumeMounts": [{
          "name": "secrets-store",
          "mountPath": "/mnt/secrets-store",
          "readOnly": true
        }]
      }],
      "volumes": [{
        "name": "secrets-store",
        "csi": {
          "driver": "secrets-store.csi.k8s.io",
          "readOnly": true,
          "volumeAttributes": {
            "secretProviderClass": "carpeta-ciudadana-secrets"
          }
        }
      }]
    }
  }'

# Wait for pod to be ready
kubectl wait --for=condition=Ready pod/test-secrets -n carpeta-ciudadana-dev --timeout=2m

# Check mounted secrets
kubectl exec test-secrets -n carpeta-ciudadana-dev -- ls -la /mnt/secrets-store

# Read secret value
kubectl exec test-secrets -n carpeta-ciudadana-dev -- cat /mnt/secrets-store/M2M_SECRET_KEY

# Cleanup
kubectl delete pod test-secrets -n carpeta-ciudadana-dev
```

### Test 2: Secret Rotation

```bash
# 1. Update secret in Key Vault
az keyvault secret set \
  --vault-name carpeta-ciudadana-dev-kv \
  --name m2m-secret-key \
  --value "new-secret-value-123"

# 2. Wait for CSI driver to refresh (2 minutes)
sleep 120

# 3. Check new value in pod
kubectl exec gateway-xxxx -n carpeta-ciudadana-dev -- cat /mnt/secrets-store/M2M_SECRET_KEY

# Should show: new-secret-value-123
```

### Test 3: Workload Identity

```bash
# Check ServiceAccount annotations
kubectl describe sa carpeta-ciudadana-sa -n carpeta-ciudadana-dev

# Should show:
# azure.workload.identity/client-id: xxxxxxxx-xxxx
# azure.workload.identity/tenant-id: yyyyyyyy-yyyy

# Check pod label
kubectl get pod gateway-xxxx -n carpeta-ciudadana-dev -o yaml | grep workload.identity

# Should show:
# azure.workload.identity/use: "true"
```

---

## 🔍 Troubleshooting

### Error: "failed to get key vault token"

**Causa**: Workload Identity no configurada correctamente.

**Solución**:
1. Verificar ServiceAccount tiene anotaciones correctas
2. Verificar pod tiene label `azure.workload.identity/use: "true"`
3. Verificar Federated credential existe en Azure Portal
4. Verificar client ID coincide

```bash
# Check federated credential
az identity federated-credential list \
  --identity-name carpeta-ciudadana-dev-aks-identity \
  --resource-group carpeta-ciudadana-dev-rg
```

### Error: "secret not found in Key Vault"

**Causa**: Secret no existe en Key Vault.

**Solución**:
```bash
# List secrets
az keyvault secret list --vault-name carpeta-ciudadana-dev-kv

# Create missing secret
az keyvault secret set \
  --vault-name carpeta-ciudadana-dev-kv \
  --name missing-secret \
  --value "value"
```

### Error: "permission denied"

**Causa**: AKS identity no tiene permisos en Key Vault.

**Solución**:
```bash
# Get identity principal ID
PRINCIPAL_ID=$(az identity show \
  --name carpeta-ciudadana-dev-aks-identity \
  --resource-group carpeta-ciudadana-dev-rg \
  --query principalId -o tsv)

# Assign role
az role assignment create \
  --role "Key Vault Secrets User" \
  --assignee $PRINCIPAL_ID \
  --scope /subscriptions/{subscription-id}/resourceGroups/carpeta-ciudadana-dev-rg/providers/Microsoft.KeyVault/vaults/carpeta-ciudadana-dev-kv
```

### Pod stuck in "ContainerCreating"

**Causa**: CSI driver no puede montar volume.

**Debug**:
```bash
# Check pod events
kubectl describe pod gateway-xxxx -n carpeta-ciudadana-dev

# Check CSI driver logs
kubectl logs -n kube-system -l app=csi-secrets-store

# Check Azure provider logs
kubectl logs -n kube-system -l app=csi-secrets-store-provider-azure
```

---

## 📊 Monitoreo

### Métricas Key Vault (Azure Monitor)

- `TotalLatency`: Latencia de requests
- `Availability`: Disponibilidad del servicio
- `SaturationShoebox`: Uso de capacidad
- `ServiceApiHit`: Requests al API

### Alertas Recomendadas

```yaml
- alert: KeyVaultHighLatency
  expr: avg(keyvault_total_latency_ms) > 1000
  annotations:
    summary: "Key Vault latency > 1 second"

- alert: KeyVaultUnauthorizedAccess
  expr: increase(keyvault_unauthorized_requests[5m]) > 10
  annotations:
    summary: "Multiple unauthorized access attempts"
```

### Audit Logs

```bash
# View audit events
az monitor activity-log list \
  --resource-group carpeta-ciudadana-dev-rg \
  --query "[?contains(resourceId, 'Microsoft.KeyVault')]" \
  --output table
```

---

## 🔑 Best Practices

### Seguridad

✅ **Purge protection**: Habilitar en producción  
✅ **Soft delete**: Mínimo 7 días  
✅ **RBAC**: Usar roles granulares  
✅ **Network**: Private endpoint en producción  
✅ **Auditoría**: Habilitar diagnostic settings  

### Operacional

✅ **Secret naming**: Usar lowercase con guiones  
✅ **Versioning**: Key Vault mantiene versiones automáticamente  
✅ **Rotation**: Configurar auto-rotation para DB passwords  
✅ **Backup**: Terraform state contiene referencias (no valores)  
✅ **DR**: Key Vault tiene geo-replication automática  

---

## 📚 Referencias

- [Azure Key Vault Documentation](https://learn.microsoft.com/en-us/azure/key-vault/)
- [Secrets Store CSI Driver](https://secrets-store-csi-driver.sigs.k8s.io/)
- [Azure Key Vault Provider](https://azure.github.io/secrets-store-csi-driver-provider-azure/)
- [Workload Identity](https://azure.github.io/azure-workload-identity/)

---

## ✅ Checklist de Implementación

- [x] Módulo Terraform Key Vault creado
- [x] Módulo Terraform CSI Driver creado
- [x] Variables Terraform configuradas
- [x] SecretProviderClass Helm template
- [x] ServiceAccount con Workload Identity
- [x] Deployment gateway actualizado (ejemplo)
- [x] values.yaml configuración completa
- [ ] Aplicar Terraform
- [ ] Migrar todos los secrets
- [ ] Actualizar todos los deployments
- [ ] Instalar Reloader (auto-restart on secret change)
- [ ] Configurar alertas
- [ ] Testing completo

---

**Generado**: 2025-10-13 02:00  
**Autor**: Manuel Jurado  
**Versión**: 1.0

