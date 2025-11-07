# External Secrets - Explicación y Configuración

## ¿Qué son External Secrets?

**External Secrets Operator** es un operador de Kubernetes que sincroniza automáticamente secrets desde almacenes externos (como Azure Key Vault) a Kubernetes secrets.

### Arquitectura

```
Azure Key Vault (Almacén Externo)
        ↓
External Secrets Operator (en Kubernetes)
        ↓
SecretStore (Configuración: cómo conectarse)
        ↓
ExternalSecret (Configuración: qué secrets traer)
        ↓
Kubernetes Secret (Resultado final)
        ↓
Pods (Usan el Kubernetes Secret)
```

## Componentes

### 1. SecretStore / ClusterSecretStore
Define **cómo conectarse** a Azure Key Vault:
- **URL del Key Vault**: `vaultUrl`
- **Método de autenticación**: `WorkloadIdentity` o `ManagedIdentity`
- **Identidad a usar**: ServiceAccount con Workload Identity

**Tipos**:
- `SecretStore`: Solo para un namespace específico
- `ClusterSecretStore`: Para todo el cluster (acceso global)

### 2. ExternalSecret
Define **qué secrets traer** desde Key Vault:
- **Nombre del secret en Key Vault**: `remoteRef.key`
- **Propiedades específicas**: `remoteRef.property` (opcional)
- **Nombre del Kubernetes secret resultante**: `target.name`
- **Intervalo de sincronización**: `refreshInterval` (ej: "5m")

### 3. Kubernetes Secret (Resultado)
El External Secrets Operator crea/actualiza automáticamente un Kubernetes Secret basado en la configuración del ExternalSecret.

## Flujo de Funcionamiento

1. **External Secrets Operator** lee los ExternalSecrets
2. Usa el **SecretStore** para obtener credenciales de conexión
3. Se conecta a **Azure Key Vault** usando Workload Identity
4. Lee los valores del Key Vault según `remoteRef`
5. Crea/actualiza el **Kubernetes Secret** automáticamente
6. Los **pods** usan el Kubernetes Secret como variable de entorno

## Configuración Actual en el Proyecto

### Problema: Duplicación de SecretStores

Actualmente hay **DOS** SecretStores diferentes:

1. **ClusterSecretStore "azure-keyvault"** (creado por Terraform)
   - Creado en: `infra/terraform/layers/application/main.tf`
   - Tipo: ClusterSecretStore (global)
   - Auth: WorkloadIdentity
   - Namespace: `external-secrets-system`

2. **SecretStore "azure-keyvault-store"** (creado por Helm)
   - Creado en: `deploy/helm/carpeta-ciudadana/templates/external-secret-store.yaml`
   - Tipo: SecretStore (namespace específico)
   - Auth: ManagedIdentity
   - Namespace: `carpeta-ciudadana`

### Estado Actual

- **Helm chart** crea ExternalSecrets que usan `azure-keyvault-store` (SecretStore)
- **Terraform** crea ClusterSecretStore `azure-keyvault` (global)
- Hay **inconsistencia**: algunos ExternalSecrets usan uno, otros usan otro

### ExternalSecrets en Helm Chart

Los ExternalSecrets en el Helm chart están configurados para usar:
```yaml
secretStoreRef:
  name: azure-keyvault-store
  kind: SecretStore
```

Pero el SecretStore creado por Helm tiene:
- `vaultUrl: ""` (vacío inicialmente)
- `authType: "ManagedIdentity"` (diferente del ClusterSecretStore)

## Cómo Funciona con Azure Key Vault

### 1. Workload Identity (Recomendado)

```yaml
authType: "WorkloadIdentity"
serviceAccountRef:
  name: "external-secrets"
  namespace: "external-secrets-system"
```

**Ventajas**:
- Más seguro
- No requiere guardar credenciales
- Usa la Managed Identity del AKS

### 2. Managed Identity

```yaml
authType: "ManagedIdentity"
identity:
  clientId: "xxx-xxx-xxx"
```

**Ventajas**:
- Más simple de configurar
- Requiere guardar clientId

## Problema Actual

### Error: `No scheme detected in URL`

El SecretStore `azure-keyvault-store` tenía `vaultUrl: ""` (vacío), lo que causaba:
- ExternalSecrets no podían sincronizar
- Kubernetes Secrets no se creaban
- Pods fallaban con `CreateContainerConfigError`

### Solución Aplicada

1. Se actualizó el SecretStore con la URL correcta del Key Vault:
   ```bash
   kubectl patch secretstore azure-keyvault-store -n carpeta-ciudadana \
     --type='json' -p='[{"op": "replace", "path": "/spec/provider/azurekv/vaultUrl", "value": "https://carpeta-ciudadana-kv-v2.vault.azure.net/"}]'
   ```

2. Se hicieron los secrets opcionales temporalmente para que los pods puedan iniciar

## Recomendación

### Opción 1: Usar Solo ClusterSecretStore de Terraform (Recomendado)

**Ventajas**:
- Configuración centralizada en Terraform
- Usa Workload Identity (más seguro)
- Es global (acceso desde cualquier namespace)

**Pasos**:
1. Eliminar SecretStore del Helm chart
2. Actualizar ExternalSecrets del Helm chart para usar `azure-keyvault` (ClusterSecretStore)
3. Asegurar que todos los ExternalSecrets usen el mismo ClusterSecretStore

### Opción 2: Usar Solo SecretStore del Helm Chart

**Ventajas**:
- Todo en el Helm chart
- Más fácil de gestionar con Helm

**Pasos**:
1. Pasar `keyvault.vaultUrl` al Helm chart desde Terraform
2. Eliminar ClusterSecretStore de Terraform
3. Asegurar que todos usen el SecretStore del Helm

## Próximos Pasos

1. ✅ SecretStore actualizado con URL correcta
2. ⏳ Verificar que ExternalSecrets se sincronicen correctamente
3. ⏳ Actualizar configuración para usar un solo SecretStore (preferiblemente ClusterSecretStore de Terraform)
4. ⏳ Hacer secrets obligatorios nuevamente una vez que se sincronicen

