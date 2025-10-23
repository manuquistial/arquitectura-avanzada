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
        }
      }
      
      webhook = {
        serviceAccount = {
          annotations = {
            "azure.workload.identity/client-id" = data.terraform_remote_state.platform.outputs.aks_managed_identity_client_id
          }
        }
      }
      
      certController = {
        serviceAccount = {
          annotations = {
            "azure.workload.identity/client-id" = data.terraform_remote_state.platform.outputs.aks_managed_identity_client_id
          }
        }
      }
    })
  ]

  depends_on = [
    data.terraform_remote_state.platform
  ]
  
  # Configurar para esperar a que esté completamente listo
  wait = true
  timeout = 600
}

# Verificar que los CRDs estén disponibles usando data source
data "external" "crd_ready" {
  depends_on = [helm_release.external_secrets]
  
  program = ["bash", "-c", <<-EOT
    echo "Checking if External Secrets CRDs are ready..."
    if kubectl get crd clustersecretstores.external-secrets.io >/dev/null 2>&1; then
      echo '{"ready": "true"}'
    else
      echo '{"ready": "false"}'
    fi
  EOT
]

# ClusterSecretStore para Azure Key Vault
resource "kubernetes_manifest" "cluster_secret_store" {
  depends_on = [
    data.external.crd_ready,
    kubernetes_secret.azure_credentials
  ]
  
  lifecycle {
    # Ignorar errores de CRD no disponible en el primer plan
    ignore_changes = [manifest]
  }
  
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
          vaultUrl = data.terraform_remote_state.platform.outputs.key_vault_uri
          authSecretRef = {
            clientId = {
              name = "azure-credentials"
              key  = "client-id"
            }
            clientSecret = {
              name = "azure-credentials"
              key  = "client-secret"
            }
          }
        }
      }
    }
  }
}

# Secret para credenciales de Azure
resource "kubernetes_secret" "azure_credentials" {
  metadata {
    name      = "azure-credentials"
    namespace = var.namespace
  }

  data = {
    client-id     = data.terraform_remote_state.platform.outputs.aks_managed_identity_client_id
    client-secret = data.terraform_remote_state.platform.outputs.aks_managed_identity_principal_id
  }

  type = "Opaque"
}
