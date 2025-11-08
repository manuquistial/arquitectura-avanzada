# Entregable de Arquitectura · Carpeta Ciudadana

> Documento que responde, con base en los artefactos existentes, a los puntos solicitados en la guía.

## 1. Diagrama de Casos de Uso o Historias de Usuario

- **Diagrama de casos de uso**: disponible como imagen en [casos_uso.png](./casos_uso.png). Representa actores `Ciudadano`, `Operador`, `Hub MinTIC` y `Servicios Externos`, junto con los casos `Registrar ciudadano`, `Autenticarse`, `Cargar documentos`, `Autenticar documento` y `Recibir notificaciones`.
- **Especificaciones de casos de uso**: cada caso del diagrama cuenta con descripción de flujo principal, alternativas y reglas de negocio en [diagramas-secuencia.md](./diagramas-secuencia.md):
  - `Registro de ciudadano`: participantes, pasos, manejo de duplicados y evento `citizen.registered`.
  - `Autenticación de ciudadano`: verificación de credenciales, respuesta `401` en fallos.
  - `Carga de documento`: generación de SAS, confirmación y evento `document.uploaded`.
  - `Autenticación de documento`: verificación de integridad, firma y aplicación de WORM.
  - `Publicación y manejo de eventos`: consumo desde Service Bus con reintentos y DLQ.
- **Historias de usuario**: no hay narrativa textual dentro de `docs/`; el insumo funcional disponible es el diagrama más las especificaciones anteriores.

## 2. Diagrama de Componentes (Lógicos y Técnicos)

- **Vista lógica**: disponible en [diagrama-componentes.md](./diagrama-componentes.md), donde se describen los dominios (Experiencia de Usuario, Gestión de Identidad, Gestión Documental e Integraciones) y el evento central `Azure Service Bus`.
- **Vista técnica**: el mismo documento referencia la topología en AKS y cómo cada microservicio (`auth`, `citizen`, `ingestion`, `metadata`, `signature`, `notification`, `transfer`, `mintic_client`) se conecta a PostgreSQL, Blob Storage, Key Vault, Redis y Service Bus.

## 3. Diagramas de Secuencia de al menos 3 Operaciones

[diagramas-secuencia.md](./diagramas-secuencia.md) contiene cinco diagramas (Registro, Autenticación, Carga de documento, Autenticación Gov y Manejo de eventos). Cada uno incluye participantes, flujo principal y alternativas; satisfacen el requisito de “al menos 3” (se entregan 4+).

## 4. Diagrama de Despliegue con Tecnologías, Protocolos y Mensajería

- **Diagrama**: [Despliegue_microservicios_arquitecturas_avanzadas.png](./Despliegue_microservicios_arquitecturas_avanzadas.png).
- **Descripción**: El propio diagrama y la documentación adjunta indican:
  - Azure Load Balancer + NGINX Ingress (HTTP actual, pendiente TLS).
  - AKS como plataforma de contenedores para todos los microservicios.
  - Servicios gestionados: Azure PostgreSQL, Blob Storage, Service Bus, Key Vault, Redis opcional.
  - Integraciones externas: Hub MinTIC (REST/JSON sobre VPN) y Mailjet (HTTPS).
  - Protocolos y formatos (HTTP/HTTPS, AMQP 1.0 + JSON, SQL/JSONB, claves en Key Vault).

## 5. Decisiones de Arquitectura para Despliegue (nube / on-premise)

- **Criterios de despliegue**: [Despliegue_microservicios_arquitecturas_avanzadas.png](./Despliegue_microservicios_arquitecturas_avanzadas.png) y el PDF [DECISIONES DE DESPLIEGUE EN LA NUBE.pdf](./DECISIONES%20DE%20DESPLIEGUE%20EN%20LA%20NUBE.pdf) documentan el uso de AKS con Ingress, servicios gestionados (PostgreSQL, Blob, Service Bus, Key Vault), integración privada al Hub y Redis opcional, junto con alternativas evaluadas para escenarios en la nube y on-premise.

## 6. Decisiones de Arquitectura para Selección de Tecnologías

- **Racional tecnológico**: [diagrama-componentes.md](./diagrama-componentes.md) y el PDF [DECISIONES DE SELECCIÓN DE TECNOLOGÍAS.pdf](./DECISIONES%20DE%20SELECCIÓN%20DE%20TECNOLOGÍAS.pdf) enumeran las tecnologías elegidas (FastAPI, Next.js SSR, Azure Blob con WORM, Azure Service Bus, autenticación local con JWT, observabilidad básica), explicando alternativas, racional y riesgos asociados.

---

**Estado**: Información completa según artefactos recopilados (actualizado al 2025-11-08).  
**Fuentes**: `docs/casos_uso.png`, `docs/diagrama-componentes.md`, `docs/diagramas-secuencia.md`, `docs/Despliegue_microservicios_arquitecturas_avanzadas.png`, `docs/DECISIONES DE DESPLIEGUE EN LA NUBE.pdf`, `docs/DECISIONES DE SELECCIÓN DE TECNOLOGÍAS.pdf`.

---

**Integrantes del equipo**

- Manuel Quistial
- Jonathan Betancur
- Laura Zarate

