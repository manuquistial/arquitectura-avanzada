# Plan de Deployment - Servicios Event Bus

> **Fecha**: 2025-11-02  
> **Objetivo**: Desplegar servicios Metadata y Notification, y verificar servicios modificados  
> **Estrategia**: Deployment por fases con pruebas

---

## 📋 Resumen Ejecutivo

**Servicios Nuevos**:
- ✅ Metadata Service (nuevo)
- ✅ Notification Service (nuevo)

**Servicios Modificados**:
- ✅ Transfer Service (agregado consumidor de eventos)
- ✅ Citizen Service (actualizada publicación de eventos)

**Estrategia**: Deployment incremental por fases, probando cada servicio antes de continuar.

---

## 🎯 Fase 1: Preparación y Verificación Pre-Deployment

### 1.1 Verificar Estado Actual

**Tareas**:
- [ ] Verificar que todos los servicios compilan localmente
- [ ] Verificar que `poetry.lock` está actualizado para todos los servicios
- [ ] Verificar que los Dockerfiles son correctos
- [ ] Verificar variables de entorno en Helm values
- [ ] Verificar configuración de Service Bus en Terraform

**Servicios a verificar**:
1. ✅ Metadata Service
2. ✅ Notification Service
3. ✅ Transfer Service (modificado)
4. ✅ Citizen Service (modificado)

**Comandos**:
```bash
# Verificar estructura de servicios
ls -la services/metadata/
ls -la services/notification/
ls -la services/transfer/
ls -la services/citizen/

# Verificar poetry.lock
cd services/metadata && poetry lock --check
cd services/notification && poetry lock --check
cd services/transfer && poetry lock --check
cd services/citizen && poetry lock --check
```

**Estimación**: 0.5 horas

---

### 1.2 Preparar Variables de Entorno

**Variables requeridas**:
- `DOCKER_HUB_USERNAME` - Usuario de Docker Hub
- `DOCKER_HUB_PASSWORD` - Token de acceso Docker Hub
- `IMAGE_REGISTRY` - Registry de imágenes (docker.io/usuario)
- `SERVICEBUS_CONNECTION_STRING` - Cadena de conexión Service Bus
- `DB_*` - Variables de base de datos (ya configuradas)

**Acción**: Verificar que todas las variables están en Terraform/Azure Key Vault

**Estimación**: 0.25 horas

---

## 🎯 Fase 2: Build y Push de Imágenes

### 2.1 Build Local (Prueba)

**Tareas**:
- [ ] Activar venv
- [ ] Instalar dependencias con Poetry
- [ ] Build local de imágenes Docker
- [ ] Verificar que las imágenes se crean correctamente
- [ ] Probar imágenes localmente (si es posible)

**Orden de Build**:
1. **Transfer Service** (servicio modificado crítico)
2. **Citizen Service** (servicio modificado)
3. **Metadata Service** (nuevo, dependiente de eventos)
4. **Notification Service** (nuevo, dependiente de eventos)

**Comandos**:
```bash
# Opción 1: Usar script automatizado (RECOMENDADO)
./scripts/build-and-push-services.sh \
  --username ${DOCKER_HUB_USERNAME} \
  --version latest \
  --no-cache

# Opción 2: Build individual
docker build -f services/transfer/Dockerfile \
  -t ${DOCKER_HUB_USERNAME}/carpeta-ciudadana-transfer:latest .
docker images | grep carpeta-ciudadana-transfer

# Repetir para:
# - services/citizen
# - services/metadata
# - services/notification
```

**Nota**: El script `build-and-push-services.sh` automatiza el proceso para todos los servicios modificados/nuevos.

**Estimación**: 1 hora

---

### 2.2 Push a Docker Hub

**Tareas**:
- [ ] Login a Docker Hub
- [ ] Push de imágenes en orden
- [ ] Usar tag `latest` (por defecto)
- [ ] Verificar que las imágenes están en Docker Hub

**Orden de Push**:
1. Transfer Service (modificado)
2. Citizen Service (modificado)
3. Metadata Service (nuevo)
4. Notification Service (nuevo)

