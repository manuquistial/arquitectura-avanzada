/**
 * Azure Key Vault Provider for Secrets Store CSI Driver
 * 
 * Allows Kubernetes pods to mount secrets from Azure Key Vault as volumes
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

# Install Secrets Store CSI Driver
resource "helm_release" "secrets_store_csi_driver" {
  name       = "csi-secrets-store"
  repository = "https://kubernetes-sigs.github.io/secrets-store-csi-driver/charts"
  chart      = "secrets-store-csi-driver"
  version    = var.csi_driver_version
  namespace  = var.namespace

  create_namespace = true

  values = [
    yamlencode({
      # Linux and Windows support
      linux = {
        enabled = true
      }
      windows = {
        enabled = false
      }

      # Sync secrets to Kubernetes secrets
      syncSecret = {
        enabled = true
      }

      # Enable secret rotation
      enableSecretRotation = var.enable_secret_rotation
      rotationPollInterval = var.rotation_poll_interval

      # Resources
      resources = {
        limits = {
          cpu    = "200m"
          memory = "256Mi"
        }
        requests = {
          cpu    = "50m"
          memory = "128Mi"
        }
      }

      # Node selector (run on all nodes)
      nodeSelector = {}

      # Tolerations (run on all nodes including masters)
      tolerations = []
    })
  ]
}

# Install Azure Key Vault Provider
resource "helm_release" "azure_keyvault_provider" {
  name       = "csi-secrets-store-provider-azure"
  repository = "https://azure.github.io/secrets-store-csi-driver-provider-azure/charts"
  chart      = "csi-secrets-store-provider-azure"
  version    = var.azure_provider_version
  namespace  = var.namespace

  values = [
    yamlencode({
      # Use Workload Identity
      workloadIdentity = {
        enabled = true
      }

      # Resources
      resources = {
        limits = {
          cpu    = "200m"
          memory = "256Mi"
        }
        requests = {
          cpu    = "50m"
          memory = "128Mi"
        }
      }
    })
  ]

  depends_on = [helm_release.secrets_store_csi_driver]
}

