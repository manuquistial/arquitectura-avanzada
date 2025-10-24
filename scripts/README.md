# Docker Build Scripts

Scripts para construir y subir las imágenes de Docker del proyecto Carpeta Ciudadana.

## Scripts Disponibles

### 1. `build-no-cache.sh` (Recomendado para uso simple)

Script simplificado que construye todas las imágenes sin cache.

```bash
# 1. Editar el script y cambiar tu username
vim scripts/build-no-cache.sh

# 2. Ejecutar
./scripts/build-no-cache.sh
```

**Configuración:**
- Edita la variable `DOCKER_HUB_USERNAME` en el script
- Opcionalmente cambia la `VERSION`

### 2. `build-and-push.sh` (Avanzado)

Script completo con múltiples opciones.

```bash
# Ejemplos de uso:
./scripts/build-and-push.sh --username tu-usuario --no-cache
./scripts/build-and-push.sh --username tu-usuario --version v1.0.0 --cleanup
./scripts/build-and-push.sh --username tu-usuario --services-only
./scripts/build-and-push.sh --username tu-usuario --frontend-only
```

**Opciones disponibles:**
- `--username USERNAME` - Usuario de Docker Hub (requerido)
- `--repository REPO` - Nombre del repositorio (default: carpeta-ciudadana)
- `--version VERSION` - Tag de la imagen (default: latest)
- `--no-cache` - Construir sin cache
- `--cleanup` - Eliminar imágenes locales después del push
- `--services-only` - Solo construir servicios (saltar frontend)
- `--frontend-only` - Solo construir frontend (saltar servicios)

### 3. `docker-config.env` (Configuración)

Archivo de configuración para el script avanzado.

```bash
# Copiar y editar
cp scripts/docker-config.env scripts/my-config.env
vim scripts/my-config.env

# Usar con el script
./scripts/build-and-push.sh --config scripts/my-config.env
```

## Requisitos

1. **Docker instalado y ejecutándose**
2. **Login en Docker Hub**:
   ```bash
   docker login
   ```

## Imágenes que se construyen

### Frontend
- `tu-usuario/carpeta-ciudadana-frontend:latest`

### Servicios
- `tu-usuario/carpeta-ciudadana-auth:latest`
- `tu-usuario/carpeta-ciudadana-citizen:latest`
- `tu-usuario/carpeta-ciudadana-ingestion:latest`
- `tu-usuario/carpeta-ciudadana-mintic_client:latest`
- `tu-usuario/carpeta-ciudadana-signature:latest`
- `tu-usuario/carpeta-ciudadana-transfer:latest`

## Solución de Problemas

### Error: "failed to solve: failed to compute cache key"

Este error ocurre cuando el contexto de build no es correcto. El script corregido maneja esto automáticamente:

- **Frontend**: Usa el directorio raíz como contexto y especifica el Dockerfile
- **Servicios**: Usa el directorio del servicio como contexto

### Error: "not logged in to Docker Hub"

```bash
docker login
# Ingresa tu username y password/token
```

### Error: "Docker is not running"

Asegúrate de que Docker Desktop esté ejecutándose.

## Uso Recomendado

Para uso diario, recomiendo el script simple:

1. Edita `build-no-cache.sh` con tu username
2. Ejecuta: `./scripts/build-no-cache.sh`

Para casos especiales, usa el script avanzado con las opciones que necesites.
