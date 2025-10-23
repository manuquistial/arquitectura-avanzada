terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
  }
}

# Azure Front Door Profile (Standard)
resource "azurerm_cdn_frontdoor_profile" "main" {
  name                = "${var.environment}-carpeta-afd"
  resource_group_name = var.resource_group_name
  sku_name            = "Standard_AzureFrontDoor"
  
  tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# Azure Front Door Origin Group
resource "azurerm_cdn_frontdoor_origin_group" "main" {
  name                     = "${var.environment}-carpeta-origin-group"
  cdn_frontdoor_profile_id = azurerm_cdn_frontdoor_profile.main.id
  
  load_balancing {
    sample_size                        = 4
    successful_samples_required        = 3
    additional_latency_in_milliseconds = 50
  }
  
  health_probe {
    interval_in_seconds = 240
    path                = "/"
    protocol            = "Http"
    request_type        = "HEAD"
  }
}

# Azure Front Door Origin (Frontend)
resource "azurerm_cdn_frontdoor_origin" "frontend" {
  name                          = "${var.environment}-carpeta-frontend-origin"
  cdn_frontdoor_origin_group_id = azurerm_cdn_frontdoor_origin_group.main.id
  
  enabled                        = true
  host_name                      = var.frontend_hostname
  http_port                      = 80
  https_port                     = 443
  origin_host_header             = var.frontend_hostname
  priority                       = 1
  weight                         = 1000
  
  certificate_name_check_enabled = false
}

# Azure Front Door Origin (API Gateway)
resource "azurerm_cdn_frontdoor_origin" "api" {
  name                          = "${var.environment}-carpeta-api-origin"
  cdn_frontdoor_origin_group_id = azurerm_cdn_frontdoor_origin_group.main.id
  
  enabled                        = true
  host_name                      = var.api_hostname
  http_port                      = 80
  https_port                     = 443
  origin_host_header             = var.api_hostname
  priority                       = 2
  weight                         = 1000
  
  certificate_name_check_enabled = false
}

# Azure Front Door Endpoint
resource "azurerm_cdn_frontdoor_endpoint" "main" {
  name                     = "${var.environment}-carpeta-endpoint"
  cdn_frontdoor_profile_id = azurerm_cdn_frontdoor_profile.main.id
  
  tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# Azure Front Door Route (Frontend)
resource "azurerm_cdn_frontdoor_route" "frontend" {
  name                          = "${var.environment}-carpeta-frontend-route"
  cdn_frontdoor_endpoint_id     = azurerm_cdn_frontdoor_endpoint.main.id
  cdn_frontdoor_origin_group_id = azurerm_cdn_frontdoor_origin_group.main.id
  cdn_frontdoor_origin_ids      = [azurerm_cdn_frontdoor_origin.frontend.id]
  
  enabled = true
  
  forwarding_protocol    = "HttpOnly"
  https_redirect_enabled = true
  patterns_to_match       = ["/*"]
  supported_protocols     = ["Http", "Https"]
  
  link_to_default_domain = true
  
  # Ensure API route is created first (higher priority)
  depends_on = [azurerm_cdn_frontdoor_route.api]
}

# Azure Front Door Route (API)
resource "azurerm_cdn_frontdoor_route" "api" {
  name                          = "${var.environment}-carpeta-api-route"
  cdn_frontdoor_endpoint_id     = azurerm_cdn_frontdoor_endpoint.main.id
  cdn_frontdoor_origin_group_id = azurerm_cdn_frontdoor_origin_group.main.id
  cdn_frontdoor_origin_ids      = [azurerm_cdn_frontdoor_origin.api.id]
  
  enabled = true
  
  forwarding_protocol    = "HttpOnly"
  https_redirect_enabled = true
  patterns_to_match       = ["/api/*"]
  supported_protocols     = ["Http", "Https"]
  
  link_to_default_domain = true
}

# Azure Front Door Security Policy (WAF)
resource "azurerm_cdn_frontdoor_security_policy" "waf" {
  count = var.enable_waf ? 1 : 0
  
  name                     = "${var.environment}-carpeta-waf-policy"
  cdn_frontdoor_profile_id = azurerm_cdn_frontdoor_profile.main.id
  
  security_policies {
    firewall {
      cdn_frontdoor_firewall_policy_id = azurerm_cdn_frontdoor_firewall_policy.main[0].id
      
      association {
        domain {
          cdn_frontdoor_domain_id = azurerm_cdn_frontdoor_endpoint.main.id
        }
        patterns_to_match = ["/*"]
      }
    }
  }
}

# Azure Front Door Firewall Policy
resource "azurerm_cdn_frontdoor_firewall_policy" "main" {
  count = var.enable_waf ? 1 : 0
  
  name                              = "carpetawaf"
  resource_group_name               = var.resource_group_name
  sku_name                          = azurerm_cdn_frontdoor_profile.main.sku_name
  enabled                           = true
  mode                              = "Prevention"
  redirect_url                      = "https://www.contoso.com"
  custom_block_response_status_code = 403
  custom_block_response_body        = "PGh0bWw+PGJvZHk+PGgxPkFjY2VzcyBEZW5pZWQ8L2gxPjwvYm9keT48L2h0bWw+"
  
  custom_rule {
    name                           = "RateLimitRule"
    enabled                        = true
    priority                      = 1
    rate_limit_duration_in_minutes = 1
    rate_limit_threshold           = 10
    type                          = "RateLimitRule"
    action                        = "Block"
    
    match_condition {
      match_variable     = "RemoteAddr"
      operator          = "IPMatch"
      negation_condition = false
      match_values      = ["192.168.1.0/24", "10.0.0.0/8"]
    }
  }
  
  # Managed rules require Premium SKU
  # managed_rule {
  #   type    = "DefaultRuleSet"
  #   version = "1.0"
  #   action  = "Block"
  # }
  
  # managed_rule {
  #   type    = "Microsoft_BotManagerRuleSet"
  #   version = "1.0"
  #   action  = "Block"
  # }
  
  tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}
