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
  value       = try(data.terraform_remote_state.security.outputs.key_vault_id, null)
}

output "key_vault_uri" {
  description = "URI of the Key Vault"
  value       = try(data.terraform_remote_state.security.outputs.key_vault_uri, null)
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

# Service Bus Outputs
output "servicebus_namespace_name" {
  description = "Service Bus namespace name"
  value       = var.servicebus_enabled ? module.servicebus[0].servicebus_namespace_name : null
}

output "servicebus_connection_string" {
  description = "Service Bus connection string"
  value       = var.servicebus_enabled ? module.servicebus[0].servicebus_connection_string : null
  sensitive   = true
}

# Security Outputs
output "keyvault_id" {
  description = "ID of the Key Vault"
  value       = var.keyvault_enabled ? try(data.terraform_remote_state.security.outputs.key_vault_id, null) : null
}

output "keyvault_name" {
  description = "Name of the Key Vault"
  value       = var.keyvault_enabled ? try(data.terraform_remote_state.security.outputs.key_vault_name, null) : null
}

# Front Door Outputs (infraestructura de red)
output "frontdoor_profile_name" {
  description = "Front Door profile name"
  value       = var.frontdoor_enabled ? module.frontdoor[0].frontdoor_profile_name : null
}

output "frontdoor_profile_id" {
  description = "Front Door profile ID"
  value       = var.frontdoor_enabled ? module.frontdoor[0].frontdoor_profile_id : null
}

output "frontdoor_endpoint_hostname" {
  description = "Front Door endpoint hostname"
  value       = var.frontdoor_enabled ? module.frontdoor[0].frontdoor_endpoint_hostname : null
}

output "frontdoor_endpoint_id" {
  description = "Front Door endpoint ID"
  value       = var.frontdoor_enabled ? module.frontdoor[0].frontdoor_endpoint_id : null
}

output "frontdoor_waf_policy_id" {
  description = "Front Door WAF policy ID"
  value       = var.frontdoor_enabled ? module.frontdoor[0].frontdoor_waf_policy_id : null
}

output "ingress_private_link_service_id" {
  description = "ID of the ingress Private Link Service"
  value       = var.private_link_service_enabled && length(azurerm_private_link_service.ingress) > 0 ? azurerm_private_link_service.ingress[0].id : null
}

output "ingress_private_link_service_alias" {
  description = "Alias of the ingress Private Link Service"
  value       = var.private_link_service_enabled && length(azurerm_private_link_service.ingress) > 0 ? azurerm_private_link_service.ingress[0].alias : null
}

# Managed Identity outputs
output "aks_managed_identity_client_id" {
  description = "Client ID of the AKS Managed Identity"
  value       = azurerm_user_assigned_identity.aks_identity.client_id
}

output "aks_kubelet_identity_principal_id" {
  description = "Principal ID of the AKS Kubelet Identity"
  value       = module.aks.kubelet_identity_object_id
}
