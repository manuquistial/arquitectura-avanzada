# Importar Recursos Existentes

Si ya tienes recursos creados en Azure que quieres gestionar con Terraform, necesitas importarlos al state.

## Resource Group

```bash
# Check if exists
az group show --name carpeta-ciudadana-dev-rg

# Import to Terraform
terraform import azurerm_resource_group.main /subscriptions/{SUBSCRIPTION_ID}/resourceGroups/carpeta-ciudadana-dev-rg
```

## AKS Cluster

```bash
terraform import module.aks.azurerm_kubernetes_cluster.main /subscriptions/{SUBSCRIPTION_ID}/resourceGroups/carpeta-ciudadana-dev-rg/providers/Microsoft.ContainerService/managedClusters/carpeta-ciudadana-dev
```

## PostgreSQL

```bash
terraform import module.postgresql.azurerm_postgresql_flexible_server.main /subscriptions/{SUBSCRIPTION_ID}/resourceGroups/carpeta-ciudadana-dev-rg/providers/Microsoft.DBforPostgreSQL/flexibleServers/dev-psql-server
```

## Storage Account

```bash
terraform import module.storage.azurerm_storage_account.main /subscriptions/{SUBSCRIPTION_ID}/resourceGroups/carpeta-ciudadana-dev-rg/providers/Microsoft.Storage/storageAccounts/devcarpetastorage
```

## Service Bus

```bash
terraform import module.servicebus.azurerm_servicebus_namespace.carpeta /subscriptions/{SUBSCRIPTION_ID}/resourceGroups/carpeta-ciudadana-dev-rg/providers/Microsoft.ServiceBus/namespaces/dev-carpeta-servicebus
```

## Automated Import Script

```bash
#!/bin/bash
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
ENVIRONMENT="dev"
RG_NAME="carpeta-ciudadana-${ENVIRONMENT}-rg"

# Import resource group
if az group show --name $RG_NAME &>/dev/null; then
  echo "Importing resource group..."
  terraform import azurerm_resource_group.main /subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RG_NAME}
fi

# Add more imports as needed
```

## CI/CD Integration

The deployment pipeline automatically attempts to import the resource group if it exists. See `.github/workflows/deploy.yml`.
