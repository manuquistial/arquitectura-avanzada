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

# Secret para credenciales de OpenSearch
resource "kubernetes_secret" "opensearch_auth" {
  metadata {
    name      = "opensearch-auth"
    namespace = var.namespace
  }

  data = {
    OS_USERNAME = var.opensearch_username
    OS_PASSWORD = var.opensearch_password
    OPENSEARCH_URL = "http://opensearch-cluster-master:9200"
  }

  type = "Opaque"
}

# Helm release para OpenSearch
resource "helm_release" "opensearch" {
  name             = "opensearch"
  repository       = "https://opensearch-project.github.io/helm-charts/"
  chart            = "opensearch"
  version          = var.chart_version
  namespace        = var.namespace
  create_namespace = true

  values = [
    file("${path.module}/../../../deploy/helm/values-opensearch.yaml")
  ]

  # Override values for single-node dev environment
  set {
    name  = "replicas"
    value = "1"
  }

  set {
    name  = "singleNode"
    value = "true"
  }

  set {
    name  = "persistence.size"
    value = var.storage_size
  }

  set {
    name  = "persistence.storageClass"
    value = var.storage_class
  }

  set {
    name  = "resources.requests.memory"
    value = var.memory_request
  }

  set {
    name  = "resources.requests.cpu"
    value = var.cpu_request
  }

  set {
    name  = "resources.limits.memory"
    value = var.memory_limit
  }

  set {
    name  = "resources.limits.cpu"
    value = var.cpu_limit
  }

  # Security configuration
  set {
    name  = "opensearchJavaOpts"
    value = "-Xms${var.heap_size} -Xmx${var.heap_size}"
  }

  # Basic auth credentials
  set_sensitive {
    name  = "extraEnvs[0].name"
    value = "OPENSEARCH_INITIAL_ADMIN_PASSWORD"
  }

  set_sensitive {
    name  = "extraEnvs[0].value"
    value = var.opensearch_password
  }

  depends_on = [kubernetes_secret.opensearch_auth]
}

# Helm release para OpenSearch Dashboards (opcional)
resource "helm_release" "opensearch_dashboards" {
  count = var.enable_dashboards ? 1 : 0

  name             = "opensearch-dashboards"
  repository       = "https://opensearch-project.github.io/helm-charts/"
  chart            = "opensearch-dashboards"
  version          = var.dashboards_chart_version
  namespace        = var.namespace
  create_namespace = true

  set {
    name  = "replicas"
    value = "1"
  }

  set {
    name  = "opensearchHosts"
    value = "http://opensearch-cluster-master:9200"
  }

  set {
    name  = "service.type"
    value = "ClusterIP"
  }

  set {
    name  = "resources.requests.memory"
    value = "512Mi"
  }

  set {
    name  = "resources.requests.cpu"
    value = "250m"
  }

  set {
    name  = "resources.limits.memory"
    value = "1Gi"
  }

  set {
    name  = "resources.limits.cpu"
    value = "500m"
  }

  depends_on = [helm_release.opensearch]
}

