# Solución: Azure PostgreSQL Flexible Server

## Problema Identificado

El proyecto tenía conflictos en la configuración de PostgreSQL que impedían el despliegue exitoso:

1. **Conflicto de módulos**: Se estaba usando el módulo `postgresql-k8s` (PostgreSQL en Kubernetes) pero también existía un módulo `postgresql-flexible` (Azure PostgreSQL Flexible Server) más completo.

2. **Recursos duplicados**: Había archivos duplicados (`main-vnet.tf`) que causaban conflictos de recursos.

3. **Variables inconsistentes**: Las variables no coincidían con las que esperaba el módulo seleccionado.

4. **Errores de validación**: SKU inválido, configuración de red inconsistente.

## Solución Implementada

### 1. Configuración Corregida

**Archivo**: `infra/terraform/main.tf`
- Cambiado el módulo de `postgresql-k8s` a `postgresql-flexible`
- Configurado correctamente la integración con VNet
- Establecido acceso privado (sin acceso público)
- Configurado backup y alta disponibilidad

**Archivo**: `infra/terraform/terraform.tfvars`
- SKU corregido: `GP_Standard_D2s_v3` (válido para Azure)
- Configuración de seguridad: acceso público deshabilitado
- Variables de autenticación configuradas

### 2. Módulo PostgreSQL Flexible

**Características implementadas**:
- ✅ Integración con VNet (acceso privado)
- ✅ Private DNS Zone para resolución interna
- ✅ Network Security Groups configurados
- ✅ Backup automático (7 días)
- ✅ Alta disponibilidad deshabilitada (para desarrollo)
- ✅ Subnet dedicada con delegación para PostgreSQL

### 3. Scripts de Despliegue

**Script principal**: `scripts/deploy-postgresql-flexible.sh`
- Verificación de prerequisitos
- Validación de configuración
- Despliegue paso a paso
- Información de conexión

**Script de verificación**: `scripts/check-postgresql-deployment.sh`
- Verificación del estado del despliegue
- Diagnóstico de problemas comunes
- Información de conectividad

## Configuración Final

### PostgreSQL Flexible Server
```hcl
module "postgresql" {
  source = "./modules/postgresql-flexible"
  
  # Configuración básica
  environment         = var.environment
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  
  # Autenticación
  admin_username = var.db_admin_username
  admin_password = var.db_admin_password
  database_name  = "carpeta_ciudadana"
  
  # PostgreSQL
  postgresql_version = "13"
  sku_name          = "GP_Standard_D2s_v3"
  storage_mb        = 32768  # 32GB
  
  # Red
  vnet_name             = module.vnet.vnet_name
  vnet_id               = module.vnet.vnet_id
  postgresql_subnet_cidr = "10.0.2.0/24"
  
  # Seguridad
  public_network_access_enabled = false  # Solo acceso privado
  allow_azure_services          = false
  allow_current_ip             = false
}
```

### Variables de Configuración
```hcl
# terraform.tfvars
db_admin_username = "psqladmin"
db_admin_password = "CarpetaCiudadana2024!Secure"
db_sku_name       = "GP_Standard_D2s_v3"
db_storage_mb     = 32768
db_enable_public_access = false
```

## Cómo Usar

### 1. Despliegue Completo
```bash
# Ejecutar script de despliegue
./scripts/deploy-postgresql-flexible.sh
```

### 2. Verificar Estado
```bash
# Verificar despliegue
./scripts/check-postgresql-deployment.sh
```

### 3. Despliegue Manual
```bash
cd infra/terraform
terraform init
terraform validate
terraform plan
terraform apply
```

## Información de Conexión

Después del despliegue, puedes obtener la información de conexión:

```bash
cd infra/terraform
terraform output postgresql_connection_string
terraform output postgresql_fqdn
```

## Costos Estimados

- **PostgreSQL Flexible Server (GP_Standard_D2s_v3)**: ~$40/mes
- **AKS (Standard_B2s)**: ~$3.80/mes
- **Storage (32GB)**: ~$1-2/mes
- **Service Bus**: ~$0.05/mes

**Total estimado**: ~$45-50/mes

## Ventajas de la Solución

1. **Seguridad**: Acceso privado a través de VNet
2. **Escalabilidad**: PostgreSQL Flexible Server puede escalarse según necesidad
3. **Backup**: Backup automático configurado
4. **Monitoreo**: Integración con Azure Monitor
5. **Alta Disponibilidad**: Configurable para producción
6. **Mantenimiento**: Ventanas de mantenimiento configuradas

## Próximos Pasos

1. **Desplegar infraestructura**: Ejecutar el script de despliegue
2. **Configurar aplicación**: Actualizar variables de conexión en la aplicación
3. **Configurar DNS**: Si tienes un dominio, configurar los registros DNS
4. **Monitoreo**: Configurar alertas y dashboards
5. **Backup**: Verificar que los backups funcionen correctamente

## Troubleshooting

### Problemas Comunes

1. **Error de SKU**: Asegúrate de usar SKUs válidos como `GP_Standard_D2s_v3`
2. **Error de red**: Verifica que la VNet y subnets estén configuradas correctamente
3. **Error de permisos**: Asegúrate de tener permisos para crear recursos en Azure
4. **Timeout**: El despliegue puede tomar 10-15 minutos, sé paciente

### Comandos Útiles

```bash
# Ver estado de Terraform
terraform show

# Ver outputs
terraform output

# Refrescar estado
terraform refresh

# Destruir recursos (¡cuidado!)
terraform destroy
```
