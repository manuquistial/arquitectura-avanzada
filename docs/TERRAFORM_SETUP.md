# 🚀 Configuración Inicial para Terraform - Carpeta Ciudadana

## 📋 Prerrequisitos y Configuraciones Iniciales

Este documento describe todos los pasos necesarios para configurar el entorno antes de ejecutar `terraform apply` sin errores.

---

## 🔧 **1. Configuración de Azure CLI**

### 1.1 Instalar Azure CLI
```bash
# macOS (Homebrew)
brew install azure-cli

# Verificar instalación
az --version
```

### 1.2 Autenticación en Azure
```bash
# Iniciar sesión en Azure
az login

# Verificar suscripción activa
az account show

# Si necesitas cambiar de suscripción
az account set --subscription "<SUSCRIPTION_ID>"
```

### 1.3 Configurar Variables de Entorno
```bash
# Configurar variables de entorno de Azure
export AZURE_SUBSCRIPTION_ID="<SUSCRIPTION_ID>"
export AZURE_TENANT_ID="<TENANT_ID>"
export AZURE_REGION="eastus"

# Agregar a ~/.zshrc para persistencia
echo 'export AZURE_SUBSCRIPTION_ID="<SUSCRIPTION_ID>"' >> ~/.zshrc
echo 'export AZURE_TENANT_ID="<TENANT_ID>"' >> ~/.zshrc
echo 'export AZURE_REGION="eastus"' >> ~/.zshrc
```

---

## 🎯 **2. Configuración de Kubernetes (AKS)**

### 2.1 Obtener Credenciales del Cluster
```bash
# Obtener credenciales administrativas del cluster AKS
az aks get-credentials \
  --resource-group carpeta-ciudadana-production-rg \
  --name carpeta-ciudadana-production \
  --admin \
  --overwrite-existing
```

### 2.2 Verificar Acceso a Kubernetes
```bash
# Verificar que el acceso funciona
kubectl get nodes

# Debería mostrar algo como:
# NAME                             STATUS   ROLES    AGE   VERSION
# aks-system-33897699-vmss000000   Ready    <none>   51m   v1.31.11
# aks-user-40009251-vmss000000     Ready    <none>   49m   v1.31.11
```

### 2.3 Configurar Permisos de Azure RBAC (si es necesario)
```bash
# Asignar rol de administrador de cluster (si no tienes permisos)
az role assignment create \
  --assignee <ID> \
  --role "Azure Kubernetes Service Cluster Admin Role" \
  --scope /subscriptions/<SUSCRIPTION_ID>/resourceGroups/carpeta-ciudadana-production-rg/providers/Microsoft.ContainerService/managedClusters/carpeta-ciudadana-production
```

---

## 📁 **3. Configuración de Variables de Entorno de Terraform**

### 3.1 Configurar .envrc (Producción)
```bash
# Copiar plantilla si no existe
cp .envrc.example .envrc

# Editar con valores reales
nano .envrc
```

### 3.2 Variables Críticas en .envrc
```bash
# Core context
export TF_VAR_environment="production"
export TF_VAR_azure_region="eastus"  # Cambiado de westus2 a eastus
export TF_VAR_project_name="carpeta-ciudadana"

# Database (REQUERIDO - valores reales)
export TF_VAR_db_admin_username="psqladmin"
export TF_VAR_db_admin_password="CarpetaCiudadana2024!Secure"

# OpenSearch (REQUERIDO - valores reales)
export TF_VAR_opensearch_username="admin"
export TF_VAR_opensearch_password="CarpetaCiudadana2024!Secure"

# cert-manager (REQUERIDO)
export TF_VAR_letsencrypt_email="manuelquistial@outlook.com"

# Kubernetes version
export TF_VAR_aks_kubernetes_version="1.32.7"
```

### 3.3 Configurar direnv (Opcional pero Recomendado)
```bash
# Instalar direnv
brew install direnv

# Configurar para el shell
echo 'eval "$(direnv hook zsh)"' >> ~/.zshrc
source ~/.zshrc

# Permitir direnv en el directorio de Terraform
cd infra/terraform
direnv allow
```

---

## 🛠️ **4. Verificación de Herramientas**

### 4.1 Verificar Terraform
```bash
terraform --version
# Debería mostrar: Terraform v1.x.x
```

### 4.2 Verificar kubectl
```bash
kubectl version --client
# Debería mostrar la versión del cliente kubectl
```

### 4.3 Verificar Helm (si se usa)
```bash
helm version
# Debería mostrar la versión de Helm
```

---

## 🔍 **5. Verificación de Recursos Azure**

