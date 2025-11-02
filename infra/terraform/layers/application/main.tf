# =============================================================================
# APPLICATION LAYER - APLICACIONES Y SERVICIOS
# =============================================================================
# Esta capa contiene las aplicaciones y servicios que se ejecutan en la plataforma:
# - Carpeta Ciudadana Application
# - cert-manager
# - KEDA
# - External Secrets Operator
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

# =============================================================================
# ROLE ASSIGNMENTS - Resolver dependencias circulares
# =============================================================================

# Asignar rol "Key Vault Secrets User" al Managed Identity de AKS
# Movido aquí para evitar dependencia circular entre PLATFORM y APPLICATION
resource "azurerm_role_assignment" "aks_to_keyvault" {
  scope                = data.terraform_remote_state.platform.outputs.key_vault_id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = data.terraform_remote_state.platform.outputs.aks_managed_identity_principal_id
  
  description = "Permite a AKS leer secrets del Key Vault"
}

# Asignar rol "Key Vault Secrets User" al Kubelet Identity (Agent Pool)
# Necesario para External Secrets Operator con Workload Identity
resource "azurerm_role_assignment" "aks_kubelet_to_keyvault" {
  scope                = data.terraform_remote_state.platform.outputs.key_vault_id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = data.terraform_remote_state.platform.outputs.aks_kubelet_identity_principal_id
  
  description = "Permite al AKS Kubelet Identity (Agent Pool) leer secrets del Key Vault para External Secrets"
}

# KEDA (Kubernetes Event-Driven Autoscaling)
module "keda" {
  source = "./modules/keda"

  keda_version                  = var.keda_version
  keda_namespace                = var.keda_namespace
  app_namespace                 = "${var.project_name}-${var.environment}"
  replica_count                 = var.keda_replica_count
  enable_prometheus_monitoring  = false

  depends_on = [data.terraform_remote_state.platform]
}

# cert-manager deployment via Helm
module "cert_manager" {
  source = "./modules/cert-manager"

  namespace          = var.cert_manager_namespace
  chart_version      = var.cert_manager_chart_version
  letsencrypt_email  = var.letsencrypt_email
  ingress_class      = var.cert_manager_ingress_class
  cpu_request        = var.cert_manager_cpu_request
  cpu_limit          = var.cert_manager_cpu_limit
  memory_request     = var.cert_manager_memory_request
  memory_limit       = var.cert_manager_memory_limit

  depends_on = [data.terraform_remote_state.platform]
}


# =============================================================================
# CARPETA CIUDADANA APPLICATION - MOVED TO SEPARATE LAYER
# =============================================================================
# Carpeta Ciudadana application has been moved to its own layer:
# - layers/carpeta-ciudadana/
# This provides better separation of concerns and allows independent deployment
# =============================================================================

# Data source para obtener outputs de External Secrets
data "terraform_remote_state" "external_secrets" {
  backend = "local"
  config = {
    path = "../external-secrets/terraform.tfstate"
  }
}

# Azure Front Door (HTTPS Gateway) - MOVED BACK TO PLATFORM LAYER
# Front Door es infraestructura de red y no necesita dependencias de aplicaciones
# Se movió a PLATFORM layer para mejor organización y despliegue más rápido

# =============================================================================
# APPLICATION SECRETS
# =============================================================================
# Maneja los secrets específicos de la aplicación:
# - M2M Authentication
# - JWT
# - NextAuth
# - API Keys
# =============================================================================

module "application_secrets" {
  source = "./modules/application-secrets"

  key_vault_id = data.terraform_remote_state.platform.outputs.key_vault_id
  environment  = var.environment
  nextauth_url = "https://app.carpeta-ciudadana.dev"

  depends_on = [data.terraform_remote_state.platform]
}

# =============================================================================
# EXTERNAL SECRETS CONFIG (CRDs ya instalados por EXTERNAL-SECRETS layer)
# =============================================================================

# Secret con credenciales/IDs para autenticación (si usas Workload Identity, puedes omitirlo)
resource "kubernetes_secret" "azure_credentials" {
  metadata {
    name      = "azure-credentials"
    namespace = var.external_secrets_namespace
  }

  data = {
    client-id     = data.terraform_remote_state.platform.outputs.aks_managed_identity_client_id
    client-secret = data.terraform_remote_state.platform.outputs.aks_managed_identity_principal_id
  }

  type = "Opaque"
}

# ClusterSecretStore apuntando a Key Vault
resource "kubernetes_manifest" "cluster_secret_store" {
  depends_on = [
    kubernetes_secret.azure_credentials
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
