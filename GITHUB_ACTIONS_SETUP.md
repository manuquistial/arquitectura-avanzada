# ⚡ GitHub Actions - Setup Rápido para Deployment Automático

**TL;DR**: ¿Con solo push a master se despliega todo? **SÍ**, pero primero configura estos 11 secrets (una vez).

---

## 🎯 Respuesta Rápida

### ¿Se Despliega Automáticamente con Push?

**✅ SÍ**, después de configurar GitHub Secrets (primera vez).

### Proceso

```
┌─────────────────────────────────────┐
│ PRIMERA VEZ (30-60 min)             │
│ ⚙️  Configurar 11 GitHub Secrets    │
└──────────────┬──────────────────────┘
               │ (una sola vez)
               ▼
┌─────────────────────────────────────┐
│ CADA DEPLOYMENT (10 segundos)       │
│ 📝 git push origin master           │
└──────────────┬──────────────────────┘
               │ (automático)
               ▼
┌─────────────────────────────────────┐
│ GITHUB ACTIONS (35 min)             │
│ 🤖 Build → Test → Deploy           │
│    TODO AUTOMÁTICO                  │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ ✅ SISTEMA EN AZURE                 │
│    13 servicios corriendo           │
│    URLs públicas disponibles        │
└─────────────────────────────────────┘
```

---

## 🔑 Secrets a Configurar (11 Críticos + 4 Opcionales)

### ✅ Críticos (Necesarios para deployment)

**Copiar y pegar en GitHub → Settings → Secrets → New secret**:

#### Azure (4 secrets)

1. **AZURE_CREDENTIALS**
   ```bash
   # Generar:
   az ad sp create-for-rbac --name "carpeta-sp" --role contributor \
     --scopes /subscriptions/TU_SUBSCRIPTION_ID --sdk-auth
   
   # Copiar TODO el JSON output → pegar en GitHub Secret
   ```

2. **AZURE_CLIENT_ID**
   ```bash
   # Del JSON anterior, copiar el valor de "clientId"
   ```

3. **AZURE_TENANT_ID**
   ```bash
   # Del JSON anterior, copiar el valor de "tenantId"
   ```

4. **AZURE_SUBSCRIPTION_ID**
   ```bash
   # Ver tu subscription:
   az account show --query id -o tsv
   ```

#### Docker Hub (2 secrets)

5. **DOCKERHUB_USERNAME**
   ```
   tu_username_dockerhub
   ```

6. **DOCKERHUB_TOKEN**
   ```bash
   # Docker Hub → Account Settings → Security → New Access Token
   # Name: "GitHub Actions"
   # Permissions: Read & Write
   # Generate → COPIAR token
   ```

#### Passwords (3 secrets)

7. **DB_ADMIN_USERNAME**
   ```
   pgadmin
   ```

8. **DB_ADMIN_PASSWORD**
   ```bash
   # Generar password seguro:
   openssl rand -base64 32
   ```

9. **REDIS_PASSWORD**
   ```bash
   openssl rand -base64 32
   ```

#### Services (2 secrets)

10. **OPENSEARCH_PASSWORD**
    ```bash
    openssl rand -base64 32
    ```

11. **LETSENCRYPT_EMAIL**
    ```
    tu_email@ejemplo.com
    ```

---

### ⚠️ Opcionales (Para notificaciones email)

12. **SMTP_HOST** - ej: `smtp.gmail.com`
13. **SMTP_USER** - ej: `tu_email@gmail.com`
14. **SMTP_PASSWORD** - Gmail App Password
15. **SMTP_FROM** - ej: `noreply@carpeta.com`

**Si no configuras estos**: El sistema funciona sin notificaciones email.

---

## 🚀 Comando Rápido (5 minutos)

```bash
# Prerequisito: GitHub CLI instalado
gh auth login

# 1. Azure Service Principal
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
SP_JSON=$(az ad sp create-for-rbac --name "carpeta-sp" --role contributor \
  --scopes /subscriptions/$SUBSCRIPTION_ID --sdk-auth)

# 2. Configurar secrets automáticamente
echo "$SP_JSON" > /tmp/azure-creds.json
gh secret set AZURE_CREDENTIALS < /tmp/azure-creds.json
gh secret set AZURE_CLIENT_ID --body "$(echo $SP_JSON | jq -r .clientId)"
gh secret set AZURE_TENANT_ID --body "$(echo $SP_JSON | jq -r .tenantId)"
gh secret set AZURE_SUBSCRIPTION_ID --body "$SUBSCRIPTION_ID"
rm /tmp/azure-creds.json

# 3. Docker Hub (MANUAL: Ve a Docker Hub UI y copia token)
read -p "Docker Hub Username: " DOCKER_USER
read -sp "Docker Hub Token: " DOCKER_TOKEN
gh secret set DOCKERHUB_USERNAME --body "$DOCKER_USER"
gh secret set DOCKERHUB_TOKEN --body "$DOCKER_TOKEN"

# 4. Passwords (generados automáticamente)
gh secret set DB_ADMIN_USERNAME --body "pgadmin"
gh secret set DB_ADMIN_PASSWORD --body "$(openssl rand -base64 32)"
gh secret set REDIS_PASSWORD --body "$(openssl rand -base64 32)"
gh secret set OPENSEARCH_PASSWORD --body "$(openssl rand -base64 32)"

# 5. LetsEncrypt
read -p "Email para certificados SSL: " EMAIL
gh secret set LETSENCRYPT_EMAIL --body "$EMAIL"

echo ""
echo "✅ Secrets configurados!"
echo ""
echo "Ahora puedes hacer:"
echo "  git push origin master"
echo ""
echo "Y GitHub Actions desplegará TODO automáticamente en 35 minutos."
```

