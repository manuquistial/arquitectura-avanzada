# Carpeta Ciudadana - Desarrollo Local Manual (Sin Docker)

Esta guía explica cómo ejecutar la aplicación Carpeta Ciudadana localmente usando instalaciones manuales de PostgreSQL, sin Docker.

## Prerrequisitos

- **Python 3.8+** - Requerido para servicios backend
- **Node.js 18+** - Requerido para frontend
- **PostgreSQL 15+** - Base de datos
- **Git** - Para clonar el repositorio

## Instalación Manual de Prerrequisitos

### macOS (usando Homebrew)

```bash
# Instalar Python y Node.js
brew install python@3.11 node

# Instalar PostgreSQL
brew install postgresql@15
brew services start postgresql@15


# Crear base de datos
createdb carpeta_ciudadana
```

### Ubuntu/Debian

```bash
# Actualizar sistema
sudo apt update

# Instalar Python y Node.js
sudo apt install python3.11 python3.11-venv python3.11-pip nodejs npm

# Instalar PostgreSQL
sudo apt install postgresql-15 postgresql-client-15
sudo systemctl start postgresql
sudo systemctl enable postgresql


# Crear base de datos
sudo -u postgres createdb carpeta_ciudadana
```

### Windows

1. **Python**: Descargar desde [python.org](https://www.python.org/downloads/)
2. **Node.js**: Descargar desde [nodejs.org](https://nodejs.org/)
3. **PostgreSQL**: Descargar desde [postgresql.org](https://www.postgresql.org/download/windows/)

## Configuración Rápida

1. **Configurar el entorno:**
   ```bash
   ./scripts/setup-manual-env.sh
   ```

2. **Verificar que PostgreSQL esté ejecutándose:**
   ```bash
   # Verificar PostgreSQL
   psql -h localhost -p 5432 -U postgres -d carpeta_ciudadana -c "SELECT version();"
   
   ```

3. **Iniciar todos los servicios:**
   ```bash
   ./scripts/start-services-manual.sh
   ```

4. **Acceder a la aplicación:**
   - Frontend: http://localhost:3000
   - Documentación API: http://localhost:8000/docs

5. **Detener todos los servicios:**
   ```bash
   ./scripts/stop-local-services.sh
   ```

## Configuración Manual Paso a Paso

### 1. Configurar PostgreSQL

```bash
# Iniciar PostgreSQL
brew services start postgresql  # macOS
# o
sudo systemctl start postgresql  # Linux

# Crear base de datos
createdb carpeta_ciudadana

# Verificar conexión
psql -h localhost -p 5432 -U postgres -d carpeta_ciudadana
```


# Verificar que esté funcionando
curl http://localhost:9200
```

### 3. Configurar Servicios Backend

Para cada servicio en el directorio `services/`:

```bash
cd services/[nombre-servicio]

# Crear entorno virtual
python3 -m venv venv

# Activar entorno virtual
source venv/bin/activate

# Instalar dependencias
pip install --upgrade pip
pip install -e .

# Configurar variables de entorno
export DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/carpeta_ciudadana"
export ENVIRONMENT="development"
export DEBUG="true"

# Iniciar servicio
python -m uvicorn app.main:app --host 0.0.0.0 --port [puerto] --reload
```

### 4. Configurar Frontend

```bash
cd apps/frontend

# Instalar dependencias
npm install

# Configurar variables de entorno
export NEXT_PUBLIC_API_URL="http://localhost:8000"
export NEXT_PUBLIC_AUTH_SERVICE_URL="http://localhost:8000"
export NEXT_PUBLIC_CITIZEN_SERVICE_URL="http://localhost:8001"
# ... (ver script completo para todas las variables)

# Iniciar servidor de desarrollo
npm run dev
```

## Puertos de Servicios

| Servicio | Puerto | URL | Descripción |
|----------|--------|-----|-------------|
| Frontend | 3000 | http://localhost:3000 | Aplicación React Next.js |
| Auth | 8000 | http://localhost:8000 | Servicio de autenticación |
| Citizen | 8001 | http://localhost:8001 | Gestión de ciudadanos |
| Ingestion | 8002 | http://localhost:8002 | Ingesta de documentos |
| Transfer | 8004 | http://localhost:8004 | Transferencias P2P |
| Signature | 8005 | http://localhost:8005 | Firmas de documentos |
| MinTIC Client | 8006 | http://localhost:8006 | Integración MinTIC Hub |
| PostgreSQL | 5432 | localhost:5432 | Base de datos |

## Variables de Entorno

Cada servicio usa las siguientes variables de entorno para desarrollo local:

```bash
# Base de datos
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/carpeta_ciudadana


# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:8000,http://localhost:8001,http://localhost:8002,http://localhost:8004,http://localhost:8005,http://localhost:8006

# Entorno
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO
```

## Orden de Inicio

1. **Infraestructura:**
   - PostgreSQL (puerto 5432)

2. **Servicios Backend:**
   - Auth (puerto 8000)
   - Citizen (puerto 8001)
   - Ingestion (puerto 8002)
   - Transfer (puerto 8004)
   - Signature (puerto 8005)
   - MinTIC Client (puerto 8006)

3. **Frontend:**
   - Next.js (puerto 3000)

## Solución de Problemas

### Puerto Ya en Uso

```bash
# Verificar qué está usando el puerto
lsof -i :[puerto]

# Matar el proceso
kill -9 [PID]
```

### Problemas de Conexión a Base de Datos

```bash
# Verificar que PostgreSQL esté ejecutándose
brew services list | grep postgresql

# Verificar conexión
psql -h localhost -p 5432 -U postgres -d carpeta_ciudadana
```

```

### Dependencias de Servicios

Los servicios tienen las siguientes dependencias:
- **Todos los servicios** → PostgreSQL
- **Frontend** → Todos los servicios backend

## Scripts Disponibles

- `./scripts/setup-manual-env.sh` - Configurar entorno de desarrollo
- `./scripts/start-services-manual.sh` - Iniciar todos los servicios
- `./scripts/stop-local-services.sh` - Detener todos los servicios

## Documentación de API

Cada servicio proporciona documentación OpenAPI:

- Auth Service: http://localhost:8000/docs
- Citizen Service: http://localhost:8001/docs
- Ingestion Service: http://localhost:8002/docs
- Transfer Service: http://localhost:8004/docs
- Signature Service: http://localhost:8005/docs
- MinTIC Client: http://localhost:8006/docs

## Notas de Seguridad

⚠️ **Importante**: Esta configuración es solo para desarrollo. Incluye:

- Contraseñas y secretos por defecto
- CORS habilitado para todos los orígenes
- Modo debug habilitado
- Sin cifrado SSL/TLS

No uses esta configuración en producción.
