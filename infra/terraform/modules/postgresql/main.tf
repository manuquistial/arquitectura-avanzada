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

# Firewall rule para AKS nodepool egress (si se especifica IP)
resource "azurerm_postgresql_flexible_server_firewall_rule" "aks_egress" {
  count = var.aks_egress_ip != "" ? 1 : 0
  
  name             = "AllowAKSNodepool"
  server_id        = azurerm_postgresql_flexible_server.main.id
  start_ip_address = var.aks_egress_ip
  end_ip_address   = var.aks_egress_ip
}

# Firewall rule para Azure services (opcional, solo para backups/monitoring)
resource "azurerm_postgresql_flexible_server_firewall_rule" "azure_services" {
  count = var.allow_azure_services ? 1 : 0
  
  name             = "AllowAzureServices"
  server_id        = azurerm_postgresql_flexible_server.main.id
  start_ip_address = "0.0.0.0"  # Valor especial: solo Azure services, NO internet
  end_ip_address   = "0.0.0.0"
}

# NOTA: 0.0.0.0-0.0.0.0 es un valor especial de Azure que permite SOLO servicios de Azure
# NO permite internet público. Para permitir internet, sería 0.0.0.0-255.255.255.255

# Configuración de conexión
resource "azurerm_postgresql_flexible_server_configuration" "connection_limit" {
  name      = "max_connections"
  server_id = azurerm_postgresql_flexible_server.main.id
  value     = "200"
}

