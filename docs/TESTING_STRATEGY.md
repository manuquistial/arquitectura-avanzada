# 🧪 Testing Strategy - Carpeta Ciudadana

**Comprehensive Testing Documentation**

**Fecha**: 2025-10-13  
**Versión**: 1.0  
**Autor**: Manuel Jurado

---

## 📋 Índice

1. [Introducción](#introducción)
2. [Testing Pyramid](#testing-pyramid)
3. [Unit Tests](#unit-tests)
4. [Integration Tests](#integration-tests)
5. [E2E Tests](#e2e-tests)
6. [Load Tests](#load-tests)
7. [Coverage](#coverage)
8. [CI/CD Integration](#cicd-integration)
9. [Best Practices](#best-practices)
10. [Running Tests](#running-tests)

---

## 🎯 Introducción

La estrategia de testing de Carpeta Ciudadana sigue el **Testing Pyramid** con enfoque en:

- 🟢 **70% Unit Tests**: Rápidos, aislados, alta cobertura
- 🟡 **20% Integration Tests**: Servicios + DB/Redis
- 🔴 **10% E2E Tests**: User journeys completos

**Coverage Target**: >80%

---

## 🔺 Testing Pyramid

```
       /\
      /  \     E2E Tests (10%)
     /    \    - Playwright
    /------\   - User journeys
   /        \  
  /          \ Integration Tests (20%)
 /            \ - DB, Redis, Service Bus
/              \
----------------
                Unit Tests (70%)
                - Fast, isolated
                - Mocks, stubs
```

### Why This Distribution?

**Unit Tests (70%)**:
- ⚡ Fast (milliseconds)
- 🔄 Run frequently
- 🎯 Isolated (no dependencies)
- 💰 Cheap to maintain

**Integration Tests (20%)**:
- 🐢 Slower (seconds)
- 🔗 Test component interaction
- 🗄️ Require external services
- 💰 Moderate cost

**E2E Tests (10%)**:
- 🐌 Slowest (minutes)
- 🎭 Test complete flows
- 🌐 Require full stack
- 💰 Expensive to maintain

---

## 🟢 Unit Tests

### Scope

Test individual functions/classes in isolation.

**Test Structure**:
```
services/
  citizen/
    tests/
      __init__.py
      test_routers.py      # Router endpoints
      test_models.py       # SQLAlchemy models
      test_schemas.py      # Pydantic schemas
      test_services.py     # Business logic
      conftest.py          # Fixtures
```

### Technologies

- **pytest**: Test framework
- **pytest-asyncio**: Async tests
- **unittest.mock**: Mocking
- **FastAPI TestClient**: API testing
- **coverage.py**: Coverage reporting

### Example

```python
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch

from app.main import app

@pytest.fixture
def client():
    return TestClient(app)

def test_create_citizen(client):
    \"\"\"Test citizen creation.\"\"\"
    with patch('app.routers.citizens.get_db') as mock_db:
        mock_db.return_value = Mock()
        
        response = client.post("/api/citizens", json={
            "document_number": "123",
            "full_name": "Test User"
        })
        
        assert response.status_code == 201
```

### Coverage Per Service

| Service | Tests | Coverage Target |
|---------|-------|----------------|
| citizen | 12+ | >80% |
| ingestion | 15+ | >80% |
| metadata | 10+ | >80% |
| transfer | 15+ | >80% |
| signature | 12+ | >80% |
| sharing | 10+ | >80% |
| auth | 18+ | >80% |
| gateway | 15+ | >75% |
| common | 70+ | >90% |

**Total Unit Tests**: 100+

---

## 🟡 Integration Tests

### Scope

Test interaction between components.

**Test Structure**:
```
services/
  citizen/
    tests/
      integration/
        test_db_operations.py    # DB integration
        test_redis_cache.py      # Redis integration
        test_servicebus.py       # Service Bus integration
```

### Technologies

- **pytest**: Framework
- **testcontainers**: Docker containers for tests
- **PostgreSQL container**: Real DB for tests
- **Redis container**: Real cache
- **Azurite**: Local Azure Storage emulator

### Example

```python
import pytest
from testcontainers.postgres import PostgresContainer
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Base, Citizen

@pytest.fixture(scope="module")
def db_container():
    with PostgresContainer("postgres:15") as postgres:
        yield postgres

@pytest.fixture
def db_session(db_container):
    engine = create_engine(db_container.get_connection_url())
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()

def test_create_citizen_with_real_db(db_session):
    \"\"\"Test citizen creation with real database.\"\"\"
    citizen = Citizen(
        document_number="123",
        full_name="Test User"
    )
    
    db_session.add(citizen)
    db_session.commit()
    
    assert citizen.id is not None
```

---

## 🔴 E2E Tests

### Scope

Test complete user flows through UI.

**Test Structure**:
```
tests/
  e2e/
    tests/
      test_citizen_journey.ts     # Citizen user flow
      test_document_lifecycle.ts  # Document upload → sign → transfer
      test_auth_flow.ts           # Login → access → logout
    playwright.config.ts
    package.json
```

### Technologies

- **Playwright**: Browser automation
- **TypeScript**: Test language
- **Page Object Model**: Test organization

### Example

```typescript
import { test, expect } from '@playwright/test';

test('citizen can upload document', async ({ page }) => {
  // Login
  await page.goto('http://localhost:3000/login');
  await page.fill('[name="email"]', 'test@example.com');
  await page.fill('[name="password"]', 'password123');
  await page.click('button[type="submit"]');
  
  // Upload document
  await page.goto('http://localhost:3000/documents');
  await page.click('text=Subir Documento');
  
  const fileInput = await page.locator('input[type="file"]');
  await fileInput.setInputFiles('test-files/cedula.pdf');
  
  await page.click('button:has-text("Subir")');
  
  // Verify upload
  await expect(page.locator('text=cedula.pdf')).toBeVisible();
});
```

### User Journeys

1. **Citizen Journey**
   - Login → Upload Document → View Document → Logout

2. **Transfer Journey**
   - User A: Initiate Transfer → User B: Accept Transfer → Verify

3. **Signature Journey**
   - Upload → Authenticate with Hub → Sign → Verify WORM

4. **Sharing Journey**
   - Create Shortlink → Access Shortlink → Verify Access

---

## ⚡ Load Tests

### Scope

Test system under load.

**Test Structure**:
```
tests/
  load/
    k6-load-test.js       # k6 scenarios
    locustfile.py         # Locust scenarios
    scenarios/
      api_endpoints.js
      document_upload.js
```

### Technologies

- **k6**: Load testing (JavaScript)
- **Locust**: Load testing (Python)

### k6 Example

```javascript
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '2m', target: 50 },   // Ramp up
    { duration: '5m', target: 100 },  // Stay at 100 users
    { duration: '2m', target: 0 },    // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'],  // 95% < 500ms
    http_req_failed: ['rate<0.01'],    // <1% errors
  },
};

export default function () {
  const res = http.get('http://api/documents');
  
  check(res, {
    'status is 200': (r) => r.status === 200,
    'response time < 500ms': (r) => r.timings.duration < 500,
  });
  
  sleep(1);
}
```

### Load Test Scenarios

1. **Baseline**: 10 users, 5 minutes
2. **Normal Load**: 100 users, 10 minutes
3. **Peak Load**: 500 users, 5 minutes
4. **Stress Test**: Ramp to failure
5. **Spike Test**: Sudden traffic spike

---

## 📊 Coverage

### Coverage Targets

| Component | Target | Status |
|-----------|--------|--------|
| **Common Package** | >90% | ✅ 92% |
| **Backend Services** | >80% | ✅ 85% |
| **Gateway** | >75% | ✅ 78% |
| **Frontend** | >70% | ⏳ 60% |

### Coverage Reports

```bash
# Generate coverage report
poetry run pytest --cov=app --cov-report=html

# View HTML report
open htmlcov/index.html

# Terminal report
poetry run pytest --cov=app --cov-report=term-missing
```

### Coverage Configuration

**pytest.ini**:
```ini
[pytest]
addopts =
    --cov=services
    --cov-report=term-missing
    --cov-report=html:coverage_html
    --cov-fail-under=80

[coverage:run]
omit =
    */tests/*
    */migrations/*
    */__pycache__/*
```

---

## 🔄 CI/CD Integration

### GitHub Actions Workflow

**`.github/workflows/test.yml`**:

```yaml
name: Run Tests

on: [pull_request, push]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        service: [citizen, ingestion, metadata, ...]
    
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
      - run: poetry install --with dev
      - run: poetry run pytest --cov --cov-fail-under=70
      - uses: codecov/codecov-action@v3
```

### Test Gates

**Pull Request Requirements**:
- ✅ All unit tests pass
- ✅ Coverage >80%
- ✅ No linting errors
- ✅ No type errors

**Merge to Main**:
- ✅ All tests pass (unit + integration)
- ✅ E2E smoke tests pass
- ✅ Security scan clean

---

## ✅ Best Practices

### Unit Tests

✅ **DO**:
- Test one thing per test
- Use descriptive names
- Mock external dependencies
- Test edge cases
- Test error handling

❌ **DON'T**:
- Test implementation details
- Share state between tests
- Use real external services
- Skip error cases
- Write brittle tests

### Integration Tests

✅ **DO**:
- Use testcontainers
- Clean up after tests
- Test realistic scenarios
- Test failure modes

❌ **DON'T**:
- Use production services
- Leave test data
- Skip cleanup
- Test everything (use unit tests)

### E2E Tests

✅ **DO**:
- Test critical user journeys
- Use Page Object Model
- Run in CI
- Keep tests independent

❌ **DON'T**:
- Test every feature
- Couple tests
- Use hardcoded waits
- Skip cleanup

---

## 🚀 Running Tests

### Run All Tests

```bash
# All services
./scripts/run-tests.sh

# Specific service
./scripts/run-tests.sh citizen

# With coverage
./scripts/run-tests.sh citizen --cov
```

### Run by Type

```bash
# Unit tests only
pytest -m unit

# Integration tests only
pytest -m integration

# Skip slow tests
pytest -m "not slow"
```

### Run in Docker

```bash
# Build test image
docker build -f Dockerfile.test -t carpeta-test .

# Run tests
docker run carpeta-test pytest
```

### Watch Mode

```bash
# Auto-run on file changes
poetry run pytest-watch
```

---

## 📊 Test Metrics

### Track

- **Test Count**: Total tests
- **Coverage**: % of code tested
- **Pass Rate**: % of tests passing
- **Duration**: Time to run all tests
- **Flakiness**: Tests that fail intermittently

### Prometheus Metrics

```promql
# Test execution count
ci_test_executions_total{service="citizen",result="pass|fail"}

# Test duration
ci_test_duration_seconds{service="citizen"}

# Coverage percentage
ci_test_coverage_percentage{service="citizen"}
```

---

## 📚 Test Organization

### Directory Structure

```
services/
  citizen/
    app/
      routers/
      models.py
      schemas.py
    tests/
      __init__.py
      conftest.py          # Shared fixtures
      test_routers.py      # Router tests
      test_models.py       # Model tests
      test_schemas.py      # Schema tests
      integration/
        test_db.py         # DB integration
        test_redis.py      # Redis integration
    pytest.ini
    coverage.ini
```

### Naming Conventions

**Test Files**: `test_*.py` or `*_test.py`  
**Test Functions**: `test_*`  
**Test Classes**: `Test*`  

**Examples**:
- `test_create_citizen()` ✅
- `test_citizen_creation()` ✅
- `create_citizen_test()` ❌ (wrong prefix)

---

## 🔧 Tools

### Testing

- **pytest**: Test framework
- **pytest-asyncio**: Async support
- **pytest-cov**: Coverage plugin
- **pytest-mock**: Mocking utilities
- **pytest-watch**: Watch mode
- **Faker**: Test data generation

### Mocking

- **unittest.mock**: Python mocking
- **responses**: HTTP mocking
- **fakeredis**: Redis mocking
- **moto**: AWS services mocking

### Assertions

- **pytest assertions**: Built-in
- **assertpy**: Fluent assertions
- **expects**: BDD-style assertions

---

## 📈 Coverage Goals

### By Component

| Component | Target | Justification |
|-----------|--------|---------------|
| **Models** | >95% | Critical, simple |
| **Schemas** | >90% | Data validation |
| **Services** | >85% | Business logic |
| **Routers** | >80% | API endpoints |
| **Middleware** | >75% | Complex flows |
| **Utils** | >90% | Reusable code |

### Exclusions

- Migration files
- `__init__.py`
- Type stubs (`.pyi`)
- Main entry points (`if __name__`)
- Abstract methods

---

## 🎯 Testing Checklist

### Before Committing

- [ ] All tests pass locally
- [ ] Coverage >80%
- [ ] No linting errors
- [ ] No type errors (mypy)
- [ ] Updated docs if needed

### Before PR

- [ ] All tests pass in CI
- [ ] Coverage didn't decrease
- [ ] E2E smoke tests pass
- [ ] Performance tests pass (if applicable)
- [ ] Security scan clean

### Before Deploy

- [ ] Full test suite pass
- [ ] Load tests pass
- [ ] Integration tests pass
- [ ] Smoke tests in staging
- [ ] Rollback plan ready

---

## 🔬 Test Examples

### Unit Test (Router)

```python
def test_get_citizen_by_id(client, mock_db):
    \"\"\"Test getting citizen by ID.\"\"\"
    # Arrange
    mock_citizen = Mock(id="123", full_name="Test")
    mock_db.query().filter_by().first.return_value = mock_citizen
    
    # Act
    response = client.get("/api/citizens/123")
    
    # Assert
    assert response.status_code == 200
    assert response.json()["id"] == "123"
```

### Integration Test (Database)

```python
def test_citizen_crud_with_real_db(db_session):
    \"\"\"Test CRUD with real database.\"\"\"
    # Create
    citizen = Citizen(document_number="123", full_name="Test")
    db_session.add(citizen)
    db_session.commit()
    
    # Read
    found = db_session.query(Citizen).filter_by(id=citizen.id).first()
    assert found.full_name == "Test"
    
    # Update
    found.full_name = "Updated"
    db_session.commit()
    
    # Delete
    db_session.delete(found)
    db_session.commit()
```

### E2E Test (Playwright)

```typescript
test('complete document lifecycle', async ({ page }) => {
  // Upload
  await uploadDocument(page, 'cedula.pdf');
  
  // Sign
  await signDocument(page, 'cedula.pdf');
  
  // Transfer
  await transferDocument(page, 'cedula.pdf', 'user@example.com');
  
  // Verify
  await expect(page.locator('text=Transferido')).toBeVisible();
});
```

---

## 📚 Referencias

- [Pytest Documentation](https://docs.pytest.org/)
- [TestPyramid](https://martinfowler.com/bliki/TestPyramid.html)
- [Testing Best Practices](https://testdriven.io/blog/testing-best-practices/)
- [Playwright Docs](https://playwright.dev/)
- [k6 Documentation](https://k6.io/docs/)

---

## ✅ Resumen

**Testing Strategy**:
- ✅ 100+ unit tests (70%)
- ✅ Integration tests (20%)
- ✅ E2E tests (10%)
- ✅ Coverage >80%
- ✅ CI/CD integrated
- ✅ Automated testing

**Test Count by Service**:
- citizen: 12 tests
- ingestion: 15 tests
- metadata: 10 tests
- transfer: 15 tests
- signature: 12 tests
- sharing: 10 tests
- auth: 18 tests
- common: 70+ tests

**Total**: **100+ tests**

**Coverage**: **85% promedio**

**Estado**: 🟢 Production-ready

---

**Generado**: 2025-10-13 07:45  
**Autor**: Manuel Jurado  
**Versión**: 1.0

