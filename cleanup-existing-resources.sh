#!/bin/bash

# Script to clean up existing Kubernetes resources that are causing conflicts
# Run this before redeploying the Helm chart

echo "Cleaning up existing resources..."

# Delete existing services
kubectl delete service carpeta-ciudadana-gateway --ignore-not-found=true
kubectl delete service carpeta-ciudadana-notification --ignore-not-found=true

# Delete existing deployments
kubectl delete deployment carpeta-ciudadana-minticClient --ignore-not-found=true
kubectl delete deployment carpeta-ciudadana-readModels --ignore-not-found=true

# Delete existing HPA
kubectl delete hpa carpeta-ciudadana-notification --ignore-not-found=true

echo "Cleanup completed. You can now redeploy the Helm chart."
