# Carpeta Ciudadana – Microservices Platform

Carpeta Ciudadana es una plataforma orientada a microservicios para la gestión de documentos, firmas y transferencias ciudadanas. El proyecto combina servicios FastAPI, un frontend Next.js y un despliegue pensado para Azure Kubernetes Service.

---

## Quickstart
- **Requisitos básicos:** Docker 24+ con Compose V2, Python 3.12+, Node.js 22+ si vas a desarrollar, Azure CLI solo para despliegues en la nube.
- **Variables locales:** crea un archivo `.env` en la raíz con, al menos, `AZURE_STORAGE_ACCOUNT_NAME`, `AZURE_STORAGE_ACCOUNT_KEY`, `REDIS_HOST`, `REDIS_PASSWORD` si quieres habilitar las integraciones que dependen de ellos. Para pruebas locales puedes dejar valores vacíos; los servicios que los usan tienen banderas para ejecutarse en modo “desacoplado”.
- **Levantar todo con imágenes publicadas:**
  ```bash
  docker compose --profile app up -d
  ```
- **Construir imágenes locales antes de levantar Compose (opcional):**
  ```bash
  docker compose --profile app build
  docker compose --profile app up -d
  ```
- **Apagar el entorno:**
  ```bash
  docker compose down --volumes
  ```

---

## Estructura del repositorio
- `apps/frontend`: interfaz Next.js 16 (App Router, Tailwind, NextAuth).
- `services/*`: microservicios FastAPI empaquetados con Poetry (`citizen`, `ingestion`, `transfer`, `signature`, `auth`, `mintic_client`, `notification`, `metadata`).
- `services/common`: librería compartida con modelos, seguridad y utilidades.
- `infra/terraform`: definición IaC por capas; revisa `infra/terraform/README-LAYERS.md`.
- `deploy/helm/carpeta-ciudadana`: chart Helm para AKS.
- `docs/`: entregables de arquitectura y diagramas de soporte.
- `scripts/`: automatizaciones para build, despliegue y mantenimiento.

---

## Servicios activos

| Servicio | Puerto | Propósito | Dependencias clave |
|----------|--------|-----------|--------------------|
| `frontend` | 3000 | UI Next.js con autenticación y dashboards | Node.js, NextAuth |
| `citizen` | 8001 | Gestión de ciudadanos y ABAC | PostgreSQL |
| `ingestion` | 8002 | Ingesta y descargas de documentos | Azure Blob, PostgreSQL |
| `transfer` | 8004 | Transferencias P2P y orquestación | PostgreSQL |
| `mintic_client` | 8005 | Integración con Hub MinTIC | Redis opcional |
| `signature` | 8006 | Firma digital y validaciones | Azure Blob, PostgreSQL |
| `auth` | 8008 | emisora JWT interna | Redis opcional |
| `notification` | 8010 | (experimental) envíos asíncronos | Azure Service Bus opcional |

El archivo `docker-compose.yml` expone los servicios estables para desarrollo; otros componentes pueden habilitarse desde el chart Helm cuando se despliega en AKS.

---

## Flujo de trabajo recomendado
1. **Preparar dependencias locales:** `poetry install` dentro de cada servicio que vayas a modificar y `npm install` en `apps/frontend`.
2. **Levantar base de datos:** `docker compose up postgres -d` (incluido en cualquier perfil).
3. **Desarrollo backend:** ejecuta los servicios con `poetry run uvicorn ...` si necesitas hot reload, o consume los contenedores provistos.
4. **Pruebas:**  
   ```bash
   pytest services/<servicio>/tests
   npm test --prefix apps/frontend
   ```
5. **Estilo y lint:** usa `ruff` para Python (`poetry run ruff check .`) y `npm run lint` para el frontend.

---

## Despliegue en Azure (resumen)
1. Autentícate y prepara la suscripción: `./scripts/azure-setup.sh`.
2. Revisa la configuración de Terraform: `cd infra/terraform && terraform init && terraform plan`.
3. Provisiona infraestructura: `terraform apply`.
4. Empaqueta y publica imágenes: `./scripts/build-and-push-services.sh --username <usuario> --version <tag>`.
5. Instala o actualiza el chart:  
   ```bash
   cd deploy/helm
   helm upgrade --install carpeta-ciudadana ./carpeta-ciudadana \
     --set image.tag=<tag>
   ```
Consulta `deploy/helm/carpeta-ciudadana/README.md` para valores detallados y `infra/terraform/README-LAYERS.md` para conocer las capas provisionadas.

---

## Documentación útil
- `docs/entregable_arquitectura.md`: visión general y decisiones de diseño.
- `docs/diagrama-componentes.md` y `docs/diagramas-secuencia.md`: diagramas actualizados.
- `Escenarios_casos_uso.md`: casos y flujos cubiertos.
- `Operador_Carpeta_Ciudadana_Azure.md`: guía operativa para el despliegue en AKS.

---

## Scripts destacados
- `scripts/build-and-push-services.sh`: build/push selectivo de imágenes.
- `scripts/build-and-push.sh`: build completo de frontend y servicios (legacy pero útil para releases).
- `scripts/deploy-service.sh`: despliegue individual de un microservicio vía Helm.
- `scripts/test-all-endpoints.sh`: smoke test básico de APIs en un entorno desplegado.
- `scripts/start-azure-services.sh` / `scripts/stop-azure-services.sh`: helpers para recursos gestionados (colas, almacenamiento).

Revisa cada script antes de ejecutarlo; varios requieren variables de entorno para credenciales o suscripción.

---

## Soporte rápido
- **Verificar estado local:** `docker compose ps`, `docker compose logs <servicio>`.
- **PostgreSQL local:** credenciales `postgres/postgres` (ver `docker-compose.yml`).
- **Errores de autenticación en AKS:** vuelve a ejecutar `az aks get-credentials`.
- **Variables faltantes:** exporta desde `.env` o usa `direnv`.

---

Proyecto desarrollado como parte del curso **Arquitectura Avanzada – Universidad EAFIT** y evolucionado para usos demostrativos. Cualquier aportación o issue es bienvenida.
