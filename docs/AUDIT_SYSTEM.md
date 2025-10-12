# 📝 Audit System - Compliance & Security Logging

**Sistema de Auditoría para Cumplimiento Normativo**

**Fecha**: 2025-10-13  
**Versión**: 1.0  
**Autor**: Manuel Jurado

---

## 📋 Índice

1. [Introducción](#introducción)
2. [Arquitectura](#arquitectura)
3. [Audit Events](#audit-events)
4. [AuditLogger Class](#auditlogger-class)
5. [API Endpoints](#api-endpoints)
6. [Dashboard de Auditoría](#dashboard-de-auditoría)
7. [Queries Comunes](#queries-comunes)
8. [Compliance](#compliance)
9. [Best Practices](#best-practices)
10. [Troubleshooting](#troubleshooting)

---

## 🎯 Introducción

El **Audit System** registra todas las operaciones críticas del sistema para:

- 📜 **Compliance**: Cumplimiento normativo (GDPR, ISO 27001)
- 🔐 **Security**: Detección de actividad sospechosa
- 🔍 **Forensics**: Investigación de incidentes
- 📊 **Analytics**: Patrones de uso
- 🛡️ **Legal**: Evidencia en disputas

### Eventos Auditados

✅ **Document Operations**:
- Upload, Download, Delete
- Sign, Verify
- WORM lock

✅ **Transfer Operations**:
- Initiate, Accept, Reject, Cancel

✅ **Sharing Operations**:
- Create shortlink, Access, Revoke

✅ **Authentication**:
- Login, Logout
- Failed login attempts

✅ **Permission Changes**:
- Role assignments
- ABAC policy updates

---

## 🏗️ Arquitectura

```
┌─────────────────────────────────────────────────┐
│          Application Services                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐     │
│  │ Citizen  │  │Ingestion │  │ Transfer │     │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘     │
│       │             │              │           │
│       └─────────────┼──────────────┘           │
│                     │                          │
└─────────────────────┼──────────────────────────┘
                      │
                      ▼
            ┌──────────────────┐
            │  AuditLogger     │
            │  (Common)        │
            └────────┬─────────┘
                     │
                     ▼
            ┌──────────────────┐
            │   PostgreSQL     │
            │  audit_events    │
            │   (Partitioned)  │
            └────────┬─────────┘
                     │
         ┌───────────┴───────────┐
         │                       │
         ▼                       ▼
   ┌──────────┐          ┌──────────┐
   │ Grafana  │          │   API    │
   │Dashboard │          │Endpoints │
   └──────────┘          └──────────┘
```

---

## 📊 Audit Events

### Schema

```sql
CREATE TABLE audit_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Who
    user_id VARCHAR(100),
    user_email VARCHAR(255),
    ip_address VARCHAR(45),
    user_agent VARCHAR(500),
    
    -- What
    event_type VARCHAR(100) NOT NULL,
    action VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,
    
    -- Where
    service_name VARCHAR(50) NOT NULL,
    resource_type VARCHAR(50),
    resource_id VARCHAR(100),
    
    -- How
    request_id VARCHAR(100),
    trace_id VARCHAR(100),
    
    -- Details
    details JSONB,
    changes JSONB,
    error_message TEXT
);
```

### Indexes

```sql
-- Time-based queries
CREATE INDEX idx_audit_timestamp ON audit_events (timestamp);

-- User queries
CREATE INDEX idx_audit_user_timestamp ON audit_events (user_id, timestamp);

-- Resource queries
CREATE INDEX idx_audit_resource ON audit_events (resource_type, resource_id);

-- Action queries
CREATE INDEX idx_audit_action_status ON audit_events (action, status);

-- Failures (partial index)
CREATE INDEX idx_audit_failures ON audit_events (timestamp DESC) 
WHERE status = 'failure';

-- JSONB search (GIN index)
CREATE INDEX idx_audit_details_gin ON audit_events USING GIN (details);
CREATE INDEX idx_audit_changes_gin ON audit_events USING GIN (changes);
```

---

## 🔧 AuditLogger Class

### Basic Usage

```python
from carpeta_common.audit_logger import AuditLogger, AuditAction, AuditStatus

# Initialize
audit = AuditLogger(db_session, service_name="citizen")

# Log event
audit.log_event(
    event_type="DOCUMENT_UPLOAD",
    action=AuditAction.CREATE,
    status=AuditStatus.SUCCESS,
    user_id="user-123",
    resource_type="document",
    resource_id="doc-456",
    ip_address="192.168.1.100",
    details={"filename": "cedula.pdf", "size": 1024}
)
```

### Convenience Methods

```python
# Document upload
audit.log_document_upload(
    user_id="user-123",
    document_id="doc-456",
    filename="cedula.pdf",
    file_size=1024,
    status=AuditStatus.SUCCESS
)

# Document sign
audit.log_document_sign(
    user_id="user-123",
    document_id="doc-456",
    hub_signature="hub_sig_123",
    status=AuditStatus.SUCCESS
)

# Transfer
audit.log_transfer(
    from_user="user-123",
    to_user="user-456",
    document_id="doc-789",
    transfer_id="transfer-111",
    action=AuditAction.TRANSFER,
    status=AuditStatus.SUCCESS
)

# Login
audit.log_login(
    user_id="user-123",
    user_email="user@example.com",
    status=AuditStatus.SUCCESS,
    ip_address="192.168.1.100"
)
```

---

## 📡 API Endpoints

### List Audit Events

**GET** `/api/audit/events`

**Query Parameters**:
- `user_id`: Filter by user
- `resource_type`: Filter by resource
- `resource_id`: Filter by specific resource
- `action`: Filter by action
- `status`: Filter by status
- `days`: Days to look back (default: 7)
- `limit`: Max results (default: 100)
- `offset`: Pagination offset

**Response**:
```json
[
  {
    "id": "event-uuid",
    "timestamp": "2025-10-13T08:00:00Z",
    "event_type": "DOCUMENT_UPLOAD",
    "user_id": "user-123",
    "user_email": "user@example.com",
    "ip_address": "192.168.1.100",
    "service_name": "ingestion",
    "resource_type": "document",
    "resource_id": "doc-456",
    "action": "create",
    "status": "success",
    "details": {
      "filename": "cedula.pdf",
      "file_size": 1024
    }
  }
]
```

### Get Audit Stats

**GET** `/api/audit/stats?days=7`

**Response**:
```json
{
  "total_events": 1250,
  "success_count": 1200,
  "failure_count": 50,
  "events_by_action": {
    "create": 450,
    "read": 600,
    "update": 100,
    "delete": 50,
    "sign": 50
  },
  "events_by_resource": {
    "document": 800,
    "transfer": 300,
    "user": 150
  },
  "top_users": [
    {"user_id": "user-123", "event_count": 150},
    {"user_id": "user-456", "event_count": 120}
  ]
}
```

### Get User History

**GET** `/api/audit/user/{user_id}/history?days=30`

Returns all audit events for specific user.

### Get Resource History

**GET** `/api/audit/resource/{resource_type}/{resource_id}`

Returns audit trail for specific resource (e.g., document).

### Get Recent Failures

**GET** `/api/audit/failures?hours=24`

Returns recent failed operations for security monitoring.

---

## 📊 Dashboard de Auditoría

### Grafana Panels

**Panel 1**: Total Audit Events (24h)  
**Panel 2**: Success Rate (gauge)  
**Panel 3**: Failures (24h)  
**Panel 4**: Active Users (24h)  
**Panel 5**: Events Over Time (timeseries)  
**Panel 6**: Events by Action (pie chart)  
**Panel 7**: Events by Resource Type (pie chart)  
**Panel 8**: Recent Failures (table)  
**Panel 9**: Top 10 Most Active Users (table)  
**Panel 10**: Most Accessed Resources (table)  
**Panel 11**: Security Events (timeseries)  
**Panel 12**: WORM Operations (timeseries)  

### Access

**URL**: `https://grafana.example.com/d/audit-dashboard`

**Permissions**: Admin only

---

## 🔍 Queries Comunes

### Get all events for document

```sql
SELECT * FROM audit_events
WHERE resource_type = 'document'
  AND resource_id = 'doc-123'
ORDER BY timestamp DESC;
```

### Get failed login attempts

```sql
SELECT user_email, ip_address, timestamp, error_message
FROM audit_events
WHERE event_type = 'USER_LOGIN'
  AND status = 'failure'
  AND timestamp > NOW() - INTERVAL '24 hours'
ORDER BY timestamp DESC;
```

### Get user activity for last 30 days

```sql
SELECT event_type, action, COUNT(*) as count
FROM audit_events
WHERE user_id = 'user-123'
  AND timestamp > NOW() - INTERVAL '30 days'
GROUP BY event_type, action
ORDER BY count DESC;
```

### Get permission changes

```sql
SELECT 
    timestamp,
    user_id as admin_user,
    resource_id as target_user,
    changes
FROM audit_events
WHERE event_type = 'PERMISSION_CHANGE'
ORDER BY timestamp DESC
LIMIT 50;
```

### Detect suspicious activity

```sql
-- Multiple failed logins from same IP
SELECT ip_address, COUNT(*) as failed_attempts
FROM audit_events
WHERE event_type = 'USER_LOGIN'
  AND status = 'failure'
  AND timestamp > NOW() - INTERVAL '1 hour'
GROUP BY ip_address
HAVING COUNT(*) > 5
ORDER BY failed_attempts DESC;
```

---

## 📋 Compliance

### GDPR Compliance

**Right to Access**:
```python
# Get all events for user
GET /api/audit/user/{user_id}/history?days=365
```

**Right to Erasure**:
```python
# Anonymize user data in audit logs
UPDATE audit_events
SET user_id = 'anonymized',
    user_email = 'anonymized@example.com'
WHERE user_id = 'user-to-delete';
```

**Data Retention**:
```python
# Auto-delete old audit events (>5 years)
DELETE FROM audit_events
WHERE timestamp < NOW() - INTERVAL '5 years';
```

### ISO 27001 Compliance

**A.12.4.1 Event Logging**:
- ✅ User IDs, timestamps, event types
- ✅ Success/failure status
- ✅ IP addresses

**A.12.4.3 Administrator Logs**:
- ✅ Permission changes logged
- ✅ Admin actions tracked

**A.12.4.4 Clock Synchronization**:
- ✅ UTC timestamps
- ✅ NTP sync (Kubernetes)

---

## ✅ Best Practices

### DO ✅

1. **Log critical operations**
   ```python
   audit.log_document_upload(...)  # Always log
   ```

2. **Include context**
   ```python
   audit.log_event(..., ip_address=client_ip, request_id=req_id)
   ```

3. **Log both success and failure**
   ```python
   try:
       operation()
       audit.log_event(..., status=AuditStatus.SUCCESS)
   except Exception as e:
       audit.log_event(..., status=AuditStatus.FAILURE, error_message=str(e))
   ```

4. **Use JSONB for flexible details**
   ```python
   details={"filename": "test.pdf", "size": 1024, "metadata": {...}}
   ```

### DON'T ❌

1. **Don't log sensitive data**
   ```python
   # Bad: Logging password
   details={"password": "secret123"}
   
   # Good: Log action only
   details={"action": "password_change"}
   ```

2. **Don't fail operations if audit fails**
   ```python
   try:
       audit.log_event(...)
   except:
       logger.error("Audit failed")
       # Continue with operation
   ```

3. **Don't log everything**
   ```python
   # Bad: Logging every GET request
   # Good: Log only critical operations
   ```

4. **Don't skip IP address**
   ```python
   # Good: Always include IP for security
   audit.log_event(..., ip_address=client_ip)
   ```

---

## 📊 Monitoring & Alerts

### Prometheus Metrics

```promql
# Audit events rate
rate(audit_events_total[5m])

# Failure rate
rate(audit_events_total{status="failure"}[5m]) /
rate(audit_events_total[5m])

# Top event types
topk(10, sum(rate(audit_events_total[1h])) by (event_type))
```

### Alerts

```yaml
- alert: HighAuditFailureRate
  expr: |
    rate(audit_events_total{status="failure"}[5m])
    /
    rate(audit_events_total[5m])
    > 0.1
  for: 5m
  annotations:
    summary: "High audit failure rate"

- alert: SuspiciousLoginAttempts
  expr: |
    sum(rate(audit_events_total{event_type="USER_LOGIN",status="failure"}[5m])) 
    by (ip_address) > 0.1
  for: 2m
  annotations:
    summary: "Suspicious login attempts from {{ $labels.ip_address }}"
```

---

## 🧪 Testing

### Unit Test

```python
def test_audit_logger(mock_db):
    audit = AuditLogger(mock_db, "test_service")
    
    audit.log_document_upload(
        user_id="user-123",
        document_id="doc-456",
        filename="test.pdf",
        file_size=1024,
        status=AuditStatus.SUCCESS
    )
    
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
```

### Integration Test

```python
def test_audit_event_stored_in_db(db_session):
    audit = AuditLogger(db_session, "test")
    
    audit.log_event(
        event_type="TEST_EVENT",
        action=AuditAction.CREATE,
        status=AuditStatus.SUCCESS,
        user_id="user-123"
    )
    
    # Verify in database
    event = db_session.query(AuditEvent).filter_by(user_id="user-123").first()
    assert event is not None
    assert event.event_type == "TEST_EVENT"
```

---

## 📚 Referencias

- [GDPR Article 30 - Records of Processing](https://gdpr-info.eu/art-30-gdpr/)
- [ISO 27001 - A.12.4 Logging and Monitoring](https://www.iso.org/standard/27001)
- [OWASP Logging Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html)

---

## ✅ Resumen

**Audit System Features**:
- ✅ Comprehensive event logging
- ✅ PostgreSQL storage (JSONB, indexes)
- ✅ AuditLogger class (convenience methods)
- ✅ API endpoints (queries, stats, history)
- ✅ Grafana dashboard (12 panels)
- ✅ Compliance-ready (GDPR, ISO 27001)
- ✅ Security monitoring (failed logins, suspicious activity)
- ✅ Forensics support (complete audit trail)

**Events Tracked**:
- Document operations (upload, sign, delete)
- Transfers (initiate, accept, reject)
- Sharing (create, access, revoke)
- Authentication (login, logout)
- Permission changes

**Queries**:
- By user, resource, action, status
- Time-based filtering
- Statistics and analytics
- Top users and resources

**Estado**: 🟢 Production-ready

---

**Generado**: 2025-10-13 08:15  
**Autor**: Manuel Jurado  
**Versión**: 1.0

