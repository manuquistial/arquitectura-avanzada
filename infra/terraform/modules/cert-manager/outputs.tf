output "namespace" {
  description = "cert-manager namespace"
  value       = kubernetes_namespace.cert_manager.metadata[0].name
}

output "letsencrypt_staging_issuer" {
  description = "Let's Encrypt staging ClusterIssuer name"
  value       = length(kubernetes_manifest.letsencrypt_staging) > 0 ? kubernetes_manifest.letsencrypt_staging[0].manifest.metadata.name : "letsencrypt-staging"
}

output "letsencrypt_prod_issuer" {
  description = "Let's Encrypt production ClusterIssuer name"
  value       = length(kubernetes_manifest.letsencrypt_prod) > 0 ? kubernetes_manifest.letsencrypt_prod[0].manifest.metadata.name : "letsencrypt-prod"
}

output "cert_manager_version" {
  description = "cert-manager chart version deployed"
  value       = helm_release.cert_manager.version
}

