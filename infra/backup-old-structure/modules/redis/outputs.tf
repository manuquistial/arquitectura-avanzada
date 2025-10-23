output "redis_hostname" {
  description = "Azure Cache for Redis hostname"
  value       = azurerm_redis_cache.main.hostname
}

output "redis_port" {
  description = "Azure Cache for Redis port"
  value       = azurerm_redis_cache.main.port
}

output "redis_ssl_port" {
  description = "Azure Cache for Redis SSL port"
  value       = azurerm_redis_cache.main.ssl_port
}

output "redis_primary_key" {
  description = "Azure Cache for Redis primary key"
  value       = azurerm_redis_cache.main.primary_access_key
  sensitive   = true
}

output "redis_secondary_key" {
  description = "Azure Cache for Redis secondary key"
  value       = azurerm_redis_cache.main.secondary_access_key
  sensitive   = true
}

output "redis_connection_string" {
  description = "Azure Cache for Redis connection string"
  value       = azurerm_redis_cache.main.primary_connection_string
  sensitive   = true
}

output "redis_id" {
  description = "Azure Cache for Redis resource ID"
  value       = azurerm_redis_cache.main.id
}