**Comandos**:
```bash
# Opción 1: Usar script automatizado (YA incluye push) - USA TAG LATEST
./scripts/build-and-push-services.sh \
  --username ${DOCKER_HUB_USERNAME} \
  --version latest \
  --no-cache

# Opción 2: Push manual - USA TAG LATEST
docker login -u ${DOCKER_HUB_USERNAME} -p ${DOCKER_HUB_TOKEN}

# Push con tag latest
docker push ${DOCKER_HUB_USERNAME}/carpeta-ciudadana-transfer:latest

# Repetir para todos los servicios
```

**Estimación**: 0.5 horas

---

## 🎯 Fase 3: Deployment - Transfer Service (Modificado)

### 3.1 Verificar Configuración Helm

**Tareas**:
- [ ] Verificar `values.yaml` para Transfer Service
- [ ] Verificar que `SERVICEBUS_ENABLED=true`
- [ ] Verificar colas: `TRANSFER_EVENTS_QUEUE`, `TRANSFER_NOTIFICATIONS_QUEUE`
- [ ] Verificar variables de Service Bus en ConfigMap/Secret

**Archivos a verificar**:
- `deploy/helm/carpeta-ciudadana/values.yaml` (sección `transfer`)
- `deploy/helm/carpeta-ciudadana/templates/configmap-app.yaml`
- `deploy/helm/carpeta-ciudadana/templates/deployment-transfer.yaml`

**Estimación**: 0.25 horas

---

### 3.2 Terraform Plan y Apply

**Tareas**:
- [ ] Ejecutar `terraform plan` para verificar cambios
- [ ] Verificar que la imagen de Transfer Service está actualizada
- [ ] Aplicar cambios con `terraform apply`
- [ ] Verificar que el deployment se crea correctamente

**Comandos**:
```bash
# Opción 1: Usar script automatizado (RECOMENDADO)
./scripts/deploy-service.sh transfer

# Opción 2: Manual (usa 'latest' por defecto configurado en Helm values.yaml)
cd infra/terraform/layers/carpeta-ciudadana
terraform init
terraform plan -out=transfer.plan
terraform apply transfer.plan
```

**Estimación**: 0.5 horas

---

### 3.3 Verificación Post-Deployment

**Tareas**:
- [ ] Verificar que el pod de Transfer Service está running
- [ ] Verificar logs del servicio (consumidor iniciado)
- [ ] Verificar que Service Bus consumer está activo
- [ ] Probar endpoint `/health` y `/ready`
- [ ] Verificar que el consumidor se inicia en logs

**Comandos**:
```bash
# Verificar pod
kubectl get pods -l app=transfer

# Verificar logs
kubectl logs -l app=transfer --tail=50 | grep -i "consumer\|service bus"

# Verificar health
kubectl port-forward svc/carpeta-ciudadana-transfer 8000:8000
curl http://localhost:8000/health
curl http://localhost:8000/ready
```

**Verificaciones**:
- ✅ Pod en estado `Running`
- ✅ Logs muestran: "Transfer Service consumer task started"
- ✅ Logs muestran: "Starting Transfer Service consumer for queue: transfer-events"
- ✅ Health check responde `200 OK`
- ✅ Ready check responde con `servicebus_enabled: true`

**Estimación**: 0.5 horas

---

### 3.4 Prueba Funcional Transfer Service

**Tareas**:
- [ ] Publicar evento de prueba `transfer.requested` manualmente (si es posible)
- [ ] Verificar que el consumidor procesa el evento
- [ ] Verificar logs del procesamiento
- [ ] Probar endpoint `/api/transfer/initiate` (si está disponible)
- [ ] Verificar que se publican eventos correctamente

**Estimación**: 0.5 horas

---

## 🎯 Fase 4: Deployment - Citizen Service (Modificado)

### 4.1 Verificar Configuración

**Tareas**:
- [ ] Verificar `values.yaml` para Citizen Service
- [ ] Verificar que `SERVICEBUS_ENABLED=true`
- [ ] Verificar que usa `citizen-events` (queue estandarizada)

**Estimación**: 0.25 horas

---

### 4.2 Terraform Plan y Apply

**Tareas**:
- [ ] Ejecutar `terraform plan`
- [ ] Aplicar cambios
- [ ] Verificar deployment

**Comandos**:
```bash
cd infra/terraform/layers/carpeta-ciudadana
terraform plan -out=citizen.plan
terraform apply citizen.plan
```

**Estimación**: 0.5 horas

---

### 4.3 Verificación Post-Deployment

