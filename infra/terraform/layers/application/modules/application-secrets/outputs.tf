# =============================================================================
# APPLICATION SECRETS MODULE OUTPUTS
# =============================================================================

output "m2m_auth_secret_id" {
  description = "ID of the M2M authentication secret"
  value       = azurerm_key_vault_secret.m2m_auth.id
}

output "jwt_secret_id" {
  description = "ID of the JWT secret"
  value       = azurerm_key_vault_secret.jwt.id
}

output "nextauth_secret_id" {
  description = "ID of the NextAuth secret"
  value       = azurerm_key_vault_secret.nextauth.id
}

output "api_keys_secret_id" {
  description = "ID of the API keys secret"
  value       = azurerm_key_vault_secret.api_keys.id
}

output "application_secrets_created" {
  description = "List of application secrets created"
  value       = keys(azurerm_key_vault_secret.application_secrets)
}
