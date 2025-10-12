/**
 * KEDA (Kubernetes Event-driven Autoscaling) Module
 * 
 * Installs KEDA for event-driven autoscaling based on:
 * - Azure Service Bus queue length
 * - Custom metrics from Prometheus
 * - HTTP traffic
 */

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

# Create KEDA namespace
resource "kubernetes_namespace" "keda" {
  metadata {
    name = var.keda_namespace
    
    labels = {
      name = var.keda_namespace
      "pod-security.kubernetes.io/enforce" = "privileged"
    }
  }
}

# Install KEDA using Helm
resource "helm_release" "keda" {
  name       = "keda"
  repository = "https://kedacore.github.io/charts"
  chart      = "keda"
  version    = var.keda_version
  namespace  = kubernetes_namespace.keda.metadata[0].name

  values = [
    yamlencode({
      # Resources for KEDA operator
      resources = {
        operator = {
          limits = {
            cpu    = var.operator_cpu_limit
            memory = var.operator_memory_limit
          }
          requests = {
            cpu    = var.operator_cpu_request
            memory = var.operator_memory_request
          }
        }
        metricServer = {
          limits = {
            cpu    = "500m"
            memory = "512Mi"
          }
          requests = {
            cpu    = "100m"
            memory = "128Mi"
          }
        }
        webhooks = {
          limits = {
            cpu    = "500m"
            memory = "512Mi"
          }
          requests = {
            cpu    = "100m"
            memory = "128Mi"
          }
        }
      }

      # Prometheus metrics
      prometheus = {
        metricServer = {
          enabled = true
          port    = 9022
          path    = "/metrics"
        }
        operator = {
          enabled = true
          port    = 8080
          path    = "/metrics"
        }
      }

      # Security
      podSecurityContext = {
        runAsNonRoot = true
        runAsUser    = 1000
        fsGroup      = 1000
      }

      # Replicas for HA
      replicaCount = var.replica_count

      # Service account
      serviceAccount = {
        create = true
        name   = "keda-operator"
      }

      # Logging
      logging = {
        operator = {
          level  = var.log_level
          format = "json"
        }
        metricServer = {
          level = var.log_level
        }
      }
    })
  ]

  depends_on = [
    kubernetes_namespace.keda
  ]
}

# Create TriggerAuthentication for Service Bus (using Azure Workload Identity)
resource "kubernetes_manifest" "servicebus_trigger_auth" {
  count = var.enable_servicebus_trigger ? 1 : 0

  manifest = {
    apiVersion = "keda.sh/v1alpha1"
    kind       = "TriggerAuthentication"
    metadata = {
      name      = "azure-servicebus-auth"
      namespace = var.app_namespace
    }
    spec = {
      podIdentity = {
        provider = "azure-workload"
      }
    }
  }

  depends_on = [
    helm_release.keda
  ]
}

# ServiceMonitor for Prometheus (if prometheus-operator is installed)
resource "kubernetes_manifest" "keda_service_monitor" {
  count = var.enable_prometheus_monitoring ? 1 : 0

  manifest = {
    apiVersion = "monitoring.coreos.com/v1"
    kind       = "ServiceMonitor"
    metadata = {
      name      = "keda-operator"
      namespace = kubernetes_namespace.keda.metadata[0].name
      labels = {
        app = "keda-operator"
      }
    }
    spec = {
      selector = {
        matchLabels = {
          "app.kubernetes.io/name" = "keda-operator"
        }
      }
      endpoints = [
        {
          port     = "metrics"
          interval = "30s"
        }
      ]
    }
  }

  depends_on = [
    helm_release.keda
  ]
}

