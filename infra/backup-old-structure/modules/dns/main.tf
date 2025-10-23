# DNS Zone for carpeta-ciudadana
resource "azurerm_dns_zone" "main" {
  name                = var.dns_zone_name
  resource_group_name = var.resource_group_name

  tags = var.tags
}

# A record pointing to the ingress IP
resource "azurerm_dns_a_record" "app" {
  name                = var.app_subdomain
  zone_name           = azurerm_dns_zone.main.name
  resource_group_name = var.resource_group_name
  ttl                 = 300
  records             = [var.ingress_ip]

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
