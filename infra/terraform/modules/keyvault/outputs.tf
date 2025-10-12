/**
 * Key Vault Module Outputs
 */

output "key_vault_id" {
  description = "Key Vault resource ID"
  value       = azurerm_key_vault.main.id
}

output "key_vault_name" {
  description = "Key Vault name"
  value       = azurerm_key_vault.main.name
}

output "key_vault_uri" {
  description = "Key Vault URI"
  value       = azurerm_key_vault.main.vault_uri
}

output "key_vault_tenant_id" {
  description = "Key Vault tenant ID"
  value       = azurerm_key_vault.main.tenant_id
}

output "secret_ids" {
  description = "Map of secret names to secret IDs"
  value = {
    postgres_host                 = azurerm_key_vault_secret.postgres_host.id
    postgres_username             = azurerm_key_vault_secret.postgres_username.id
    postgres_password             = azurerm_key_vault_secret.postgres_password.id
    postgres_database             = azurerm_key_vault_secret.postgres_database.id
    servicebus_connection_string  = azurerm_key_vault_secret.servicebus_connection_string.id
    m2m_secret_key                = azurerm_key_vault_secret.m2m_secret_key.id
    storage_account_name          = azurerm_key_vault_secret.storage_account_name.id
    opensearch_username           = azurerm_key_vault_secret.opensearch_username.id
    opensearch_password           = azurerm_key_vault_secret.opensearch_password.id
  }
}

