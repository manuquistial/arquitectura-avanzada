terraform {
  required_version = ">= 1.6"
  
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.80"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.12"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.24"
    }
    time = {
      source  = "hashicorp/time"
      version = "~> 0.10"
    }
  }
  
  # Backend configurado en backend-config.tf
}

provider "azurerm" {
  features {
    resource_group {
      prevent_deletion_if_contains_resources = false
    }
  }
}

# Provider para Helm
# Uses kubeconfig file from environment (generated after AKS creation)
# For initial deployment, use two-stage apply (see CI/CD pipeline)
provider "helm" {
  kubernetes {
    config_path = "~/.kube/config"
  }
}

# Provider para Kubernetes  
# Uses kubeconfig file from environment (generated after AKS creation)
# For initial deployment, use two-stage apply (see CI/CD pipeline)
provider "kubernetes" {
  config_path = "~/.kube/config"
}

# Resource Group principal
resource "azurerm_resource_group" "main" {
  name     = "${var.project_name}-${var.environment}-rg"
  location = var.azure_region

  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# Virtual Network
module "vnet" {
  source = "./modules/vnet"

  environment         = var.environment
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  vnet_cidr           = var.vnet_cidr
  subnet_cidrs        = var.subnet_cidrs
}

# AKS (Kubernetes) - Advanced configuration
module "aks" {
  source = "./modules/aks"

  environment         = var.environment
  cluster_name        = "${var.project_name}-${var.environment}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  subnet_id           = module.vnet.aks_subnet_id
  
  # Kubernetes version
  kubernetes_version        = var.aks_kubernetes_version
  automatic_channel_upgrade = var.aks_automatic_upgrade
  
  # Cluster configuration
  private_cluster_enabled = var.aks_private_cluster
  sku_tier                = var.aks_sku_tier
  authorized_ip_ranges    = var.aks_authorized_ip_ranges
  admin_group_object_ids  = var.aks_admin_groups
  
  # Availability zones (multi-AZ)
  availability_zones = var.aks_availability_zones
  
  # System node pool (K8s controllers)
  system_vm_size    = var.aks_system_vm_size
  system_node_count = var.aks_system_node_count
  system_node_min   = var.aks_system_node_min
  system_node_max   = var.aks_system_node_max
  
  # User node pool (applications)
  user_vm_size  = var.aks_user_vm_size
  user_node_min = var.aks_user_node_min
  user_node_max = var.aks_user_node_max
  
  # Spot node pool (workers)
  enable_spot_nodepool = var.aks_enable_spot
  spot_vm_size         = var.aks_spot_vm_size
  spot_node_min        = var.aks_spot_node_min
  spot_node_max        = var.aks_spot_node_max
  spot_max_price       = var.aks_spot_max_price
  
  # Auto-scaling
  enable_auto_scaling = var.aks_enable_autoscaling
  
  # Network
  service_cidr   = var.aks_service_cidr
  dns_service_ip = var.aks_dns_service_ip
  outbound_type  = var.aks_outbound_type
  
  # Maintenance window
  maintenance_window_day   = var.aks_maintenance_day
  maintenance_window_hours = var.aks_maintenance_hours
  
  # Legacy (backward compatibility)
  node_count = var.aks_node_count
  vm_size    = var.aks_vm_size
}

# PostgreSQL Flexible Server
module "postgresql" {
  source = "./modules/postgresql"

  environment         = var.environment
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  subnet_id           = module.vnet.db_subnet_id
  admin_username      = var.db_admin_username
  admin_password      = var.db_admin_password
  sku_name            = var.db_sku_name
  storage_mb          = var.db_storage_mb
  
  # Firewall configuration
  aks_egress_ip        = var.db_aks_egress_ip
  allow_azure_services = var.db_allow_azure_services
  
  depends_on = [module.aks]
}

# Blob Storage
module "storage" {
  source = "./modules/storage"

  project_name        = "carpeta-ciudadana"
  environment         = var.environment
  azure_region        = var.azure_region
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  domain_name         = var.domain_name
}

# Azure Cognitive Search (equivalente a OpenSearch)
# Comentado para ahorrar costos ($75/mes)
# Usaremos Elasticsearch self-hosted en AKS
# module "search" {
#   source = "./modules/search"
#
#   environment         = var.environment
#   resource_group_name = azurerm_resource_group.main.name
#   location            = azurerm_resource_group.main.location
#   sku                 = var.search_sku
# }

# Service Bus (equivalente a SQS/SNS)
module "servicebus" {
  source = "./modules/servicebus"

  namespace_name      = "${var.environment}-carpeta-servicebus"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  
  tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# KEDA (Kubernetes Event-Driven Autoscaling)
module "keda" {
  source = "./modules/keda"

  keda_version                  = var.keda_version
  keda_namespace                = var.keda_namespace
  app_namespace                 = "${var.project_name}-${var.environment}"
  replica_count                 = var.keda_replica_count
  enable_servicebus_trigger     = true
  enable_prometheus_monitoring  = true  # Always enable for production

  depends_on = [module.aks, module.servicebus]
}

# Azure Key Vault (for secrets management)
module "keyvault" {
  source = "./modules/keyvault"

  project_name               = var.project_name
  environment                = var.environment
  location                   = azurerm_resource_group.main.location
  resource_group_name        = azurerm_resource_group.main.name
  tenant_id                  = data.azurerm_client_config.current.tenant_id
  aks_identity_principal_id  = azurerm_user_assigned_identity.aks_identity.principal_id
  
  # Secrets values
  postgres_host                 = module.postgresql.fqdn
  postgres_username             = var.db_admin_username
  postgres_password             = var.db_admin_password
  postgres_database             = "carpeta_ciudadana"
  servicebus_connection_string  = module.servicebus.primary_connection_string
  m2m_secret_key                = var.m2m_secret_key
  storage_account_name          = module.storage.storage_account_name
  redis_password                = var.redis_password
  opensearch_username           = var.opensearch_username
  opensearch_password           = var.opensearch_password
  azure_b2c_tenant_id           = var.azure_b2c_tenant_id
  azure_b2c_client_id           = var.azure_b2c_client_id
  azure_b2c_client_secret       = var.azure_b2c_client_secret
  
  # Configuration
  sku_name                      = var.keyvault_sku
  enable_public_access          = var.keyvault_enable_public_access
  purge_protection_enabled      = var.keyvault_purge_protection
  soft_delete_retention_days    = var.keyvault_soft_delete_days

  depends_on = [module.aks, module.postgresql, module.servicebus, module.storage]
}

# CSI Secrets Store Driver (for Key Vault integration)
module "csi_secrets_driver" {
  source = "./modules/csi-secrets-driver"

  namespace                = var.csi_secrets_namespace
  enable_secret_rotation   = var.csi_enable_rotation
  rotation_poll_interval   = var.csi_rotation_interval

  depends_on = [module.aks, module.keyvault]
}

# Azure AD B2C (equivalente a Cognito)
# Comentado - Requiere permisos especiales en Azure for Students
# Usaremos autenticación simple por ahora
# module "adb2c" {
#   source = "./modules/adb2c"
#
#   environment         = var.environment
#   resource_group_name = azurerm_resource_group.main.name
#   domain_name         = var.adb2c_domain_name
# }

# Container Registry (ACR - equivalente a ECR)
# Comentado para ahorrar $5/mes - Usaremos Docker Hub (gratis)
# module "acr" {
#   source = "./modules/acr"
#
#   environment         = var.environment
#   resource_group_name = azurerm_resource_group.main.name
#   location            = azurerm_resource_group.main.location
#   sku                 = var.acr_sku
# }

# Key Vault (para certificados mTLS)
# Comentado - Requiere permisos adicionales
# Usaremos certificados self-signed por ahora
# module "keyvault" {
#   source = "./modules/keyvault"
#
#   environment         = var.environment
#   resource_group_name = azurerm_resource_group.main.name
#   location            = azurerm_resource_group.main.location
#   tenant_id           = data.azurerm_client_config.current.tenant_id
# }

# Managed Identity para AKS
resource "azurerm_user_assigned_identity" "aks_identity" {
  name                = "${var.project_name}-${var.environment}-aks-identity"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
}

# Role assignments para Managed Identity
# resource "azurerm_role_assignment" "aks_to_acr" {
#   scope                = module.acr.acr_id
#   role_definition_name = "AcrPull"
#   principal_id         = azurerm_user_assigned_identity.aks_identity.principal_id
# }

# Role assignment para el cluster AKS (System Managed Identity)
# Permite a los pods del cluster generar User Delegation SAS tokens
resource "azurerm_role_assignment" "aks_cluster_to_storage" {
  scope                = module.storage.storage_account_id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = module.aks.identity_principal_id
  
  depends_on = [module.aks, module.storage]
}

# Role assignment adicional para la User Assigned Identity (si se usa)
resource "azurerm_role_assignment" "aks_identity_to_storage" {
  scope                = module.storage.storage_account_id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_user_assigned_identity.aks_identity.principal_id
}

# cert-manager deployment via Helm
module "cert_manager" {
  source = "./modules/cert-manager"

  namespace          = var.cert_manager_namespace
  chart_version      = var.cert_manager_chart_version
  letsencrypt_email  = var.letsencrypt_email
  ingress_class      = var.cert_manager_ingress_class
  cpu_request        = var.cert_manager_cpu_request
  cpu_limit          = var.cert_manager_cpu_limit
  memory_request     = var.cert_manager_memory_request
  memory_limit       = var.cert_manager_memory_limit

  depends_on = [module.aks]
}

# Observability stack (OpenTelemetry + Prometheus)
module "observability" {
  source = "./modules/observability"

  namespace                  = var.observability_namespace
  otel_chart_version         = var.otel_chart_version
  otel_replicas              = var.otel_replicas
  prometheus_chart_version   = var.prometheus_chart_version
  prometheus_retention       = var.prometheus_retention
  prometheus_storage_size    = var.prometheus_storage_size

  depends_on = [module.aks]
}

# OpenSearch deployment via Helm
module "opensearch" {
  source = "./modules/opensearch"

  namespace           = var.opensearch_namespace
  chart_version       = var.opensearch_chart_version
  storage_size        = var.opensearch_storage_size
  storage_class       = var.opensearch_storage_class
  memory_request      = var.opensearch_memory_request
  memory_limit        = var.opensearch_memory_limit
  cpu_request         = var.opensearch_cpu_request
  cpu_limit           = var.opensearch_cpu_limit
  heap_size           = var.opensearch_heap_size
  opensearch_username = var.opensearch_username
  opensearch_password = var.opensearch_password
  enable_dashboards   = var.opensearch_enable_dashboards

  depends_on = [module.aks]
}

# Data sources
data "azurerm_client_config" "current" {}

