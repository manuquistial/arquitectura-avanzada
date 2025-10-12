# 🔧 Troubleshooting Guide - Carpeta Ciudadana

**Solución de Problemas Comunes**

**Versión**: 1.0.0  
**Fecha**: 2025-10-13  
**Autor**: Manuel Jurado

---

## 📋 Índice

1. [Development Issues](#development-issues)
2. [Deployment Issues](#deployment-issues)
3. [Kubernetes Issues](#kubernetes-issues)
4. [Database Issues](#database-issues)
5. [Network Issues](#network-issues)
6. [Security Issues](#security-issues)
7. [Performance Issues](#performance-issues)
8. [Monitoring Issues](#monitoring-issues)

---

## 🐛 Development Issues

### Issue: Services won't start locally

**Symptoms**:
```bash
./start-services.sh
# Error: Port already in use
```

**Solutions**:

1. **Check ports**:
```bash
# Find processes using ports
lsof -i :8000  # Gateway
lsof -i :8001  # Citizen
lsof -i :3000  # Frontend

# Kill process
kill -9 <PID>
```

2. **Stop all services**:
```bash
./stop-services.sh
docker-compose down
```

3. **Clean restart**:
```bash
make clean
docker-compose up -d
./start-services.sh
```

---

### Issue: Docker Compose fails

**Symptoms**:
```bash
docker-compose up -d
# Error: Cannot create container
```

**Solutions**:

1. **Check Docker is running**:
```bash
docker ps
# If error, start Docker Desktop
```

2. **Clean Docker**:
```bash
docker-compose down -v  # Remove volumes
docker system prune -a  # Clean all
```

3. **Rebuild images**:
```bash
docker-compose build --no-cache
docker-compose up -d
```

---

### Issue: Poetry dependency conflicts

**Symptoms**:
```bash
poetry install
# Error: Dependency conflict
```

**Solutions**:

1. **Update lock file**:
```bash
poetry lock --no-update
poetry install
```

2. **Clear cache**:
```bash
poetry cache clear pypi --all
rm poetry.lock
poetry install
```

3. **Use specific versions**:
```toml
# pyproject.toml
[tool.poetry.dependencies]
python = "^3.13"
fastapi = "0.104.1"  # Pin specific version
```

---

### Issue: Frontend build fails

**Symptoms**:
```bash
cd apps/frontend && npm run build
# Error: Module not found
```

**Solutions**:

1. **Clean install**:
```bash
rm -rf node_modules package-lock.json
npm install
```

2. **Clear Next.js cache**:
```bash
rm -rf .next
npm run build
```

3. **Check Node version**:
```bash
node --version  # Should be 20+
nvm use 20
```

---

## 🚀 Deployment Issues

### Issue: Terraform apply fails

**Symptoms**:
```bash
terraform apply
# Error: Resource already exists
```

**Solutions**:

1. **Import existing resources**:
```bash
terraform import azurerm_resource_group.rg /subscriptions/.../resourceGroups/carpeta-rg
```

2. **State refresh**:
```bash
terraform refresh
terraform plan
```

3. **Destroy and recreate**:
```bash
terraform destroy -target=azurerm_kubernetes_cluster.aks
terraform apply
```

---

### Issue: Helm upgrade fails

**Symptoms**:
```bash
helm upgrade carpeta-ciudadana ./carpeta-ciudadana
# Error: Release already exists
```

**Solutions**:

1. **Force upgrade**:
```bash
helm upgrade --install --force carpeta-ciudadana ./carpeta-ciudadana
```

2. **Rollback**:
```bash
helm rollback carpeta-ciudadana 0  # Rollback to previous
```

3. **Uninstall and reinstall**:
```bash
helm uninstall carpeta-ciudadana -n carpeta-ciudadana
helm install carpeta-ciudadana ./carpeta-ciudadana -n carpeta-ciudadana
```

---

### Issue: Docker image push fails

**Symptoms**:
```bash
docker push manuquistial/gateway:latest
# Error: denied
```

**Solutions**:

1. **Login to Docker Hub**:
```bash
docker login
# Enter username and password
```

2. **Check image tag**:
```bash
docker images | grep gateway
# Ensure correct tag
```

3. **Rebuild and push**:
```bash
docker build -t manuquistial/gateway:latest .
docker push manuquistial/gateway:latest
```

---

## ☸️ Kubernetes Issues

### Issue: Pods crashing (CrashLoopBackOff)

**Symptoms**:
```bash
kubectl get pods
# NAME                        READY   STATUS             RESTARTS
# gateway-xxx                 0/1     CrashLoopBackOff   5
```

**Solutions**:

1. **Check logs**:
```bash
kubectl logs gateway-xxx -n carpeta-ciudadana
kubectl logs gateway-xxx -n carpeta-ciudadana --previous
```

2. **Describe pod**:
```bash
kubectl describe pod gateway-xxx -n carpeta-ciudadana
# Check Events section
```

3. **Common causes**:
   - Missing environment variables → Check ConfigMap/Secrets
   - Invalid config → Check values.yaml
   - Resource limits too low → Increase limits
   - Health check failing → Check /health endpoint

4. **Fix example (env vars)**:
```yaml
# values.yaml
gateway:
  env:
    - name: DATABASE_URL
      value: "postgresql://..."  # Was missing
```

---

### Issue: ImagePullBackOff

**Symptoms**:
```bash
kubectl get pods
# NAME                        READY   STATUS             
# gateway-xxx                 0/1     ImagePullBackOff
```

**Solutions**:

1. **Check image exists**:
```bash
docker pull manuquistial/gateway:latest
```

2. **Check image pull secret**:
```bash
kubectl get secrets -n carpeta-ciudadana
kubectl describe secret regcred -n carpeta-ciudadana
```

3. **Recreate secret**:
```bash
kubectl delete secret regcred -n carpeta-ciudadana
kubectl create secret docker-registry regcred \
  --docker-server=https://index.docker.io/v1/ \
  --docker-username=<username> \
  --docker-password=<password> \
  -n carpeta-ciudadana
```

---

### Issue: Service not accessible

**Symptoms**:
```bash
curl http://gateway-svc:8000
# Connection refused
```

**Solutions**:

1. **Check service**:
```bash
kubectl get svc -n carpeta-ciudadana
kubectl describe svc gateway -n carpeta-ciudadana
```

2. **Check endpoints**:
```bash
kubectl get endpoints gateway -n carpeta-ciudadana
# Should list pod IPs
```

3. **Port forward for testing**:
```bash
kubectl port-forward svc/gateway 8000:8000 -n carpeta-ciudadana
curl http://localhost:8000/health
```

4. **Check NetworkPolicy**:
```bash
kubectl get networkpolicy -n carpeta-ciudadana
# Ensure policy allows traffic
```

---

### Issue: Persistent Volume not binding

**Symptoms**:
```bash
kubectl get pvc
# NAME          STATUS    VOLUME   CAPACITY
# postgres-pvc  Pending
```

**Solutions**:

1. **Check storage class**:
```bash
kubectl get storageclass
kubectl describe storageclass default
```

2. **Check PV**:
```bash
kubectl get pv
# Ensure PV exists and matches PVC
```

3. **Force delete PVC and recreate**:
```bash
kubectl delete pvc postgres-pvc -n carpeta-ciudadana --force --grace-period=0
# Recreate via Helm
```

---

## 🗄️ Database Issues

### Issue: Cannot connect to PostgreSQL

**Symptoms**:
```python
# Error: could not connect to server
psycopg2.OperationalError: connection refused
```

**Solutions**:

1. **Check database is running**:
```bash
kubectl get pods -l app=postgresql -n carpeta-ciudadana
kubectl logs postgresql-xxx -n carpeta-ciudadana
```

2. **Check connection string**:
```bash
# Print env var
kubectl exec gateway-xxx -n carpeta-ciudadana -- env | grep DATABASE_URL
```

3. **Test connection**:
```bash
kubectl exec -it postgresql-xxx -n carpeta-ciudadana -- psql -U postgres -d carpeta_ciudadana
\dt  # List tables
```

4. **Check firewall rules** (Azure PostgreSQL):
```bash
az postgres flexible-server firewall-rule list \
  --resource-group carpeta-rg \
  --name carpeta-postgres
```

---

### Issue: Migration fails

**Symptoms**:
```bash
alembic upgrade head
# Error: relation already exists
```

**Solutions**:

1. **Check current revision**:
```bash
alembic current
alembic history
```

2. **Force to specific revision**:
```bash
alembic stamp head
alembic upgrade head
```

3. **Rollback and retry**:
```bash
alembic downgrade -1
alembic upgrade head
```

4. **Reset database** (DEV ONLY):
```bash
alembic downgrade base
alembic upgrade head
```

---

## 🌐 Network Issues

### Issue: NetworkPolicy blocking traffic

**Symptoms**:
```bash
# Pods can't communicate
curl http://citizen-svc:8001/health
# Connection timeout
```

**Solutions**:

1. **Check NetworkPolicy**:
```bash
kubectl get networkpolicy -n carpeta-ciudadana
kubectl describe networkpolicy gateway-netpol -n carpeta-ciudadana
```

2. **Temporarily disable** (testing only):
```bash
kubectl delete networkpolicy --all -n carpeta-ciudadana
```

3. **Fix NetworkPolicy**:
```yaml
# Allow gateway → citizen
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: citizen-netpol
spec:
  podSelector:
    matchLabels:
      app: citizen
  ingress:
    - from:
      - podSelector:
          matchLabels:
            app: gateway
      ports:
        - protocol: TCP
          port: 8001
```

---

### Issue: DNS resolution failing

**Symptoms**:
```bash
# Can't resolve service names
nslookup gateway-svc
# server can't find gateway-svc
```

**Solutions**:

1. **Check CoreDNS**:
```bash
kubectl get pods -n kube-system -l k8s-app=kube-dns
kubectl logs -n kube-system -l k8s-app=kube-dns
```

2. **Test DNS from pod**:
```bash
kubectl run -it --rm debug --image=busybox --restart=Never -- sh
nslookup gateway-svc.carpeta-ciudadana.svc.cluster.local
```

3. **Restart CoreDNS**:
```bash
kubectl rollout restart deployment coredns -n kube-system
```

---

## 🔐 Security Issues

### Issue: Azure AD B2C authentication fails

**Symptoms**:
```bash
# Frontend login redirect fails
# Error: Invalid client
```

**Solutions**:

1. **Check B2C configuration**:
```bash
# Verify in Azure Portal:
# - Tenant ID correct
# - Client ID correct
# - Redirect URI matches (http://localhost:3000/api/auth/callback/azure-ad-b2c)
```

2. **Check environment variables**:
```bash
# apps/frontend/.env.local
AZURE_AD_B2C_TENANT_NAME=your-tenant
AZURE_AD_B2C_CLIENT_ID=your-client-id
AZURE_AD_B2C_CLIENT_SECRET=your-secret
```

3. **Check user flow**:
   - Ensure user flow is published
   - Check user attributes configuration

---

### Issue: Key Vault access denied

**Symptoms**:
```bash
# Pods can't access secrets
kubectl logs gateway-xxx -n carpeta-ciudadana
# Error: Access denied to Key Vault
```

**Solutions**:

1. **Check Workload Identity**:
```bash
kubectl get serviceaccount -n carpeta-ciudadana
kubectl describe sa default -n carpeta-ciudadana
# Should have azure.workload.identity annotations
```

2. **Check Key Vault access policy**:
```bash
az keyvault show --name carpeta-keyvault --query properties.accessPolicies
```

3. **Grant access**:
```bash
# Get AKS Managed Identity
IDENTITY_ID=$(az aks show -g carpeta-rg -n carpeta-aks --query identity.principalId -o tsv)

# Grant access
az keyvault set-policy --name carpeta-keyvault \
  --object-id $IDENTITY_ID \
  --secret-permissions get list
```

---

## ⚡ Performance Issues

### Issue: High latency (P95 > 500ms)

**Symptoms**:
```bash
# Grafana shows high latency
# Prometheus: histogram_quantile(0.95, ...) > 500ms
```

**Solutions**:

1. **Check database queries**:
```sql
-- Enable query logging
ALTER SYSTEM SET log_min_duration_statement = 100;  -- Log queries > 100ms
SELECT pg_reload_conf();

-- Check slow queries
SELECT * FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;
```

2. **Add database indexes**:
```sql
CREATE INDEX idx_documents_user_created ON documents (user_id, created_at);
EXPLAIN ANALYZE SELECT * FROM documents WHERE user_id = 'user-123';
```

3. **Increase pod resources**:
```yaml
# values.yaml
gateway:
  resources:
    limits:
      cpu: 1000m  # Was 500m
      memory: 1Gi  # Was 512Mi
```

4. **Scale replicas**:
```bash
kubectl scale deployment gateway --replicas=5 -n carpeta-ciudadana
```

5. **Check Redis cache hit rate**:
```bash
redis-cli INFO stats | grep keyspace_hits
# If hit rate < 80%, adjust cache TTL
```

---

### Issue: High CPU usage

**Symptoms**:
```bash
kubectl top pods -n carpeta-ciudadana
# NAME          CPU(cores)   MEMORY(bytes)
# gateway-xxx   980m         512Mi
```

**Solutions**:

1. **Profile application**:
```python
# Add profiling
import cProfile
cProfile.run('my_function()')
```

2. **Check for infinite loops**:
```bash
# Check logs for repeated errors
kubectl logs gateway-xxx -n carpeta-ciudadana | grep ERROR | sort | uniq -c
```

3. **Increase HPA target**:
```yaml
# values.yaml
gateway:
  hpa:
    targetCPUUtilizationPercentage: 80  # Was 70
```

---

## 📊 Monitoring Issues

### Issue: Prometheus not scraping metrics

**Symptoms**:
```bash
# Grafana shows "No data"
# Prometheus targets down
```

**Solutions**:

1. **Check ServiceMonitor**:
```bash
kubectl get servicemonitor -n carpeta-ciudadana
kubectl describe servicemonitor gateway -n carpeta-ciudadana
```

2. **Check Prometheus config**:
```bash
kubectl get configmap prometheus-config -n monitoring -o yaml
```

3. **Check pod labels**:
```bash
kubectl get pods --show-labels -n carpeta-ciudadana
# Ensure labels match ServiceMonitor selector
```

4. **Test metrics endpoint**:
```bash
kubectl port-forward svc/gateway 8000:8000 -n carpeta-ciudadana
curl http://localhost:8000/metrics
```

---

### Issue: Grafana dashboards not loading

**Symptoms**:
```bash
# Grafana UI shows "Error loading dashboard"
```

**Solutions**:

1. **Check Grafana logs**:
```bash
kubectl logs -l app=grafana -n monitoring
```

2. **Re-import dashboards**:
```bash
# From observability/grafana-dashboards/
kubectl create configmap grafana-dashboards \
  --from-file=. \
  -n monitoring
```

3. **Check Grafana datasource**:
```bash
# Grafana UI → Configuration → Data Sources
# Ensure Prometheus datasource is configured
```

---

## 🔍 Common Error Messages

### "context deadline exceeded"

**Cause**: Timeout waiting for operation

**Solutions**:
- Increase timeout in code
- Check network connectivity
- Check if target service is responsive

---

### "too many open files"

**Cause**: File descriptor limit exceeded

**Solutions**:
```bash
# Increase limit
ulimit -n 65536

# Check current limit
ulimit -n
```

---

### "out of memory"

**Cause**: Pod memory limit exceeded

**Solutions**:
```yaml
# Increase memory limit
resources:
  limits:
    memory: 2Gi  # Was 1Gi
```

---

## 📚 Additional Resources

- [Kubernetes Debugging](https://kubernetes.io/docs/tasks/debug/)
- [Docker Debugging](https://docs.docker.com/config/containers/logging/)
- [FastAPI Debugging](https://fastapi.tiangolo.com/tutorial/debugging/)
- [Azure AKS Troubleshooting](https://learn.microsoft.com/en-us/azure/aks/troubleshooting)

---

## 🆘 Getting Help

**Still stuck?**

1. **Check logs**:
   ```bash
   make logs-<service>
   kubectl logs <pod> -n carpeta-ciudadana --previous
   ```

2. **Check events**:
   ```bash
   kubectl get events -n carpeta-ciudadana --sort-by='.lastTimestamp'
   ```

3. **Open an issue**:
   - [GitHub Issues](https://github.com/manuquistial/arquitectura-avanzada/issues)
   - Include logs, error messages, and steps to reproduce

---

**Last Updated**: 2025-10-13  
**Version**: 1.0.0  
**Author**: Manuel Jurado

