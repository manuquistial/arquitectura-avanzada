output "tenant_id" {
  description = "B2C Tenant ID"
  value       = azurerm_aadb2c_directory.main.tenant_id
}

output "domain_name" {
  description = "B2C Domain name"
  value       = azurerm_aadb2c_directory.main.domain_name
}

