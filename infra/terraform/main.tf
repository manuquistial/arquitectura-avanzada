terraform {
  required_version = ">= 1.7"
  
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
    azuread = {
      source  = "hashicorp/azuread"
      version = "~> 3.0"
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
  
  # Usar OIDC (Federated Identity) para autenticación en GitHub Actions
  use_oidc = true
  
  # Subscription ID - se puede obtener automáticamente o especificar explícitamente
  subscription_id = var.azure_subscription_id
}

# Provider para Azure AD
provider "azuread" {
  use_oidc = true
}

# Provider para Helm
# Uses kubeconfig file from environment (generated after AKS creation)
# For initial deployment, use two-stage apply (see CI/CD pipeline)
provider "helm" {
  kubernetes {
    config_path = "~/.kube/config"
    config_context = "carpeta-ciudadana-production-admin"
  }
}

# Provider para Kubernetes  
# Uses kubeconfig file from environment (generated after AKS creation)
# For initial deployment, use two-stage apply (see CI/CD pipeline)
provider "kubernetes" {
  config_path = "~/.kube/config"
  config_context = "carpeta-ciudadana-production-admin"
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
  tenant_id               = data.azurerm_client_config.current.tenant_id
  
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

# PostgreSQL Flexible Server con Private Endpoint
module "postgresql" {
  source = "./modules/postgresql-flexible"

  # Environment and location
  environment         = var.environment
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  
  # Dependencies
  depends_on = [module.vnet]
  
  # Authentication
  admin_username = var.db_admin_username
  admin_password = var.db_admin_password
  
  # Database configuration
  database_name = "carpeta_ciudadana"
  
  # PostgreSQL configuration
  postgresql_version = "16"  # Updated to PostgreSQL 16
  sku_name          = var.db_sku_name
  storage_mb        = var.db_storage_mb
  
  # Network configuration - Private Endpoint
  vnet_name             = module.vnet.vnet_name
  vnet_id               = module.vnet.vnet_id
  postgresql_subnet_cidr = var.subnet_cidrs.db
  
  # Backup and availability
  backup_retention_days        = 7
  geo_redundant_backup        = false
  availability_zone           = "1"
  high_availability_mode      = "Disabled"
  
  # Security - Private Endpoint configuration
  public_network_access_enabled = false  # Disabled for private access
  allow_azure_services          = false   # Not needed with private endpoint
  allow_current_ip             = false   # Not needed with private endpoint
  current_ip_address           = "0.0.0.0"  # Not used
  aks_egress_ip               = ""       # Not needed with private endpoint
}

# Kubernetes Secrets para conexión privada - DISABLED
# module "kubernetes_secrets" {
#   source = "./modules/kubernetes-secrets"

#   # Namespace
#   namespace = "${var.project_name}-${var.environment}"

#   # PostgreSQL configuration
#   postgresql_fqdn        = module.postgresql.fqdn
#   postgresql_username    = var.db_admin_username
#   postgresql_password    = var.db_admin_password
#   postgresql_database    = "carpeta_ciudadana"

#   # Azure Storage
#   azure_storage_enabled        = true
#   azure_storage_account_name   = module.storage.storage_account_name
#   azure_storage_account_key    = module.storage.primary_access_key
#   azure_storage_container_name = "documents"

#   # Service Bus
#   servicebus_enabled           = true
#   servicebus_connection_string = module.servicebus.primary_connection_string

#   # Redis
#   redis_enabled   = var.redis_enabled
#   redis_host      = var.redis_enabled ? module.redis[0].redis_hostname : ""
#   redis_port      = var.redis_enabled ? module.redis[0].redis_port : "6380"
#   redis_password  = var.redis_enabled ? module.redis[0].redis_primary_key : ""
#   redis_ssl       = "true"

#   # Azure AD B2C
#   azure_b2c_enabled        = var.azure_b2c_enabled
#   azure_b2c_tenant_id      = var.azure_b2c_enabled ? module.azure_ad_b2c[0].b2c_tenant_id : ""
#   azure_b2c_client_id      = var.azure_b2c_enabled ? module.azure_ad_b2c[0].client_id : ""
#   azure_b2c_client_secret  = var.azure_b2c_enabled ? module.azure_ad_b2c[0].client_secret : ""

#   # M2M Authentication
#   m2m_secret_key = var.m2m_secret_key
# }

# Blob Storage
module "storage" {
  source = "./modules/storage"

  project_name        = "carpeta-ciudadana"
  environment         = var.environment
  azure_region        = var.azure_region
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  domain_name         = var.domain_name
  
  # Security Center contact
  security_contact_email = var.security_contact_email
  security_contact_phone = var.security_contact_phone
}

# Azure Cognitive Search removed - using OpenSearch instead

# Service Bus (Azure messaging)
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

# Redis for caching and rate limiting
# Habilitado para suscripción estándar
module "redis" {
  count  = var.redis_enabled ? 1 : 0
  source = "./modules/redis"

  environment         = var.environment
  location            = var.azure_region
  resource_group_name = azurerm_resource_group.main.name
  
  # Redis configuration
  capacity                    = var.redis_capacity
  family                      = var.redis_family
  sku_name                    = var.redis_sku
  enable_non_ssl_port         = var.redis_enable_non_ssl_port
  minimum_tls_version         = var.redis_minimum_tls_version
  enable_authentication       = var.redis_enable_authentication
  maxmemory_policy           = var.redis_maxmemory_policy
  enable_vnet_integration     = var.redis_enable_vnet_integration
  subnet_id                  = var.redis_enable_vnet_integration ? module.vnet.subnet_ids["aks"] : null
  private_static_ip_address  = var.redis_enable_vnet_integration ? "10.0.1.10" : null
  vnet_id                    = var.redis_enable_vnet_integration ? module.vnet.vnet_id : null
  private_endpoint_subnet_id = var.redis_enable_vnet_integration ? module.vnet.subnet_ids["aks"] : null
  enable_firewall_rules       = var.redis_enable_firewall_rules
  aks_subnet_start_ip        = var.redis_enable_firewall_rules ? "10.0.1.0" : null
  aks_subnet_end_ip          = var.redis_enable_firewall_rules ? "10.0.1.255" : null
  allow_azure_services        = var.redis_allow_azure_services
  
  depends_on = [module.aks]
}

# DNS Zone for application domain
module "dns" {
  source = "./modules/dns"

  dns_zone_name       = var.dns_zone_name
  resource_group_name = azurerm_resource_group.main.name
  app_subdomain       = var.app_subdomain
  ingress_ip          = "135.224.5.72"  # IP del ingress controller
  
  tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
  
  depends_on = [module.aks]
}

# KEDA (Kubernetes Event-Driven Autoscaling)
module "keda" {
  source = "./modules/keda"

  keda_version                  = var.keda_version
  keda_namespace                = var.keda_namespace
  app_namespace                 = "${var.project_name}-${var.environment}"
  replica_count                 = var.keda_replica_count
  enable_servicebus_trigger     = true
  enable_prometheus_monitoring  = false  # Disabled for cost optimization

  depends_on = [module.aks, module.servicebus]
}

# Azure Key Vault removed - using environment variables instead

# CSI Secrets Store Driver removed - using environment variables instead

# Azure API Management (API Gateway) - REMOVED
# APIM is overkill for this application, using Front Door instead

# Azure AD B2C (authentication)
# Habilitado con configuración optimizada para Azure for Students
module "azure_ad_b2c" {
  count  = var.azure_b2c_enabled ? 1 : 0
  source = "./modules/azure-ad-b2c"

  environment           = var.environment
  b2c_tenant_name       = var.azure_b2c_tenant_name
  redirect_uris         = var.azure_b2c_redirect_uris
  logout_redirect_uri   = var.azure_b2c_logout_redirect_uri
  user_flow_name        = var.azure_b2c_user_flow_name
  enable_implicit_flow  = var.azure_b2c_enable_implicit_flow
  enable_authorization_code_flow = var.azure_b2c_enable_authorization_code_flow
  enable_client_credentials_flow = var.azure_b2c_enable_client_credentials_flow

  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# Azure Front Door (HTTPS Gateway)
module "frontdoor" {
  count  = var.frontdoor_enabled ? 1 : 0
  source = "./modules/frontdoor"

  environment         = var.environment
  resource_group_name = azurerm_resource_group.main.name
  frontend_hostname   = var.frontdoor_frontend_hostname
  api_hostname        = var.frontdoor_api_hostname
  enable_waf          = var.frontdoor_enable_waf
  
  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
  
  depends_on = [module.aks]
}

# Azure Container Registry removed - using Docker Hub instead

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

# Observability stack removed - using Azure Monitor instead


# OpenSearch deployment
module "opensearch" {
  source = "./modules/opensearch"
  
  opensearch_username = var.opensearch_username
  opensearch_password = var.opensearch_password
  
  depends_on = [
    module.aks
  ]
}


# Carpeta Ciudadana Application (main services) - ENABLED
module "carpeta_ciudadana" {
  source = "./modules/carpeta-ciudadana"

  # Namespace configuration
  namespace         = "carpeta-ciudadana-${var.environment}"
  create_namespace  = true
  
  # Chart configuration
  chart_path    = "../../deploy/helm/carpeta-ciudadana"
  chart_version = "0.1.0"
  timeout       = 600
  
  # Global configuration
  environment         = var.environment
  image_registry      = "manuelquistial"
  image_pull_policy   = "IfNotPresent"
  log_level           = "INFO"
  
  # Workload Identity
  use_workload_identity        = true
  workload_identity_client_id  = azurerm_user_assigned_identity.aks_identity.client_id
  workload_identity_tenant_id  = data.azurerm_client_config.current.tenant_id
  
  # Feature flags
  m2m_auth_enabled     = true
  migrations_enabled   = true  # Enabled for production
  servicebus_enabled   = true  # Enabled for production
  servicebus_namespace = "${var.environment}-carpeta-servicebus"
  servicebus_connection_string = module.servicebus.primary_connection_string
  
  # Resource optimization
  resource_optimization_enabled = true
  max_replicas                  = 2
  default_cpu_request           = "100m"
  default_memory_request        = "128Mi"
  default_cpu_limit             = "300m"
  default_memory_limit          = "512Mi"
  
  # Security configuration
  cors_origins   = "http://localhost:3000,http://localhost:3001"
  hsts_enabled   = false  # Set to true for production HTTPS
  csp_enabled    = true
  csp_report_uri = ""
  
  # Database configuration - Using Private Endpoint
  database_url    = module.postgresql.connection_string_asyncpg
  postgres_uri    = module.postgresql.connection_string_uri
  m2m_secret_key  = var.m2m_secret_key
  
  # Azure configuration
  azure_storage_account_name    = module.storage.storage_account_name
  azure_storage_account_key     = module.storage.primary_access_key
  azure_storage_container_name  = "documents"
  
  # Azure B2C configuration (enabled for production)
  azure_b2c_enabled        = var.azure_b2c_enabled
  azure_b2c_tenant_name    = var.azure_b2c_enabled ? module.azure_ad_b2c[0].b2c_tenant_name : ""
  azure_b2c_tenant_id      = var.azure_b2c_enabled ? module.azure_ad_b2c[0].b2c_tenant_id : ""
  azure_b2c_client_id      = var.azure_b2c_enabled ? module.azure_ad_b2c[0].client_id : ""
  azure_b2c_client_secret  = var.azure_b2c_enabled ? module.azure_ad_b2c[0].client_secret : ""
  
  # MinTIC configuration
  mintic_hub_url      = "https://govcarpeta-apis-4905ff3c005b.herokuapp.com"
  mintic_operator_id  = "demo-operator"
  mintic_operator_name = "Demo Operator"

  depends_on = [
    module.aks,
    module.postgresql,
    module.storage,
    module.servicebus,
    module.keda,
    module.azure_ad_b2c,
    module.redis,
    module.cert_manager
  ]
}

# Data sources
data "azurerm_client_config" "current" {}

# Get current IP address for firewall rules
data "http" "current_ip" {
  url = "https://ipv4.icanhazip.com"
}

