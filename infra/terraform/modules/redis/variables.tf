variable "environment" {
  description = "Environment name (e.g., production, development)"
  type        = string
}

variable "location" {
  description = "Azure region"
  type        = string
}

variable "resource_group_name" {
  description = "Resource group name"
  type        = string
}

# Azure Cache for Redis Configuration
variable "capacity" {
  description = "Redis cache capacity (0, 1, 2, 3, 4, 5, 6 for Basic/Standard, 1-5 for Premium)"
  type        = number
  default     = 1
}

variable "family" {
  description = "Redis cache family (C for Basic/Standard, P for Premium)"
  type        = string
  default     = "C"
  validation {
    condition     = contains(["C", "P"], var.family)
    error_message = "Family must be either C (Basic/Standard) or P (Premium)."
  }
}

variable "sku_name" {
  description = "Redis cache SKU name (Basic, Standard, Premium)"
  type        = string
  default     = "Standard"
  validation {
    condition     = contains(["Basic", "Standard", "Premium"], var.sku_name)
    error_message = "SKU name must be Basic, Standard, or Premium."
  }
}

# Security Configuration
variable "enable_non_ssl_port" {
  description = "Enable non-SSL port (6379)"
  type        = bool
  default     = false
}

variable "minimum_tls_version" {
  description = "Minimum TLS version (1.0, 1.1, 1.2)"
  type        = string
  default     = "1.2"
  validation {
    condition     = contains(["1.0", "1.1", "1.2"], var.minimum_tls_version)
    error_message = "Minimum TLS version must be 1.0, 1.1, or 1.2."
  }
}

variable "enable_authentication" {
  description = "Enable authentication"
  type        = bool
  default     = true
}

# Redis Configuration
variable "maxmemory_policy" {
  description = "Redis maxmemory policy"
  type        = string
  default     = "allkeys-lru"
  validation {
    condition = contains([
      "allkeys-lru", "allkeys-random", "volatile-lru", "volatile-random",
      "volatile-ttl", "noeviction"
    ], var.maxmemory_policy)
    error_message = "Invalid maxmemory policy."
  }
}

# VNet Integration
variable "enable_vnet_integration" {
  description = "Enable VNet integration"
  type        = bool
  default     = false
}

variable "subnet_id" {
  description = "Subnet ID for Redis cache"
  type        = string
  default     = ""
}

variable "private_static_ip_address" {
  description = "Private static IP address for Redis cache"
  type        = string
  default     = ""
}

variable "vnet_id" {
  description = "Virtual Network ID"
  type        = string
  default     = ""
}

variable "private_endpoint_subnet_id" {
  description = "Private endpoint subnet ID"
  type        = string
  default     = ""
}

# Firewall Configuration
variable "enable_firewall_rules" {
  description = "Enable firewall rules"
  type        = bool
  default     = false
}

variable "aks_subnet_start_ip" {
  description = "AKS subnet start IP for firewall rule"
  type        = string
  default     = "10.0.1.0"
}

variable "aks_subnet_end_ip" {
  description = "AKS subnet end IP for firewall rule"
  type        = string
  default     = "10.0.1.255"
}

variable "allow_azure_services" {
  description = "Allow Azure services access"
  type        = bool
  default     = false
}