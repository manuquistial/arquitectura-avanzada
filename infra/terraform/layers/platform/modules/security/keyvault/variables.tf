# Variables for Azure Key Vault Module

variable "keyvault_name" {
  description = "Name of the Azure Key Vault"
  type        = string
  default     = "carpeta-ciudadana-kv-v2"
}

variable "location" {
  description = "Azure region for the Key Vault"
  type        = string
}

variable "resource_group_name" {
  description = "Name of the resource group"
  type        = string
}

variable "environment" {
  description = "Environment name (dev, staging, production)"
  type        = string
}

variable "sku_name" {
  description = "SKU name for the Key Vault"
  type        = string
  default     = "standard"
  validation {
    condition     = contains(["standard", "premium"], var.sku_name)
    error_message = "SKU name must be either 'standard' or 'premium'."
  }
}

variable "purge_protection_enabled" {
  description = "Enable purge protection for the Key Vault"
  type        = bool
  default     = true
}

variable "soft_delete_retention_days" {
  description = "Number of days to retain soft deleted items"
  type        = number
  default     = 90
  validation {
    condition     = var.soft_delete_retention_days >= 7 && var.soft_delete_retention_days <= 90
    error_message = "Soft delete retention days must be between 7 and 90."
  }
}

variable "network_acls_default_action" {
  description = "Default action for network ACLs"
  type        = string
  default     = "Deny"
  validation {
    condition     = contains(["Allow", "Deny"], var.network_acls_default_action)
    error_message = "Network ACLs default action must be either 'Allow' or 'Deny'."
  }
}

variable "network_acls_bypass" {
  description = "Bypass for network ACLs"
  type        = string
  default     = "AzureServices"
  validation {
    condition     = contains(["None", "AzureServices"], var.network_acls_bypass)
    error_message = "Network ACLs bypass must be either 'None' or 'AzureServices'."
  }
}

variable "allowed_subnet_ids" {
  description = "List of subnet IDs allowed to access the Key Vault"
  type        = list(string)
  default     = []
}

variable "allowed_ip_rules" {
  description = "List of IP addresses/ranges allowed to access the Key Vault"
  type        = list(string)
  default     = []
}

variable "aks_managed_identity_principal_id" {
  description = "Principal ID of the AKS Managed Identity"
  type        = string
  default     = ""
}

variable "aks_oidc_issuer_url" {
  description = "OIDC issuer URL of the AKS cluster"
  type        = string
  default     = null
}

variable "external_secrets_namespace" {
  description = "Namespace where External Secrets Operator is deployed"
  type        = string
  default     = "external-secrets-system"
}

variable "initial_secrets" {
  description = "Initial secrets to create in the Key Vault"
  type        = map(string)
  default     = {}
}
