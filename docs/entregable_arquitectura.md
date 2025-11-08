# Entregable de Arquitectura · Carpeta Ciudadana

> Documento que responde, con base en los artefactos existentes, a los puntos solicitados en la guía.

## 1. Diagrama de Casos de Uso o Historias de Usuario

- **Diagrama de casos de uso**: disponible como imagen en `docs/casos_uso.png`. Representa actores `Ciudadano`, `Operador`, `Hub MinTIC` y `Servicios Externos`, junto con los casos `Registrar ciudadano`, `Autenticarse`, `Cargar documentos`, `Autenticar documento` y `Recibir notificaciones`.
- **Historias de usuario**: no hay un documento dedicado dentro de `docs/` que las detalle; el insumo principal en este repositorio es el diagrama mencionado.

## 2. Casos de Uso con Especificaciones

Los siguientes insumos dentro de `docs/` cubren la información solicitada:

- **CU1 Registrar ciudadano**: descrito en `docs/diagramas-secuencia.md` (sección “Registro de ciudadano”), con participantes, flujo principal, alternativas y evento `citizen.registered`.
- **CU2 Autenticarse en el operador**: `docs/diagramas-secuencia.md` (sección “Autenticación de ciudadano”) detalla el uso de `auth`, verificación en PostgreSQL y manejo de credenciales inválidas.
- **CU3 Cargar documentos**: `docs/diagramas-secuencia.md` (sección “Carga de documento”) explica la generación de SAS URL, confirmación al backend y publicación del evento `document.uploaded`.
- **CU4 Autenticación Gov**: `docs/diagramas-secuencia.md` (sección “Autenticación de documento”) cubre la interacción con `signature`, `mintic_client`, Hub MinTIC y la aplicación de WORM.
- **CU5 Notificaciones de eventos**: `docs/diagramas-secuencia.md` (sección “Publicación y manejo de eventos”) describe el flujo de Service Bus hacia `notification`, con reintentos y DLQ.

## 3. Historias de Usuario y Escenarios

No se encontraron historias de usuario textuales dentro de `docs/`. El repositorio aporta únicamente el diagrama de casos de uso y los diagramas de secuencia para comprender los escenarios principales.

## 4. Diagrama de Componentes (Lógicos y Técnicos)

- **Vista lógica**: disponible en `docs/diagrama-componentes.md`, donde se describen los dominios (Experiencia de Usuario, Gestión de Identidad, Gestión Documental e Integraciones) y el evento central `Azure Service Bus`.
- **Vista técnica**: el mismo documento referencia la topología en AKS y cómo cada microservicio (`auth`, `citizen`, `ingestion`, `metadata`, `signature`, `notification`, `transfer`, `mintic_client`) se conecta a PostgreSQL, Blob Storage, Key Vault, Redis y Service Bus.

## 5. Diagramas de Secuencia de al menos 3 Operaciones

`docs/diagramas-secuencia.md` contiene cinco diagramas (Registro, Autenticación, Carga de documento, Autenticación Gov y Manejo de eventos). Cada uno incluye participantes, flujo principal y alternativas; satisfacen el requisito de “al menos 3” (se entregan 4+).

## 6. Diagrama de Despliegue con Tecnologías, Protocolos y Mensajería

- **Diagrama**: `docs/Despliegue_microservicios_arquitecturas_avanzadas.png`.
- **Descripción**: El propio diagrama y la documentación adjunta indican:
  - Azure Load Balancer + NGINX Ingress (HTTP actual, pendiente TLS).
  - AKS como plataforma de contenedores para todos los microservicios.
  - Servicios gestionados: Azure PostgreSQL, Blob Storage, Service Bus, Key Vault, Redis opcional.
  - Integraciones externas: Hub MinTIC (REST/JSON sobre VPN) y Mailjet (HTTPS).
  - Protocolos y formatos (HTTP/HTTPS, AMQP 1.0 + JSON, SQL/JSONB, claves en Key Vault).

## 7. Decisiones de Arquitectura

Las decisiones de arquitectura se pueden consultar en las presentaciones y diagramas dentro de `docs/`:

- **Criterios de despliegue**: `docs/Despliegue_microservicios_arquitecturas_avanzadas.png` y el PDF `docs/DECISIONES DE DESPLIEGUE EN LA NUBE.pdf` documentan el uso de AKS con Ingress, servicios gestionados (PostgreSQL, Blob, Service Bus, Key Vault), integración privada al Hub y Redis opcional.
- **Selección tecnológica**: `docs/diagrama-componentes.md` y el PDF `docs/DECISIONES DE SELECCIÓN DE TECNOLOGÍAS.pdf` enumeran las tecnologías elegidas (FastAPI, Next.js SSR, Azure Blob con WORM, Azure Service Bus, autenticación local con JWT, observabilidad básica) junto con alternativas y racional.
- Estos artefactos incluyen el detalle de alternativas evaluadas, justificación y riesgos asociados.

---

**Estado**: Información completa según artefactos recopilados (actualizado al 2025-11-08).  
**Fuentes**: `docs/casos_uso.png`, `docs/diagrama-componentes.md`, `docs/diagramas-secuencia.md`, `docs/Despliegue_microservicios_arquitecturas_avanzadas.png`, `docs/DECISIONES DE DESPLIEGUE EN LA NUBE.pdf`, `docs/DECISIONES DE SELECCIÓN DE TECNOLOGÍAS.pdf`.

