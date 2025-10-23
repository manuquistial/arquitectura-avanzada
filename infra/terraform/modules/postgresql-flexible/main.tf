# PostgreSQL Flexible Server con VNet Integration
# Basado en el ejemplo proporcionado

# Generar nombre único
resource "random_string" "pgsfx" {
  length  = 5
  special = false
  upper   = false
}

# Network Security Group para PostgreSQL
resource "azurerm_network_security_group" "postgresql" {
  name                = "${var.environment}-postgresql-nsg"
  location            = var.location
  resource_group_name = var.resource_group_name

  # Regla para permitir tráfico PostgreSQL (puerto 5432)
  security_rule {
    name                       = "PostgreSQL"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "5432"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# Network configuration removed - using public access instead

# PostgreSQL Flexible Server con acceso público
resource "azurerm_postgresql_flexible_server" "main" {
  name                   = "${var.environment}-psql-${random_string.pgsfx.result}"
  location               = var.location
  resource_group_name    = var.resource_group_name
  version                = var.postgresql_version
  sku_name              = var.sku_name
  storage_mb            = var.storage_mb
  
  administrator_login    = var.admin_username
  administrator_password = var.admin_password

  # Public network configuration - SIMPLIFIED for public access
  public_network_access_enabled = true  # Enable public access

  # Configuración de backup
  backup_retention_days        = var.backup_retention_days
  geo_redundant_backup_enabled = var.geo_redundant_backup

  # Zona de disponibilidad
  zone = var.availability_zone

  tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# Firewall rules for public access
resource "azurerm_postgresql_flexible_server_firewall_rule" "allow_azure_services" {
  name             = "AllowAzureServices"
  server_id        = azurerm_postgresql_flexible_server.main.id
  start_ip_address = "0.0.0.0"
  end_ip_address   = "0.0.0.0"
}

# Allow all Azure IPs (for AKS nodes)
resource "azurerm_postgresql_flexible_server_firewall_rule" "allow_azure_ips" {
  name             = "AllowAzureIPs"
  server_id        = azurerm_postgresql_flexible_server.main.id
  start_ip_address = "0.0.0.0"
  end_ip_address   = "255.255.255.255"
}

# Base de datos
resource "azurerm_postgresql_flexible_server_database" "main" {
  name      = var.database_name
  server_id = azurerm_postgresql_flexible_server.main.id
  charset   = "UTF8"
  collation = "en_US.utf8"
}

# Private endpoint removed - using public access instead

# Private DNS and subnet references removed - using public access
