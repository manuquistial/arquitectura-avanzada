output "namespace" {
  description = "Observability namespace"
  value       = kubernetes_namespace.observability.metadata[0].name
}

output "otel_collector_endpoint" {
  description = "OpenTelemetry Collector OTLP endpoint"
  value       = "http://otel-collector-opentelemetry-collector.${kubernetes_namespace.observability.metadata[0].name}.svc.cluster.local:4317"
}

output "prometheus_endpoint" {
  description = "Prometheus server endpoint"
  value       = "http://prometheus-server.${kubernetes_namespace.observability.metadata[0].name}.svc.cluster.local"
}

