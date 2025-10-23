variable "azure_region" {
  description = "Azure region"
  type        = string
  default     = "eastus"
}

variable "azure_subscription_id" {
  description = "Azure subscription ID"
  type        = string
  default     = null  # Se puede obtener automáticamente si no se especifica
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
}

# Security Center Contact
variable "security_contact_email" {
  description = "Security Center contact email"
  type        = string
  default     = "security@carpeta-ciudadana.com"
}

variable "security_contact_phone" {
  description = "Security Center contact phone"
  type        = string
  default     = "+1-555-0123"
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "carpeta-ciudadana"
}

# VNet
variable "vnet_cidr" {
  description = "CIDR block for VNet"
  type        = string
  default     = "10.0.0.0/16"
}

variable "subnet_cidrs" {
  description = "Subnet CIDR blocks"
  type = object({
    aks = string
    db  = string
  })
  default = {
    aks = "10.0.1.0/24"
    db  = "10.0.2.0/24"
  }
}

# AKS - Advanced Configuration
variable "aks_node_count" {
  description = "DEPRECATED: Number of AKS nodes (use aks_system_node_count)"
  type        = number
  default     = 1
}

variable "aks_vm_size" {
  description = "DEPRECATED: AKS node VM size (use aks_system_vm_size)"
  type        = string
  default     = "Standard_D4s_v3"
}

# Kubernetes version
variable "aks_kubernetes_version" {
  description = "Kubernetes version"
  type        = string
  default     = "1.31.11"
}

variable "aks_automatic_upgrade" {
  description = "Automatic upgrade channel (patch, stable, rapid, node-image, none)"
  type        = string
  default     = "patch"
}

# Cluster configuration
variable "aks_private_cluster" {
  description = "Enable private cluster (API server not public)"
  type        = bool
  default     = false  # true for production
}

variable "aks_sku_tier" {
  description = "AKS SKU tier (Free, Standard)"
  type        = string
  default     = "Free"  # Standard for production (99.95% SLA)
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

# Availability zones (multi-AZ)
variable "aks_availability_zones" {
  description = "Availability zones for node pools"
  type        = list(string)
  default     = ["1", "2", "3"]
}

# System node pool (K8s controllers)
variable "aks_system_vm_size" {
  description = "VM size for system node pool"
  type        = string
  default     = "Standard_D4s_v3"  # Increased from D2s_v3 to D4s_v3 (4 vCPU, 16GB RAM)
}

variable "aks_system_node_count" {
  description = "System node count (if autoscaling disabled)"
  type        = number
  default     = 1
}

variable "aks_system_node_min" {
  description = "Minimum system nodes (autoscaling)"
  type        = number
  default     = 1
}

variable "aks_system_node_max" {
  description = "Maximum system nodes (autoscaling)"
  type        = number
  default     = 5  # Increased from 3 to 5 for better system resilience
}

# User node pool (applications)
variable "aks_user_vm_size" {
  description = "VM size for user node pool"
  type        = string
  default     = "Standard_D4s_v3"  # Increased from D2s_v3 to D4s_v3 (4 vCPU, 16GB RAM)
}

variable "aks_user_node_min" {
  description = "Minimum user nodes"
  type        = number
  default     = 3  # Increased from 2 to 3 for better availability
}

variable "aks_user_node_max" {
  description = "Maximum user nodes"
  type        = number
  default     = 20  # Increased from 10 to 20 for better scaling capacity
}

# Spot node pool (KEDA workers)
variable "aks_enable_spot" {
  description = "Enable spot node pool"
  type        = bool
  default     = true
}

variable "aks_spot_vm_size" {
  description = "VM size for spot node pool"
  type        = string
  default     = "Standard_D4s_v3"  # Increased from D2s_v3 to D4s_v3 for better performance
}

variable "aks_spot_node_min" {
  description = "Minimum spot nodes"
  type        = number
  default     = 0  # Can scale to zero for cost optimization
}

variable "aks_spot_node_max" {
  description = "Maximum spot nodes"
  type        = number
  default     = 25  # Increased from 10 to 25 for better scaling capacity
}

variable "aks_spot_max_price" {
  description = "Max price for spot instances (-1 = regular price)"
  type        = number
  default     = -1
}

# Auto-scaling
variable "aks_enable_autoscaling" {
  description = "Enable cluster autoscaler"
  type        = bool
  default     = true
}

# Network
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
  description = "Outbound type (loadBalancer, userDefinedRouting)"
  type        = string
  default     = "loadBalancer"
}

# Maintenance window
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

# PostgreSQL
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

variable "db_high_availability" {
  description = "Enable high availability for PostgreSQL"
  type        = bool
  default     = false
}

variable "db_backup_retention_days" {
  description = "PostgreSQL backup retention days"
  type        = number
  default     = 3
}

variable "db_enable_public_access" {
  description = "Enable public network access to PostgreSQL (true for dev, false for prod with private endpoint)"
  type        = bool
  default     = false  # Changed to false for private endpoint configuration
}

variable "db_aks_egress_ip" {
  description = "AKS nodepool egress IP for PostgreSQL firewall (leave empty to query dynamically)"
  type        = string
  default     = ""
}