**Tareas**:
- [ ] Verificar que el pod está running
- [ ] Verificar logs (eventos publicados correctamente)
- [ ] Probar registro de ciudadano
- [ ] Verificar que se publica `citizen.registered` a `citizen-events`

**Verificaciones**:
- ✅ Pod en estado `Running`
- ✅ Logs muestran publicación de eventos
- ✅ Evento `citizen.registered` se publica a `citizen-events`

**Estimación**: 0.5 horas

---

## 🎯 Fase 5: Deployment - Metadata Service (NUEVO)

### 5.1 Verificar Configuración Helm

**Tareas**:
- [ ] Verificar que `metadata.enabled=true` en `values.yaml`
- [ ] Verificar configuración de Service Bus
- [ ] Verificar cola: `DOCUMENT_EVENTS_QUEUE=document-events`
- [ ] Verificar variables de DB (mismo que otros servicios)
- [ ] Verificar configuración de Redis (opcional)
- [ ] Verificar configuración opcional de `signature-events`

**Archivos**:
- `deploy/helm/carpeta-ciudadana/values.yaml` (sección `metadata`)
- `deploy/helm/carpeta-ciudadana/templates/deployment-metadata.yaml`
- `deploy/helm/carpeta-ciudadana/templates/configmap-app.yaml`

**Estimación**: 0.5 horas

---

### 5.2 Terraform - Agregar Metadata Service

**Tareas**:
- [ ] Verificar que Terraform tiene configuración para Metadata Service
- [ ] Agregar recursos si faltan (deployment, service, configmap)
- [ ] Ejecutar `terraform plan`
- [ ] Verificar que no hay dependencias faltantes
- [ ] Aplicar cambios

**Comandos**:
```bash
cd infra/terraform/layers/carpeta-ciudadana

# Verificar plan
terraform plan -out=metadata.plan

# Aplicar (primera vez)
terraform apply metadata.plan
```

**Estimación**: 1 hora

---

### 5.3 Verificación Post-Deployment

**Tareas**:
- [ ] Verificar que el pod está running
- [ ] Verificar logs del consumidor
- [ ] Verificar que consume `document-events`
- [ ] Probar endpoints `/health`, `/ready`, `/db/health`
- [ ] Verificar conexión a DB

**Comandos**:
```bash
# Verificar pod
kubectl get pods -l app=metadata

# Verificar logs
kubectl logs -l app=metadata --tail=50 | grep -i "consumer\|metadata"

# Verificar health
kubectl port-forward svc/carpeta-ciudadana-metadata 8000:8000
curl http://localhost:8000/health
curl http://localhost:8000/ready
curl http://localhost:8000/db/health
```

**Verificaciones**:
- ✅ Pod en estado `Running`
- ✅ Logs muestran: "Metadata Service consumer task started"
- ✅ Logs muestran: "Starting Metadata Service consumer for queue: document-events"
- ✅ Health check responde `200 OK`
- ✅ Ready check responde con `servicebus_enabled: true`
- ✅ DB health check responde `connected`

**Estimación**: 0.5 horas

---

### 5.4 Prueba Funcional Metadata Service

**Tareas**:
- [ ] Subir un documento (trigger `document.uploaded`)
- [ ] Verificar que Metadata Service consume el evento
- [ ] Verificar logs del procesamiento
- [ ] Probar endpoint `/api/documents/{document_id}` (si está disponible)
- [ ] Verificar que se actualiza metadata correctamente

**Comandos**:
```bash
# Monitorear logs mientras se sube documento
kubectl logs -l app=metadata -f | grep -i "document.uploaded"

# Probar endpoint de metadata
curl http://localhost:8000/api/documents/{document_id}
```

**Verificaciones**:
- ✅ Evento `document.uploaded` es consumido
- ✅ Logs muestran procesamiento exitoso
- ✅ Metadata se actualiza en DB

**Estimación**: 0.5 horas

---

### 5.5 Monitoreo y Validación

**Tareas**:
- [ ] Monitorear consumo de eventos durante 10-15 minutos
- [ ] Verificar que no hay errores en logs
- [ ] Verificar que la cola `document-events` se procesa
- [ ] Verificar métricas del servicio (si están disponibles)

**Estimación**: 0.5 horas

---

## 🎯 Fase 6: Deployment - Notification Service (NUEVO)

### 6.1 Verificar Configuración Helm

