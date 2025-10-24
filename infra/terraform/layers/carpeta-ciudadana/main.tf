# Carpeta Ciudadana Application Layer
# Este layer contiene la aplicación principal que consume todos los servicios

# Data sources para obtener información de otros layers
data "terraform_remote_state" "base" {
  backend = "local"
  config = {
    path = "../base/terraform.tfstate"
  }
}

data "terraform_remote_state" "platform" {
  backend = "local"
  config = {
    path = "../platform/terraform.tfstate"
  }
}

data "terraform_remote_state" "external_secrets" {
  backend = "local"
  config = {
    path = "../external-secrets/terraform.tfstate"
  }
}

data "azurerm_client_config" "current" {}

# Carpeta Ciudadana Helm Chart
module "carpeta_ciudadana" {
  source = "./modules/carpeta-ciudadana"

  # Información del cluster
  cluster_name                = data.terraform_remote_state.platform.outputs.aks_cluster_name
  cluster_resource_group_name = data.terraform_remote_state.platform.outputs.resource_group_name
  cluster_oidc_issuer_url     = data.terraform_remote_state.platform.outputs.aks_oidc_issuer_url

  # Configuración de la aplicación
  environment = var.environment
  namespace   = var.namespace

  # Workload Identity
  workload_identity_client_id = data.terraform_remote_state.platform.outputs.aks_managed_identity_client_id
  workload_identity_tenant_id = data.azurerm_client_config.current.tenant_id

  # Configuración de la base de datos
  database_url    = data.terraform_remote_state.platform.outputs.database_connection_string
  postgres_uri    = data.terraform_remote_state.platform.outputs.database_connection_string
  m2m_secret_key  = var.m2m_secret_key
  
  # Variables adicionales de base de datos
  database_host     = data.terraform_remote_state.platform.outputs.database_fqdn
  database_name     = data.terraform_remote_state.platform.outputs.database_name
  database_username = "carpeta_ciudadana_user"
  database_password = "temp_password_123"

  # Configuración de Redis
  redis_host     = data.terraform_remote_state.platform.outputs.redis_hostname
  redis_port     = data.terraform_remote_state.platform.outputs.redis_port
  redis_password = data.terraform_remote_state.platform.outputs.redis_primary_key

  # Configuración de Azure Storage
  azure_storage_account_name    = data.terraform_remote_state.platform.outputs.storage_account_name
  azure_storage_account_key     = data.terraform_remote_state.platform.outputs.storage_account_key
  azure_storage_container_name  = "documents"
  
  # Variables adicionales de storage
  storage_account_name = data.terraform_remote_state.platform.outputs.storage_account_name
  storage_account_key  = data.terraform_remote_state.platform.outputs.storage_account_key
  storage_container    = "documents"

  # Configuración de Key Vault
  key_vault_name = data.terraform_remote_state.platform.outputs.keyvault_name
  key_vault_uri  = data.terraform_remote_state.platform.outputs.key_vault_uri

  # Configuración de External Secrets
  external_secrets_namespace    = data.terraform_remote_state.external_secrets.outputs.external_secrets_namespace
  cluster_secret_store_name     = data.terraform_remote_state.external_secrets.outputs.cluster_secret_store_name

  # Configuración de Ingress
  domain_name = var.domain_name
  enable_tls  = var.enable_tls

  # Frontend configuration
  frontend_url = var.frontend_url
  # nextauth_secret is automatically generated and stored in Azure Key Vault

  # Configuración de Front Door
  frontdoor_enabled           = var.frontdoor_enabled
  frontdoor_frontend_hostname = var.frontdoor_frontend_hostname
  frontdoor_api_hostname       = var.frontdoor_api_hostname
  frontdoor_enable_waf         = var.frontdoor_enable_waf

  # Configuración de CORS
  cors_origins = var.cors_origins

  # Tags
  tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
    Service     = "Carpeta Ciudadana"
  }
}