variable "db_allow_azure_services" {
  description = "Allow Azure services to access PostgreSQL (for backups, monitoring)"
  type        = bool
  default     = false
}

# Cognitive Search
variable "search_sku" {
  description = "Azure Cognitive Search SKU"
  type        = string
  default     = "basic"
}

# Service Bus
variable "servicebus_sku" {
  description = "Service Bus SKU"
  type        = string
  default     = "Basic"
}

# Azure AD B2C
variable "adb2c_domain_name" {
  description = "Azure AD B2C domain name"
  type        = string
  default     = "carpetaciudadana"
}

# Container Registry
variable "acr_sku" {
  description = "ACR SKU"
  type        = string
  default     = "Basic"
}

# cert-manager
variable "cert_manager_namespace" {
  description = "Kubernetes namespace for cert-manager"
  type        = string
  default     = "cert-manager"
}

variable "cert_manager_chart_version" {
  description = "cert-manager Helm chart version"
  type        = string
  default     = "v1.13.3"
}

variable "letsencrypt_email" {
  description = "Email address for Let's Encrypt notifications"
  type        = string
}

variable "cert_manager_ingress_class" {
  description = "Ingress class for cert-manager HTTP-01 challenge"
  type        = string
  default     = "nginx"
}

variable "cert_manager_cpu_request" {
  description = "cert-manager CPU request"
  type        = string
  default     = "100m"
}

variable "cert_manager_cpu_limit" {
  description = "cert-manager CPU limit"
  type        = string
  default     = "200m"
}

variable "cert_manager_memory_request" {
  description = "cert-manager memory request"
  type        = string
  default     = "128Mi"
}

variable "cert_manager_memory_limit" {
  description = "cert-manager memory limit"
  type        = string
  default     = "256Mi"
}

variable "enable_tls" {
  description = "Enable TLS for Ingress (requires domain)"
  type        = bool
  default     = false
}

variable "domain_name" {
  description = "Domain name for Ingress (optional)"
  type        = string
  default     = ""
}

# Observability
variable "observability_namespace" {
  description = "Kubernetes namespace for observability stack"
  type        = string
  default     = "observability"
}

variable "otel_chart_version" {
  description = "OpenTelemetry Collector chart version"
  type        = string
  default     = "0.78.0"
}

variable "otel_replicas" {
  description = "OpenTelemetry Collector replicas"
  type        = number
  default     = 2
}

variable "prometheus_chart_version" {
  description = "Prometheus chart version"
  type        = string
  default     = "25.8.0"
}

variable "prometheus_retention" {
  description = "Prometheus data retention"
  type        = string
  default     = "15d"
}

# KEDA (Kubernetes Event-Driven Autoscaling)
variable "keda_version" {
  description = "KEDA Helm chart version"
  type        = string
  default     = "2.13.0"
}

variable "keda_namespace" {
  description = "Kubernetes namespace for KEDA"
  type        = string
  default     = "keda-system"
}

variable "keda_replica_count" {
  description = "Number of replicas for KEDA operator (HA)"
  type        = number
  default     = 2
}

# Key Vault - REMOVED (using traditional Kubernetes secrets instead)

# M2M Authentication
variable "m2m_secret_key" {
  description = "M2M authentication secret key (generate with: openssl rand -hex 32)"
  type        = string
  sensitive   = true
  default     = ""
}

# Redis
variable "redis_password" {
  description = "Redis password (optional)"
  type        = string
  sensitive   = true
  default     = ""
}

# Azure AD B2C
variable "azure_b2c_tenant_id" {
  description = "Azure AD B2C tenant ID"
  type        = string
  sensitive   = true
  default     = ""
}

variable "azure_b2c_client_id" {
  description = "Azure AD B2C client ID"
  type        = string
  sensitive   = true
  default     = ""
}

variable "azure_b2c_client_secret" {
  description = "Azure AD B2C client secret"
  type        = string
  sensitive   = true
  default     = ""
}

# CSI Secrets Store Driver - REMOVED (using traditional Kubernetes secrets instead)

variable "prometheus_storage_size" {
  description = "Prometheus storage size"
  type        = string
  default     = "10Gi"
}

# OpenSearch
variable "opensearch_namespace" {
  description = "Kubernetes namespace for OpenSearch"
  type        = string
  default     = "search"
}


# DNS Configuration
variable "dns_zone_name" {
  description = "DNS zone name (e.g., carpeta-ciudadana.dev)"
  type        = string
  default     = "carpeta-ciudadana.dev"
}

variable "app_subdomain" {
  description = "Application subdomain (e.g., app)"
  type        = string
  default     = "app"
}

# Azure AD B2C Configuration
variable "azure_b2c_tenant_name" {
  description = "Azure AD B2C tenant name (e.g., carpetaciudadana)"
  type        = string
  default     = "carpetaciudadana"
}

variable "azure_b2c_enabled" {
  description = "Enable Azure AD B2C authentication"
  type        = bool
  default     = true
}

