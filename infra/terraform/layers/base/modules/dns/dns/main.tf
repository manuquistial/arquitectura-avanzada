# DNS Zone for carpeta-ciudadana
resource "azurerm_dns_zone" "main" {
  name                = var.dns_zone_name
  resource_group_name = var.resource_group_name

  tags = var.tags
}

# A record pointing to the ingress IP (legacy public exposure)
resource "azurerm_dns_a_record" "app" {
  count               = var.ingress_ip != "" ? 1 : 0
  name                = var.app_subdomain
  zone_name           = azurerm_dns_zone.main.name
  resource_group_name = var.resource_group_name
  ttl                 = 300
  records             = [var.ingress_ip]

  tags = var.tags
}

# CNAME pointing to the Private Link Service alias (Front Door)
resource "azurerm_dns_cname_record" "app_pls" {
  count               = var.ingress_alias != "" ? 1 : 0
  name                = var.app_subdomain
  zone_name           = azurerm_dns_zone.main.name
  resource_group_name = var.resource_group_name
  ttl                 = 300
  record              = var.ingress_alias

  tags = var.tags
}

# CNAME record for www
resource "azurerm_dns_cname_record" "www" {
  name                = "www"
  zone_name           = azurerm_dns_zone.main.name
  resource_group_name = var.resource_group_name
  ttl                 = 300
  record              = "${var.app_subdomain}.${azurerm_dns_zone.main.name}"

  tags = var.tags
}
