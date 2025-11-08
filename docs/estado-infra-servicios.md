# Estado de Infraestructura y Servicios

## Resumen Ejecutivo
- Se identificaron componentes críticos deshabilitados (migraciones, TLS, autoscaling, observabilidad) debido a restricciones de recursos.
- Integraciones clave (Gateway, correo transaccional, eventos Service Bus secundarios) no están operativas en el despliegue actual.
- Las definiciones de Terraform mantienen desactivados Front Door/WAF, secretos de Mailjet y recursos de KEDA relacionados con métricas.

## Hallazgos en Helm (`deploy/helm/carpeta-ciudadana/values.yaml`)
- `migrations.enabled = false`: no se ejecutan trabajos de `alembic upgrade` (#L25-41).
- `resourceOptimization.enabled = false`: se ignoran los límites mínimos/ajustados (#L33-42).
- `security.hstsEnabled = false` y `security.cspEnabled = false`: headers de seguridad apagados (#L53-55).
- TLS deshabilitado: `ingress.tls.enabled = false`, sin cert-manager ni redirecciones HTTPS (#L523-545).
- Observabilidad apagada: `observability.enabled = false` y `otel.enabled = false` (#L469-476, #L567-575).
- Autoscaling desactivado en todos los servicios; varios críticos forzados a 1 réplica (`aut*.enabled = false`, `maxReplicas = 1`) (#L71-258).
- `podDisruptionBudget.enabled = false`: no hay protección ante mantenimientos (#L507-511).
- Notificaciones por correo deshabilitadas: `notification.smtp.enabled = false`, `notification.mailjet.enabled = false` (#L329-335).
- Sin despliegue para `gateway`: la arquitectura documentada lo menciona, pero no hay bloque `gateway` en valores ni templates.

## Hallazgos en Terraform
### Capa `application` (`infra/terraform/layers/application`)
- Mailjet inactivo: `var.mailjet_enabled = false`, `kubernetes_manifest.mailjet_secrets` con `count = 0` (variables.tf #L173-208, main.tf #L223-292).
- KEDA sin disparadores ni métricas: `servicebus_trigger_auth` y `keda_service_monitor` con `count = 0` (modules/keda/main.tf #L100-157).

### Capa `carpeta-ciudadana`
- Front Door/WAF deshabilitados por defecto (`frontdoor_enabled = false`, `frontdoor_enable_waf = false`) en `terraform.tfvars.example` (#L19-26).

## Hallazgos en Servicios
- `notification`: SMTP y Mailjet deshabilitados (`MAILJET_ENABLED=false`, `SMTP_ENABLED=false`), por lo que sólo registra eventos (app/config.py #L26-63).
- `metadata` y `transfer`: aunque los defaults de código usan `SERVICEBUS_ENABLED=false`, el chart/terraform les inyecta `SERVICEBUS_ENABLED=true` junto con los secretos de Service Bus, por lo que dependen del bus en despliegues gestionados.
- `auth`: integración con Azure AD B2C removida del código (comentario `Azure AD B2C - REMOVED`).
- `mintic_client`: permite URLs inseguras (`ALLOW_INSECURE_OPERATOR_URLS=true` por defecto) si no se sobreescribe (app/config.py #L38-48).

## Recomendaciones
- Rehabilitar migraciones o documentar proceso alterno antes de despliegues.
- Activar TLS (cert-manager, redirecciones, headers de seguridad) cuando el entorno ya no sea puramente experimental.
- Definir si se implementará el `gateway` descrito en la arquitectura o ajustar la documentación y diagramas.
- Encender observabilidad/KEDA/Mailjet sólo cuando existan credenciales/presupuesto; mientras tanto, mantener la documentación actualizada.
- Verificar que `SERVICEBUS_ENABLED` esté configurado en `true` en ambientes productivos para `metadata`, `notification` y `transfer`.
- Revisar la bandera `ALLOW_INSECURE_OPERATOR_URLS` en `mintic_client` para entornos productivos.
