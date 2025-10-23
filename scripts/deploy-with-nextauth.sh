#!/bin/bash
# deploy-with-nextauth.sh

# 1. Desplegar infraestructura
terraform apply

# 2. Obtener IP del LoadBalancer
LB_IP=$(kubectl get service frontend -n carpeta-ciudadana-production -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

# 3. Actualizar terraform.tfvars
sed -i "s/PLACEHOLDER_LOADBALANCER_IP/$LB_IP/" infra/terraform/terraform.tfvars

# 4. Aplicar cambio de configuración
terraform apply

echo "NextAuth URL configurado: http://$LB_IP"