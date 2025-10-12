output "namespace" {
  description = "cert-manager namespace"
  value       = kubernetes_namespace.cert_manager.metadata[0].name
}

output "letsencrypt_staging_issuer" {
  description = "Let's Encrypt staging ClusterIssuer name"
  value       = kubernetes_manifest.letsencrypt_staging.manifest.metadata.name
}

output "letsencrypt_prod_issuer" {
  description = "Let's Encrypt production ClusterIssuer name"
  value       = kubernetes_manifest.letsencrypt_prod.manifest.metadata.name
}

output "cert_manager_version" {
  description = "cert-manager chart version deployed"
  value       = helm_release.cert_manager.version
}