variable "azure_b2c_redirect_uris" {
  description = "Azure AD B2C redirect URIs"
  type        = list(string)
  default = [
    "http://localhost:3000/api/auth/callback/azure-ad-b2c",
    "https://carpeta-ciudadana.com/api/auth/callback/azure-ad-b2c"
  ]
}

variable "azure_b2c_logout_redirect_uri" {
  description = "Azure AD B2C logout redirect URI"
  type        = string
  default     = "http://localhost:3000"
}

variable "azure_b2c_user_flow_name" {
  description = "Azure AD B2C user flow name"
  type        = string
  default     = "B2C_1_signupsignin"
}

variable "azure_b2c_enable_implicit_flow" {
  description = "Enable implicit flow for Azure AD B2C"
  type        = bool
  default     = true
}

variable "azure_b2c_enable_authorization_code_flow" {
  description = "Enable authorization code flow for Azure AD B2C"
  type        = bool
  default     = true
}

variable "azure_b2c_enable_client_credentials_flow" {
  description = "Enable client credentials flow for Azure AD B2C"
  type        = bool
  default     = true
}

# Azure Cognitive Search
variable "azure_search_enabled" {
  description = "Enable Azure Cognitive Search"
  type        = bool
  default     = true
}

# Azure Cache for Redis
variable "redis_enabled" {
  description = "Enable Azure Cache for Redis"
  type        = bool
  default     = true
}

variable "redis_sku" {
  description = "Redis SKU (Basic, Standard, Premium)"
  type        = string
  default     = "Standard"
  validation {
    condition     = contains(["Basic", "Standard", "Premium"], var.redis_sku)
    error_message = "Redis SKU must be Basic, Standard, or Premium."
  }
}

variable "redis_capacity" {
  description = "Redis cache capacity"
  type        = number
  default     = 1
}

variable "redis_family" {
  description = "Redis cache family (C for Basic/Standard, P for Premium)"
  type        = string
  default     = "C"
  validation {
    condition     = contains(["C", "P"], var.redis_family)
    error_message = "Redis family must be C (Basic/Standard) or P (Premium)."
  }
}


variable "redis_enable_non_ssl_port" {
  description = "Enable non-SSL port (6379)"
  type        = bool
  default     = false
}

variable "redis_minimum_tls_version" {
  description = "Minimum TLS version"
  type        = string
  default     = "1.2"
  validation {
    condition     = contains(["1.0", "1.1", "1.2"], var.redis_minimum_tls_version)
    error_message = "Minimum TLS version must be 1.0, 1.1, or 1.2."
  }
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
  validation {
    condition = contains([
      "allkeys-lru", "allkeys-random", "volatile-lru", "volatile-random",
      "volatile-ttl", "noeviction"
    ], var.redis_maxmemory_policy)
    error_message = "Invalid maxmemory policy."
  }
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

# Azure Key Vault
variable "keyvault_enabled" {
  description = "Enable Azure Key Vault"
  type        = bool
  default     = true
}

variable "keyvault_sku" {
  description = "Key Vault SKU (standard, premium)"
  type        = string
  default     = "standard"
}

variable "keyvault_enable_public_access" {
  description = "Enable public access to Key Vault"
  type        = bool
  default     = false
}

variable "keyvault_purge_protection" {
  description = "Enable purge protection for Key Vault"
  type        = bool
  default     = true
}

variable "keyvault_soft_delete_days" {
  description = "Key Vault soft delete retention days"
  type        = number
  default     = 90
}

# CSI Secrets Driver
variable "csi_secrets_enabled" {
  description = "Enable CSI Secrets Store Driver"
  type        = bool
  default     = true
}

variable "csi_secrets_namespace" {
  description = "CSI Secrets Store Driver namespace"
  type        = string
  default     = "csi-secrets-store"
}

variable "csi_enable_rotation" {
  description = "Enable secret rotation"
  type        = bool
  default     = true
}

variable "csi_rotation_interval" {
  description = "Secret rotation interval"
  type        = string
  default     = "2m"
}

# Azure Container Registry
variable "acr_enabled" {
  description = "Enable Azure Container Registry"
  type        = bool
  default     = true
}

# Observability
variable "observability_enabled" {
  description = "Enable observability stack"
  type        = bool
  default     = true
}

# Azure API Management - REMOVED (using Front Door instead)

variable "opensearch_username" {
  description = "OpenSearch admin username"
  type        = string
  default     = "admin"
}

variable "opensearch_password" {
  description = "OpenSearch admin password"
  type        = string
  default     = "admin123"
  sensitive   = true
}

# Azure Front Door variables
variable "frontdoor_enabled" {
  description = "Enable Azure Front Door for HTTPS"
  type        = bool
  default     = true
}

variable "frontdoor_frontend_hostname" {
  description = "Frontend hostname for Front Door"
  type        = string
  default     = "135.222.244.88"
}

variable "frontdoor_api_hostname" {
  description = "API hostname for Front Door"
  type        = string
  default     = "135.234.144.31"
}

variable "frontdoor_enable_waf" {
  description = "Enable Web Application Firewall on Front Door"
  type        = bool
  default     = true
}


