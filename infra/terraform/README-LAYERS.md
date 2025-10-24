# 🏗️ Arquitectura en Capas - Carpeta Ciudadana

Esta infraestructura ha sido reorganizada en **3 capas** para eliminar dependencias circulares y facilitar el mantenimiento.

## 📁 Estructura de Capas

```
infra/terraform/
├── layers/
│   ├── base/                    # 🔧 BASE LAYER
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   └── modules/
│   │       ├── networking/
│   │       └── dns/
│   ├── platform/               # 🏗️ PLATFORM LAYER
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   └── modules/
│   │       ├── aks/
│   │       ├── database/
│   │       ├── storage/
│   │       ├── cache/
│   │       └── security/
│   └── application/             # 🚀 APPLICATION LAYER
│       ├── main.tf
│       ├── variables.tf
│       ├── outputs.tf
│       └── modules/
│           ├── carpeta-ciudadana/
│           ├── monitoring/
│           └── ingress/
├── shared/                      # 🔄 SHARED RESOURCES
│   ├── variables.tf
│   ├── outputs.tf
│   └── providers.tf
└── deployments/                 # 🚀 DEPLOYMENT SCRIPTS
    ├── deploy-base.sh
    ├── deploy-platform.sh
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

## 🏗️ PLATFORM LAYER (Servicios de Plataforma)

**Recursos:**
- AKS Cluster
- PostgreSQL Database
- Azure Storage
- Redis Cache
- Key Vault
- Front Door

**Despliegue:**
```bash
cd layers/platform
cp terraform.tfvars.example terraform.tfvars
# Editar terraform.tfvars con tus valores
terraform init
terraform plan
terraform apply
```

## 🚀 APPLICATION LAYER (Aplicaciones)

**Recursos:**
- Carpeta Ciudadana App
- cert-manager
- KEDA
- External Secrets

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
./deployments/deploy-platform.sh
./deployments/deploy-application.sh
```

### Opción 2: Despliegue Manual
```bash
# 1. Base Layer
cd layers/base
terraform init && terraform apply

# 2. Platform Layer
cd ../platform
terraform init && terraform apply

# 3. Application Layer
cd ../application
terraform init && terraform apply
```

## 🔄 Flujo de Dependencias

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   BASE LAYER    │    │ PLATFORM LAYER  │    │APPLICATION LAYER│
│                 │    │                 │    │                 │
│ • Resource Group│───▶│ • AKS           │───▶│ • Apps          │
│ • VNet          │    │ • PostgreSQL    │    │ • Secrets       │
│ • DNS           │    │ • Storage       │    │ • Monitoring    │
│ • Subnets       │    │ • Redis         │    │ • Ingress       │
│                 │    │ • Key Vault     │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## ✅ Beneficios de esta Arquitectura

1. **✅ Sin Dependencias Circulares**: Cada capa depende solo de la anterior
2. **✅ Despliegue Incremental**: Puedes desplegar capa por capa
3. **✅ Mantenimiento Independiente**: Cambios en una capa no afectan otras
4. **✅ Escalabilidad**: Fácil agregar nuevos servicios
5. **✅ CI/CD Optimizado**: Pipelines separados por capa
6. **✅ Rollback Seguro**: Puedes hacer rollback por capa

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

