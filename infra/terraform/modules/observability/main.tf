terraform {
  required_providers {
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.12"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.24"
    }
  }
}

# Namespace para observabilidad
resource "kubernetes_namespace" "observability" {
  metadata {
    name = var.namespace
    labels = {
      "app.kubernetes.io/name"       = "observability"
      "app.kubernetes.io/managed-by" = "terraform"
    }
  }
}

# OpenTelemetry Collector
resource "helm_release" "otel_collector" {
  name       = "otel-collector"
  repository = "https://open-telemetry.github.io/opentelemetry-helm-charts"
  chart      = "opentelemetry-collector"
  version    = var.otel_chart_version
  namespace  = kubernetes_namespace.observability.metadata[0].name

  values = [
    file("${path.module}/../../../observability/otel-collector-values.yaml")
  ]

  set {
    name  = "mode"
    value = "deployment"
  }

  set {
    name  = "replicaCount"
    value = var.otel_replicas
  }

  set {
    name  = "resources.requests.cpu"
    value = var.otel_cpu_request
  }

  set {
    name  = "resources.requests.memory"
    value = var.otel_memory_request
  }

  set {
    name  = "resources.limits.cpu"
    value = var.otel_cpu_limit
  }

  set {
    name  = "resources.limits.memory"
    value = var.otel_memory_limit
  }

  depends_on = [kubernetes_namespace.observability]
}

# Prometheus
resource "helm_release" "prometheus" {
  name       = "prometheus"
  repository = "https://prometheus-community.github.io/helm-charts"
  chart      = "prometheus"
  version    = var.prometheus_chart_version
  namespace  = kubernetes_namespace.observability.metadata[0].name

  values = [
    file("${path.module}/../../../observability/prometheus-values.yaml")
  ]

  set {
    name  = "server.retention"
    value = var.prometheus_retention
  }

  set {
    name  = "server.persistentVolume.size"
    value = var.prometheus_storage_size
  }

  set {
    name  = "server.resources.requests.cpu"
    value = var.prometheus_cpu_request
  }

  set {
    name  = "server.resources.requests.memory"
    value = var.prometheus_memory_request
  }

  set {
    name  = "server.resources.limits.cpu"
    value = var.prometheus_cpu_limit
  }

  set {
    name  = "server.resources.limits.memory"
    value = var.prometheus_memory_limit
  }

  depends_on = [kubernetes_namespace.observability]
}

