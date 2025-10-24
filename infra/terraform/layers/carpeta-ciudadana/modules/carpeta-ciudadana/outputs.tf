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
  value       = var.frontend_url != "" ? var.frontend_url : "http://${data.kubernetes_service.frontend_lb.status.0.load_balancer.0.ingress.0.ip}"
}

output "frontend_lb_ip" {
  description = "LoadBalancer IP of the frontend service"
  value       = data.kubernetes_service.frontend_lb.status.0.load_balancer.0.ingress.0.ip
}

output "frontend_lb_hostname" {
  description = "LoadBalancer hostname of the frontend service"
  value       = try(data.kubernetes_service.frontend_lb.status.0.load_balancer.0.ingress.0.hostname, null)
}

output "frontdoor_endpoint" {
  description = "Front Door endpoint"
  value       = var.frontdoor_enabled ? "https://${var.frontdoor_frontend_hostname}" : null
}

output "frontdoor_id" {
  description = "ID of the Front Door"
  value       = var.frontdoor_enabled ? "frontdoor-${var.environment}" : null
}

