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
  default     = false  # CronJob handles this, lifecycle is backup
}

variable "enable_blob_versioning" {
  description = "Enable blob versioning for immutability"
  type        = bool
  default     = true
}

variable "enable_change_feed" {
  description = "Enable change feed for audit trail"
  type        = bool
  default     = false  # Costs extra
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
