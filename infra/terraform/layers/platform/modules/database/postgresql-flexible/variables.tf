variable "environment" {
  description = "Environment name"
  type        = string
}

variable "resource_group_name" {
  description = "Resource group name"
  type        = string
}

variable "location" {
  description = "Azure location"
  type        = string
}

variable "admin_username" {
  description = "PostgreSQL admin username"
  type        = string
  sensitive   = true
  validation {
    condition     = length(var.admin_username) >= 1 && !can(regex("[:@/\\s]", var.admin_username))
    error_message = "admin_username no debe estar vacío ni contener ':', '@', '/', espacios u otros caracteres no válidos para URI."
  }
}

variable "admin_password" {
  description = "PostgreSQL admin password"
  type        = string
  sensitive   = true
}

variable "postgresql_version" {
  description = "PostgreSQL version"
  type        = string
  default     = "16"
  validation {
    # Flexible Server hoy soporta 12-16; 11 está EOL
    condition     = contains(["12", "13", "14", "15", "16"], var.postgresql_version)
    error_message = "PostgreSQL version must be one of: 12, 13, 14, 15, 16."
  }
}

variable "sku_name" {
  description = "PostgreSQL SKU name (e.g., B_Standard_B1ms, GP_Standard_D2s_v5, MO_Standard_E2s_v5)"
  type        = string
  default     = "GP_Standard_D2s_v5"
  validation {
    # Patrones válidos por familia: Burstable (B), General Purpose (GP), Memory Optimized (MO)
    condition = can(regex("^(B_Standard_B\\w+|GP_Standard_D\\w+|MO_Standard_E\\w+)$", var.sku_name))
    error_message = "SKU must look like: B_Standard_B*, GP_Standard_D*, or MO_Standard_E* (e.g., GP_Standard_D2s_v5)."
  }
}

variable "storage_mb" {
  description = "Storage size in MB"
  type        = number
  default     = 32768
  validation {
    condition     = var.storage_mb >= 32768 && var.storage_mb <= 16777216
    error_message = "Storage size must be between 32GB (32768 MB) and 16TB (16777216 MB)."
  }
}

variable "database_name" {
  description = "Database name to create"
  type        = string
  default     = "carpeta_ciudadana"
  validation {
    condition     = length(var.database_name) > 0 && can(regex("^[A-Za-z0-9_]+$", var.database_name))
    error_message = "Database name must be non-empty and only contain letters, numbers, and underscores."
  }
}

variable "database_charset" {
  description = "Database charset"
  type        = string
  default     = "UTF8"
  validation {
    condition     = var.database_charset == "UTF8"
    error_message = "Flexible Server usually supports UTF8; use UTF8."
  }
}

variable "database_collation" {
  description = "Database collation"
  type        = string
  default     = "en_US.utf8"
  validation {
    condition     = can(regex("^[A-Za-z_\\.0-9]+$", var.database_collation))
    error_message = "Collation must be a valid locale string like en_US.utf8."
  }
}

variable "backup_retention_days" {
  description = "Backup retention in days"
  type        = number
  default     = 7
  validation {
    condition     = var.backup_retention_days >= 7 && var.backup_retention_days <= 35
    error_message = "Backup retention must be between 7 and 35 days."
  }
}

variable "geo_redundant_backup" {
  description = "Enable geo-redundant backup"
  type        = bool
  default     = false
}

variable "high_availability_mode" {
  description = "High availability mode"
  type        = string
  default     = "Disabled"
  validation {
    condition     = contains(["Disabled", "SameZone", "ZoneRedundant"], var.high_availability_mode)
    error_message = "High availability mode must be one of: Disabled, SameZone, ZoneRedundant."
  }
  # Bloquea HA con SKU Burstable
  validation {
    condition     = !(var.high_availability_mode != "Disabled" && can(regex("^B_", var.sku_name)))
    error_message = "High Availability is not supported with Burstable SKUs (B_*). Use GP_* or MO_*."
  }
}

variable "public_network_access_enabled" {
  description = "Enable public network access"
  type        = bool
  default     = true
}

variable "allow_azure_services" {
  description = "Allow Azure services to access the server (0.0.0.0 rule)"
  type        = bool
  default     = false
  # Evita que intenten abrir firewall si PNA está deshabilitado
  validation {
    condition     = !(var.allow_azure_services && !var.public_network_access_enabled)
    error_message = "allow_azure_services requires public_network_access_enabled = true."
  }
}

variable "aks_egress_ip" {
  description = "AKS egress IP address for firewall rule"
  type        = string
  default     = ""
  # Valida formato IPv4 cuando viene poblado y que PNA esté activo
  validation {
    condition = (
      var.aks_egress_ip == "" ||
      (can(regex("^([0-9]{1,3}\\.){3}[0-9]{1,3}$", var.aks_egress_ip)) && var.public_network_access_enabled)
    )
    error_message = "aks_egress_ip must be a valid IPv4 and requires public_network_access_enabled = true."
  }
}

variable "allow_current_ip" {
  description = "Allow current IP address for management"
  type        = bool
  default     = true
  validation {
    condition     = !(var.allow_current_ip && !var.public_network_access_enabled)
    error_message = "allow_current_ip requires public_network_access_enabled = true."
  }
}

variable "current_ip_address" {
  description = "Current IP address for firewall rule"
  type        = string
  default     = "0.0.0.0"
  validation {
    condition     = can(regex("^([0-9]{1,3}\\.){3}[0-9]{1,3}$", var.current_ip_address))
    error_message = "current_ip_address must be a valid IPv4 address."
  }
}

variable "maintenance_day" {
  description = "Maintenance window day (0=Sunday, 1=Monday, etc.)"
  type        = number
  default     = 0
  validation {
    condition     = var.maintenance_day >= 0 && var.maintenance_day <= 6
    error_message = "Maintenance day must be between 0 (Sunday) and 6 (Saturday)."
  }
}

variable "maintenance_start_hour" {
  description = "Maintenance window start hour (0-23)"
  type        = number
  default     = 2
  validation {
    condition     = var.maintenance_start_hour >= 0 && var.maintenance_start_hour <= 23
    error_message = "Maintenance start hour must be between 0 and 23."
  }
}

variable "maintenance_start_minute" {
  description = "Maintenance window start minute (0-59)"
  type        = number
  default     = 0
  validation {
    condition     = var.maintenance_start_minute >= 0 && var.maintenance_start_minute <= 59
    error_message = "Maintenance start minute must be between 0 and 59."
  }
}

# VNet Integration Variables
variable "vnet_name" {
  description = "Name of the virtual network"
  type        = string
}

variable "vnet_id" {
  description = "ID of the virtual network"
  type        = string
}

variable "postgresql_subnet_cidr" {
  description = "CIDR block for PostgreSQL subnet"
  type        = string
  default     = "10.0.3.0/24"
}

variable "availability_zone" {
  description = "Availability zone for PostgreSQL server"
  type        = string
  default     = "1"
}
