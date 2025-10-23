# Outputs for Carpeta Ciudadana Module

output "helm_release_name" {
  description = "Name of the Helm release"
  value       = helm_release.carpeta_ciudadana.name
}

output "helm_release_namespace" {
  description = "Namespace of the Helm release"
  value       = helm_release.carpeta_ciudadana.namespace
}

output "helm_release_status" {
  description = "Status of the Helm release"
  value       = helm_release.carpeta_ciudadana.status
}

output "application_url" {
  description = "URL of the application"
  value       = var.domain_name != "" ? "https://${var.domain_name}" : "http://localhost"
}

output "frontdoor_endpoint" {
  description = "Front Door endpoint"
  value       = var.frontdoor_enabled ? "https://${var.frontdoor_frontend_hostname}" : null
}

output "frontdoor_id" {
  description = "ID of the Front Door"
  value       = var.frontdoor_enabled ? "frontdoor-${var.environment}" : null
}

