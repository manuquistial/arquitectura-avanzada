terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
}

# Suffix aleatorio para evitar conflictos de nombre (estable dentro del estado)
resource "random_string" "suffix" {
  length  = 5
  upper   = false
  special = false
}

# Azure Front Door Profile (Standard)
resource "azurerm_cdn_frontdoor_profile" "main" {
  name                = var.profile_name != "" ? var.profile_name : "${var.environment}-carpeta-afd-${random_string.suffix.result}"
  resource_group_name = var.resource_group_name
  sku_name            = var.sku_name

  tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
  }

  # Timeout extendido para Front Door (puede tardar 30-45 minutos)
  timeouts {
    create = "45m"
    update = "45m"
    read   = "5m"
    delete = "45m"
  }
}

# Azure Front Door Origin Group (Frontend)
resource "azurerm_cdn_frontdoor_origin_group" "frontend" {
  name                     = var.frontend_origin_group_name != "" ? var.frontend_origin_group_name : "${var.environment}-carpeta-origin-group"
  cdn_frontdoor_profile_id = azurerm_cdn_frontdoor_profile.main.id

  load_balancing {
    sample_size                        = 4
    successful_samples_required        = 3
    additional_latency_in_milliseconds = 50
  }

  health_probe {
    interval_in_seconds = 240
    path                = "/health"
    protocol            = "Http"
    request_type        = "GET"
  }

  lifecycle {
    create_before_destroy = true
  }
}

# Azure Front Door Origin Group (API)
resource "azurerm_cdn_frontdoor_origin_group" "api" {
  name                     = var.api_origin_group_name != "" ? var.api_origin_group_name : "${var.environment}-carpeta-api-origin-group"
  cdn_frontdoor_profile_id = azurerm_cdn_frontdoor_profile.main.id

  load_balancing {
    sample_size                        = 4
    successful_samples_required        = 3
    additional_latency_in_milliseconds = 50
  }

  health_probe {
    interval_in_seconds = 240
    path                = "/health"
    protocol            = "Http"
    request_type        = "GET"
  }

  lifecycle {
    create_before_destroy = true
  }
}

# Azure Front Door Origin (Frontend)
resource "azurerm_cdn_frontdoor_origin" "frontend" {
  name                          = "${var.environment}-carpeta-frontend-origin"
  cdn_frontdoor_origin_group_id = azurerm_cdn_frontdoor_origin_group.frontend.id

  enabled            = true
  host_name          = var.frontend_hostname
  http_port          = 80
  https_port         = 443
  origin_host_header = var.frontend_hostname
  priority           = 1
  weight             = 1000

  certificate_name_check_enabled = var.private_link_enabled ? true : false

  dynamic "private_link" {
    for_each = var.private_link_enabled && var.private_link_target_id != "" ? [var.private_link_target_id] : []
    content {
      private_link_target_id = private_link.value
      location               = var.private_link_location
      request_message        = var.private_link_request_message
      target_type            = var.private_link_target_type
    }
  }

  lifecycle {
    create_before_destroy = true
  }
}

# Azure Front Door Origin (API Gateway)
resource "azurerm_cdn_frontdoor_origin" "api" {
  name                          = "${var.environment}-carpeta-api-origin"
  cdn_frontdoor_origin_group_id = azurerm_cdn_frontdoor_origin_group.api.id

  enabled            = true
  host_name          = var.api_hostname
  http_port          = 80
  https_port         = 443
  origin_host_header = var.api_hostname
  priority           = 2
  weight             = 1000

  certificate_name_check_enabled = var.private_link_enabled ? true : false

  dynamic "private_link" {
    for_each = var.private_link_enabled && var.private_link_target_id != "" ? [var.private_link_target_id] : []
    content {
      private_link_target_id = private_link.value
      location               = var.private_link_location
      request_message        = var.private_link_request_message
      target_type            = var.private_link_target_type
    }
  }

  lifecycle {
    create_before_destroy = true
  }
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
  cdn_frontdoor_origin_group_id = azurerm_cdn_frontdoor_origin_group.frontend.id
  cdn_frontdoor_origin_ids      = [azurerm_cdn_frontdoor_origin.frontend.id]

  enabled = true

  forwarding_protocol    = "HttpOnly"
  https_redirect_enabled = true
  patterns_to_match      = ["/*"]
  supported_protocols    = ["Http", "Https"]

  link_to_default_domain = true

}

# Azure Front Door Route (API)
resource "azurerm_cdn_frontdoor_route" "api" {
  name                          = "${var.environment}-carpeta-api-route"
  cdn_frontdoor_endpoint_id     = azurerm_cdn_frontdoor_endpoint.main.id
  cdn_frontdoor_origin_group_id = azurerm_cdn_frontdoor_origin_group.api.id
  cdn_frontdoor_origin_ids      = [azurerm_cdn_frontdoor_origin.api.id]

  enabled = true

  forwarding_protocol    = "HttpOnly"
  https_redirect_enabled = true
  patterns_to_match      = ["/api/*"]
  supported_protocols    = ["Http", "Https"]

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
    priority                       = 1
    rate_limit_duration_in_minutes = 1
    rate_limit_threshold           = 10
    type                           = "RateLimitRule"
    action                         = "Block"

    match_condition {
      match_variable     = "RemoteAddr"
      operator           = "IPMatch"
      negation_condition = false
      match_values       = ["192.168.1.0/24", "10.0.0.0/8"]
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
