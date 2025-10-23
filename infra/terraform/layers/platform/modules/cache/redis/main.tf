# Azure Cache for Redis
resource "azurerm_redis_cache" "main" {
  name                = "${var.environment}-carpeta-redis"
  location            = var.location
  resource_group_name = var.resource_group_name
  capacity            = var.capacity
  family              = var.family
  sku_name            = var.sku_name
  
  # Security configuration - TLS only for production
  minimum_tls_version = var.minimum_tls_version
  
  # Redis configuration
  redis_configuration {
    maxmemory_policy = var.maxmemory_policy
  }
  
  tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
    Service     = "Redis Cache"
  }
}

# Redis Firewall Rules (if public access is enabled)
resource "azurerm_redis_firewall_rule" "aks_subnet" {
  count               = var.enable_firewall_rules ? 1 : 0
  name                = "akssubnetaccess"
  redis_cache_name    = azurerm_redis_cache.main.name
  resource_group_name = var.resource_group_name
  start_ip            = var.aks_subnet_start_ip
  end_ip              = var.aks_subnet_end_ip
}

# Redis Firewall Rule for Azure Services
resource "azurerm_redis_firewall_rule" "azure_services" {
  count               = var.enable_firewall_rules && var.allow_azure_services ? 1 : 0
  name                = "azureservicesaccess"
  redis_cache_name    = azurerm_redis_cache.main.name
  resource_group_name = var.resource_group_name
  start_ip            = "0.0.0.0"
  end_ip              = "0.0.0.0"
}

# Private DNS Zone for Redis (if VNet integration is enabled)
resource "azurerm_private_dns_zone" "redis" {
  count               = var.enable_vnet_integration ? 1 : 0
  name                = "privatelink.redis.cache.windows.net"
  resource_group_name = var.resource_group_name
  
  tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# Private DNS Zone Virtual Network Link
resource "azurerm_private_dns_zone_virtual_network_link" "redis" {
  count                 = var.enable_vnet_integration ? 1 : 0
  name                  = "${var.environment}-redis-dns-link"
  resource_group_name   = var.resource_group_name
  private_dns_zone_name = azurerm_private_dns_zone.redis[0].name
  virtual_network_id    = var.vnet_id
  registration_enabled  = false
  
  tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# Private Endpoint for Redis (if VNet integration is enabled)
resource "azurerm_private_endpoint" "redis" {
  count               = var.enable_vnet_integration ? 1 : 0
  name                = "${var.environment}-redis-pe"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.private_endpoint_subnet_id
  
  private_service_connection {
    name                           = "${var.environment}-redis-psc"
    private_connection_resource_id = azurerm_redis_cache.main.id
    subresource_names              = ["redisCache"]
    is_manual_connection           = false
  }
  
  private_dns_zone_group {
    name                 = "${var.environment}-redis-dns-zone-group"
    private_dns_zone_ids = [azurerm_private_dns_zone.redis[0].id]
  }
  
  tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}