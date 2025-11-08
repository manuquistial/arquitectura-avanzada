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

# Data source para outputs de la capa security (Key Vault)
data "terraform_remote_state" "security" {
  backend = "local"
  config = {
    path = "../security/terraform.tfstate"
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
  # Temporarily disabled depends_on to allow deployment without AKS updates
  # depends_on = [module.aks]

  # Authentication
  admin_username = var.db_admin_username
  admin_password = var.db_admin_password

  # Database configuration
  database_name = "carpeta_ciudadana"

  # PostgreSQL configuration
  postgresql_version = "16"
  sku_name           = var.db_sku_name
  storage_mb         = var.db_storage_mb

  # Network configuration - Private Endpoint
  vnet_name              = data.terraform_remote_state.base.outputs.vnet_name
  vnet_id                = data.terraform_remote_state.base.outputs.vnet_id
  postgresql_subnet_cidr = var.subnet_cidrs.db

  # Backup and availability
  backup_retention_days  = 7
  geo_redundant_backup   = false
  availability_zone      = "1"
  high_availability_mode = "Disabled"

  # Security - Private Endpoint configuration
  public_network_access_enabled = false
  allow_azure_services          = false
  allow_current_ip              = false

  # Key Vault for automatic secret management (from security layer)
  key_vault_id       = var.keyvault_enabled ? data.terraform_remote_state.security.outputs.key_vault_id : ""
  current_ip_address = "0.0.0.0"
  aks_egress_ip      = ""
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

  # Key Vault for automatic secret management (from security layer)
  key_vault_id = var.keyvault_enabled ? data.terraform_remote_state.security.outputs.key_vault_id : ""

  # Security Center contact
  security_contact_email = var.security_contact_email
  security_contact_phone = var.security_contact_phone

  # Network rules - Allow access from AKS subnet
  enable_storage_network_rules = true
  allowed_subnet_ids           = [data.terraform_remote_state.base.outputs.aks_subnet_id]
  allowed_ip_addresses         = []
}

# Redis for caching and rate limiting
module "cache" {
  count  = var.redis_enabled ? 1 : 0
  source = "./modules/cache/redis"

  environment         = var.environment
  location            = data.terraform_remote_state.base.outputs.location
  resource_group_name = data.terraform_remote_state.base.outputs.resource_group_name

  # Redis configuration
  capacity                   = var.redis_capacity
  family                     = var.redis_family
  sku_name                   = var.redis_sku
  enable_non_ssl_port        = var.redis_enable_non_ssl_port
  minimum_tls_version        = var.redis_minimum_tls_version
  enable_authentication      = var.redis_enable_authentication
  maxmemory_policy           = var.redis_maxmemory_policy
  enable_vnet_integration    = var.redis_enable_vnet_integration
  subnet_id                  = var.redis_enable_vnet_integration ? data.terraform_remote_state.base.outputs.aks_subnet_id : null
  private_static_ip_address  = var.redis_enable_vnet_integration ? "10.0.1.10" : null
  vnet_id                    = var.redis_enable_vnet_integration ? data.terraform_remote_state.base.outputs.vnet_id : null
  private_endpoint_subnet_id = var.redis_enable_vnet_integration ? data.terraform_remote_state.base.outputs.aks_subnet_id : null
  enable_firewall_rules      = var.redis_enable_firewall_rules
  aks_subnet_start_ip        = var.redis_enable_firewall_rules ? "10.0.1.0" : null
  aks_subnet_end_ip          = var.redis_enable_firewall_rules ? "10.0.1.255" : null
  allow_azure_services       = var.redis_allow_azure_services

  # Key Vault for automatic secret management (from security layer)
  key_vault_id = var.keyvault_enabled ? data.terraform_remote_state.security.outputs.key_vault_id : ""

  # Temporarily disabled depends_on to allow deployment without AKS updates
  # depends_on = [module.aks]
}

# Azure Service Bus for event-driven architecture
module "servicebus" {
  count  = var.servicebus_enabled ? 1 : 0
  source = "./modules/messaging/servicebus"

  environment         = var.environment
  location            = data.terraform_remote_state.base.outputs.location
  resource_group_name = data.terraform_remote_state.base.outputs.resource_group_name

  # Service Bus configuration
  sku                           = var.servicebus_sku
  capacity                      = var.servicebus_capacity
  public_network_access_enabled = var.servicebus_public_network_access_enabled
  minimum_tls_version           = var.servicebus_minimum_tls_version

  # Key Vault for automatic secret management (from security layer)
  key_vault_id = var.keyvault_enabled ? data.terraform_remote_state.security.outputs.key_vault_id : ""

  # Temporarily disabled depends_on to allow deployment without AKS updates
  # depends_on = [module.aks]
}

## Key Vault is now created in SECURITY layer

# Random IDs for secrets - MOVED TO APPLICATION LAYER

# Private Link Service for ingress controller
data "azurerm_lb" "ingress" {
  count               = var.private_link_service_enabled ? 1 : 0
  name                = var.private_link_load_balancer_name != "" ? var.private_link_load_balancer_name : "kubernetes"
  resource_group_name = var.private_link_load_balancer_resource_group != "" ? var.private_link_load_balancer_resource_group : module.aks.node_resource_group

  depends_on = [module.aks]
}

locals {
  private_link_frontend_configurations = var.private_link_service_enabled ? try(data.azurerm_lb.ingress[0].frontend_ip_configuration, []) : []
  private_link_frontend_ip_configuration_ids = var.private_link_service_enabled ? compact(
    var.private_link_frontend_ip_configuration_id != "" ? [
      var.private_link_frontend_ip_configuration_id
      ] : (
      var.private_link_frontend_ip_configuration_name != "" ? (
        length([
          for config in local.private_link_frontend_configurations : config.id
          if config.name == var.private_link_frontend_ip_configuration_name
        ]) > 0 ?
        [
          for config in local.private_link_frontend_configurations : config.id
          if config.name == var.private_link_frontend_ip_configuration_name
        ] :
        [try(local.private_link_frontend_configurations[0].id, "")]
        ) : [
        try(local.private_link_frontend_configurations[0].id, "")
      ]
    )
  ) : []
}

resource "azurerm_private_link_service" "ingress" {
  count               = var.private_link_service_enabled ? 1 : 0
  name                = var.private_link_service_name != "" ? var.private_link_service_name : "${var.project_name}-${var.environment}-ingress-pls"
  location            = data.terraform_remote_state.base.outputs.location
  resource_group_name = data.terraform_remote_state.base.outputs.resource_group_name

  load_balancer_frontend_ip_configuration_ids = local.private_link_frontend_ip_configuration_ids

  visibility_subscription_ids    = var.private_link_visibility_subscription_ids
  auto_approval_subscription_ids = var.private_link_auto_approval_subscription_ids
  fqdns                          = var.private_link_fqdns
  enable_proxy_protocol          = false

  nat_ip_configuration {
    name                       = "primary"
    subnet_id                  = data.terraform_remote_state.base.outputs.aks_subnet_id
    primary                    = true
    private_ip_address_version = "IPv4"
  }

  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "Terraform"
    Layer       = "Platform"
  }

  lifecycle {
    precondition {
      condition     = length(local.private_link_frontend_ip_configuration_ids) > 0
      error_message = "No se pudo determinar el frontend IP configuration del Load Balancer para el Private Link Service. Especifica private_link_frontend_ip_configuration_id o un nombre válido."
    }

    ignore_changes = [
      load_balancer_frontend_ip_configuration_ids,
      visibility_subscription_ids,
      auto_approval_subscription_ids,
      fqdns
    ]
  }
}

