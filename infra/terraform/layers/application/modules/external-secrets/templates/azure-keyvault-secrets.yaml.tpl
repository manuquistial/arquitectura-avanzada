# Azure Key Vault Secrets Configuration
# Este archivo configura la sincronización de secrets desde Azure Key Vault
# Usa Workload Identity para autenticación segura
# Generado automáticamente por Terraform

---
# ClusterSecretStore para Azure Key Vault (acceso global)
apiVersion: external-secrets.io/v1beta1
kind: ClusterSecretStore
metadata:
  name: azure-keyvault-store
  labels:
    app.kubernetes.io/name: carpeta-ciudadana
    app.kubernetes.io/part-of: carpeta-ciudadana
    component: secrets
spec:
  provider:
    azurekv:
      vaultUrl: "${keyvault_uri}"
      authType: "WorkloadIdentity"
      serviceAccountRef:
        name: "external-secrets"
        namespace: "external-secrets-system"

---
# External Secret para Base de Datos
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: database-credentials
  namespace: carpeta-ciudadana
  labels:
    app.kubernetes.io/name: carpeta-ciudadana
    app.kubernetes.io/part-of: carpeta-ciudadana
    component: database
spec:
  refreshInterval: "5m"  # Sincronizar cada 5 minutos
  secretStoreRef:
    name: azure-keyvault-store
    kind: ClusterSecretStore
  target:
    name: database-credentials
    creationPolicy: Owner
  data:
  - secretKey: DATABASE_URL
    remoteRef:
      key: database-credentials
      property: database-url
  - secretKey: POSTGRES_URI
    remoteRef:
      key: database-credentials
      property: postgres-uri
  - secretKey: DB_HOST
    remoteRef:
      key: database-credentials
      property: db-host
  - secretKey: DB_PORT
    remoteRef:
      key: database-credentials
      property: db-port
  - secretKey: DB_NAME
    remoteRef:
      key: database-credentials
      property: db-name
  - secretKey: DB_USER
    remoteRef:
      key: database-credentials
      property: db-user
  - secretKey: DB_PASSWORD
    remoteRef:
      key: database-credentials
      property: db-password
  - secretKey: DB_SSLMODE
    remoteRef:
      key: database-credentials
      property: db-sslmode

---
# External Secret para Azure Storage
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: azure-storage-secrets
  namespace: carpeta-ciudadana
  labels:
    app.kubernetes.io/name: carpeta-ciudadana
    app.kubernetes.io/part-of: carpeta-ciudadana
    component: azure-storage
spec:
  refreshInterval: "5m"
  secretStoreRef:
    name: azure-keyvault-store
    kind: ClusterSecretStore
  target:
    name: azure-storage-secrets
    creationPolicy: Owner
  data:
  - secretKey: AZURE_STORAGE_ACCOUNT_NAME
    remoteRef:
      key: azure-storage
      property: account-name
  - secretKey: AZURE_STORAGE_ACCOUNT_KEY
    remoteRef:
      key: azure-storage
      property: account-key
  - secretKey: AZURE_STORAGE_CONTAINER_NAME
    remoteRef:
      key: azure-storage
      property: container-name

---
# External Secret para Service Bus
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: servicebus-secrets
  namespace: carpeta-ciudadana
  labels:
    app.kubernetes.io/name: carpeta-ciudadana
    app.kubernetes.io/part-of: carpeta-ciudadana
    component: servicebus
spec:
  refreshInterval: "5m"
  secretStoreRef:
    name: azure-keyvault-store
    kind: ClusterSecretStore
  target:
    name: servicebus-secrets
    creationPolicy: Owner
  data:
  - secretKey: SERVICEBUS_CONNECTION_STRING
    remoteRef:
      key: servicebus
      property: connection-string
  - secretKey: SERVICEBUS_NAMESPACE
    remoteRef:
      key: servicebus
      property: namespace

---
# External Secret para Redis
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: redis-secrets
  namespace: carpeta-ciudadana
  labels:
    app.kubernetes.io/name: carpeta-ciudadana
    app.kubernetes.io/part-of: carpeta-ciudadana
    component: redis
spec:
  refreshInterval: "5m"
  secretStoreRef:
    name: azure-keyvault-store
    kind: ClusterSecretStore
  target:
    name: redis-secrets
    creationPolicy: Owner
  data:
  - secretKey: REDIS_HOST
    remoteRef:
      key: redis
      property: host
  - secretKey: REDIS_PORT
    remoteRef:
      key: redis
      property: port
  - secretKey: REDIS_PASSWORD
    remoteRef:
      key: redis
      property: password
  - secretKey: REDIS_SSL
    remoteRef:
      key: redis
      property: ssl

