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
          "azure.workload.identity/client-id" = var.aks_managed_identity_client_id
        }
      }
      
      webhook = {
        serviceAccount = {
          annotations = {
            "azure.workload.identity/client-id" = var.aks_managed_identity_client_id
          }
        }
      }
      
      certController = {
        serviceAccount = {
          annotations = {
            "azure.workload.identity/client-id" = var.aks_managed_identity_client_id
          }
        }
      }
    })
  ]

  depends_on = [
    var.aks_managed_identity_principal_id
  ]
}

# Esperar a que los CRDs se instalen
resource "time_sleep" "wait_for_crds" {
  depends_on = [
    helm_release.external_secrets
  ]
  
  create_duration = "30s"
}

# ClusterSecretStore para Azure Key Vault
resource "kubernetes_manifest" "cluster_secret_store" {
  depends_on = [
    time_sleep.wait_for_crds
  ]
  
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
}

# Aplicar configuración de External Secrets usando template
resource "kubernetes_manifest" "azure_keyvault_secrets" {
  depends_on = [
    time_sleep.wait_for_crds,
    kubernetes_manifest.cluster_secret_store
  ]
  
  manifest = yamldecode(templatefile("${path.module}/templates/azure-keyvault-secrets.yaml.tpl", {
    keyvault_uri = "https://${var.keyvault_name}.vault.azure.net/"
  }))
}

# Data source para obtener información del tenant
data "azurerm_client_config" "current" {}
