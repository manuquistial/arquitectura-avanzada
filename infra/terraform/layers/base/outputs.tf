# =============================================================================
# BASE LAYER OUTPUTS
# =============================================================================
# Outputs que serán consumidos por las capas superiores
# =============================================================================

# Resource Group
output "resource_group_name" {
  description = "Name of the main resource group"
  value       = azurerm_resource_group.main.name
}

output "resource_group_id" {
  description = "ID of the main resource group"
  value       = azurerm_resource_group.main.id
}

output "location" {
  description = "Azure region"
  value       = azurerm_resource_group.main.location
}

# Networking
output "vnet_id" {
  description = "ID of the virtual network"
  value       = module.networking.vnet_id
}

output "vnet_name" {
  description = "Name of the virtual network"
  value       = module.networking.vnet_name
}

output "aks_subnet_id" {
  description = "ID of the AKS subnet"
  value       = module.networking.aks_subnet_id
}

output "db_subnet_id" {
  description = "ID of the database subnet"
  value       = module.networking.db_subnet_id
}

# DNS
output "dns_zone_name" {
  description = "Name of the DNS zone"
  value       = module.dns.dns_zone_name
}

output "dns_zone_id" {
  description = "ID of the DNS zone"
  value       = module.dns.dns_zone_id
}


