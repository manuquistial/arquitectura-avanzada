# Storage module variables

variable "project_name" {
  description = "Project name"
  type        = string
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
}

variable "azure_region" {
  description = "Azure region"
  type        = string
}

variable "resource_group_name" {
  description = "Resource group name"
  type        = string
}

variable "location" {
  description = "Azure location/region"
  type        = string
  default     = ""
}

variable "domain_name" {
  description = "Domain name for CORS configuration"
  type        = string
  default     = "localhost"
}

variable "container_name" {
  description = "Blob container name"
  type        = string
  default     = "documents"
}

variable "account_tier" {
  description = "Storage account tier (Standard, Premium)"
  type        = string
  default     = "Standard"
}

variable "account_replication_type" {
  description = "Storage replication type (LRS, GRS, RA-GRS, GZRS)"
  type        = string
  default     = "LRS"
}

variable "enable_lifecycle_policy" {
  description = "Enable lifecycle management policy"
  type        = bool
  default     = true
}

variable "enable_auto_delete_unsigned" {
  description = "Enable auto-delete of UNSIGNED documents > 30d"
  type        = bool
  default     = false # CronJob handles this, lifecycle is backup
}

variable "enable_blob_versioning" {
  description = "Enable blob versioning for immutability"
  type        = bool
  default     = true
}

variable "enable_change_feed" {
  description = "Enable change feed for audit trail"
  type        = bool
  default     = false # Costs extra
}

variable "enable_public_access" {
  description = "Allow public blob access (false for security)"
  type        = bool
  default     = false
}

variable "enable_https_only" {
  description = "Force HTTPS only"
  type        = bool
  default     = true
}

variable "min_tls_version" {
  description = "Minimum TLS version"
  type        = string
  default     = "TLS1_2"
}

variable "tags" {
  description = "Tags for storage resources"
  type        = map(string)
  default     = {}
}

# Microsoft Defender for Storage Configuration
variable "enable_defender_for_storage" {
  description = "Enable Microsoft Defender for Storage"
  type        = bool
  default     = true
}

variable "defender_storage_tier" {
  description = "Defender for Storage tier (Free, Standard)"
  type        = string
  default     = "Standard"
  validation {
    condition     = contains(["Free", "Standard"], var.defender_storage_tier)
    error_message = "Defender storage tier must be Free or Standard."
  }
}

variable "enable_malware_scanning" {
  description = "Enable malware scanning on upload"
  type        = bool
  default     = true
}

variable "enable_sensitive_data_discovery" {
  description = "Enable sensitive data discovery"
  type        = bool
  default     = true
}

variable "override_subscription_settings" {
  description = "Override subscription-level settings"
  type        = bool
  default     = false
}

variable "security_contact_email" {
  description = "Security contact email for alerts"
  type        = string
  default     = ""
}

variable "security_contact_phone" {
  description = "Security contact phone for alerts"
  type        = string
  default     = ""
}

# Storage Network Security
variable "enable_storage_network_rules" {
  description = "Enable network rules for storage account"
  type        = bool
  default     = true
}

variable "allowed_ip_addresses" {
  description = "List of allowed IP addresses"
  type        = list(string)
  default     = []
}

variable "allowed_subnet_ids" {
  description = "List of allowed subnet IDs"
  type        = list(string)
  default     = []
}

# Enhanced Storage Security
variable "enable_infrastructure_encryption" {
  description = "Enable infrastructure encryption"
  type        = bool
  default     = true
}

variable "enable_cross_tenant_replication" {
  description = "Enable cross-tenant replication"
  type        = bool
  default     = false
}

variable "blob_delete_retention_days" {
  description = "Blob delete retention days"
  type        = number
  default     = 7
}

variable "change_feed_retention_days" {
  description = "Change feed retention days"
  type        = number
  default     = 7
}

# CORS Configuration
variable "cors_allowed_origins" {
  description = "CORS allowed origins"
  type        = list(string)
  default     = ["https://localhost", "http://localhost:3000"]
}

variable "cors_allowed_methods" {
  description = "CORS allowed methods"
  type        = list(string)
  default     = ["GET", "PUT", "HEAD"]
}

variable "cors_allowed_headers" {
  description = "CORS allowed headers"
  type        = list(string)
  default     = ["Content-Type", "x-ms-blob-type", "x-ms-blob-content-type"]
}

variable "cors_exposed_headers" {
  description = "CORS exposed headers"
  type        = list(string)
  default     = ["x-ms-request-id", "x-ms-version"]
}

variable "cors_max_age_in_seconds" {
  description = "CORS max age in seconds"
  type        = number
  default     = 3600
}

# Key Vault Configuration
variable "key_vault_id" {
  description = "Azure Key Vault ID for storing secrets"
  type        = string
  default     = ""
}

