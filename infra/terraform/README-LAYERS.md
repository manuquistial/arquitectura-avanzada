# 🏗️ Arquitectura en Capas - Carpeta Ciudadana

Esta infraestructura ha sido reorganizada en **5 capas** para eliminar dependencias circulares y facilitar el mantenimiento.

## 📁 Estructura de Capas

```
infra/terraform/
├── layers/
│   ├── base/                      # 🔧 BASE LAYER (RG, VNet, DNS)
│   ├── security/                  # 🔐 SECURITY LAYER (Key Vault, MI ESO)
│   ├── platform/                  # 🏗️ PLATFORM LAYER (AKS, DB, Storage, Redis)
│   ├── external-secrets/          # 🔑 ESO LAYER (Helm/operator, bindings)
│   ├── application/               # 🚀 APPLICATION LAYER (cert-manager, kedacd ../)
│   └── carpeta-ciudadana/         # 📦 APP CHART LAYER (helm app)
├── shared/                        # 🔄 SHARED RESOURCES
└── deployments/                   # 🚀 DEPLOYMENT SCRIPTS
    ├── deploy-base.sh
    ├── deploy-security.sh
    ├── deploy-platform.sh
    ├── deploy-external-secrets.sh
    └── deploy-application.sh
```

## 🔧 BASE LAYER (Infraestructura Base)

**Recursos:**
- Resource Group
- Virtual Network
- Subnets
- DNS Zone

**Despliegue:**
```bash
cd layers/base
cp terraform.tfvars.example terraform.tfvars
# Editar terraform.tfvars con tus valores
terraform init
terraform plan
terraform apply
```

## 🔐 SECURITY LAYER (Key Vault)

**Recursos:**
- Key Vault (RBAC, ACLs)
- Managed Identity para External Secrets

**Despliegue:**
```bash
cd layers/security
cp terraform.tfvars.example terraform.tfvars
# Editar terraform.tfvars con tus valores
terraform init
terraform plan
terraform apply
```

## 🏗️ PLATFORM LAYER (Servicios de Plataforma)

**Recursos:**
- AKS Cluster
- PostgreSQL Database
- Azure Storage (usa Key Vault de security)
- Redis Cache
- ~~Azure Front Door~~ (Deshabilitado por defecto - se usa LoadBalancer de Kubernetes + Ingress)

**Despliegue:**
```bash
cd layers/platform
cp terraform.tfvars.example terraform.tfvars
# Editar terraform.tfvars con tus valores
terraform init
terraform plan
terraform apply
```

## 🔑 EXTERNAL SECRETS LAYER (Operator)

**Recursos:**
- External Secrets Operator (Helm)
- ClusterSecretStore vinculado a Key Vault

**Despliegue:**
```bash
cd layers/external-secrets
cp terraform.tfvars.example terraform.tfvars
# Editar terraform.tfvars con tus valores (si aplica)
terraform init
terraform plan
terraform apply
```

## 🚀 APPLICATION LAYER (Aplicaciones)

**Recursos:**
- cert-manager
- KEDA
- External Secrets configuration (ClusterSecretStore)

**Despliegue:**
```bash
cd layers/application
cp terraform.tfvars.example terraform.tfvars
# Editar terraform.tfvars con tus valores
terraform init
terraform plan
terraform apply
```

## 🚀 Despliegue Automático

### Opción 1: Scripts Automáticos
```bash
# Desplegar todo en orden
./deployments/deploy-base.sh
./deployments/deploy-security.sh
./deployments/deploy-platform.sh
./deployments/deploy-external-secrets.sh
./deployments/deploy-application.sh
```

### Opción 2: Despliegue Manual
```bash
# 1. Base Layer
cd layers/base
terraform init && terraform apply

# 2. Security Layer
cd ../security
terraform init && terraform apply

# 3. Platform Layer
cd ../platform
terraform init && terraform apply

# 4. External Secrets Layer
cd ../external-secrets
terraform init && terraform apply

# 5. Application Layer
cd ../application
terraform init && terraform apply

# 6. Carpeta Ciudadana (si aplica)
cd ../carpeta-ciudadana
terraform init && terraform apply
```

