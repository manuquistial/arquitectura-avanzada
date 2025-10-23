# Configuración de Private Endpoint para PostgreSQL

Este documento explica la configuración de Private Endpoint y Private DNS Zone para conectar AKS con Azure Database for PostgreSQL de forma segura y privada.

## Arquitectura

```
[VNet Principal: 10.0.0.0/16]
├── [Subnet AKS: 10.0.1.0/24] ───> AKS Pods
├── [Subnet DB: 10.0.2.0/24] ───> PostgreSQL Flexible Server (sin IP pública)
├── [Private Endpoint] ──> PostgreSQL (IP privada)
└── [Private DNS Zone] ──> privatelink.postgres.database.azure.com
```

## Componentes Implementados

### 1. Private DNS Zone
- **Zona DNS**: `privatelink.postgres.database.azure.com`
- **Función**: Resuelve el FQDN del PostgreSQL a una IP privada
- **Vinculación**: Conectada a la VNet principal

### 2. PostgreSQL Flexible Server
- **Acceso público**: Deshabilitado (`public_network_access_enabled = false`)
- **Subnet delegada**: Usa la subnet `db-subnet` con delegación para PostgreSQL
- **Private DNS Zone**: Vinculada para resolución DNS privada

### 3. Private Endpoint
- **Ubicación**: En la subnet de AKS (`aks-subnet`)
- **Función**: Proporciona IP privada para acceder al PostgreSQL
- **Conexión**: Automática con el servidor PostgreSQL

### 4. Kubernetes Secrets
- **PostgreSQL Secret**: Contiene credenciales y FQDN privado
- **Azure Storage Secret**: Credenciales de Azure Storage
- **Service Bus Secret**: Connection string de Service Bus
- **Redis Secret**: Credenciales de Redis
- **Azure AD B2C Secret**: Configuración de autenticación
- **M2M Secret**: Clave para autenticación machine-to-machine

## Configuración de Conexión

### Variables de Entorno en los Pods

Los pods acceden a la base de datos usando las siguientes variables de entorno desde los secrets de Kubernetes:

```bash
# PostgreSQL
PGHOST=postgresql-server-name.privatelink.postgres.database.azure.com
PGUSER=admin@postgresql-server-name
PGPASSWORD=password
PGDATABASE=carpeta_ciudadana
PGPORT=5432
PGSSLMODE=require

# Azure Storage
AZURE_STORAGE_ACCOUNT_NAME=storage-account-name
AZURE_STORAGE_ACCOUNT_KEY=storage-key
AZURE_STORAGE_CONTAINER_NAME=documents

# Service Bus
SERVICEBUS_CONNECTION_STRING=Endpoint=sb://...

# Redis
REDIS_HOST=redis-host.privatelink.redis.cache.windows.net
REDIS_PORT=6380
REDIS_PASSWORD=redis-password
REDIS_SSL=true

# Azure AD B2C
AZURE_B2C_TENANT_ID=tenant-id
AZURE_B2C_CLIENT_ID=client-id
AZURE_B2C_CLIENT_SECRET=client-secret

# M2M Authentication
M2M_SECRET_KEY=secret-key
```

## Beneficios de Seguridad

1. **Tráfico Privado**: Todo el tráfico entre AKS y PostgreSQL ocurre dentro de la VNet
2. **Sin Exposición Pública**: PostgreSQL no tiene IP pública
3. **DNS Privado**: Resolución DNS interna sin exposición a Internet
4. **Secrets Seguros**: Credenciales almacenadas en Kubernetes Secrets
5. **Cumplimiento**: Cumple con estándares de seguridad empresarial

## Verificación de la Configuración

### 1. Verificar Private Endpoint
```bash
# Desde un pod en AKS
kubectl exec -it <pod-name> -- nslookup postgresql-server-name.privatelink.postgres.database.azure.com
```

### 2. Verificar Conexión a PostgreSQL
```bash
# Desde un pod en AKS
kubectl exec -it <pod-name> -- psql "host=$PGHOST user=$PGUSER password=$PGPASSWORD dbname=$PGDATABASE sslmode=require"
```

### 3. Verificar Secrets de Kubernetes
```bash
# Listar secrets
kubectl get secrets -n carpeta-ciudadana-production

# Ver contenido de un secret (base64 encoded)
kubectl get secret postgresql-secret -n carpeta-ciudadana-production -o yaml
```

## Troubleshooting

### Problema: No se puede resolver el DNS
**Solución**: Verificar que la Private DNS Zone esté vinculada a la VNet y que el Private Endpoint esté en la subnet correcta.

### Problema: Conexión rechazada
**Solución**: Verificar que el PostgreSQL esté configurado con `public_network_access_enabled = false` y que el Private Endpoint esté activo.

### Problema: Secrets no encontrados
**Solución**: Verificar que el módulo `kubernetes_secrets` se haya aplicado correctamente y que el namespace exista.

## Archivos Modificados

1. `infra/terraform/modules/postgresql-flexible/main.tf` - Configuración de Private Endpoint
2. `infra/terraform/modules/kubernetes-secrets/` - Nuevo módulo para secrets
3. `infra/terraform/main.tf` - Integración de los nuevos módulos
4. `deploy/helm/carpeta-ciudadana/values-*.yaml` - Configuración de Helm para usar secrets

## Próximos Pasos

1. Aplicar los cambios de Terraform
2. Verificar que los secrets se creen correctamente
3. Actualizar las aplicaciones para usar las variables de entorno de los secrets
4. Probar la conectividad desde los pods
5. Monitorear el tráfico para asegurar que sea privado
