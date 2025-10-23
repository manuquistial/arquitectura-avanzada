output "opensearch_endpoint" {
  description = "OpenSearch cluster endpoint"
  value       = "opensearch-cluster-master.${var.namespace}.svc.cluster.local:9200"
}

output "opensearch_dashboards_endpoint" {
  description = "OpenSearch Dashboards endpoint (if enabled)"
  value       = var.enable_dashboards ? "opensearch-dashboards.${var.namespace}.svc.cluster.local:5601" : null
}

output "secret_name" {
  description = "Name of the Kubernetes secret containing OpenSearch credentials"
  value       = kubernetes_secret.opensearch_auth.metadata[0].name
}

output "service_name" {
  description = "OpenSearch service name"
  value       = "opensearch-cluster-master"
}

