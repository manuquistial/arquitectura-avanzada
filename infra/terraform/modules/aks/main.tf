resource "azurerm_kubernetes_cluster" "main" {
  name                = var.cluster_name
  location            = var.location
  resource_group_name = var.resource_group_name
  dns_prefix          = "${var.cluster_name}-dns"
  
  # Kubernetes version
  kubernetes_version        = var.kubernetes_version
  automatic_channel_upgrade = var.automatic_channel_upgrade
  
  # Private cluster (optional, for production)
  private_cluster_enabled = var.private_cluster_enabled
  
  # Workload Identity (required for Key Vault CSI)
  oidc_issuer_enabled       = true
  workload_identity_enabled = true
  
  # System (default) node pool - For K8s controllers only
  default_node_pool {
    name                = "system"
    node_count          = var.enable_auto_scaling ? null : var.system_node_count
    vm_size             = var.system_vm_size
    vnet_subnet_id      = var.subnet_id
    
    # Auto-scaling
    enable_auto_scaling = var.enable_auto_scaling
    min_count           = var.enable_auto_scaling ? var.system_node_min : null
    max_count           = var.enable_auto_scaling ? var.system_node_max : null
    
    # Zonal deployment (multi-AZ for HA)
    zones = var.availability_zones
    
    # System pool configuration
    only_critical_addons_enabled = true  # Only system pods
    
    # Node labels
    node_labels = {
      "nodepool" = "system"
      "workload" = "system"
    }
    
    # Taints (prevent user workloads)
    node_taints = [
      "CriticalAddonsOnly=true:NoSchedule"
    ]
    
    # OS disk
    os_disk_type    = "Ephemeral"
    os_disk_size_gb = 30
    
    tags = {
      Environment = var.environment
      NodePool    = "system"
    }
  }
  
  # Managed identity
  identity {
    type = "SystemAssigned"
  }
  
  # Network profile - Azure CNI (required for NetworkPolicies)
  network_profile {
    network_plugin    = "azure"  # azure CNI (not kubenet)
    network_policy    = "azure"  # Enable NetworkPolicy support
    load_balancer_sku = "standard"
    service_cidr      = var.service_cidr
    dns_service_ip    = var.dns_service_ip
    
    # Outbound type
    outbound_type = var.outbound_type
  }
  
  # API server access
  api_server_access_profile {
    authorized_ip_ranges = var.authorized_ip_ranges
  }
  
  # Azure AD integration
  azure_active_directory_role_based_access_control {
    azure_rbac_enabled     = true
    admin_group_object_ids = var.admin_group_object_ids
  }
  
  # Maintenance window
  maintenance_window {
    allowed {
      day   = var.maintenance_window_day
      hours = var.maintenance_window_hours
    }
  }
  
  # SKU tier
  sku_tier = var.sku_tier
  
  tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# User node pool - For application workloads
resource "azurerm_kubernetes_cluster_node_pool" "user" {
  name                  = "user"
  kubernetes_cluster_id = azurerm_kubernetes_cluster.main.id
  vm_size               = var.user_vm_size
  vnet_subnet_id        = var.subnet_id
  
  # Auto-scaling
  enable_auto_scaling = true
  min_count           = var.user_node_min
  max_count           = var.user_node_max
  
  # Zonal deployment
  zones = var.availability_zones
  
  # Node labels
  node_labels = {
    "nodepool" = "user"
    "workload" = "applications"
  }
  
  # OS disk
  os_disk_type    = "Ephemeral"
  os_disk_size_gb = 100
  
  tags = {
    Environment = var.environment
    NodePool    = "user"
  }
}

# Spot node pool - For KEDA workers (70% cost savings)
resource "azurerm_kubernetes_cluster_node_pool" "spot" {
  count = var.enable_spot_nodepool ? 1 : 0
  
  name                  = "spot"
  kubernetes_cluster_id = azurerm_kubernetes_cluster.main.id
  vm_size               = var.spot_vm_size
  vnet_subnet_id        = var.subnet_id
  
  # Spot configuration
  priority        = "Spot"
  eviction_policy = "Delete"
  spot_max_price  = var.spot_max_price  # -1 = pay up to regular price
  
  # Auto-scaling
  enable_auto_scaling = true
  min_count           = var.spot_node_min
  max_count           = var.spot_node_max
  
  # Zonal deployment
  zones = var.availability_zones
  
  # Node labels
  node_labels = {
    "nodepool"                                = "spot"
    "workload"                                = "workers"
    "kubernetes.azure.com/scalesetpriority"   = "spot"
  }
  
  # Taints (only spot-tolerant workloads)
  node_taints = [
    "kubernetes.azure.com/scalesetpriority=spot:NoSchedule"
  ]
  
  # OS disk
  os_disk_type    = "Ephemeral"
  os_disk_size_gb = 100
  
  tags = {
    Environment = var.environment
    NodePool    = "spot"
    Priority    = "Spot"
  }
}

# RBAC para workload identity
resource "azurerm_role_assignment" "aks_network" {
  scope                = var.subnet_id
  role_definition_name = "Network Contributor"
  principal_id         = azurerm_kubernetes_cluster.main.identity[0].principal_id
}

