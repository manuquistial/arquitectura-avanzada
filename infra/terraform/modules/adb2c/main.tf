# Note: Azure AD B2C directory creation requires special permissions
# Typically done manually or via Azure Portal first time

resource "azurerm_aadb2c_directory" "main" {
  country_code            = "CO"  # Colombia
  data_residency_location = "United States"
  display_name            = "${var.domain_name} B2C"
  domain_name             = "${var.domain_name}.onmicrosoft.com"
  resource_group_name     = var.resource_group_name
  sku_name                = "PremiumP1"
  
  tags = {
    Environment = var.environment
  }
}

