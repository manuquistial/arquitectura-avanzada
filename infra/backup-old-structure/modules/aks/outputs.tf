output "cluster_name" {
  description = "AKS cluster name"
  value       = azurerm_kubernetes_cluster.main.name
}

output "cluster_id" {
  description = "AKS cluster ID"
  value       = azurerm_kubernetes_cluster.main.id
}

output "kube_config" {
  description = "Kubernetes config"
  value       = azurerm_kubernetes_cluster.main.kube_config_raw
  sensitive   = true
}

output "client_certificate" {
  description = "Client certificate"
  value       = azurerm_kubernetes_cluster.main.kube_config[0].client_certificate
  sensitive   = true
}

output "client_key" {
  description = "Client key"
  value       = azurerm_kubernetes_cluster.main.kube_config[0].client_key
  sensitive   = true
}

output "cluster_ca_certificate" {
  description = "Cluster CA certificate"
  value       = azurerm_kubernetes_cluster.main.kube_config[0].cluster_ca_certificate
  sensitive   = true
}

output "cluster_endpoint" {
  description = "Kubernetes cluster endpoint"
  value       = azurerm_kubernetes_cluster.main.kube_config[0].host
}

output "host" {
  description = "Kubernetes host"
  value       = azurerm_kubernetes_cluster.main.kube_config[0].host
}

output "identity_principal_id" {
  description = "AKS identity principal ID"
  value       = azurerm_kubernetes_cluster.main.identity[0].principal_id
}

output "managed_identity_principal_id" {
  description = "AKS managed identity principal ID (alias for identity_principal_id)"
  value       = azurerm_kubernetes_cluster.main.identity[0].principal_id
}

output "oidc_issuer_url" {
  description = "OIDC issuer URL (for Workload Identity)"
  value       = azurerm_kubernetes_cluster.main.oidc_issuer_url
}

output "kubelet_identity_object_id" {
  description = "Kubelet identity object ID"
  value       = azurerm_kubernetes_cluster.main.kubelet_identity[0].object_id
}

output "system_nodepool_id" {
  description = "System node pool ID"
  value       = azurerm_kubernetes_cluster.main.default_node_pool[0].name
}

output "user_nodepool_id" {
  description = "User node pool ID"
  value       = azurerm_kubernetes_cluster_node_pool.user.id
}

output "spot_nodepool_id" {
  description = "Spot node pool ID (if enabled)"
  value       = var.enable_spot_nodepool ? azurerm_kubernetes_cluster_node_pool.spot[0].id : null
}

output "node_resource_group" {
  description = "Node resource group name (MC_*)"
  value       = azurerm_kubernetes_cluster.main.node_resource_group
}

