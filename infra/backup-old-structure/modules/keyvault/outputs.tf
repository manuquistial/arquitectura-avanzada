# Outputs for Azure Key Vault Module

output "key_vault_id" {
  description = "ID of the Azure Key Vault"
  value       = azurerm_key_vault.main.id
}

output "key_vault_name" {
  description = "Name of the Azure Key Vault"
  value       = azurerm_key_vault.main.name
}

output "key_vault_uri" {
  description = "URI of the Azure Key Vault"
  value       = azurerm_key_vault.main.vault_uri
}

output "external_secrets_identity_id" {
  description = "ID of the Managed Identity for External Secrets Operator"
  value       = azurerm_user_assigned_identity.external_secrets.id
}

output "external_secrets_identity_client_id" {
  description = "Client ID of the Managed Identity for External Secrets Operator"
  value       = azurerm_user_assigned_identity.external_secrets.client_id
}

output "external_secrets_identity_principal_id" {
  description = "Principal ID of the Managed Identity for External Secrets Operator"
  value       = azurerm_user_assigned_identity.external_secrets.principal_id
}

output "external_secrets_application_client_id" {
  description = "Client ID of the Azure AD Application for External Secrets Operator"
  value       = azuread_application.external_secrets.client_id
}

output "external_secrets_service_principal_object_id" {
  description = "Object ID of the Service Principal for External Secrets Operator"
  value       = azuread_service_principal.external_secrets.object_id
}