**Tareas**:
- [ ] Verificar que `notification.enabled=true` en `values.yaml`
- [ ] Verificar configuración de Service Bus
- [ ] Verificar cola: `CITIZEN_EVENTS_QUEUE=citizen-events`
- [ ] Verificar variables de DB (opcional para Notification)
- [ ] Verificar configuración de SMTP (opcional, deshabilitado por ahora)

**Archivos**:
- `deploy/helm/carpeta-ciudadana/values.yaml` (sección `notification`)
- `deploy/helm/carpeta-ciudadana/templates/deployment-notification.yaml`
- `deploy/helm/carpeta-ciudadana/templates/configmap-app.yaml`

**Estimación**: 0.5 horas

---

### 6.2 Terraform - Agregar Notification Service

**Tareas**:
- [ ] Verificar que Terraform tiene configuración para Notification Service
- [ ] Agregar recursos si faltan
- [ ] Ejecutar `terraform plan`
- [ ] Aplicar cambios

**Comandos**:
```bash
cd infra/terraform/layers/carpeta-ciudadana
terraform plan -out=notification.plan
terraform apply notification.plan
```
<｜tool▁calls▁begin｜><｜tool▁call▁begin｜>
read_file

**Estimación**: 1 hora

---

### 6.3 Verificación Post-Deployment

**Tareas**:
- [ ] Verificar que el pod está running
- [ ] Verificar logs del consumidor
- [ ] Verificar que consume `citizen-events`
- [ ] Probar endpoints `/health`, `/ready`
- [ ] Verificar conexión a Service Bus

**Comandos**:
```bash
# Verificar pod
kubectl get pods -l app=notification

# Verificar logs
kubectl logs -l app=notification --tail=50 | grep -i "consumer\|notification"

# Verificar health
kubectl port-forward svc/carpeta-ciudadana-notification 8000:8000
curl http://localhost:8000/health
curl http://localhost:8000/ready
```

**Verificaciones**:
- ✅ Pod en estado `Running`
- ✅ Logs muestran: "Notification Service consumer task started"
- ✅ Logs muestran: "Starting Notification Service consumer for queue: citizen-events"
- ✅ Health check responde `200 OK`
- ✅ Ready check responde con `servicebus_enabled: true`

**Estimación**: 0.5 horas

---

### 6.4 Prueba Funcional Notification Service

**Tareas**:
- [ ] Registrar un nuevo ciudadano (trigger `citizen.registered`)
- [ ] Verificar que Notification Service consume el evento
- [ ] Verificar logs del procesamiento
- [ ] Verificar que se envía email de bienvenida (mock)

**Comandos**:
```bash
# Monitorear logs mientras se registra ciudadano
kubectl logs -l app=notification -f | grep -i "citizen.registered"

# Verificar en Citizen Service que se publicó evento
kubectl logs -l app=citizen --tail=50 | grep -i "citizen.registered"
```

**Verificaciones**:
- ✅ Evento `citizen.registered` es consumido
- ✅ Logs muestran procesamiento exitoso
- ✅ Logs muestran: "[MOCK EMAIL] Sending welcome email"

**Estimación**: 0.5 horas

---

### 6.5 Monitoreo y Validación

**Tareas**:
- [ ] Monitorear consumo de eventos durante 10-15 minutos
- [ ] Verificar que no hay errores en logs
- [ ] Verificar que la cola `citizen-events` se procesa
- [ ] Verificar integración end-to-end: Citizen → Notification

**Estimación**: 0.5 horas

---

## 🎯 Fase 7: Verificación End-to-End

### 7.1 Verificar Flujo Completo

**Tareas**:
- [ ] Probar flujo completo: registro de ciudadano → notificación
- [ ] Probar flujo: subida de documento → metadata actualizado
- [ ] Probar flujo: transferencia → eventos procesados
- [ ] Verificar que todos los servicios comunican correctamente

**Escenarios de Prueba**:
1. **Registro de Ciudadano**:
   - Citizen Service registra ciudadano
   - Publica `citizen.registered` → `citizen-events`
   - Notification Service consume y procesa
   
2. **Subida de Documento**:
   - Ingestion Service sube documento
   - Publica `document.uploaded` → `document-events`
   - Metadata Service consume y actualiza metadata