## 🔄 Flujo de Dependencias

```
┌──────────────┐   ┌───────────────┐   ┌──────────────────────┐   ┌────────────────────┐   ┌────────────────┐
│  BASE LAYER  │──▶│ SECURITY LAYER│──▶│ PLATFORM LAYER       │──▶│ EXTERNAL SECRETS    │──▶│ APPLICATION     │
│ (RG,VNet,DNS)│   │ (Key Vault)   │   │ (AKS,DB,Storage)     │   │ (ESO + Store)       │   │ (cert,keda)    │
│              │   │               │   │ LoadBalancer(K8s)    │   │                     │   │ Ingress(NGINX) │
└──────────────┘   └───────────────┘   └──────────────────────┘   └────────────────────┘   └────────────────┘
                                                                                                           │
                                                                                                           ▼
                                                                                                    CARPETA CIUDADANA
```

## 🌐 Arquitectura de Red (Sin Front Door)

Este proyecto está configurado para usar **LoadBalancer de Kubernetes + Ingress NGINX + cert-manager** en lugar de Azure Front Door:

```
Internet
   │
   ▼
┌─────────────────────────────────┐
│  LoadBalancer (AKS)             │  ← Azure LoadBalancer creado por Kubernetes
│  IP Pública: <EXTERNAL-IP>       │
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│  Ingress Controller (NGINX)      │  ← Routing y SSL/TLS termination
│  + cert-manager                  │  ← Certificados automáticos (Let's Encrypt)
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│  Services (Frontend/API)        │  ← Aplicaciones en AKS
└─────────────────────────────────┘
```

**Beneficios de esta arquitectura:**
- ✅ **Más simple**: Sin dependencias externas de Front Door
- ✅ **Menor costo**: LoadBalancer básico de Azure es más económico
- ✅ **SSL/TLS automático**: cert-manager gestiona certificados Let's Encrypt
- ✅ **Routing flexible**: Ingress NGINX permite reglas avanzadas
- ✅ **Despliegue rápido**: No hay que esperar creación de Front Door (30-45 min)

**Cuándo usar Front Door en el futuro:**
- Si necesitas CDN global para contenido estático
- Si requieres WAF avanzado (ModSecurity puede ayudar en Ingress)
- Si tienes usuarios distribuidos globalmente
- Si necesitas DDoS protection a nivel de red global

Para habilitar Front Door en el futuro, simplemente cambia `frontdoor_enabled = true` en `terraform.tfvars`.

## ✅ Beneficios de esta Arquitectura

1. **✅ Sin Dependencias Circulares**: Cada capa depende solo de la anterior
2. **✅ Despliegue Incremental**: Puedes desplegar capa por capa
3. **✅ Mantenimiento Independiente**: Cambios en una capa no afectan otras
4. **✅ Escalabilidad**: Fácil agregar nuevos servicios
5. **✅ CI/CD Optimizado**: Pipelines separados por capa
6. **✅ Rollback Seguro**: Puedes hacer rollback por capa
7. **✅ Arquitectura Simplificada**: Usa LoadBalancer de Kubernetes (sin Front Door)

## 🛠️ Migración desde la Estructura Anterior

Si tienes recursos desplegados con la estructura anterior:

1. **No elimines** los recursos existentes
2. **Despliega** la nueva estructura en paralelo
3. **Migra** los datos gradualmente
4. **Elimina** la estructura anterior cuando esté todo migrado

## 📚 Documentación Adicional

- [Base Layer Documentation](./layers/base/README.md)
- [Platform Layer Documentation](./layers/platform/README.md)
- [Application Layer Documentation](./layers/application/README.md)