# Azure Front Door (HTTPS Gateway) - Infraestructura de red
# Front Door es infraestructura de red/gateway y no necesita dependencias de aplicaciones
# Se despliega en PLATFORM layer para mejor organización y despliegue más rápido
module "frontdoor" {
  count  = var.frontdoor_enabled ? 1 : 0
  source = "./modules/frontdoor"

  environment                  = var.environment
  resource_group_name          = data.terraform_remote_state.base.outputs.resource_group_name
  frontend_hostname            = var.frontdoor_frontend_hostname
  api_hostname                 = var.frontdoor_api_hostname
  enable_waf                   = var.frontdoor_enable_waf
  sku_name                     = var.frontdoor_sku_name
  private_link_enabled         = var.private_link_service_enabled
  private_link_location        = data.terraform_remote_state.base.outputs.location
  private_link_target_id       = var.private_link_service_enabled && length(azurerm_private_link_service.ingress) > 0 ? azurerm_private_link_service.ingress[0].id : ""
  private_link_request_message = var.private_link_request_message
  private_link_target_type     = var.private_link_target_type
  frontend_origin_group_name   = var.frontdoor_frontend_origin_group_name
  api_origin_group_name        = var.frontdoor_api_origin_group_name

  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "Terraform"
    Layer       = "Platform"
  }

  # Front Door solo necesita el Resource Group (de BASE layer)
  # No necesita AKS ni otras dependencias
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
