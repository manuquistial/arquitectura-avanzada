# Kubernetes Manifests Post-Apply

These manifests need to be applied AFTER the AKS cluster is created and configured.

## Why Not in Terraform?

`kubernetes_manifest` resources require a Kubernetes REST client during `terraform plan`, which is not available until the cluster exists. This creates a circular dependency.

## Apply After Cluster Creation

After `terraform apply` completes and you have configured kubectl:

```bash
# Configure kubectl
az aks get-credentials --resource-group carpeta-ciudadana-dev-rg --name carpeta-ciudadana-dev

# Apply manifests
kubectl apply -f k8s-manifests/
```

## Included Manifests

- `clusterissuer-staging.yaml` - Let's Encrypt staging issuer
- `clusterissuer-prod.yaml` - Let's Encrypt production issuer  
- `keda-triggerauth.yaml` - KEDA Service Bus trigger authentication
- `keda-servicemonitor.yaml` - KEDA Prometheus ServiceMonitor

## Automated Application

These manifests are automatically applied by the Helm chart deployment in CI/CD.
