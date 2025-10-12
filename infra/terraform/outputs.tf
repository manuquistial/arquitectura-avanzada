output "resource_group_name" {
  description = "Resource group name"
  value       = azurerm_resource_group.main.name
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
  description = "PostgreSQL FQDN"
  value       = module.postgresql.fqdn
}

output "postgresql_admin_username" {
  description = "PostgreSQL admin username"
  value       = module.postgresql.admin_username
  sensitive   = true
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

output "servicebus_connection_string" {
  description = "Service Bus connection string - SENSITIVE"
  value       = module.servicebus.primary_connection_string
  sensitive   = true
}

output "servicebus_namespace_name" {
  description = "Service Bus namespace name"
  value       = module.servicebus.namespace_name
  sensitive   = false
}

output "servicebus_queue_names" {
  description = "Service Bus queue names"
  value       = module.servicebus.queue_names
  sensitive   = false
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

# output "keyvault_uri" {
#   description = "Key Vault URI"
#   value       = module.keyvault.vault_uri
# }

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

# Observability outputs
output "observability_namespace" {
  description = "Observability stack namespace"
  value       = module.observability.namespace
}

output "otel_collector_endpoint" {
  description = "OpenTelemetry Collector endpoint"
  value       = module.observability.otel_collector_endpoint
}

output "prometheus_endpoint" {
  description = "Prometheus server endpoint"
  value       = module.observability.prometheus_endpoint
}

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

