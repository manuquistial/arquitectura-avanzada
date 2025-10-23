# NGINX Ingress Controller Module
# Deploys NGINX Ingress Controller using Helm

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

# Kubernetes namespace for NGINX Ingress Controller
resource "kubernetes_namespace" "nginx_ingress" {
  metadata {
    name = var.namespace
    labels = {
      "app" = "nginx-ingress"
      "name" = var.namespace
    }
  }
}

# NGINX Ingress Controller Helm release
resource "helm_release" "nginx_ingress" {
  name       = "ingress-nginx"
  repository = "https://kubernetes.github.io/ingress-nginx"
  chart      = "ingress-nginx"
  version    = var.chart_version
  namespace  = var.namespace

  # Values for NGINX Ingress Controller
  values = [
    yamlencode({
      controller = {
        # Service configuration
        service = {
          type = "LoadBalancer"
          annotations = {
            "service.beta.kubernetes.io/azure-load-balancer-internal" = "false"
            "service.beta.kubernetes.io/azure-load-balancer-health-probe-request-path" = "/healthz"
          }
        }
        
        # Resource requests and limits
        resources = {
          requests = {
            cpu    = var.cpu_request
            memory = var.memory_request
          }
          limits = {
            cpu    = var.cpu_limit
            memory = var.memory_limit
          }
        }
        
        # Node selector for user node pool
        nodeSelector = {
          "nodepool" = "user"
        }
        
        # Metrics configuration
        metrics = {
          enabled = true
          service = {
            annotations = {
              "prometheus.io/scrape" = "true"
              "prometheus.io/port"   = "10254"
            }
          }
        }
        
        # Config for Azure Load Balancer
        config = {
          "use-proxy-protocol" = "false"
          "enable-ssl-passthrough" = "true"
        }
        
        # Admission webhook configuration
        admissionWebhooks = {
          enabled = true
          patch = {
            enabled = true
            image = {
              tag = var.chart_version
            }
          }
        }
      }
      
      # Default backend configuration
      defaultBackend = {
        enabled = true
        replicaCount = 1
        resources = {
          requests = {
            cpu    = "10m"
            memory = "20Mi"
          }
          limits = {
            cpu    = "10m"
            memory = "20Mi"
          }
        }
      }
    })
  ]

  depends_on = [kubernetes_namespace.nginx_ingress]
}

# Wait for NGINX Ingress Controller to be ready
resource "time_sleep" "wait_for_nginx_ingress" {
  depends_on = [helm_release.nginx_ingress]
  create_duration = "60s"
}
