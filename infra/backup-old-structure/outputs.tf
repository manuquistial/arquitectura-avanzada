output "resource_group_name" {
  description = "Resource group name"
  value       = azurerm_resource_group.main.name
}

# Azure Key Vault Outputs
output "key_vault_id" {
  description = "ID of the Azure Key Vault"
  value       = var.keyvault_enabled ? module.keyvault[0].key_vault_id : null
}

output "key_vault_name" {
  description = "Name of the Azure Key Vault"
  value       = var.keyvault_enabled ? module.keyvault[0].key_vault_name : null
}

output "key_vault_uri" {
  description = "URI of the Azure Key Vault"
  value       = var.keyvault_enabled ? module.keyvault[0].key_vault_uri : null
}

output "external_secrets_identity_client_id" {
  description = "Client ID of the Managed Identity for External Secrets Operator"
  value       = var.keyvault_enabled ? module.keyvault[0].external_secrets_identity_client_id : null
}

output "external_secrets_identity_principal_id" {
  description = "Principal ID of the Managed Identity for External Secrets Operator"
  value       = var.keyvault_enabled ? module.keyvault[0].external_secrets_identity_principal_id : null
}

output "aks_cluster_name" {
  description = "AKS cluster name"
  value       = module.aks.cluster_name
}

output "aks_cluster_id" {
  description = "AKS cluster ID"
  value       = module.aks.cluster_id
}

output "aks_kube_config" {
  description = "AKS kubeconfig - SENSITIVE, use az aks get-credentials instead"
  value       = module.aks.kube_config
  sensitive   = true
}

output "postgresql_fqdn" {
  description = "PostgreSQL server FQDN"
  value       = module.postgresql.fqdn
}

output "postgresql_admin_username" {
  description = "PostgreSQL admin username"
  value       = var.db_admin_username
  sensitive   = true
}

output "postgresql_connection_string" {
  description = "PostgreSQL connection string"
  value       = module.postgresql.connection_string_uri
  sensitive   = true
}

output "postgresql_server_name" {
  description = "PostgreSQL server name"
  value       = module.postgresql.server_name
}

output "postgresql_server_id" {
  description = "PostgreSQL server ID"
  value       = module.postgresql.server_id
}

output "db_admin_password" {
  description = "Database admin password (from variables, for scripts only)"
  value       = var.db_admin_password
  sensitive   = true
}

output "opensearch_username" {
  description = "OpenSearch admin username"
  value       = var.opensearch_username
  sensitive   = true
}

output "opensearch_password" {
  description = "OpenSearch admin password (from variables, for scripts only)"
  value       = var.opensearch_password
  sensitive   = true
}

output "storage_account_name" {
  description = "Storage account name"
  value       = module.storage.storage_account_name
}

output "storage_container_name" {
  description = "Storage container name"
  value       = module.storage.container_name
  sensitive   = false
}

# output "search_endpoint" {
#   description = "Azure Cognitive Search endpoint"
#   value       = module.search.endpoint
# }

# output "search_primary_key" {
#   description = "Azure Cognitive Search primary key"
#   value       = module.search.primary_key
#   sensitive   = true
# }

# Service Bus outputs - REMOVED

# Redis outputs
output "redis_hostname" {
  description = "Azure Cache for Redis hostname"
  value       = var.redis_enabled ? module.redis[0].redis_hostname : null
}

output "redis_port" {
  description = "Azure Cache for Redis port"
  value       = var.redis_enabled ? module.redis[0].redis_port : null
}

output "redis_ssl_port" {
  description = "Azure Cache for Redis SSL port"
  value       = var.redis_enabled ? module.redis[0].redis_ssl_port : null
}

output "redis_primary_key" {
  description = "Azure Cache for Redis primary key"
  value       = var.redis_enabled ? module.redis[0].redis_primary_key : null
  sensitive   = true
}

output "redis_connection_string" {
  description = "Azure Cache for Redis connection string"
  value       = var.redis_enabled ? module.redis[0].redis_connection_string : null
  sensitive   = true
}

output "redis_id" {
  description = "Azure Cache for Redis resource ID"
  value       = var.redis_enabled ? module.redis[0].redis_id : null
}

# output "acr_login_server" {
#   description = "ACR login server"
#   value       = module.acr.login_server
# }

