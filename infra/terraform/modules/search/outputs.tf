output "endpoint" {
  description = "Search service endpoint"
  value       = "https://${azurerm_search_service.main.name}.search.windows.net"
}

output "primary_key" {
  description = "Primary admin key"
  value       = azurerm_search_service.main.primary_key
  sensitive   = true
}

output "query_keys" {
  description = "Query keys"
  value       = azurerm_search_service.main.query_keys
  sensitive   = true
}