3. **Transferencia**:
   - Transfer Service inicia transferencia
   - Publica `transfer.requested` → `transfer-events`
   - Transfer Service (consumer) procesa asíncronamente

**Estimación**: 1 hora

---

### 7.2 Verificar Métricas y Monitoreo

**Tareas**:
- [ ] Verificar logs de todos los servicios
- [ ] Verificar que no hay errores en DLQ
- [ ] Verificar consumo de mensajes en Service Bus
- [ ] Verificar métricas de Kubernetes (CPU, memoria)
- [ ] Documentar cualquier problema encontrado

**Estimación**: 0.5 horas

---

### 7.3 Rollback Plan (Si es Necesario)

**Tareas**:
- [ ] Documentar pasos de rollback para cada servicio
- [ ] Preparar rollback de imágenes anteriores
- [ ] Documentar comandos de rollback en Terraform

**Nota**: Si es necesario rollback, usar imagen anterior con tag específico si se guardó. Por defecto se usa `latest`.

**Estimación**: 0.25 horas

---

## 📊 Resumen de Tiempos

| Fase | Descripción | Tiempo Estimado |
|------|-------------|-----------------|
| 1 | Preparación y Verificación | 0.75 horas |
| 2 | Build y Push Imágenes | 1.5 horas |
| 3 | Deployment Transfer Service | 1.75 horas |
| 4 | Deployment Citizen Service | 1.25 horas |
| 5 | Deployment Metadata Service | 3.0 horas |
| 6 | Deployment Notification Service | 3.0 horas |
| 7 | Verificación End-to-End | 1.75 horas |
| **TOTAL** | | **13 horas** (~2 días de trabajo) |

---

## ✅ Checklist Final

### Pre-Deployment
- [ ] Todos los servicios compilan localmente
- [ ] `poetry.lock` actualizado para todos
- [ ] Dockerfiles correctos
- [ ] Variables de entorno configuradas

### Build y Push
- [ ] Transfer Service: build y push ✅
- [ ] Citizen Service: build y push ✅
- [ ] Metadata Service: build y push ✅
- [ ] Notification Service: build y push ✅

### Deployment
- [ ] Transfer Service: desplegado y verificado ✅
- [ ] Citizen Service: desplegado y verificado ✅
- [ ] Metadata Service: desplegado y verificado ✅
- [ ] Notification Service: desplegado y verificado ✅

### Post-Deployment
- [ ] Todos los servicios en estado `Running`
- [ ] Todos los consumidores activos
- [ ] Flujos end-to-end funcionando
- [ ] No hay errores en logs
- [ ] Métricas dentro de rangos normales

---

## 🚨 Problemas Comunes y Soluciones

### Problema 1: Pod no inicia
**Causa**: Imagen no encontrada o errores de configuración
**Solución**: 
- Verificar que la imagen existe en Docker Hub
- Verificar tags en `values.yaml`
- Verificar logs: `kubectl describe pod <pod-name>`

### Problema 2: Consumer no inicia
**Causa**: Service Bus no configurado o credenciales incorrectas
**Solución**:
- Verificar `SERVICEBUS_CONNECTION_STRING` en secrets
- Verificar `SERVICEBUS_ENABLED=true` en ConfigMap
- Verificar logs del servicio

### Problema 3: Eventos no se consumen
**Causa**: Cola incorrecta o permisos
**Solución**:
- Verificar nombre de cola en configuración
- Verificar que la cola existe en Service Bus
- Verificar permisos del service principal

### Problema 4: Errores de DB
**Causa**: Configuración de DB incorrecta
**Solución**:
- Verificar variables de DB en secrets
- Verificar que la DB acepta conexiones
- Verificar logs de conexión

---

## 📝 Notas Importantes

1. **Orden de Deployment**: Es crítico seguir el orden propuesto para asegurar dependencias correctas.

2. **Pruebas Incrementales**: Probar cada servicio antes de continuar evita acumular problemas.

3. **Versiones**: Se usa tag `latest` por defecto. Para rollback, usar imagen anterior si se guardó.

4. **Service Bus**: Verificar que las colas existen antes de desplegar consumidores.

5. **ConfigMaps y Secrets**: Actualizar todos los ConfigMaps/Secrets necesarios antes de desplegar.

6. **Monitoreo**: Monitorear logs y métricas durante y después del deployment.

---

*Documento generado el 2025-11-02*

