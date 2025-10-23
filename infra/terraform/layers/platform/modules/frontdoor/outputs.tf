output "frontdoor_profile_name" {
  description = "Front Door profile name"
  value       = azurerm_cdn_frontdoor_profile.main.name
}

output "frontdoor_profile_id" {
  description = "Front Door profile ID"
  value       = azurerm_cdn_frontdoor_profile.main.id
}

output "frontdoor_endpoint_hostname" {
  description = "Front Door endpoint hostname"
  value       = azurerm_cdn_frontdoor_endpoint.main.host_name
}

output "frontdoor_endpoint_id" {
  description = "Front Door endpoint ID"
  value       = azurerm_cdn_frontdoor_endpoint.main.id
}

# Custom domains not implemented yet
# output "frontdoor_custom_domain_ids" {
#   description = "Front Door custom domain IDs"
#   value       = var.custom_domain_names != [] ? [
#     for domain in var.custom_domain_names : 
#     azurerm_cdn_frontdoor_custom_domain.custom_domain[domain].id
#   ] : []
# }

output "frontdoor_waf_policy_id" {
  description = "Front Door WAF policy ID"
  value       = var.enable_waf ? azurerm_cdn_frontdoor_security_policy.waf[0].id : null
}

output "frontdoor_firewall_policy_id" {
  description = "Front Door firewall policy ID"
  value       = var.enable_waf ? azurerm_cdn_frontdoor_firewall_policy.main[0].id : null
}