---
# External Secret para Azure AD B2C
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: azure-b2c-secrets
  namespace: carpeta-ciudadana
  labels:
    app.kubernetes.io/name: carpeta-ciudadana
    app.kubernetes.io/part-of: carpeta-ciudadana
    component: azure-b2c
spec:
  refreshInterval: "5m"
  secretStoreRef:
    name: azure-keyvault-store
    kind: ClusterSecretStore
  target:
    name: azure-b2c-secrets
    creationPolicy: Owner
  data:
  - secretKey: AZURE_AD_B2C_TENANT_NAME
    remoteRef:
      key: azure-b2c
      property: tenant-name
  - secretKey: AZURE_AD_B2C_TENANT_ID
    remoteRef:
      key: azure-b2c
      property: tenant-id
  - secretKey: AZURE_AD_B2C_CLIENT_ID
    remoteRef:
      key: azure-b2c
      property: client-id
  - secretKey: AZURE_AD_B2C_CLIENT_SECRET
    remoteRef:
      key: azure-b2c
      property: client-secret

---
# External Secret para JWT
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: jwt-secret
  namespace: carpeta-ciudadana
  labels:
    app.kubernetes.io/name: carpeta-ciudadana
    app.kubernetes.io/part-of: carpeta-ciudadana
    component: jwt
spec:
  refreshInterval: "5m"
  secretStoreRef:
    name: azure-keyvault-store
    kind: ClusterSecretStore
  target:
    name: jwt-secret
    creationPolicy: Owner
  data:
  - secretKey: JWT_SECRET_KEY
    remoteRef:
      key: jwt
      property: secret-key

---
# External Secret para M2M Auth
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: m2m-auth-secrets
  namespace: carpeta-ciudadana
  labels:
    app.kubernetes.io/name: carpeta-ciudadana
    app.kubernetes.io/part-of: carpeta-ciudadana
    component: m2m-auth
spec:
  refreshInterval: "5m"
  secretStoreRef:
    name: azure-keyvault-store
    kind: ClusterSecretStore
  target:
    name: m2m-auth-secrets
    creationPolicy: Owner
  data:
  - secretKey: M2M_SECRET_KEY
    remoteRef:
      key: m2m-auth
      property: secret-key
  - secretKey: M2M_MAX_TIMESTAMP_AGE
    remoteRef:
      key: m2m-auth
      property: max-timestamp-age
  - secretKey: M2M_NONCE_TTL
    remoteRef:
      key: m2m-auth
      property: nonce-ttl

---
# External Secret para NextAuth
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: nextauth-secret
  namespace: carpeta-ciudadana
  labels:
    app.kubernetes.io/name: carpeta-ciudadana
    app.kubernetes.io/part-of: carpeta-ciudadana
    component: nextauth
spec:
  refreshInterval: "5m"
  secretStoreRef:
    name: azure-keyvault-store
    kind: ClusterSecretStore
  target:
    name: nextauth-secret
    creationPolicy: Owner
  data:
  - secretKey: NEXTAUTH_SECRET
    remoteRef:
      key: nextauth
      property: secret
  - secretKey: NEXTAUTH_URL
    remoteRef:
      key: nextauth
      property: url

---
# External Secret para Frontend Configuration
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: frontend-config
  namespace: carpeta-ciudadana
  labels:
    app.kubernetes.io/name: carpeta-ciudadana
    app.kubernetes.io/part-of: carpeta-ciudadana
    component: frontend
spec:
  refreshInterval: "5m"
  secretStoreRef:
    name: azure-keyvault-store
    kind: ClusterSecretStore
  target:
    name: frontend-config
    creationPolicy: Owner
  data:
  - secretKey: NEXT_PUBLIC_AUTH_SERVICE_URL
    remoteRef:
      key: frontend-config
      property: auth-service-url
  - secretKey: NEXT_PUBLIC_CITIZEN_SERVICE_URL
    remoteRef:
      key: frontend-config
      property: citizen-service-url
  - secretKey: NEXT_PUBLIC_INGESTION_SERVICE_URL
    remoteRef:
      key: frontend-config
      property: ingestion-service-url
  - secretKey: NEXT_PUBLIC_SIGNATURE_SERVICE_URL
    remoteRef:
      key: frontend-config
      property: signature-service-url
  - secretKey: NEXT_PUBLIC_TRANSFER_SERVICE_URL
    remoteRef:
      key: frontend-config
      property: transfer-service-url
  - secretKey: NEXT_PUBLIC_MINTIC_SERVICE_URL
    remoteRef:
      key: frontend-config
      property: mintic-service-url
  - secretKey: NEXT_PUBLIC_API_URL
    remoteRef:
      key: frontend-config
      property: api-url
