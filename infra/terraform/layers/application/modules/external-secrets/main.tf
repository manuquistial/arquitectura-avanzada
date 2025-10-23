# =============================================================================
# EXTERNAL SECRETS OPERATOR MODULE
# =============================================================================
# Módulo para desplegar External Secrets Operator
# =============================================================================

# External Secrets Operator via Helm
resource "helm_release" "external_secrets" {
  name       = "external-secrets"
  repository = "https://charts.external-secrets.io"
  chart      = "external-secrets"
  version    = var.chart_version
  namespace  = var.namespace

  create_namespace = true

  values = [
    yamlencode({
      installCRDs = true
      
      serviceAccount = {
        annotations = {
          "azure.workload.identity/client-id" = var.aks_managed_identity_principal_id
        }
      }
      
      webhook = {
        serviceAccount = {
          annotations = {
            "azure.workload.identity/client-id" = var.aks_managed_identity_principal_id
          }
        }
      }
      
      certController = {
        serviceAccount = {
          annotations = {
            "azure.workload.identity/client-id" = var.aks_managed_identity_principal_id
          }
        }
      }
    })
  ]

  depends_on = [
    var.aks_managed_identity_principal_id
  ]
}

# ClusterSecretStore para Azure Key Vault
resource "kubernetes_manifest" "cluster_secret_store" {
  manifest = {
    apiVersion = "external-secrets.io/v1beta1"
    kind       = "ClusterSecretStore"
    metadata = {
      name = "azure-keyvault"
    }
    spec = {
      provider = {
        azurekv = {
          tenantId = data.azurerm_client_config.current.tenant_id
          vaultUrl = "https://${var.keyvault_name}.vault.azure.net/"
          authType = "WorkloadIdentity"
          serviceAccountRef = {
            name      = "external-secrets"
            namespace = var.namespace
          }
        }
      }
    }
  }

  depends_on = [helm_release.external_secrets]
}

# Data source para obtener información del tenant
data "azurerm_client_config" "current" {}
