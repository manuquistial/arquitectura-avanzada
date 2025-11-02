# Azure Key Vault Secret for PostgreSQL Database
# This automatically creates the database credentials secret in Key Vault during deployment

resource "azurerm_key_vault_secret" "database_credentials" {
  count        = var.key_vault_id != "" ? 1 : 0
  name         = "database-credentials"
  value        = jsonencode({
    database-url = "postgresql+asyncpg://${var.admin_username}:${var.admin_password}@${azurerm_postgresql_flexible_server.main.fqdn}:5432/${azurerm_postgresql_flexible_server_database.main.name}?ssl=require"
    postgres-uri = "postgresql://${var.admin_username}:${var.admin_password}@${azurerm_postgresql_flexible_server.main.fqdn}:5432/${azurerm_postgresql_flexible_server_database.main.name}?sslmode=require"
    db-host      = azurerm_postgresql_flexible_server.main.fqdn
    db-port      = "5432"
    db-name      = azurerm_postgresql_flexible_server_database.main.name
    db-user      = var.admin_username
    db-password  = var.admin_password
    db-sslmode   = "require"
  })
  key_vault_id = var.key_vault_id
  
  tags = {
    Environment = var.environment
    Component   = "database"
    AutoManaged = "true"
  }
  
  depends_on = [
    azurerm_postgresql_flexible_server.main,
    azurerm_postgresql_flexible_server_database.main
  ]
}