# output "acr_admin_username" {
#   description = "ACR admin username"
#   value       = module.acr.admin_username
#   sensitive   = true
# }

# output "acr_admin_password" {
#   description = "ACR admin password"
#   value       = module.acr.admin_password
#   sensitive   = true
# }

# Key Vault outputs removed - using traditional Kubernetes secrets

output "managed_identity_client_id" {
  description = "Managed Identity Client ID"
  value       = azurerm_user_assigned_identity.aks_identity.client_id
}

output "aks_cluster_principal_id" {
  description = "AKS Cluster System Managed Identity Principal ID"
  value       = module.aks.identity_principal_id
}

output "aks_cluster_identity_type" {
  description = "AKS Cluster Identity Type"
  value       = "SystemAssigned"
}

# Observability outputs - DISABLED for Azure for Students
# output "observability_namespace" {
#   description = "Observability stack namespace"
#   value       = module.observability.namespace
# }
# 
# output "otel_collector_endpoint" {
#   description = "OpenTelemetry Collector endpoint"
#   value       = module.observability.otel_collector_endpoint
# }
# 
# output "prometheus_endpoint" {
#   description = "Prometheus server endpoint"
#   value       = module.observability.prometheus_endpoint
# }

# cert-manager outputs
output "cert_manager_namespace" {
  description = "cert-manager namespace"
  value       = module.cert_manager.namespace
}

output "letsencrypt_staging_issuer" {
  description = "Let's Encrypt staging ClusterIssuer name"
  value       = module.cert_manager.letsencrypt_staging_issuer
}

output "letsencrypt_prod_issuer" {
  description = "Let's Encrypt production ClusterIssuer name"
  value       = module.cert_manager.letsencrypt_prod_issuer
}

# OpenSearch outputs
output "opensearch_endpoint" {
  description = "OpenSearch cluster endpoint"
  value       = module.opensearch.opensearch_endpoint
}

output "opensearch_dashboards_endpoint" {
  description = "OpenSearch Dashboards endpoint"
  value       = module.opensearch.opensearch_dashboards_endpoint
}

output "opensearch_secret_name" {
  description = "Name of the Kubernetes secret containing OpenSearch credentials"
  value       = module.opensearch.secret_name
}

# DNS outputs
output "dns_zone_name" {
  description = "DNS zone name"
  value       = module.dns.dns_zone_name
}

output "app_fqdn" {
  description = "Application fully qualified domain name"
  value       = module.dns.app_fqdn
}

output "dns_nameservers" {
  description = "DNS zone nameservers"
  value       = module.dns.nameservers
}

# Carpeta Ciudadana Application outputs - ENABLED
output "carpeta_ciudadana_namespace" {
  description = "Kubernetes namespace where the application is deployed"
  value       = module.carpeta_ciudadana.namespace
}

output "carpeta_ciudadana_helm_release_name" {
  description = "Helm release name for the application"
  value       = module.carpeta_ciudadana.helm_release_name
}

output "carpeta_ciudadana_helm_release_status" {
  description = "Helm release status for the application"
  value       = module.carpeta_ciudadana.helm_release_status
}

# Azure AD B2C outputs
# Azure AD B2C outputs - REMOVED

# Azure API Management outputs
# Azure API Management outputs - REMOVED (using Front Door instead)

# Azure Front Door outputs
output "frontdoor_endpoint_hostname" {
  description = "Azure Front Door endpoint hostname (HTTPS URL)"
  value       = var.frontdoor_enabled ? module.frontdoor[0].frontdoor_endpoint_hostname : null
}

output "frontdoor_profile_name" {
  description = "Azure Front Door profile name"
  value       = var.frontdoor_enabled ? module.frontdoor[0].frontdoor_profile_name : null
}

output "frontdoor_profile_id" {
  description = "Azure Front Door profile ID"
  value       = var.frontdoor_enabled ? module.frontdoor[0].frontdoor_profile_id : null
}

# KEDA outputs
output "keda_namespace" {
  description = "Namespace where KEDA is installed"
  value       = module.keda.keda_namespace
}

output "keda_release_name" {
  description = "Helm release name for KEDA"
  value       = module.keda.keda_release_name
}

output "keda_version" {
  description = "Installed KEDA version"
  value       = module.keda.keda_version
}

output "keda_status" {
  description = "KEDA Helm release status"
  value       = module.keda.keda_status
}

