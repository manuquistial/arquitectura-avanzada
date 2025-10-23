# Carpeta Ciudadana Application Module
# Deploys the main application Helm chart with all services

terraform {
  required_providers {
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.12"
    }
  }
}

# Create namespace for the application
resource "kubernetes_namespace" "app" {
  count = var.create_namespace ? 1 : 0

  metadata {
    name = var.namespace
    labels = {
      name = var.namespace
      app  = "carpeta-ciudadana"
    }
  }
}

# Secrets are now managed by Azure Key Vault + External Secrets Operator
# No need for manual Kubernetes secrets creation

# Deploy the main application Helm chart
resource "helm_release" "carpeta_ciudadana" {
  name      = "carpeta-ciudadana"
  chart     = var.chart_path
  namespace = var.namespace
  version   = var.chart_version

  # Values from variables
  values = [
    yamlencode({
      global = {
        environment         = var.environment
        imageRegistry       = var.image_registry
        imagePullPolicy     = var.image_pull_policy
        logLevel            = var.log_level
        useWorkloadIdentity = var.use_workload_identity

        workloadIdentity = {
          clientId = var.workload_identity_client_id
          tenantId = var.workload_identity_tenant_id
        }

        # Using Azure Key Vault + External Secrets Operator

        azureB2C = {
          enabled = var.azure_b2c_enabled
        }

        m2mAuth = {
          enabled    = var.m2m_auth_enabled
          secretName = var.m2m_secret_name
          secretKey  = var.m2m_secret_key
        }

        resourceOptimization = {
          enabled     = var.resource_optimization_enabled
          maxReplicas = var.max_replicas
          defaultRequests = {
            cpu    = var.default_cpu_request
            memory = var.default_memory_request
          }
          defaultLimits = {
            cpu    = var.default_cpu_limit
            memory = var.default_memory_limit
          }
        }

        security = {
          hstsEnabled  = var.hsts_enabled
          cspEnabled   = var.csp_enabled
          cspReportUri = var.csp_report_uri
        }
      }

      migrations = {
        enabled = var.migrations_enabled
      }

      # servicebus - REMOVED

      corsOrigins = var.cors_origins

      # Service configurations
      frontend       = var.frontend_config
      citizen        = var.citizen_config
      ingestion      = var.ingestion_config
      signature      = var.signature_config
      metadata       = var.metadata_config
      transfer       = var.transfer_config
      readModels     = var.read_models_config
      minticClient   = var.mintic_client_config
      transferWorker = var.transfer_worker_config

      # Azure configuration
      azure = {
        storage = {
          accountName   = var.azure_storage_account_name
          accountKey    = var.azure_storage_account_key
          containerName = var.azure_storage_container_name
        }
      }

      # Database configuration - Using Private Endpoint
      database = {
        url = var.database_url
        postgresUri = var.postgres_uri
      }

      # MinTIC configuration
      mintic = {
        hubUrl       = var.mintic_hub_url
        operatorId   = var.mintic_operator_id
        operatorName = var.mintic_operator_name
      }
    })
  ]

  # Wait for deployment to complete
  wait            = true
  timeout         = var.timeout
  atomic          = true
  cleanup_on_fail = true

  depends_on = [
    kubernetes_namespace.app
  ]
}
