/**
 * Key Vault Module Variables
 */

variable "project_name" {
  description = "Project name"
  type        = string
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
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

variable "tenant_id" {
  description = "Azure AD tenant ID"
  type        = string
}

variable "aks_identity_principal_id" {
  description = "AKS Managed Identity principal ID (for RBAC)"
  type        = string
}

# Key Vault Configuration
variable "sku_name" {
  description = "Key Vault SKU (standard or premium)"
  type        = string
  default     = "standard"
}

variable "soft_delete_retention_days" {
  description = "Soft delete retention in days (7-90)"
  type        = number
  default     = 7
}

variable "purge_protection_enabled" {
  description = "Enable purge protection (prevents permanent deletion)"
  type        = bool
  default     = false  # true for production
}

variable "enable_public_access" {
  description = "Enable public network access"
  type        = bool
  default     = true  # false for production with private endpoint
}

variable "allowed_ip_ranges" {
  description = "List of allowed IP ranges"
  type        = list(string)
  default     = []
}

variable "allowed_subnet_ids" {
  description = "List of allowed subnet IDs"
  type        = list(string)
  default     = []
}

variable "enable_rbac" {
  description = "Use RBAC for authorization (recommended)"
  type        = bool
  default     = true
}

variable "enable_certificate_access" {
  description = "Grant certificate access to AKS identity"
  type        = bool
  default     = false
}

# Secrets Values
variable "postgres_host" {
  description = "PostgreSQL host"
  type        = string
}

variable "postgres_username" {
  description = "PostgreSQL username"
  type        = string
  sensitive   = true
}

variable "postgres_password" {
  description = "PostgreSQL password"
  type        = string
  sensitive   = true
}

variable "postgres_database" {
  description = "PostgreSQL database name"
  type        = string
  default     = "carpeta_ciudadana"
}

variable "servicebus_connection_string" {
  description = "Service Bus connection string"
  type        = string
  sensitive   = true
}

variable "m2m_secret_key" {
  description = "M2M authentication secret key"
  type        = string
  sensitive   = true
}

variable "storage_account_name" {
  description = "Azure Storage account name"
  type        = string
}

variable "redis_password" {
  description = "Redis password (optional)"
  type        = string
  default     = ""
  sensitive   = true
}

variable "opensearch_username" {
  description = "OpenSearch username"
  type        = string
  default     = "admin"
}

variable "opensearch_password" {
  description = "OpenSearch password"
  type        = string
  sensitive   = true
}

variable "azure_b2c_tenant_id" {
  description = "Azure AD B2C tenant ID"
  type        = string
  default     = ""
  sensitive   = true
}

variable "azure_b2c_client_id" {
  description = "Azure AD B2C client ID"
  type        = string
  default     = ""
  sensitive   = true
}

variable "azure_b2c_client_secret" {
  description = "Azure AD B2C client secret"
  type        = string
  default     = ""
  sensitive   = true
}

# Diagnostics
variable "enable_diagnostics" {
  description = "Enable diagnostic settings"
  type        = bool
  default     = false
}

variable "log_analytics_workspace_id" {
  description = "Log Analytics workspace ID for diagnostics"
  type        = string
  default     = ""
}