---

## 📊 Qué Hace GitHub Actions Automáticamente

```yaml
on:
  push:
    branches: [master]  # ← Se dispara aquí

jobs:
  # 1. Tests (5 min)
  frontend-test: ✅
  backend-test: ✅  # 12 servicios en paralelo
  
  # 2. Security (3 min)
  trivy-scan: ✅
  secrets-scan: ✅
  
  # 3. Build (8 min)
  build-and-push: ✅  # 13 imágenes
  
  # 4. Infrastructure (5 min)
  infra-apply: ✅  # Terraform
    - AKS cluster
    - PostgreSQL
    - Redis
    - Service Bus
    - Blob Storage
    - Key Vault
  
  # 5. Platform (3 min)
  platform-install: ✅
    - Nginx Ingress
    - cert-manager
    - Prometheus/Grafana
    - Loki/Promtail
  
  # 6. Application (10 min)
  create-secrets: ✅  # K8s secrets
  helm-deploy: ✅    # 13 servicios
  
  # 7. Migrations (3 min)
  db-migrations: ✅  # 8 jobs paralelos
  
  # 8. Verify (1 min)
  verify-deployment: ✅

# ⏱️ TOTAL: ~35 minutos
# 👤 TU PARTE: git push (10 segundos)
```

---

## ✅ Checklist de Verificación

### Antes del Primer Push

```bash
# ✅ Verificar secrets configurados
gh secret list

# Deberías ver al menos estos 11:
✅ AZURE_CREDENTIALS
✅ AZURE_CLIENT_ID
✅ AZURE_TENANT_ID
✅ AZURE_SUBSCRIPTION_ID
✅ DOCKERHUB_USERNAME
✅ DOCKERHUB_TOKEN
✅ DB_ADMIN_USERNAME
✅ DB_ADMIN_PASSWORD
✅ REDIS_PASSWORD
✅ OPENSEARCH_PASSWORD
✅ LETSENCRYPT_EMAIL

# Si todos están → ✅ Listo para push
```

### Después del Push

```bash
# 1. Ver workflow corriendo
gh run list
gh run watch  # Ver en tiempo real

# 2. Esperar ~35 minutos

# 3. Cuando termine, verificar
# GitHub Actions → Summary → Ver URLs

# 4. Probar
curl http://INGRESS_IP
curl http://INGRESS_IP/api/health
```

---

## 🎯 FAQ

**P: ¿Necesito correr Terraform manualmente?**  
R: ❌ NO. GitHub Actions lo hace automáticamente.

**P: ¿Necesito construir Docker images manualmente?**  
R: ❌ NO. GitHub Actions las build y push automáticamente.

**P: ¿Necesito configurar kubectl?**  
R: ❌ NO para deployment automático. Sí si quieres verificar manualmente.

**P: ¿Cuánto cuesta Azure?**  
R: ~$35/mes en desarrollo. Azure for Students da $100 gratis (2-5 meses).

**P: ¿Qué pasa si falla el deployment?**  
R: GitHub Actions hace rollback automático. Ver logs en Actions tab.

**P: ¿Puedo usar mi propio dominio?**  
R: ✅ SÍ. Configura secret `DOMAIN_NAME` y actualiza DNS.

**P: ¿Funciona sin SMTP?**  
R: ✅ SÍ. Solo no habrá notificaciones email.

**P: ¿Cuánto tarda el primer deployment?**  
R: 35-40 minutos (crea todo desde cero).

**P: ¿Y los siguientes deployments?**  
R: 20-25 minutos (solo actualiza, no crea).

**P: ¿Puedo deployment a staging primero?**  
R: ✅ SÍ. Push a rama `develop` o usa workflow_dispatch.

---

## 📚 Más Información

**Guía Completa**: [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md) (100+ páginas)

**Workflows Detallados**: [.github/workflows/README.md](../.github/workflows/README.md)

**Troubleshooting**: [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)

---

## ✨ Conclusión

### SÍ, es 100% Automático (Después de Setup)

**Setup Inicial** (UNA VEZ):
```bash
# 1. Configurar 11 GitHub Secrets
# ⏱️ 30-60 minutos
```

**Cada Deployment** (SIEMPRE):
```bash
# 1. git push origin master
# 2. Esperar 35 minutos
# 3. ✅ Sistema desplegado en Azure

# ⏱️ Tu tiempo: 10 segundos
# ⏱️ Tiempo automático: 35 minutos
# 👤 Intervención manual: CERO
```

---

<div align="center">

**🚀 Listo para Desplegar? 🚀**

**1️⃣** Configure secrets → **2️⃣** Push to master → **3️⃣** ¡Listo!

[Ver Guía Completa](./DEPLOYMENT_GUIDE.md)

</div>

---

**Última actualización**: 2025-10-13  
**Versión**: 1.0.0

