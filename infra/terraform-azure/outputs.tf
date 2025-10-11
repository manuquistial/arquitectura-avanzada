output "resource_group_name" {
  description = "Resource group name"
  value       = azurerm_resource_group.main.name
}

output "aks_cluster_name" {
  description = "AKS cluster name"
  value       = module.aks.cluster_name
}

output "aks_cluster_id" {
  description = "AKS cluster ID"
  value       = module.aks.cluster_id
}

output "aks_kube_config" {
  description = "AKS kubeconfig"
  value       = module.aks.kube_config
  sensitive   = true
}

output "postgresql_fqdn" {
  description = "PostgreSQL FQDN"
  value       = module.postgresql.fqdn
}

output "postgresql_admin_username" {
  description = "PostgreSQL admin username"
  value       = module.postgresql.admin_username
  sensitive   = true
}

output "storage_account_name" {
  description = "Storage account name"
  value       = module.storage.storage_account_name
}

output "storage_container_name" {
  description = "Storage container name"
  value       = module.storage.container_name
}

output "storage_primary_connection_string" {
  description = "Storage primary connection string"
  value       = module.storage.primary_connection_string
  sensitive   = true
}

output "search_endpoint" {
  description = "Azure Cognitive Search endpoint"
  value       = module.search.endpoint
}

output "search_primary_key" {
  description = "Azure Cognitive Search primary key"
  value       = module.search.primary_key
  sensitive   = true
}

output "servicebus_connection_string" {
  description = "Service Bus connection string"
  value       = module.servicebus.connection_string
  sensitive   = true
}

output "servicebus_queue_name" {
  description = "Service Bus queue name"
  value       = module.servicebus.queue_name
}

output "acr_login_server" {
  description = "ACR login server"
  value       = module.acr.login_server
}

output "acr_admin_username" {
  description = "ACR admin username"
  value       = module.acr.admin_username
  sensitive   = true
}

output "acr_admin_password" {
  description = "ACR admin password"
  value       = module.acr.admin_password
  sensitive   = true
}

output "keyvault_uri" {
  description = "Key Vault URI"
  value       = module.keyvault.vault_uri
}

output "managed_identity_client_id" {
  description = "Managed Identity Client ID"
  value       = azurerm_user_assigned_identity.aks_identity.client_id
}

