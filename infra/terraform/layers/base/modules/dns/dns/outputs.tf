output "dns_zone_name" {
  description = "DNS zone name"
  value       = azurerm_dns_zone.main.name
}

output "dns_zone_id" {
  description = "DNS zone ID"
  value       = azurerm_dns_zone.main.id
}

output "app_fqdn" {
  description = "Application fully qualified domain name"
  value       = "${var.app_subdomain}.${azurerm_dns_zone.main.name}"
}

output "nameservers" {
  description = "DNS zone nameservers"
  value       = azurerm_dns_zone.main.name_servers
}
