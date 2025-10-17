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

# Use existing db-subnet instead of creating a new one
data "azurerm_subnet" "postgresql" {
  name                 = "db-subnet"
  virtual_network_name = var.vnet_name
  resource_group_name  = var.resource_group_name
}

# Update the existing subnet to add PostgreSQL delegation
resource "azurerm_subnet" "postgresql_update" {
  name                 = "db-subnet"
  virtual_network_name = var.vnet_name
  resource_group_name  = var.resource_group_name
  address_prefixes     = [var.postgresql_subnet_cidr]
  service_endpoints    = ["Microsoft.Storage"]

  delegation {
    name = "postgresql-delegation"

    service_delegation {
      name = "Microsoft.DBforPostgreSQL/flexibleServers"

      actions = [
        "Microsoft.Network/virtualNetworks/subnets/join/action",
      ]
    }
  }

  # Import the existing subnet
  lifecycle {
    ignore_changes = [address_prefixes]
  }
}

# Asociar NSG con la subnet
resource "azurerm_subnet_network_security_group_association" "postgresql" {
  subnet_id                 = azurerm_subnet.postgresql_update.id
  network_security_group_id = azurerm_network_security_group.postgresql.id
}

# Private DNS Zone para PostgreSQL
resource "azurerm_private_dns_zone" "postgresql" {
  name                = "${var.environment}-${random_string.pgsfx.result}.postgres.database.azure.com"
  resource_group_name = var.resource_group_name

  depends_on = [azurerm_subnet_network_security_group_association.postgresql]
}

# Link de Private DNS Zone con VNet
resource "azurerm_private_dns_zone_virtual_network_link" "postgresql" {
  name                  = "${var.environment}-postgresql-link"
  private_dns_zone_name = azurerm_private_dns_zone.postgresql.name
  virtual_network_id    = var.vnet_id
  resource_group_name   = var.resource_group_name

  registration_enabled = false
}

# PostgreSQL Flexible Server con VNet Integration
resource "azurerm_postgresql_flexible_server" "main" {
  name                   = "${var.environment}-psql-${random_string.pgsfx.result}"
  location               = var.location
  resource_group_name    = var.resource_group_name
  version                = var.postgresql_version
  sku_name              = var.sku_name
  storage_mb            = var.storage_mb
  
  administrator_login    = var.admin_username
  administrator_password = var.admin_password

  # VNet Integration
  delegated_subnet_id    = azurerm_subnet.postgresql_update.id
  private_dns_zone_id   = azurerm_private_dns_zone.postgresql.id
  
  # Disable public access for security
  public_network_access_enabled = false

  # Configuración de backup
  backup_retention_days        = var.backup_retention_days
  geo_redundant_backup_enabled = var.geo_redundant_backup

  # Zona de disponibilidad
  zone = var.availability_zone

  tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
  }

  depends_on = [azurerm_private_dns_zone_virtual_network_link.postgresql]
}

# Base de datos
resource "azurerm_postgresql_flexible_server_database" "main" {
  name      = var.database_name
  server_id = azurerm_postgresql_flexible_server.main.id
  charset   = "UTF8"
  collation = "en_US.utf8"
}
