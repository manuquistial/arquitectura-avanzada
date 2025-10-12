# Transfer Worker

Dedicated consumer service for processing transfer requests from Azure Service Bus queue.

## Overview

This service is designed to scale independently from the API services, consuming transfer messages from a Service Bus queue and processing them asynchronously.

## Features

- **Event-Driven**: Consumes messages from Azure Service Bus
- **Auto-Scaling**: Scales based on queue length using KEDA
- **Concurrent Processing**: Processes multiple messages in parallel
- **Graceful Shutdown**: Completes in-flight messages before shutdown
- **DLQ Support**: Failed messages moved to Dead Letter Queue
- **Observability**: Health, readiness, and metrics endpoints

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SERVICEBUS_CONNECTION_STRING` | Azure Service Bus connection string | Required |
| `SERVICEBUS_TRANSFER_QUEUE` | Queue name for transfers | `transfers` |
| `MAX_CONCURRENT_MESSAGES` | Max concurrent messages to process | `10` |
| `PREFETCH_COUNT` | Number of messages to prefetch | `20` |
| `MAX_WAIT_TIME` | Max time to wait for messages (seconds) | `60` |
| `LOG_LEVEL` | Logging level | `INFO` |

## Endpoints

### Health
```
GET /health
```
Returns 200 if service is running.

### Readiness
```
GET /ready
```
Returns 200 if consumer is active and ready to process messages.

### Metrics
```
GET /metrics
```
Returns basic processing metrics:
- `messages_processed`: Total messages processed
- `messages_failed`: Total messages failed
- `messages_in_progress`: Current messages being processed

## Scaling with KEDA

The worker scales automatically based on Service Bus queue length:

- **Min replicas**: 0 (scales to zero when queue is empty)
- **Max replicas**: 30
- **Target**: 5 messages per pod
- **Cooldown**: 300 seconds

See `deploy/helm/carpeta-ciudadana/templates/scaledobject-transfer-worker.yaml` for configuration.

## Development

### Local Run
```bash
cd services/transfer_worker
poetry install
poetry run python -m app.main
```

### Test
```bash
poetry run pytest
```

### Build Docker Image
```bash
docker build -t carpeta-transfer-worker:latest .
```

## Architecture

```
┌─────────────────────┐
│  Transfer API       │
│  (REST endpoint)    │
└──────────┬──────────┘
           │
           │ Publishes message
           ▼
┌─────────────────────┐
│  Service Bus Queue  │
│  (transfers)        │
└──────────┬──────────┘
           │
           │ Consumes (KEDA triggers scale)
           ▼
┌─────────────────────┐
│  Transfer Worker    │
│  (0-30 replicas)    │
└──────────┬──────────┘
           │
           │ Updates
           ▼
┌─────────────────────┐
│  PostgreSQL         │
│  (transfer table)   │
└─────────────────────┘
```

## Processing Flow

1. Message received from Service Bus queue
2. Validate transfer data
3. Check ownership (source and destination)
4. Update transfer status to "processing"
5. Copy document references
6. Update transfer status to "completed"
7. Send notifications to involved parties
8. Emit domain events
9. Complete message (removed from queue)

## Error Handling

- **Transient errors**: Message reprocessed (max 3 retries)
- **Permanent errors**: Message moved to DLQ
- **Timeout**: Message visibility timeout = 5 minutes

## Monitoring

### Prometheus Metrics (TODO)
- `transfer_worker_messages_processed_total`
- `transfer_worker_messages_failed_total`
- `transfer_worker_processing_duration_seconds`
- `transfer_worker_queue_length`

### Alerts (TODO)
- High failure rate (>10%)
- Long processing time (>30s p95)
- DLQ accumulation (>100 messages)

## Deployment

Deployed via Helm chart:
```bash
helm upgrade --install carpeta-ciudadana deploy/helm/carpeta-ciudadana \
  --set transferWorker.enabled=true \
  --set transferWorker.minReplicas=0 \
  --set transferWorker.maxReplicas=30
```

## TODOs

- [ ] Implement actual transfer processing logic
- [ ] Add Prometheus metrics
- [ ] Add distributed tracing (OpenTelemetry)
- [ ] Add retry strategy configuration
- [ ] Add circuit breaker for external calls
- [ ] Add integration tests
- [ ] Add load testing scenarios

