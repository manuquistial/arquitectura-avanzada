# =============================================================================
# SECURITY LAYER - KEY VAULT AND IDENTITIES
# =============================================================================

# Consume base outputs
data "terraform_remote_state" "base" {
  backend = "local"
  config = {
    path = "../base/terraform.tfstate"
  }
}

# Current tenant info
data "azurerm_client_config" "current" {}

# Detect current public IP to allow Terraform client through Key Vault firewall
data "http" "current_ip" {
  url = "https://ipv4.icanhazip.com"
}

# If a fixed allowlist is provided, use it. Otherwise, fallback to current IP
locals {
  resolved_kv_allow_ips = length(var.keyvault_allowed_ip_rules) > 0 ? var.keyvault_allowed_ip_rules : [format("%s/32", chomp(data.http.current_ip.response_body))]
}

# Key Vault module (reusing platform module)
module "keyvault" {
  source = "../platform/modules/security/keyvault"

  keyvault_name                = var.keyvault_name
  location                     = data.terraform_remote_state.base.outputs.location
  resource_group_name          = data.terraform_remote_state.base.outputs.resource_group_name
  environment                  = var.environment
  sku_name                     = var.keyvault_sku_name
  purge_protection_enabled     = var.keyvault_purge_protection_enabled
  soft_delete_retention_days   = var.keyvault_soft_delete_retention_days
  network_acls_default_action  = var.keyvault_network_acls_default_action
  network_acls_bypass          = var.keyvault_network_acls_bypass
  allowed_subnet_ids           = [data.terraform_remote_state.base.outputs.aks_subnet_id]
  # Use fixed list if provided, otherwise detected current IP
  allowed_ip_rules             = local.resolved_kv_allow_ips

  # No AKS yet in this layer; leave defaults (module must be conditional for AKS roles)
  aks_managed_identity_principal_id = ""
  aks_kubelet_identity_principal_id = ""
  aks_oidc_issuer_url               = null

  initial_secrets = {}
}


