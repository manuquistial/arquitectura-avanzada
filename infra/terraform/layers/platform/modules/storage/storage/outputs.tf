output "storage_account_name" {
  description = "Storage account name"
  value       = azurerm_storage_account.main.name
}

output "storage_account_id" {
  description = "Storage account ID"
  value       = azurerm_storage_account.main.id
}

output "container_name" {
  description = "Container name"
  value       = azurerm_storage_container.documents.name
}

output "primary_connection_string" {
  description = "Primary connection string"
  value       = azurerm_storage_account.main.primary_connection_string
  sensitive   = true
}

output "primary_access_key" {
  description = "Primary access key"
  value       = azurerm_storage_account.main.primary_access_key
  sensitive   = true
}

output "primary_blob_endpoint" {
  description = "Primary blob endpoint"
  value       = azurerm_storage_account.main.primary_blob_endpoint
}

# Microsoft Defender for Storage outputs
output "defender_for_storage_enabled" {
  description = "Whether Microsoft Defender for Storage is enabled"
  value       = var.enable_defender_for_storage
}

output "storage_defender_id" {
  description = "Microsoft Defender for Storage ID"
  value       = var.enable_defender_for_storage ? azurerm_security_center_storage_defender.main[0].id : null
}

output "security_center_pricing_tier" {
  description = "Security Center pricing tier for Storage"
  value       = "Standard"  # Configured manually via Azure CLI
}

output "storage_network_rules_enabled" {
  description = "Whether storage network rules are enabled"
  value       = var.enable_storage_network_rules
}

output "storage_network_rules_id" {
  description = "Storage account network rules ID"
  value       = var.enable_storage_network_rules ? azurerm_storage_account_network_rules.main[0].id : null
}

output "security_center_contact_id" {
  description = "Security Center contact ID"
  value       = "/subscriptions/635ab07e-b29c-417e-b2b2-008bc4fc57d6/providers/Microsoft.Security/securityContacts/default"
}

output "security_center_contact_email" {
  description = "Security Center contact email"
  value       = "security@cuentas.gob.co"
}

