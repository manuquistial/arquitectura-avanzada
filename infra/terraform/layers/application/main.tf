# =============================================================================
# APPLICATION LAYER - APLICACIONES Y SERVICIOS
# =============================================================================
# Esta capa contiene las aplicaciones y servicios que se ejecutan en la plataforma:
# - Carpeta Ciudadana Application
# - cert-manager
# - KEDA
# - OpenSearch
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

# OpenSearch deployment
module "opensearch" {
  source = "./modules/opensearch"
  
  opensearch_username = var.opensearch_username
  opensearch_password = var.opensearch_password
  
  depends_on = [
    data.terraform_remote_state.platform
  ]
}

# Carpeta Ciudadana Application (main services)
module "carpeta_ciudadana" {
  source = "./modules/carpeta-ciudadana/carpeta-ciudadana"

  # Namespace configuration
  namespace         = "${var.project_name}-${var.environment}"
  create_namespace  = true
  
  # Chart configuration
  chart_path    = "../../../deploy/helm/carpeta-ciudadana"
  chart_version = "0.1.0"
  timeout       = 600
  
  # Global configuration
  environment         = var.environment
  image_registry      = "manuelquistial"
  image_pull_policy   = "IfNotPresent"
  log_level           = "INFO"
  
  # Workload Identity
  use_workload_identity        = true
  workload_identity_client_id  = data.terraform_remote_state.platform.outputs.aks_managed_identity_client_id
  workload_identity_tenant_id  = data.azurerm_client_config.current.tenant_id
  
  # Feature flags
  m2m_auth_enabled     = true
  migrations_enabled   = true
  
  # Resource optimization
  resource_optimization_enabled = true
  max_replicas                  = 2
  default_cpu_request           = "100m"
  default_memory_request        = "128Mi"
  default_cpu_limit             = "300m"
  default_memory_limit          = "512Mi"
  
  # Security configuration
  cors_origins   = "http://localhost:3000,http://localhost:3001"
  hsts_enabled   = false
  csp_enabled    = true
  csp_report_uri = ""
  
  # Database configuration - Using Private Endpoint
  database_url    = data.terraform_remote_state.platform.outputs.database_connection_string
  postgres_uri    = data.terraform_remote_state.platform.outputs.database_connection_string
  m2m_secret_key  = var.m2m_secret_key
  
  # Azure configuration
  azure_storage_account_name    = data.terraform_remote_state.platform.outputs.storage_account_name
  azure_storage_account_key     = data.terraform_remote_state.platform.outputs.storage_account_key
  azure_storage_container_name  = "documents"
  
  # MinTIC configuration
  mintic_hub_url      = "https://govcarpeta-apis-4905ff3c005b.herokuapp.com"
  mintic_operator_id  = "demo-operator"
  mintic_operator_name = "Demo Operator"

  depends_on = [
    data.terraform_remote_state.platform,
    data.terraform_remote_state.external_secrets,
    module.keda,
    module.cert_manager,
    module.opensearch
  ]
}

# Data source para obtener outputs de External Secrets
data "terraform_remote_state" "external_secrets" {
  backend = "local"
  config = {
    path = "../external-secrets/terraform.tfstate"
  }
}

# Azure Front Door (HTTPS Gateway) - Moved from PLATFORM LAYER
module "frontdoor" {
  count  = var.frontdoor_enabled ? 1 : 0
  source = "./modules/frontdoor"

  environment         = var.environment
  resource_group_name = "carpeta-ciudadana-production-rg"
  frontend_hostname   = var.frontdoor_frontend_hostname
  api_hostname        = var.frontdoor_api_hostname
  enable_waf          = var.frontdoor_enable_waf
  
  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "Terraform"
    Layer       = "Application"
  }
  
  depends_on = [module.carpeta_ciudadana]
}
