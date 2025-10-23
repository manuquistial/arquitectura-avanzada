# Carpeta Ciudadana - Local Development Setup

This guide explains how to run the Carpeta Ciudadana application locally using virtual environments (venv) for Python services and npm for the frontend.

## Prerequisites

- **Python 3.8+** - Required for backend services
- **Node.js 18+** - Required for frontend
- **Docker** - Required for infrastructure services (PostgreSQL, OpenSearch)
- **Git** - For cloning the repository

## Quick Start

1. **Setup the local environment:**
   ```bash
   ./scripts/setup-local-env.sh
   ```

2. **Start infrastructure services:**
   ```bash
   ./scripts/start-infrastructure.sh
   ```

3. **Start all application services:**
   ```bash
   ./scripts/start-local-services.sh
   ```

4. **Access the application:**
   - Frontend: http://localhost:3000
   - API Documentation: http://localhost:8000/docs (Auth service)

5. **Stop all services:**
   ```bash
   ./scripts/stop-local-services.sh
   ./scripts/stop-infrastructure.sh
   ```

## Service Ports

The following ports are used for local development:

| Service | Port | URL | Description |
|---------|------|-----|-------------|
| Frontend | 3000 | http://localhost:3000 | Next.js React application |
| Auth | 8000 | http://localhost:8000 | Authentication service |
| Citizen | 8001 | http://localhost:8001 | Citizen management service |
| Ingestion | 8002 | http://localhost:8002 | Document ingestion service |
| Metadata | 8003 | http://localhost:8003 | Metadata and search service |
| Transfer | 8004 | http://localhost:8004 | P2P transfer service |
| Signature | 8005 | http://localhost:8005 | Document signature service |
| MinTIC Client | 8006 | http://localhost:8006 | MinTIC Hub integration |
| Read Models | 8007 | http://localhost:8007 | CQRS read models |
| PostgreSQL | 5432 | localhost:5432 | Database |
| OpenSearch | 9200 | http://localhost:9200 | Search engine |

## Manual Setup (Alternative)

If you prefer to set up services manually:

### 1. Infrastructure Services

Start PostgreSQL and OpenSearch using Docker:

```bash
# PostgreSQL
docker run --name carpeta-postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=carpeta_ciudadana \
  -e POSTGRES_USER=postgres \
  -p 5432:5432 \
  -d postgres:15-alpine

# OpenSearch
docker run --name carpeta-opensearch \
  -e discovery.type=single-node \
  -e "OPENSEARCH_JAVA_OPTS=-Xms512m -Xmx512m" \
  -e "DISABLE_SECURITY_PLUGIN=true" \
  -p 9200:9200 \
  -p 9600:9600 \
  -d opensearchproject/opensearch:2.11.0
```

### 2. Backend Services

For each service in the `services/` directory:

```bash
cd services/[service-name]

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -e .

# Start service (replace [port] with the appropriate port)
python -m uvicorn app.main:app --host 0.0.0.0 --port [port] --reload
```

### 3. Frontend

```bash
cd apps/frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

## Environment Configuration

The local development environment uses the following configuration:

- **Database**: PostgreSQL on localhost:5432
- **Search**: OpenSearch on localhost:9200
- **CORS**: Configured for all local ports
- **Environment**: development mode with debug enabled
- **Azure Services**: Mocked or disabled for local development

## Troubleshooting

### Port Already in Use

If you get "port already in use" errors:

1. Check what's using the port:
   ```bash
   lsof -i :[port]
   ```

2. Kill the process:
   ```bash
   kill -9 [PID]
   ```

3. Or use the cleanup script:
   ```bash
   ./scripts/stop-local-services.sh
   ```

### Database Connection Issues

1. Ensure PostgreSQL is running:
   ```bash
   docker ps | grep postgres
   ```

2. Check database connection:
   ```bash
   psql -h localhost -p 5432 -U postgres -d carpeta_ciudadana
   ```

### Service Dependencies

Services have the following dependencies:
- **All services** → PostgreSQL
- **Metadata service** → OpenSearch
- **Frontend** → All backend services

Start services in this order:
1. Infrastructure (PostgreSQL, OpenSearch)
2. Backend services
3. Frontend

## Development Workflow

1. **Make changes** to any service
2. **Services auto-reload** with uvicorn's `--reload` flag
3. **Frontend auto-reloads** with Next.js development server
4. **Database migrations** run automatically on service startup

## API Documentation

Each service provides OpenAPI documentation:

- Auth Service: http://localhost:8000/docs
- Citizen Service: http://localhost:8001/docs
- Ingestion Service: http://localhost:8002/docs
- Metadata Service: http://localhost:8003/docs
- Transfer Service: http://localhost:8004/docs
- Signature Service: http://localhost:8005/docs
- MinTIC Client: http://localhost:8006/docs
- Read Models: http://localhost:8007/docs

## Testing

Run tests for individual services:

```bash
# Backend service tests
cd services/[service-name]
source venv/bin/activate
pytest

# Frontend tests
cd apps/frontend
npm test
```

## Logs

Service logs are displayed in the terminal where you started them. For better log management, you can redirect logs to files:

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload >> logs/auth.log 2>&1 &
```

## Performance

For better performance during development:

1. **Use SSD storage** for faster file I/O
2. **Increase Docker memory** allocation (8GB+ recommended)
3. **Close unused applications** to free up system resources
4. **Use Python 3.11+** for better performance

## Security Notes

⚠️ **Important**: This local setup is for development only. It includes:

- Default passwords and secrets
- CORS enabled for all origins
- Debug mode enabled
- No SSL/TLS encryption

Do not use this configuration in production.
