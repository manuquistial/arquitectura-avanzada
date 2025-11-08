output "vnet_id" {
  description = "VNet ID"
  value       = azurerm_virtual_network.main.id
}

output "vnet_name" {
  description = "VNet name"
  value       = azurerm_virtual_network.main.name
}

output "aks_subnet_id" {
  description = "AKS subnet ID"
  value       = azurerm_subnet.aks.id
}

output "aks_network_security_group_id" {
  description = "AKS subnet Network Security Group ID"
  value       = azurerm_network_security_group.aks.id
}

output "db_subnet_id" {
  description = "Database subnet ID"
  value       = azurerm_subnet.db.id
}

# Note: APIM and Redis subnets are not created in this simplified VNet module
# output "apim_subnet_id" - Not created
# output "redis_subnet_id" - Not created

