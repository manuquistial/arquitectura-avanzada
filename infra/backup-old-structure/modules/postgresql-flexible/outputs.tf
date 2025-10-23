output "server_id" {
  description = "PostgreSQL server ID"
  value       = azurerm_postgresql_flexible_server.main.id
}

output "server_name" {
  description = "PostgreSQL server name"
  value       = azurerm_postgresql_flexible_server.main.name
}

output "fqdn" {
  description = "PostgreSQL server FQDN"
  value       = azurerm_postgresql_flexible_server.main.fqdn
}

output "database_name" {
  description = "Database name"
  value       = azurerm_postgresql_flexible_server_database.main.name
}

# URI (pgsql://) — con credenciales URL-encoded
output "connection_string_uri" {
  description = "PostgreSQL connection string (URI)"
  value       = "postgresql://${urlencode(var.admin_username)}:${urlencode(var.admin_password)}@${azurerm_postgresql_flexible_server.main.fqdn}:5432/${var.database_name}?sslmode=require"
  sensitive   = true
}

# libpq (psql / drivers C/Python)
output "connection_string_libpq" {
  description = "PostgreSQL connection string (libpq keywords)"
  value       = "host=${azurerm_postgresql_flexible_server.main.fqdn} port=5432 dbname=${var.database_name} user=${var.admin_username} password=${var.admin_password} sslmode=require"
  sensitive   = true
}

# AsyncPG URI (postgresql+asyncpg://) — para SQLAlchemy async
output "connection_string_asyncpg" {
  description = "PostgreSQL connection string for asyncpg driver"
  value       = "postgresql+asyncpg://${urlencode(var.admin_username)}:${urlencode(var.admin_password)}@${azurerm_postgresql_flexible_server.main.fqdn}:5432/${var.database_name}?ssl=require"
  sensitive   = true
}

output "version" {
  description = "PostgreSQL version"
  value       = azurerm_postgresql_flexible_server.main.version
}

output "sku_name" {
  description = "PostgreSQL SKU name"
  value       = azurerm_postgresql_flexible_server.main.sku_name
}

output "storage_mb" {
  description = "Storage size in MB"
  value       = azurerm_postgresql_flexible_server.main.storage_mb
}

# Public access outputs - private endpoint references removed
