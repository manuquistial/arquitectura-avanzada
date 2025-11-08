# =============================================================================
# PLATFORM LAYER VARIABLES
# =============================================================================
# Variables específicas para la capa de plataforma
# =============================================================================

# Importar variables compartidas
variable "azure_region" {
  description = "Azure region"
  type        = string
}

variable "azure_subscription_id" {
  description = "Azure subscription ID"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "project_name" {
  description = "Project name"
  type        = string
}

variable "domain_name" {
  description = "Domain name for Ingress"
  type        = string
}

variable "dns_zone_name" {
  description = "DNS zone name"
  type        = string
}

variable "app_subdomain" {
  description = "Application subdomain"
  type        = string
}

variable "enable_tls" {
  description = "Enable TLS for Ingress"
  type        = bool
  default     = false
}

variable "vnet_cidr" {
  description = "CIDR block for the virtual network"
  type        = string
  default     = "10.0.0.0/16"
}

variable "security_contact_email" {
  description = "Security Center contact email"
  type        = string
}

variable "security_contact_phone" {
  description = "Security Center contact phone"
  type        = string
}

variable "subnet_cidrs" {
  description = "Subnet CIDR blocks"
  type = object({
    aks = string
    db  = string
  })
}

# AKS Configuration
variable "aks_kubernetes_version" {
  description = "Kubernetes version"
  type        = string
  default     = "1.31.11"
}

variable "aks_automatic_upgrade" {
  description = "Automatic upgrade channel"
  type        = string
  default     = "patch"
}

variable "aks_private_cluster" {
  description = "Enable private cluster"
  type        = bool
  default     = false
}

variable "aks_sku_tier" {
  description = "AKS SKU tier"
  type        = string
  default     = "Free"
}

variable "aks_authorized_ip_ranges" {
  description = "Authorized IP ranges for API server"
  type        = list(string)
  default     = []
}

variable "aks_admin_groups" {
  description = "Azure AD group object IDs for cluster admins"
  type        = list(string)
  default     = []
}

variable "aks_availability_zones" {
  description = "Availability zones for node pools"
  type        = list(string)
  default     = ["1", "2", "3"]
}

variable "aks_system_vm_size" {
  description = "VM size for system node pool"
  type        = string
  default     = "Standard_B2ms"
}

variable "aks_system_node_count" {
  description = "System node count"
  type        = number
  default     = 1
}

variable "aks_system_node_min" {
  description = "Minimum system nodes"
  type        = number
  default     = 1
}

variable "aks_system_node_max" {
  description = "Maximum system nodes"
  type        = number
  default     = 5
}

variable "aks_user_vm_size" {
  description = "VM size for user node pool"
  type        = string
  default     = "Standard_B2ms"
}

variable "aks_user_node_min" {
  description = "Minimum user nodes"
  type        = number
  default     = 2
}

variable "aks_user_node_max" {
  description = "Maximum user nodes"
  type        = number
  default     = 20
}

variable "aks_enable_spot" {
  description = "Enable spot node pool"
  type        = bool
  default     = true
}

variable "aks_spot_vm_size" {
  description = "VM size for spot node pool"
  type        = string
  default     = "Standard_B2ms"
}

variable "aks_spot_node_min" {
  description = "Minimum spot nodes (increased to 1 to ensure Spot availability for metadata, notification, signature)"
  type        = number
  default     = 1 # Increased from 0 to ensure Spot nodes are always available
}

variable "aks_spot_node_max" {
  description = "Maximum spot nodes"
  type        = number
  default     = 25
}

variable "aks_spot_max_price" {
  description = "Max price for spot instances"
  type        = number
  default     = -1
}

variable "aks_enable_autoscaling" {
  description = "Enable cluster autoscaler"
  type        = bool
  default     = true
}

variable "aks_service_cidr" {
  description = "Kubernetes service CIDR"
  type        = string
  default     = "10.1.0.0/16"
}

variable "aks_dns_service_ip" {
  description = "Kubernetes DNS service IP"
  type        = string
  default     = "10.1.0.10"
}

variable "aks_outbound_type" {
  description = "Outbound type"
  type        = string
  default     = "loadBalancer"
}

variable "aks_maintenance_day" {
  description = "Maintenance window day"
  type        = string
  default     = "Sunday"
}

variable "aks_maintenance_hours" {
  description = "Maintenance window hours"
  type        = list(number)
  default     = [2, 3, 4]
}

variable "aks_node_count" {
  description = "DEPRECATED: Number of AKS nodes"
  type        = number
  default     = 1
}

variable "aks_vm_size" {
  description = "DEPRECATED: AKS node VM size"
  type        = string
  default     = "Standard_B2ms"
}

# Database Configuration
variable "db_admin_username" {
  description = "Database admin username"
  type        = string
  sensitive   = true
}

variable "db_admin_password" {
  description = "Database admin password"
  type        = string
  sensitive   = true
}

variable "db_sku_name" {
  description = "PostgreSQL SKU"
  type        = string
  default     = "B_Standard_B1ms"
}

variable "db_storage_mb" {
  description = "PostgreSQL storage in MB"
  type        = number
  default     = 32768
}

# Redis Configuration
variable "redis_enabled" {
  description = "Enable Azure Cache for Redis"
  type        = bool
  default     = true
}

variable "redis_sku" {
  description = "Redis SKU"
  type        = string
  default     = "Standard"
}

variable "redis_capacity" {
  description = "Redis cache capacity"
  type        = number
  default     = 1
}

variable "redis_family" {
  description = "Redis cache family"
  type        = string
  default     = "C"
}

variable "redis_enable_non_ssl_port" {
  description = "Enable non-SSL port"
  type        = bool
  default     = false
}

variable "redis_minimum_tls_version" {
  description = "Minimum TLS version"
  type        = string
  default     = "1.2"
}

variable "redis_enable_authentication" {
  description = "Enable authentication"
  type        = bool
  default     = true
}

variable "redis_maxmemory_policy" {
  description = "Redis maxmemory policy"
  type        = string
  default     = "allkeys-lru"
}

variable "redis_enable_vnet_integration" {
  description = "Enable VNet integration"
  type        = bool
  default     = true
}

variable "redis_enable_firewall_rules" {
  description = "Enable firewall rules"
  type        = bool
  default     = true
}

variable "redis_allow_azure_services" {
  description = "Allow Azure services access"
  type        = bool
  default     = false
}

# Service Bus Configuration
variable "servicebus_enabled" {
  description = "Enable Azure Service Bus"
  type        = bool
  default     = true
}

variable "servicebus_sku" {
  description = "Service Bus SKU (Basic or Standard)"
  type        = string
  default     = "Standard"
}

variable "servicebus_capacity" {
  description = "Service Bus capacity (only for Standard SKU)"
  type        = number
  default     = 0
}

variable "servicebus_public_network_access_enabled" {
  description = "Enable public network access for Service Bus"
  type        = bool
  default     = true
}

variable "servicebus_minimum_tls_version" {
  description = "Minimum TLS version for Service Bus"
  type        = string
  default     = "1.2"
}

# Key Vault Configuration
variable "keyvault_enabled" {
  description = "Enable Azure Key Vault"
  type        = bool
  default     = true
}

variable "keyvault_name" {
  description = "Name of the Azure Key Vault"
  type        = string
  default     = "carpeta-ciudadana-kv-v2"
}

variable "keyvault_sku_name" {
  description = "SKU name for the Key Vault"
  type        = string
  default     = "standard"
}

variable "keyvault_purge_protection_enabled" {
  description = "Enable purge protection for the Key Vault"
  type        = bool
  default     = true
}

variable "keyvault_soft_delete_retention_days" {
  description = "Number of days to retain soft deleted items"
  type        = number
  default     = 90
}

variable "keyvault_network_acls_default_action" {
  description = "Default action for network ACLs"
  type        = string
  default     = "Deny"
}

variable "keyvault_network_acls_bypass" {
  description = "Bypass for network ACLs"
  type        = string
  default     = "AzureServices"
}

variable "keyvault_allowed_ip_rules" {
  description = "List of IP addresses/ranges allowed to access the Key Vault"
  type        = list(string)
  default     = []
}

variable "keyvault_initial_secrets" {
  description = "Initial secrets to create in the Key Vault"
  type        = map(string)
  default     = {}
}

# External Secrets variables moved to EXTERNAL-SECRETS LAYER

# Front Door Configuration (infraestructura de red)
# DESHABILITADO POR DEFECTO - El proyecto usa LoadBalancer de Kubernetes + Ingress
variable "frontdoor_enabled" {
  description = "Enable Azure Front Door (disabled by default - uses Kubernetes LoadBalancer + Ingress)"
  type        = bool
  default     = false
}

variable "frontdoor_frontend_hostname" {
  description = "Hostname for the frontend service (IP or FQDN)"
  type        = string
  default     = ""
}

variable "frontdoor_api_hostname" {
  description = "Hostname for the API gateway service (IP or FQDN)"
  type        = string
  default     = ""
}

variable "frontdoor_enable_waf" {
  description = "Enable Web Application Firewall (WAF) for Front Door (only if frontdoor_enabled = true)"
  type        = bool
  default     = false
}

variable "frontdoor_frontend_origin_group_name" {
  description = "Optional name for the Front Door origin group used by the frontend origin"
  type        = string
  default     = ""
}

variable "frontdoor_api_origin_group_name" {
  description = "Optional name for the Front Door origin group used by the API origin"
  type        = string
  default     = ""
}

variable "frontdoor_sku_name" {
  description = "Azure Front Door SKU (Standard_AzureFrontDoor or Premium_AzureFrontDoor)"
  type        = string
  default     = "Premium_AzureFrontDoor"
}

# Private Link Service configuration
variable "private_link_service_enabled" {
  description = "Enable Azure Private Link Service for the ingress controller"
  type        = bool
  default     = false
}

variable "private_link_service_name" {
  description = "Name for the Private Link Service (defaults to <project>-<env>-ingress-pls)"
  type        = string
  default     = ""
}

variable "private_link_load_balancer_name" {
  description = "Name of the Load Balancer exposing the ingress controller"
  type        = string
  default     = ""
}

variable "private_link_load_balancer_resource_group" {
  description = "Resource group of the ingress Load Balancer (defaults to AKS node resource group)"
  type        = string
  default     = ""
}

variable "private_link_frontend_ip_configuration_name" {
  description = "Frontend IP configuration name in the ingress Load Balancer"
  type        = string
  default     = "kubernetes"
}

variable "private_link_frontend_ip_configuration_id" {
  description = "Explicit frontend IP configuration ID in the ingress Load Balancer"
  type        = string
  default     = ""
}

variable "private_link_visibility_subscription_ids" {
  description = "Subscription IDs that can request the Private Link Service"
  type        = list(string)
  default     = []
}

variable "private_link_auto_approval_subscription_ids" {
  description = "Subscription IDs auto-approved for Private Link connections"
  type        = list(string)
  default     = []
}

variable "private_link_fqdns" {
  description = "Optional FQDNs advertised by the Private Link Service"
  type        = list(string)
  default     = []
}

variable "private_link_request_message" {
  description = "Optional message displayed when approving Private Link connections"
  type        = string
  default     = "Azure Front Door access request"
}

variable "private_link_target_type" {
  description = "Private Link target type (e.g., sites, web, blob, Gateway)"
  type        = string
  default     = "sites"
}