### 5.1 Verificar que el Resource Group existe
```bash
az group show --name carpeta-ciudadana-production-rg
```

### 5.2 Verificar que el cluster AKS existe
```bash
az aks show \
  --resource-group carpeta-ciudadana-production-rg \
  --name carpeta-ciudadana-production \
  --query "{name:name, resourceGroup:resourceGroup, provisioningState:provisioningState}"
```

### 5.3 Verificar permisos de Azure
```bash
# Verificar roles asignados
az role assignment list \
  --assignee e86bf64e-0691-4d73-91fa-db96f9ab4e7d \
  --query "[].{role:roleDefinitionName, scope:scope}"
```

---

## 🚀 **6. Ejecución de Terraform**

### 6.1 Inicializar Terraform
```bash
cd infra/terraform
terraform init
```

### 6.2 Validar Configuración
```bash
terraform validate
# Debería mostrar: Success! The configuration is valid.
```

### 6.3 Plan de Ejecución
```bash
terraform plan
# Debería mostrar el plan sin errores de autorización
```

### 6.4 Aplicar Cambios
```bash
terraform apply
# Confirmar con 'yes' cuando se solicite
```

---

## ⚠️ **7. Solución de Problemas Comunes**

### 7.1 Error: "Unauthorized" en recursos de Kubernetes
**Solución:**
```bash
# Reconfigurar credenciales administrativas
az aks get-credentials \
  --resource-group carpeta-ciudadana-production-rg \
  --name carpeta-ciudadana-production \
  --admin \
  --overwrite-existing

# Verificar acceso
kubectl get nodes
```

### 7.2 Error: "Tenant not found"
**Solución:**
```bash
# Verificar tenant correcto
az account show --query tenantId

# Usar el tenant correcto en el login
az login --tenant 48d06645-ab3b-4ac4-b121-c63bb238ef6e
```

### 7.3 Error: "Subscription not found"
**Solución:**
```bash
# Listar suscripciones disponibles
az account list --output table

# Cambiar a la suscripción correcta
az account set --subscription "635ab07e-b29c-417e-b2b2-008bc4fc57d6"
```

### 7.4 Error: Variables de entorno no encontradas
**Solución:**
```bash
# Verificar variables cargadas
echo $TF_VAR_environment
echo $TF_VAR_azure_region

# Recargar variables si es necesario
source .envrc
```

---

## 📊 **8. Checklist de Verificación**

Antes de ejecutar `terraform apply`, verifica que:

- [ ] ✅ Azure CLI autenticado (`az account show`)
- [ ] ✅ Variables de entorno configuradas (`echo $TF_VAR_environment`)
- [ ] ✅ Acceso a Kubernetes funcionando (`kubectl get nodes`)
- [ ] ✅ Terraform inicializado (`terraform init`)
- [ ] ✅ Configuración válida (`terraform validate`)
- [ ] ✅ Plan sin errores (`terraform plan`)

---

## 🎯 **9. Comandos de Verificación Rápida**

```bash
# Script de verificación completa
#!/bin/bash
echo "🔍 Verificando configuración..."

# Azure CLI
echo "Azure CLI:"
az account show --query "{subscription:name, tenant:tenantId}" -o table

# Kubernetes
echo "Kubernetes:"
kubectl get nodes --no-headers | wc -l

# Terraform
echo "Terraform:"
terraform validate

# Variables
echo "Variables críticas:"
echo "TF_VAR_environment: $TF_VAR_environment"
echo "TF_VAR_azure_region: $TF_VAR_azure_region"
echo "AZURE_SUBSCRIPTION_ID: $AZURE_SUBSCRIPTION_ID"

echo "✅ Verificación completada"
```

---

## 📝 **10. Notas Importantes**

- **Región**: Se cambió de `westus2` a `eastus` para mejor disponibilidad de cuotas
- **Permisos**: Se requiere rol de "Owner" o "Contributor" en la suscripción
- **Kubernetes**: Se requiere acceso administrativo al cluster AKS
- **Variables**: Las contraseñas deben ser seguras y únicas
- **Backup**: Siempre hacer backup del estado de Terraform antes de cambios importantes

---

## 🆘 **11. Contacto y Soporte**

Si encuentras problemas no cubiertos en este documento:

1. Verificar logs de Terraform: `terraform plan -detailed-exitcode`
2. Verificar logs de Azure: `az activity log list --resource-group carpeta-ciudadana-production-rg`
3. Verificar logs de Kubernetes: `kubectl get events --all-namespaces`

---

**Última actualización**: $(date)
**Versión**: 1.0
**Autor**: Manuel Quistial
