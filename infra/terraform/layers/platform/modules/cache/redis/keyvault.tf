# Azure Key Vault Secret for Redis Cache
# This automatically creates the Redis credentials secret in Key Vault during deployment

resource "azurerm_key_vault_secret" "redis" {
  count        = var.key_vault_id != "" ? 1 : 0
  name         = "redis"
  value        = jsonencode({
    host             = azurerm_redis_cache.main.hostname
    port             = tostring(azurerm_redis_cache.main.ssl_port)
    password         = azurerm_redis_cache.main.primary_access_key
    ssl              = "true"
    connection-string = "redis://:${azurerm_redis_cache.main.primary_access_key}@${azurerm_redis_cache.main.hostname}:${azurerm_redis_cache.main.ssl_port}?ssl=True"
    session-db       = "0"
  })
  key_vault_id = var.key_vault_id
  
  tags = {
    Environment = var.environment
    Component   = "redis"
    AutoManaged = "true"
  }
  
  depends_on = [
    azurerm_redis_cache.main
  ]
}

