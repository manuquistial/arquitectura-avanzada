# Diagrama de Componentes — Carpeta Ciudadana

> En este documento está el diagrama de componentes del sistema.

![Diagrama de Componentes](./img/componentes.png)


## Alcance
Arquitectura actual expuesta por **Ingress NGINX** (LoadBalancer + Ingress). Microservicios activos: **auth**, **citizen**, **metadata**, **ingestion**, **mintic_client**, **signature**, **notification**, **transfer**.

## Conectividad clave
- **Ingress NGINX** enruta a todos los controllers de los microservicios.
- **Auth** → PostgreSQL; **Redis** solo para sesiones.
- **Citizen** → PostgreSQL; publica en **Azure Service Bus**; usa **mintic_client** para Hub.
- **Metadata** → PostgreSQL y **Key Vault**; gestiona estados y **WORM/legal hold**.
- **Ingestion** → Blob, PostgreSQL, **Service Bus**, **Key Vault**; genera SAS y confirma cargas.
- **Signature** ↔ **Ingestion** (SAS/props), ↔ **Metadata** (estado/bloqueo), → **mintic_client** (Hub), publica en **Service Bus**, usa **Key Vault**.
- **mintic_client** → MinTIC Hub API; usa **Key Vault**.
- **Notification** consume eventos desde **Service Bus** y persiste en PostgreSQL; usa **Key Vault**.
- **Transfer** publica/consume en **Service Bus** y consulta **Citizen/Metadata**; usa **Key Vault**.

## Eventos relevantes
- `citizen.registered` (Citizen)
- `document.uploaded` (Ingestion)
- `document.authenticated` (Signature)
