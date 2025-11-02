# =============================================================================
# SECURITY LAYER OUTPUTS
# =============================================================================

output "key_vault_id" {
  description = "ID of the Key Vault"
  value       = module.keyvault.key_vault_id
}

output "key_vault_name" {
  description = "Name of the Key Vault"
  value       = module.keyvault.key_vault_name
}

output "key_vault_uri" {
  description = "URI of the Key Vault"
  value       = module.keyvault.key_vault_uri
}

output "external_secrets_identity_client_id" {
  description = "Client ID of the MI used by External Secrets"
  value       = module.keyvault.external_secrets_identity_client_id
}


