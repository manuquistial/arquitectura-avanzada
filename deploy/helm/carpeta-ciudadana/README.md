# Carpeta Ciudadana - Despliegue en Azure

Este directorio contiene la configuración de Helm para desplegar Carpeta Ciudadana en Azure Kubernetes Service (AKS) con dominios generados automáticamente por Azure.

## 🚀 Despliegue Rápido

### Opción 1: Despliegue Automático Completo
```bash
# Ejecutar el script de despliegue completo con configuración automática de dominio
./scripts/deploy-with-domain.sh
```

### Opción 2: Despliegue Manual por Pasos
```bash
# 1. Configurar secretos
./scripts/configure-secrets.sh

# 2. Desplegar con Helm
./scripts/deploy.sh

# 3. Obtener dominio generado por Azure
./scripts/get-azure-domain.sh

# 4. Actualizar configuración con el dominio
./scripts/update-domain-config.sh
```

## 📋 Prerrequisitos

### Herramientas Necesarias
- `kubectl` - Cliente de Kubernetes
- `helm` - Gestor de paquetes de Kubernetes
- `curl` - Para pruebas de conectividad
- `base64` - Para codificación de secretos

### Acceso a Azure
- Cluster de AKS configurado y accesible
- Permisos para crear recursos en el cluster
- Acceso a Azure Storage, PostgreSQL, Redis, Service Bus

## 🔧 Configuración

### Variables de Entorno
Copia el archivo de ejemplo y configura las variables:
```bash
cp scripts/secrets.env.example scripts/secrets.env
# Edita scripts/secrets.env con tus valores
```

### Secretos Requeridos
- **Base de datos**: `DATABASE_URL`
- **Redis**: `REDIS_HOST`, `REDIS_PASSWORD`
- **Azure Storage**: `AZURE_STORAGE_ACCOUNT_KEY`
- **Azure AD B2C**: `AZURE_AD_B2C_*`
- **NextAuth**: `NEXTAUTH_SECRET`, `NEXTAUTH_URL`
- **Service Bus**: `SERVICEBUS_CONNECTION_STRING`
- **M2M Auth**: `M2M_SECRET_KEY`

## 🌐 Dominios Generados por Azure

El sistema está configurado para usar dominios generados automáticamente por Azure:

### Tipos de Dominios
1. **Load Balancer IP**: `http://20.123.45.67`
2. **Application Gateway**: `http://carpeta-ciudadana-aks.westus2.cloudapp.azure.com`
3. **Azure Front Door**: `https://carpeta-ciudadana.azurefd.net`

### Configuración Automática
- El sistema detecta automáticamente el tipo de dominio
- Actualiza todas las configuraciones necesarias
- Configura CORS para permitir el dominio
- Actualiza NextAuth URL y redirect URIs

## 📊 Servicios Desplegados

### Frontend (Next.js)
- **Puerto**: 3000
- **Servicio**: LoadBalancer
- **Ruta**: `/`
- **Funcionalidades**: Login, Dashboard, Documentos, Transferencias

### Backend Services
- **Auth Service**: `/api/auth`
- **Citizen Service**: `/api/users`
- **Ingestion Service**: `/api/documents`
- **Metadata Service**: `/api/metadata`
- **Signature Service**: `/api/signature`
- **Transfer Service**: `/api/transfers`
- **MinTIC Service**: `/api/mintic`
- **Read Models Service**: `/api/dashboard`
- **Notification Service**: `/api/notifications`

### Gateway
- **Puerto**: 8000
- **Función**: Enrutamiento interno de APIs
- **Health Check**: `/health`

## 🔍 Verificación

### Comandos de Verificación
```bash
# Estado de los pods
kubectl get pods -n carpeta-ciudadana

# Servicios
kubectl get services -n carpeta-ciudadana

# Ingress
kubectl get ingress -n carpeta-ciudadana

# Logs del frontend
kubectl logs -f deployment/carpeta-ciudadana-frontend -n carpeta-ciudadana
```

### Pruebas de Conectividad
```bash
# Health check
curl http://TU_DOMINIO/health

# Frontend
curl http://TU_DOMINIO/

# API
curl http://TU_DOMINIO/api/auth/health
```

## 🔧 Mantenimiento

### Actualizar Dominio
```bash
# Si el dominio cambia, actualizar la configuración
./scripts/get-azure-domain.sh
./scripts/update-domain-config.sh
```

### Reiniciar Servicios
```bash
# Reiniciar todos los servicios
kubectl rollout restart deployment -n carpeta-ciudadana

# Reiniciar un servicio específico
kubectl rollout restart deployment/carpeta-ciudadana-frontend -n carpeta-ciudadana
```

### Ver Logs
```bash
# Logs del frontend
kubectl logs -f deployment/carpeta-ciudadana-frontend -n carpeta-ciudadana

# Logs de un servicio específico
kubectl logs -f deployment/carpeta-ciudadana-auth -n carpeta-ciudadana
```

## 🚨 Solución de Problemas

### Problemas Comunes

#### 1. Load Balancer sin IP Externa
```bash
# Verificar estado del servicio
kubectl get service carpeta-ciudadana-frontend -n carpeta-ciudadana

# Verificar eventos
kubectl get events -n carpeta-ciudadana
```

#### 2. Pods no Inician
```bash
# Verificar logs de un pod específico
kubectl logs deployment/carpeta-ciudadana-frontend -n carpeta-ciudadana

# Verificar recursos
kubectl describe pod -l app=frontend -n carpeta-ciudadana
```

#### 3. Dominio no Accesible
```bash
# Verificar conectividad
curl -v http://TU_DOMINIO/health

# Verificar DNS
nslookup TU_DOMINIO
```

### Comandos de Diagnóstico
```bash
# Estado general
kubectl get all -n carpeta-ciudadana

# Recursos del cluster
kubectl top nodes
kubectl top pods -n carpeta-ciudadana

# Configuración de red
kubectl get networkpolicies -n carpeta-ciudadana
```

## 📚 Documentación Adicional

- [Configuración de Helm](values.yaml)
- [Scripts de Despliegue](scripts/)
- [Configuración de Secretos](scripts/secrets.env.example)
- [Documentación de la Aplicación](../../docs/)

## 🆘 Soporte

Para problemas o preguntas:
1. Revisar los logs: `kubectl logs -f deployment/carpeta-ciudadana-frontend -n carpeta-ciudadana`
2. Verificar el estado: `kubectl get all -n carpeta-ciudadana`
3. Consultar la documentación en `../../docs/`
