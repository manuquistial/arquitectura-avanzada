# Configurar GitHub Actions para Azure

## 🎯 Problema

Azure for Students no permite crear Service Principals porque requiere permisos de "Directory Administrator".

---

## ✅ Solución 1: Federated Credentials (Recomendado)

**No requiere Service Principal!** Usa Workload Identity Federation (método moderno).

### Ventajas:
- ✅ No requiere permisos de Active Directory
- ✅ Más seguro (sin secrets)
- ✅ Tokens temporales
- ✅ Funciona con Azure for Students

### Paso 1: Ejecutar el script de setup

```bash
~/setup-github-federated-auth.sh
```

Te pedirá:
- Tu usuario GitHub
- Nombre del repositorio

### Paso 2: Configurar GitHub Secrets

Después del script, ejecuta:

```bash
# Copiar los valores que el script te dio:
gh secret set AZURE_CLIENT_ID --body "TU_CLIENT_ID"
gh secret set AZURE_TENANT_ID --body "TU_TENANT_ID"
gh secret set AZURE_SUBSCRIPTION_ID --body "TU_SUBSCRIPTION_ID"

# Si usas Docker Hub (gratis):
gh secret set DOCKERHUB_USERNAME --body "tu_usuario_dockerhub"
gh secret set DOCKERHUB_TOKEN --body "tu_token_dockerhub"
```

### Paso 3: Actualizar el workflow

El archivo ya está creado: `.github/workflows/ci-azure-federated.yml`

¡Listo! Ahora cada push a main desplegará automáticamente.

---

## ✅ Solución 2: Elevar Permisos (Si es cuenta institucional)

Si tu cuenta Azure for Students es de tu universidad:

### Opción A: Contactar IT de la universidad

```
Para: it@tuuniversidad.edu
Asunto: Solicitud de permisos Azure AD para proyecto académico

Hola,

Soy estudiante de [Tu Carrera] y estoy trabajando en un proyecto 
de arquitectura de software que requiere desplegar en Azure.

Necesito permisos para crear Service Principals en Azure AD 
para configurar CI/CD con GitHub Actions.

¿Podrían asignarme el rol "Application Developer" en Azure AD?

Gracias,
[Tu Nombre]
```

### Opción B: Solicitar a través del Portal Azure

1. Ve a https://portal.azure.com
2. Azure Active Directory → Roles and administrators
3. Busca si tienes solicitudes pendientes o contacta soporte

---

## ✅ Solución 3: Usar tus Credenciales Directamente (NO recomendado)

⚠️ Menos seguro pero funciona:

```bash
# Crear un Personal Access Token en Azure
az ad app create --display-name "github-actions-app"

# Obtener App ID
APP_ID=$(az ad app list --display-name "github-actions-app" --query "[0].appId" -o tsv)

# Crear secret para la app
az ad app credential reset --id $APP_ID --append
```

Si esto también falla, es confirmación de que tu cuenta no tiene permisos.

---

## ✅ Solución 4: CI/CD Híbrido (Pragmático)

Para proyecto universitario, esto es completamente válido:

### Pipeline híbrido:
```yaml
# .github/workflows/ci-simple.yml

on:
  push:
    branches: [main]

jobs:
  # Tests automáticos (no requieren Azure)
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run tests
        run: make test
  
  # Build automático (no requiere Azure)
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Login to Docker Hub
        uses: docker/login-action@v3
        with:
          username: ${{ secrets.DOCKERHUB_USERNAME }}
          password: ${{ secrets.DOCKERHUB_TOKEN }}
      
      - name: Build and push
        run: make docker-build && make docker-push
  
  # Deploy manual (lo haces tú desde tu laptop)
  # No necesita estar en GitHub Actions
```

Luego despliegas manualmente:
```bash
# Desde tu laptop
az aks get-credentials --resource-group carpeta-ciudadana-dev-rg --name carpeta-ciudadana-dev
kubectl apply -f deployments/
```

---

## 🎓 Para tu Presentación

### Con Federated Credentials (Solución 1):
> "Implementé CI/CD con GitHub Actions usando Workload Identity Federation, 
> eliminando la necesidad de almacenar secretos y siguiendo las mejores 
> prácticas de seguridad zero-trust de Azure."

### Con Deploy Manual (Solución 4):
> "Implementé un pipeline de CI con tests y builds automáticos, con deployment 
> controlado manual para mayor seguridad y control del ambiente de producción."

**Ambas son válidas y profesionales!**

---

## 🚀 Mi Recomendación

**Usa Solución 1 (Federated Credentials)**:

1. ✅ No requiere permisos especiales
2. ✅ Más seguro que Service Principal
3. ✅ Es el método moderno de Microsoft
4. ✅ Impresiona más en presentaciones

### Próximos pasos:

```bash
# 1. Primero termina el terraform apply
cd /Users/manueljurado/arquitectura_avanzada/infra/terraform-azure
terraform apply

# 2. Luego configura GitHub Actions con federated auth
~/setup-github-federated-auth.sh

# 3. Configura Docker Hub (gratis)
# https://hub.docker.com/signup

# 4. Push tu código
git push origin main

# 5. ¡GitHub Actions se ejecutará automáticamente!
```

---

## 📋 Checklist

- [ ] `terraform apply` completado
- [ ] AKS cluster creado
- [ ] Ejecutar `~/setup-github-federated-auth.sh`
- [ ] Crear cuenta Docker Hub
- [ ] Configurar GitHub Secrets
- [ ] Push a main
- [ ] Ver GitHub Actions ejecutarse

¿Quieres que continuemos con el `terraform apply` ahora?

