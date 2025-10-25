# Azure Key Vault Secret for Storage Account
# This automatically creates the storage account secrets in Key Vault during deployment

resource "azurerm_key_vault_secret" "azure_storage" {
  count        = var.key_vault_id != "" ? 1 : 0
  name         = "azure-storage"
  value        = jsonencode({
    account-name    = azurerm_storage_account.main.name
    account-key     = azurerm_storage_account.main.primary_access_key
    container-name  = azurerm_storage_container.documents.name
    connection-string = azurerm_storage_account.main.primary_connection_string
    blob-endpoint  = azurerm_storage_account.main.primary_blob_endpoint
  })
  key_vault_id = var.key_vault_id
  
  tags = {
    Environment = var.environment
    Component   = "storage"
    AutoManaged = "true"
  }
}
