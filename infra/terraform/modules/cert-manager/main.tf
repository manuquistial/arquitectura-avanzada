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

# Namespace para cert-manager
resource "kubernetes_namespace" "cert_manager" {
  metadata {
    name = var.namespace
    labels = {
      "app.kubernetes.io/name"    = "cert-manager"
      "app.kubernetes.io/managed-by" = "terraform"
    }
  }
}

# Helm release para cert-manager
resource "helm_release" "cert_manager" {
  name       = "cert-manager"
  repository = "https://charts.jetstack.io"
  chart      = "cert-manager"
  version    = var.chart_version
  namespace  = kubernetes_namespace.cert_manager.metadata[0].name

  # Instalar CRDs
  set {
    name  = "installCRDs"
    value = "true"
  }

  set {
    name  = "global.leaderElection.namespace"
    value = var.namespace
  }

  # Configuración de recursos
  set {
    name  = "resources.requests.cpu"
    value = var.cpu_request
  }

  set {
    name  = "resources.requests.memory"
    value = var.memory_request
  }

  set {
    name  = "resources.limits.cpu"
    value = var.cpu_limit
  }

  set {
    name  = "resources.limits.memory"
    value = var.memory_limit
  }

  # Webhook resources
  set {
    name  = "webhook.resources.requests.cpu"
    value = "50m"
  }

  set {
    name  = "webhook.resources.requests.memory"
    value = "64Mi"
  }

  set {
    name  = "webhook.resources.limits.cpu"
    value = "100m"
  }

  set {
    name  = "webhook.resources.limits.memory"
    value = "128Mi"
  }

  # Cainjector resources
  set {
    name  = "cainjector.resources.requests.cpu"
    value = "50m"
  }

  set {
    name  = "cainjector.resources.requests.memory"
    value = "64Mi"
  }

  set {
    name  = "cainjector.resources.limits.cpu"
    value = "100m"
  }

  set {
    name  = "cainjector.resources.limits.memory"
    value = "128Mi"
  }

  depends_on = [kubernetes_namespace.cert_manager]
}

# ClusterIssuer para Let's Encrypt Staging
resource "kubernetes_manifest" "letsencrypt_staging" {
  manifest = {
    apiVersion = "cert-manager.io/v1"
    kind       = "ClusterIssuer"
    metadata = {
      name = "letsencrypt-staging"
    }
    spec = {
      acme = {
        # Let's Encrypt staging server
        server = "https://acme-staging-v02.api.letsencrypt.org/directory"
        email  = var.letsencrypt_email
        
        # Usar Kubernetes secrets para almacenar la cuenta ACME
        privateKeySecretRef = {
          name = "letsencrypt-staging-account-key"
        }
        
        # Usar HTTP-01 challenge
        solvers = [
          {
            http01 = {
              ingress = {
                class = var.ingress_class
              }
            }
          }
        ]
      }
    }
  }

  depends_on = [helm_release.cert_manager]
}

# ClusterIssuer para Let's Encrypt Production
resource "kubernetes_manifest" "letsencrypt_prod" {
  manifest = {
    apiVersion = "cert-manager.io/v1"
    kind       = "ClusterIssuer"
    metadata = {
      name = "letsencrypt-prod"
    }
    spec = {
      acme = {
        # Let's Encrypt production server
        server = "https://acme-v02.api.letsencrypt.org/directory"
        email  = var.letsencrypt_email
        
        # Usar Kubernetes secrets para almacenar la cuenta ACME
        privateKeySecretRef = {
          name = "letsencrypt-prod-account-key"
        }
        
        # Usar HTTP-01 challenge
        solvers = [
          {
            http01 = {
              ingress = {
                class = var.ingress_class
              }
            }
          }
        ]
      }
    }
  }

  depends_on = [helm_release.cert_manager]
}

# Esperar a que cert-manager esté listo
resource "time_sleep" "wait_for_cert_manager" {
  depends_on = [helm_release.cert_manager]
  
  create_duration = "30s"
}

