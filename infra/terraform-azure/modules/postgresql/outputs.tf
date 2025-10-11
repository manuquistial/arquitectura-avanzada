output "fqdn" {
  description = "PostgreSQL FQDN"
  value       = azurerm_postgresql_flexible_server.main.fqdn
}

output "admin_username" {
  description = "Admin username"
  value       = azurerm_postgresql_flexible_server.main.administrator_login
  sensitive   = true
}

output "database_name" {
  description = "Database name"
  value       = azurerm_postgresql_flexible_server_database.main.name
}

output "server_id" {
  description = "Server ID"
  value       = azurerm_postgresql_flexible_server.main.id
}

