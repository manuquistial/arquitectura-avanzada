# Azure AD B2C Module Outputs

output "b2c_tenant_name" {
  description = "Azure AD B2C tenant name"
  value       = var.b2c_tenant_name
}

output "b2c_tenant_id" {
  description = "Azure AD B2C tenant ID"
  value       = data.azurerm_client_config.current.tenant_id
}

output "client_id" {
  description = "Azure AD B2C application client ID"
  value       = azuread_application.carpeta_ciudadana.client_id
  sensitive   = true
}

output "client_secret" {
  description = "Azure AD B2C application client secret"
  value       = azuread_application_password.carpeta_ciudadana.value
  sensitive   = true
}

output "application_object_id" {
  description = "Azure AD B2C application object ID"
  value       = azuread_application.carpeta_ciudadana.object_id
}

output "authority_url" {
  description = "Azure AD B2C authority URL"
  value       = "https://${var.b2c_tenant_name}.b2clogin.com/${var.b2c_tenant_name}.onmicrosoft.com"
}

output "issuer_url" {
  description = "Azure AD B2C issuer URL"
  value       = "https://${var.b2c_tenant_name}.b2clogin.com/${data.azurerm_client_config.current.tenant_id}/v2.0"
}

output "jwks_uri" {
  description = "Azure AD B2C JWKS URI"
  value       = "https://${var.b2c_tenant_name}.b2clogin.com/${var.b2c_tenant_name}.onmicrosoft.com/${var.user_flow_name}/discovery/v2.0/keys"
}

output "well_known_config_url" {
  description = "Azure AD B2C well-known configuration URL"
  value       = "https://${var.b2c_tenant_name}.b2clogin.com/${var.b2c_tenant_name}.onmicrosoft.com/${var.user_flow_name}/v2.0/.well-known/openid_configuration"
}

output "user_flow_name" {
  description = "B2C user flow name"
  value       = var.user_flow_name
}

output "redirect_uris" {
  description = "Configured redirect URIs"
  value       = var.redirect_uris
}
