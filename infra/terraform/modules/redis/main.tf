# Redis module for AKS - Minimal configuration for Azure for Students
resource "helm_release" "redis" {
  name       = "redis"
  repository = "https://charts.bitnami.com/bitnami"
  chart      = "redis"
  version    = "19.0.1"
  namespace  = var.namespace

  # Minimal Redis configuration for Azure for Students
  set {
    name  = "auth.enabled"
    value = "false"
  }

  set {
    name  = "master.persistence.enabled"
    value = "false"
  }

  set {
    name  = "replica.replicaCount"
    value = "0"
  }

  # Minimal resources for Azure for Students
  set {
    name  = "master.resources.requests.memory"
    value = "16Mi"
  }

  set {
    name  = "master.resources.requests.cpu"
    value = "10m"
  }

  set {
    name  = "master.resources.limits.memory"
    value = "32Mi"
  }

  set {
    name  = "master.resources.limits.cpu"
    value = "25m"
  }

  # Service configuration
  set {
    name  = "master.service.type"
    value = "ClusterIP"
  }

  set {
    name  = "master.service.ports.redis"
    value = "6379"
  }

  # Disable NetworkPolicy to avoid permission issues
  set {
    name  = "networkPolicy.enabled"
    value = "false"
  }

  # Disable metrics
  set {
    name  = "metrics.enabled"
    value = "false"
  }

  # Use simple Redis image
  set {
    name  = "image.registry"
    value = "docker.io"
  }

  set {
    name  = "image.repository"
    value = "redis"
  }

  set {
    name  = "image.tag"
    value = "7-alpine"
  }

  # depends_on removed for Azure for Students compatibility
}