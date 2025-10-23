# =============================================================================
# PLATFORM LAYER OUTPUTS
# =============================================================================
# Outputs que serán consumidos por la capa de aplicación
# =============================================================================

# Resource Group Outputs
output "resource_group_name" {
  description = "Name of the resource group"
  value       = data.terraform_remote_state.base.outputs.resource_group_name
}

# AKS Outputs
output "aks_cluster_name" {
  description = "Name of the AKS cluster"
  value       = module.aks.cluster_name
}

output "aks_cluster_id" {
  description = "ID of the AKS cluster"
  value       = module.aks.cluster_id
}

output "aks_kubeconfig" {
  description = "Kubeconfig for the AKS cluster"
  value       = module.aks.kube_config
  sensitive   = true
}

output "aks_managed_identity_principal_id" {
  description = "Principal ID of the AKS Managed Identity"
  value       = module.aks.managed_identity_principal_id
}

output "aks_oidc_issuer_url" {
  description = "OIDC issuer URL of the AKS cluster"
  value       = module.aks.oidc_issuer_url
}

# Key Vault Outputs
output "key_vault_id" {
  description = "ID of the Key Vault"
  value       = module.security[0].key_vault_id
}

output "key_vault_uri" {
  description = "URI of the Key Vault"
  value       = module.security[0].key_vault_uri
}

# Database Outputs
output "database_connection_string" {
  description = "PostgreSQL connection string"
  value       = module.database.connection_string_uri
  sensitive   = true
}

output "database_fqdn" {
  description = "PostgreSQL FQDN"
  value       = module.database.fqdn
}

output "database_name" {
  description = "Database name"
  value       = "carpeta_ciudadana"
}

# Storage Outputs
output "storage_account_name" {
  description = "Azure Storage account name"
  value       = module.storage.storage_account_name
}

output "storage_account_key" {
  description = "Azure Storage account key"
  value       = module.storage.primary_access_key
  sensitive   = true
}

output "storage_container_name" {
  description = "Azure Storage container name"
  value       = "documents"
}

# Cache Outputs
output "redis_hostname" {
  description = "Redis hostname"
  value       = var.redis_enabled ? module.cache[0].redis_hostname : null
}

output "redis_port" {
  description = "Redis port"
  value       = var.redis_enabled ? "6380" : null
}

output "redis_primary_key" {
  description = "Redis primary key"
  value       = var.redis_enabled ? module.cache[0].redis_primary_key : null
  sensitive   = true
}

# Security Outputs
output "keyvault_id" {
  description = "ID of the Key Vault"
  value       = var.keyvault_enabled ? module.security[0].key_vault_id : null
}

output "keyvault_name" {
  description = "Name of the Key Vault"
  value       = var.keyvault_enabled ? module.security[0].key_vault_name : null
}

# Front Door Outputs
# Front Door outputs moved to APPLICATION LAYER

# Managed Identity outputs
output "aks_managed_identity_client_id" {
  description = "Client ID of the AKS Managed Identity"
  value       = azurerm_user_assigned_identity.aks_identity.client_id
}
