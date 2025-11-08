# =============================================================================
# BASE LAYER - INFRAESTRUCTURA BASE
# =============================================================================
# Esta capa contiene la infraestructura base necesaria para todas las demás capas:
# - Resource Group
# - Virtual Network
# - Subnets
# - DNS Zone
# =============================================================================

# Resource Group principal
resource "azurerm_resource_group" "main" {
  name     = "${var.project_name}-${var.environment}-rg"
  location = var.azure_region

  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "Terraform"
    Layer       = "Base"
  }
}

# Virtual Network
module "networking" {
  source = "./modules/networking/vnet"

  environment         = var.environment
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  vnet_cidr           = var.vnet_cidr
  subnet_cidrs        = var.subnet_cidrs
}

# DNS Zone for application domain
module "dns" {
  source = "./modules/dns/dns"

  dns_zone_name       = var.dns_zone_name
  resource_group_name = azurerm_resource_group.main.name
  app_subdomain       = var.app_subdomain
  ingress_ip          = var.ingress_ip
  ingress_alias       = var.ingress_alias

  tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
    Layer       = "Base"
  }
}
