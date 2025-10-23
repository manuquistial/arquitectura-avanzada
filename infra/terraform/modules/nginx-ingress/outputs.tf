output "namespace" {
  description = "Kubernetes namespace for NGINX Ingress Controller"
  value       = kubernetes_namespace.nginx_ingress.metadata[0].name
}

output "service_name" {
  description = "Name of the NGINX Ingress Controller service"
  value       = "ingress-nginx-controller"
}

output "service_namespace" {
  description = "Namespace of the NGINX Ingress Controller service"
  value       = var.namespace
}

output "ingress_class" {
  description = "Ingress class name for NGINX Ingress Controller"
  value       = "nginx"
}
