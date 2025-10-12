# GitHub Actions Workflows

Este directorio contiene los workflows de CI/CD para el proyecto Carpeta Ciudadana.

## Workflows Disponibles

### 1. `ci.yml` - Continuous Integration

**Trigger**: Push a cualquier branch, Pull Requests

**Acciones**:
- Linting de código Python (ruff)
- Tests unitarios
- Build de imágenes Docker (opcional)
- Validación de Terraform

**No despliega** a infraestructura real.

### 2. `deploy.yml` - Continuous Deployment

**Trigger**: 
- Push a `main`/`master`
- Workflow manual (workflow_dispatch)

**Ambientes**:
- `dev` (default)
- `staging`
- `prod`

**Pasos**:

#### Job 1: `terraform` - Deploy Infrastructure
1. Checkout código
2. Setup Terraform
3. Azure login
4. Terraform init
5. Crear `terraform.tfvars` desde GitHub Secrets
6. Terraform plan
7. Terraform apply
8. Exportar outputs (sensibles a artifacts, no sensibles a GITHUB_OUTPUT)

#### Job 2: `deploy-app` - Deploy Application
1. Checkout código
2. Download Terraform outputs (artifacts)
3. Azure login
4. Get AKS credentials
5. Setup Helm
6. Install Nginx Ingress Controller (si no existe)
7. **Crear Kubernetes Secrets** desde Terraform outputs
8. Deploy con Helm
9. Verificación de deployment
10. Obtener URLs de acceso

## Secrets Requeridos en GitHub

### Azure
- `AZURE_CREDENTIALS`: Credenciales de Service Principal para Azure
  ```json
  {
    "clientId": "...",
    "clientSecret": "...",
    "subscriptionId": "...",
    "tenantId": "..."
  }
  ```

### Database
- `DB_ADMIN_USERNAME`: Usuario admin de PostgreSQL
- `DB_ADMIN_PASSWORD`: Password del admin

### OpenSearch
- `OPENSEARCH_PASSWORD`: Password de OpenSearch admin

### cert-manager
- `LETSENCRYPT_EMAIL`: Email para notificaciones de Let's Encrypt

### Opcional
- `DOMAIN_NAME`: Dominio (si lo tienes)
- `REDIS_PASSWORD`: Password de Redis (si usas Azure Cache)
- `SMTP_HOST`: Servidor SMTP
- `SMTP_PORT`: Puerto SMTP
- `SMTP_USER`: Usuario SMTP
- `SMTP_PASSWORD`: Password SMTP
- `SMTP_FROM`: Email remitente
- `ACS_ENDPOINT`: Azure Communication Services endpoint
- `ACS_KEY`: Azure Communication Services key

## Configurar Secrets en GitHub

```bash
# En tu repositorio de GitHub
Settings → Secrets and variables → Actions → New repository secret

# O con GitHub CLI
gh secret set AZURE_CREDENTIALS < azure-credentials.json
gh secret set DB_ADMIN_USERNAME -b"psqladmin"
gh secret set DB_ADMIN_PASSWORD -b"YourStrongPassword"
gh secret set OPENSEARCH_PASSWORD -b"YourOpenSearchPassword"
gh secret set LETSENCRYPT_EMAIL -b"your-email@example.com"
```

## Crear Azure Service Principal

```bash
# Crear Service Principal con permisos de Contributor
az ad sp create-for-rbac \
  --name "carpeta-ciudadana-github-actions" \
  --role contributor \
  --scopes /subscriptions/<subscription-id>/resourceGroups/carpeta-ciudadana-dev-rg \
  --sdk-auth

# Copiar el JSON output completo a AZURE_CREDENTIALS en GitHub Secrets
```

## Flujo de Despliegue

```
┌─────────────────────┐
│  Push to main       │
│  or Manual Trigger  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Job: terraform     │
│  ├─ Terraform init  │
│  ├─ Create tfvars   │
│  ├─ Terraform apply │
│  └─ Export outputs  │
└──────────┬──────────┘
           │
           │ Artifacts
           │ (sensitive outputs)
           ▼
┌─────────────────────┐
│  Job: deploy-app    │
│  ├─ Get AKS creds   │
│  ├─ Create Secrets  │◄─── From Terraform outputs
│  ├─ Helm upgrade    │◄─── From GitHub Secrets
│  └─ Verify         │
└─────────────────────┘
```

## Seguridad

### ✅ Secrets NO en logs
- Terraform wrapper: false (no imprime outputs)
- Secrets marcados como `sensitive = true`
- Outputs sensibles en artifacts (encrypted), no en GITHUB_OUTPUT

### ✅ Secrets NO en código
- Todos los valores sensibles desde GitHub Secrets
- `terraform.tfvars` generado en runtime, nunca commiteado
- Connection strings desde Terraform outputs

### ✅ Principle of Least Privilege
- Service Principal con rol mínimo necesario
- Secrets por namespace
- RBAC configurado en AKS

## Debugging Workflows

### Ver logs de un workflow

```bash
# Listar workflows
gh workflow list

# Ver runs recientes
gh run list --workflow=deploy.yml

# Ver logs de un run específico
gh run view <run-id> --log
```

### Re-ejecutar workflow fallido

```bash
# Re-run
gh run rerun <run-id>

# Re-run solo jobs fallidos
gh run rerun <run-id> --failed
```

### Workflow manual

```bash
# Trigger manual
gh workflow run deploy.yml -f environment=dev

# Con staging
gh workflow run deploy.yml -f environment=staging

# Con prod
gh workflow run deploy.yml -f environment=prod
```

## Ambientes de GitHub

Configurar en: `Settings → Environments`

### dev
- **Protection rules**: None
- **Secrets**: Pueden ser diferentes de prod

### staging
- **Protection rules**: Review required (optional)
- **Secrets**: Similares a prod

### prod
- **Protection rules**: 
  - Required reviewers: 1+
  - Wait timer: 5 min
  - Deployment branches: main/master only
- **Secrets**: Producción real

## Best Practices

1. **Nunca commitear secrets**: Usar GitHub Secrets siempre
2. **Revisar plans**: Terraform plan debe ser revisado antes de apply
3. **Ambientes separados**: Dev/Staging/Prod en namespaces diferentes
4. **Rollback**: Helm permite rollback fácil
5. **Monitoring**: Verificar deployment después de aplicar

## Rollback

```bash
# Ver historial de releases
helm history carpeta-ciudadana -n <namespace>

# Rollback a versión anterior
helm rollback carpeta-ciudadana <revision> -n <namespace>

# Rollback a versión anterior inmediata
helm rollback carpeta-ciudadana -n <namespace>
```

## Referencias

- [GitHub Actions Documentation](https://docs.github.com/actions)
- [Helm Documentation](https://helm.sh/docs/)
- [Azure DevOps](https://learn.microsoft.com/azure/devops/)

