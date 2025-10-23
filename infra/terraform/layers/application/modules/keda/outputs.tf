/**
 * KEDA Module Outputs
 */

output "keda_namespace" {
  description = "Namespace where KEDA is installed"
  value       = kubernetes_namespace.keda.metadata[0].name
}

output "keda_release_name" {
  description = "Helm release name for KEDA"
  value       = helm_release.keda.name
}

output "keda_version" {
  description = "Installed KEDA version"
  value       = helm_release.keda.version
}

output "keda_status" {
  description = "KEDA Helm release status"
  value       = helm_release.keda.status
}

