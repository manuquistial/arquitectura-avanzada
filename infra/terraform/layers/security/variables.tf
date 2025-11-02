# =============================================================================
# SECURITY LAYER VARIABLES
# =============================================================================

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
  default     = "carpeta-ciudadana"
}

# Key Vault configuration
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


