resource "azurerm_postgresql_flexible_server" "main" {
  name                = "${var.environment}-psql-server"
  location            = var.location
  resource_group_name = var.resource_group_name
  
  sku_name   = var.sku_name
  storage_mb = var.storage_mb
  version    = "14"
  
  administrator_login    = var.admin_username
  administrator_password = var.admin_password
  
  backup_retention_days        = 7
  geo_redundant_backup_enabled = false
  
  # zone = "1"  # Comentado - no disponible en northcentralus
  
  tags = {
    Environment = var.environment
  }
}

resource "azurerm_postgresql_flexible_server_database" "main" {
  name      = "carpeta_ciudadana"
  server_id = azurerm_postgresql_flexible_server.main.id
  charset   = "UTF8"
  collation = "en_US.utf8"
}

# Firewall rule para permitir acceso desde Azure services
resource "azurerm_postgresql_flexible_server_firewall_rule" "azure_services" {
  name             = "allow-azure-services"
  server_id        = azurerm_postgresql_flexible_server.main.id
  start_ip_address = "0.0.0.0"
  end_ip_address   = "0.0.0.0"
}

# Configuración de conexión
resource "azurerm_postgresql_flexible_server_configuration" "connection_limit" {
  name      = "max_connections"
  server_id = azurerm_postgresql_flexible_server.main.id
  value     = "200"
}

