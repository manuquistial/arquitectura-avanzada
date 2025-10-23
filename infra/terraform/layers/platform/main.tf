# =============================================================================
# PLATFORM LAYER - SERVICIOS DE PLATAFORMA
# =============================================================================
# Esta capa contiene los servicios de plataforma necesarios para las aplicaciones:
# - AKS Cluster
# - PostgreSQL Database
# - Azure Storage
# - Redis Cache
# - Key Vault
# - Front Door
# =============================================================================

# Data source para obtener outputs de la capa base
data "terraform_remote_state" "base" {
  backend = "local"
  config = {
    path = "../base/terraform.tfstate"
  }
}

# Data source para obtener información del tenant
data "azurerm_client_config" "current" {}

# AKS (Kubernetes) - Advanced configuration
module "aks" {
  source = "./modules/aks/aks"

  environment         = var.environment
  cluster_name        = "${var.project_name}-${var.environment}"
  resource_group_name = data.terraform_remote_state.base.outputs.resource_group_name
  location            = data.terraform_remote_state.base.outputs.location
  subnet_id           = data.terraform_remote_state.base.outputs.aks_subnet_id
  
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
module "database" {
  source = "./modules/database/postgresql-flexible"

  # Environment and location
  environment         = var.environment
  resource_group_name = data.terraform_remote_state.base.outputs.resource_group_name
  location            = data.terraform_remote_state.base.outputs.location
  
  # Dependencies
  depends_on = [module.aks]
  
  # Authentication
  admin_username = var.db_admin_username
  admin_password = var.db_admin_password
  
  # Database configuration
  database_name = "carpeta_ciudadana"
  
  # PostgreSQL configuration
  postgresql_version = "16"
  sku_name          = var.db_sku_name
  storage_mb        = var.db_storage_mb
  
  # Network configuration - Private Endpoint
  vnet_name             = data.terraform_remote_state.base.outputs.vnet_name
  vnet_id               = data.terraform_remote_state.base.outputs.vnet_id
  postgresql_subnet_cidr = var.subnet_cidrs.db
  
  # Backup and availability
  backup_retention_days        = 7
  geo_redundant_backup        = false
  availability_zone           = "1"
  high_availability_mode      = "Disabled"
  
  # Security - Private Endpoint configuration
  public_network_access_enabled = false
  allow_azure_services          = false
  allow_current_ip             = false
  current_ip_address           = "0.0.0.0"
  aks_egress_ip               = ""
}

# Azure Storage
module "storage" {
  source = "./modules/storage/storage"

  project_name        = var.project_name
  environment         = var.environment
  azure_region        = data.terraform_remote_state.base.outputs.location
  resource_group_name = data.terraform_remote_state.base.outputs.resource_group_name
  location            = data.terraform_remote_state.base.outputs.location
  domain_name         = var.domain_name
  
  # Security Center contact
  security_contact_email = var.security_contact_email
  security_contact_phone = var.security_contact_phone
}

# Redis for caching and rate limiting
module "cache" {
  count  = var.redis_enabled ? 1 : 0
  source = "./modules/cache/redis"

  environment         = var.environment
  location            = data.terraform_remote_state.base.outputs.location
  resource_group_name = data.terraform_remote_state.base.outputs.resource_group_name
  
  # Redis configuration
  capacity                    = var.redis_capacity
  family                      = var.redis_family
  sku_name                    = var.redis_sku
  enable_non_ssl_port         = var.redis_enable_non_ssl_port
  minimum_tls_version         = var.redis_minimum_tls_version
  enable_authentication       = var.redis_enable_authentication
  maxmemory_policy           = var.redis_maxmemory_policy
  enable_vnet_integration     = var.redis_enable_vnet_integration
  subnet_id                  = var.redis_enable_vnet_integration ? data.terraform_remote_state.base.outputs.aks_subnet_id : null
  private_static_ip_address  = var.redis_enable_vnet_integration ? "10.0.1.10" : null
  vnet_id                    = var.redis_enable_vnet_integration ? data.terraform_remote_state.base.outputs.vnet_id : null
  private_endpoint_subnet_id = var.redis_enable_vnet_integration ? data.terraform_remote_state.base.outputs.aks_subnet_id : null
  enable_firewall_rules       = var.redis_enable_firewall_rules
  aks_subnet_start_ip        = var.redis_enable_firewall_rules ? "10.0.1.0" : null
  aks_subnet_end_ip          = var.redis_enable_firewall_rules ? "10.0.1.255" : null
  allow_azure_services        = var.redis_allow_azure_services
  
  depends_on = [module.aks]
}

# Azure Key Vault para gestión centralizada de secrets
module "security" {
  count  = var.keyvault_enabled ? 1 : 0
  source = "./modules/security/keyvault"

  keyvault_name                        = var.keyvault_name
  location                            = data.terraform_remote_state.base.outputs.location
  resource_group_name                 = data.terraform_remote_state.base.outputs.resource_group_name
  environment                         = var.environment
  sku_name                           = var.keyvault_sku_name
  purge_protection_enabled           = var.keyvault_purge_protection_enabled
  soft_delete_retention_days         = var.keyvault_soft_delete_retention_days
  network_acls_default_action        = var.keyvault_network_acls_default_action
  network_acls_bypass                = var.keyvault_network_acls_bypass
  allowed_subnet_ids                 = [data.terraform_remote_state.base.outputs.aks_subnet_id]
  allowed_ip_rules                   = var.keyvault_allowed_ip_rules
  aks_managed_identity_principal_id  = module.aks.managed_identity_principal_id
  aks_oidc_issuer_url               = module.aks.oidc_issuer_url
  external_secrets_namespace        = var.external_secrets_namespace
  initial_secrets                   = var.keyvault_initial_secrets

  depends_on = [data.terraform_remote_state.base, module.aks]
}

# Azure Front Door (HTTPS Gateway)
module "frontdoor" {
  count  = var.frontdoor_enabled ? 1 : 0
  source = "./modules/frontdoor"

  environment         = var.environment
  resource_group_name = data.terraform_remote_state.base.outputs.resource_group_name
  frontend_hostname   = var.frontdoor_frontend_hostname
  api_hostname        = var.frontdoor_api_hostname
  enable_waf          = var.frontdoor_enable_waf
  
  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "Terraform"
    Layer       = "Platform"
  }
  
  depends_on = [module.aks]
}

# Managed Identity para AKS
resource "azurerm_user_assigned_identity" "aks_identity" {
  name                = "${var.project_name}-${var.environment}-aks-identity"
  resource_group_name = data.terraform_remote_state.base.outputs.resource_group_name
  location            = data.terraform_remote_state.base.outputs.location
}

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
