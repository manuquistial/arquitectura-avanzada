output "apim_id" {
  description = "API Management ID"
  value       = azurerm_api_management.main.id
}

output "apim_name" {
  description = "API Management name"
  value       = azurerm_api_management.main.name
}

output "apim_gateway_url" {
  description = "API Management gateway URL"
  value       = azurerm_api_management.main.gateway_url
}

output "apim_developer_portal_url" {
  description = "API Management developer portal URL"
  value       = azurerm_api_management.main.developer_portal_url
}

output "apim_management_api_url" {
  description = "API Management management API URL"
  value       = azurerm_api_management.main.management_api_url
}

output "apim_public_ip_addresses" {
  description = "API Management public IP addresses"
  value       = azurerm_api_management.main.public_ip_addresses
}

output "subscription_key" {
  description = "API Management subscription key"
  value       = azurerm_api_management_subscription.main.primary_key
  sensitive   = true
}

output "apim_identity_principal_id" {
  description = "API Management managed identity principal ID"
  value       = azurerm_api_management.main.identity[0].principal_id
}

output "apim_identity_tenant_id" {
  description = "API Management managed identity tenant ID"
  value       = azurerm_api_management.main.identity[0].tenant_id
}

output "private_endpoint_id" {
  description = "Private endpoint ID for API Management"
  value       = var.enable_private_endpoint ? azurerm_private_endpoint.apim[0].id : null
}

output "private_dns_zone_id" {
  description = "Private DNS zone ID for API Management"
  value       = var.enable_private_endpoint ? azurerm_private_dns_zone.apim[0].id : null
}

output "subscription_id" {
  description = "API Management subscription ID"
  value       = azurerm_api_management_subscription.main.id
}
