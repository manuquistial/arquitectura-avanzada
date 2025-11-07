# =============================================================================
# EXTERNAL SECRETS LAYER
# =============================================================================
# Capa intermedia para External Secrets Operator
# Se despliega después de PLATFORM, antes de APPLICATION
# =============================================================================

# Data source para obtener outputs de la capa de plataforma
data "terraform_remote_state" "platform" {
  backend = "local"
  config = {
    path = "../platform/terraform.tfstate"
  }
}

# Data source para obtener información del tenant
data "azurerm_client_config" "current" {}

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
          "azure.workload.identity/client-id" = data.terraform_remote_state.platform.outputs.aks_managed_identity_client_id
          "azure.workload.identity/tenant-id" = data.azurerm_client_config.current.tenant_id
        }
      }
      
      webhook = {
        serviceAccount = {
          annotations = {
            "azure.workload.identity/client-id" = data.terraform_remote_state.platform.outputs.aks_managed_identity_client_id
            "azure.workload.identity/tenant-id" = data.azurerm_client_config.current.tenant_id
          }
        }
      }
      
      certController = {
        serviceAccount = {
          annotations = {
            "azure.workload.identity/client-id" = data.terraform_remote_state.platform.outputs.aks_managed_identity_client_id
            "azure.workload.identity/tenant-id" = data.azurerm_client_config.current.tenant_id
          }
        }
      }
    })
  ]

  depends_on = [
    data.terraform_remote_state.platform
  ]
  
  # Configurar para esperar a que esté completamente listo
  wait    = true
  timeout = 900
}

# CRDs y configuración (ClusterSecretStore y secret) se gestionan en APPLICATION LAYER
