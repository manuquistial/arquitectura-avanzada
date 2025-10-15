output "redis_service_name" {
  description = "Redis service name for other services to reference"
  value       = "redis-master"
}

output "redis_service_port" {
  description = "Redis service port"
  value       = 6379
}

output "redis_service_fqdn" {
  description = "Redis service FQDN"
  value       = "redis-master.${var.namespace}.svc.cluster.local"
}
