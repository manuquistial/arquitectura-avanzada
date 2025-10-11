resource "azurerm_search_service" "main" {
  name                = "${var.environment}-search"
  resource_group_name = var.resource_group_name
  location            = var.location
  sku                 = var.sku
  
  tags = {
    Environment = var.environment
  }
}

