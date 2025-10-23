# Azure API Management Module

# API Management instance
resource "azurerm_api_management" "main" {
  name                = var.apim_name
  location            = var.location
  resource_group_name = var.resource_group_name
  publisher_name      = var.publisher_name
  publisher_email     = var.publisher_email

  sku_name = var.sku_name

  identity {
    type = "SystemAssigned"
  }

  tags = {
    Environment = var.environment
    Project     = "Carpeta Ciudadana"
  }
}

# API Management subscription
resource "azurerm_api_management_subscription" "main" {
  api_management_name = azurerm_api_management.main.name
  resource_group_name = var.resource_group_name
  display_name        = "Carpeta Ciudadana Subscription"
  product_id          = azurerm_api_management_product.main.id
}

# API Management product
resource "azurerm_api_management_product" "main" {
  api_management_name = azurerm_api_management.main.name
  resource_group_name = var.resource_group_name
  product_id          = "carpeta-ciudadana"
  display_name        = "Carpeta Ciudadana API"
  description         = "API for Carpeta Ciudadana application"
  published           = true
  approval_required   = false
  subscription_required = true
}

# Private endpoint for API Management
resource "azurerm_private_endpoint" "apim" {
  count               = var.enable_private_endpoint ? 1 : 0
  name                = "${var.apim_name}-pe"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.subnet_id

  private_service_connection {
    name                           = "${var.apim_name}-psc"
    private_connection_resource_id = azurerm_api_management.main.id
    subresource_names              = ["gateway"]
    is_manual_connection           = false
  }

  tags = {
    Environment = var.environment
    Project     = "Carpeta Ciudadana"
  }
}

# Private DNS zone for API Management
resource "azurerm_private_dns_zone" "apim" {
  count               = var.enable_private_endpoint ? 1 : 0
  name                = "privatelink.azure-api.net"
  resource_group_name = var.resource_group_name
}

# Private DNS zone virtual network link
resource "azurerm_private_dns_zone_virtual_network_link" "apim" {
  count                 = var.enable_private_endpoint ? 1 : 0
  name                  = "${var.apim_name}-dns-link"
  resource_group_name   = var.resource_group_name
  private_dns_zone_name = azurerm_private_dns_zone.apim[0].name
  virtual_network_id    = var.vnet_id
  registration_enabled  = false

  tags = {
    Environment = var.environment
    Project     = "Carpeta Ciudadana"
  }
}

# API Management API
resource "azurerm_api_management_api" "carpeta_ciudadana" {
  name                = "carpeta-ciudadana-api"
  resource_group_name = var.resource_group_name
  api_management_name = azurerm_api_management.main.name
  revision            = "1"
  display_name        = "Carpeta Ciudadana API"
  path                = "api"
  protocols           = ["https"]

  import {
    content_format = "openapi"
    content_value  = file("${path.module}/openapi/gateway.yaml")
  }
}

# API Management Backend for Citizen Service
resource "azurerm_api_management_backend" "citizen" {
  name                = "citizen-backend"
  resource_group_name = var.resource_group_name
  api_management_name = azurerm_api_management.main.name
  protocol            = "http"
  url                 = "http://48.194.40.108/api/citizens"
}

# API Management Backend for Metadata Service
resource "azurerm_api_management_backend" "metadata" {
  name                = "metadata-backend"
  resource_group_name = var.resource_group_name
  api_management_name = azurerm_api_management.main.name
  protocol            = "http"
  url                 = "http://carpeta-ciudadana-metadata.carpeta-ciudadana-production.svc.cluster.local:8000"
}

# API Management Backend for Transfer Service
resource "azurerm_api_management_backend" "transfer" {
  name                = "transfer-backend"
  resource_group_name = var.resource_group_name
  api_management_name = azurerm_api_management.main.name
  protocol            = "http"
  url                 = "http://carpeta-ciudadana-transfer.carpeta-ciudadana-production.svc.cluster.local:8000"
}

# API Management Backend for Signature Service
resource "azurerm_api_management_backend" "signature" {
  name                = "signature-backend"
  resource_group_name = var.resource_group_name
  api_management_name = azurerm_api_management.main.name
  protocol            = "http"
  url                 = "http://carpeta-ciudadana-signature.carpeta-ciudadana-production.svc.cluster.local:8000"
}

# API Management Backend for Ingestion Service
resource "azurerm_api_management_backend" "ingestion" {
  name                = "ingestion-backend"
  resource_group_name = var.resource_group_name
  api_management_name = azurerm_api_management.main.name
  protocol            = "http"
  url                 = "http://carpeta-ciudadana-ingestion.carpeta-ciudadana-production.svc.cluster.local:8000"
}

# API Management Backend for Mintic Client Service
resource "azurerm_api_management_backend" "mintic_client" {
  name                = "mintic-client-backend"
  resource_group_name = var.resource_group_name
  api_management_name = azurerm_api_management.main.name
  protocol            = "http"
  url                 = "http://carpeta-ciudadana-mintic-client.carpeta-ciudadana-production.svc.cluster.local:8000"
}
