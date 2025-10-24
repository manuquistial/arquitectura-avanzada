# Outputs for Carpeta Ciudadana Layer

output "application_namespace" {
  description = "Namespace where Carpeta Ciudadana is deployed"
  value       = var.namespace
}

output "application_url" {
  description = "URL of the Carpeta Ciudadana application"
  value       = var.domain_name != "" ? "https://${var.domain_name}" : "http://localhost"
}

output "frontdoor_endpoint" {
  description = "Front Door endpoint"
  value       = var.frontdoor_enabled ? module.carpeta_ciudadana.frontdoor_endpoint : null
}

output "frontdoor_id" {
  description = "ID of the Front Door"
  value       = var.frontdoor_enabled ? module.carpeta_ciudadana.frontdoor_id : null
}


