Historia: Registro de un ciudadano a la carpeta ciudadana
Autenticacion en el operador por parte del Ciudadano (Login)
 Cargar Documentos en la Carpeta Ciudadana
Autenticar Documentos atraves de Gov  Carpeta

## Escenarios 
### 1. Ciudadano carga un documento PDF exitosamente
Marta está autenticada en la plataforma
y tiene tier "PREMIUM" con cuota de 100 documentos/mes
y ha usado 45 documentos este mes
y accede a la sección "Cargar Documento"
cuando Marta selecciona el archivo "Cedula_Ciudadania.pdf" (2.5 MB)
y hace clic en "Subir Documento"
Entonces el frontend valida el archivo localmente:
```typescript
    // File: apps/frontend/src/app/upload/page.tsx
    const validateFile = (file: File) => {
      const allowedTypes = ['application/pdf', 'image/jpeg', 'image/png']
      const maxSize = 50 * 1024 * 1024 // 50 MB
      
      if (!allowedTypes.includes(file.type)) {
        throw new Error('Tipo de archivo no permitido')
      }
      
      if (file.size > maxSize) {
        throw new Error('El archivo excede el tamaño máximo de 50 MB')
      }
      
      return true
    }
```
y solicita una SAS URL para upload:
```typescript
    const response = await fetch('/api/documents/upload-url', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        filename: 'Cedula_Ciudadania.pdf',
        content_type: 'application/pdf',
        file_size: 2621440, // 2.5 MB en bytes
        document_type: 'IDENTIFICATION'
      })
    })
```
y el servicio `ingestion` recibe la petición:
```python
    # File: services/ingestion/app/routers/documents.py
    @router.post("/upload-url")
    async def generate_upload_url(
        upload_request: UploadUrlRequest,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
        redis: Redis = Depends(get_redis)
    ):
        # Verificar rate limit según tier
        rate_limit_key = f"upload:{current_user.citizen_id}:month"
        uploads_this_month = await redis.get(rate_limit_key) or 0
        
        tier_limits = {
            "FREE": 10,
            "BASIC": 50,
            "PREMIUM": 100,
            "ENTERPRISE": 1000
        }
        
        if int(uploads_this_month) >= tier_limits[current_user.tier]:
            raise HTTPException(
                status_code=429,
                detail=f"Límite de {tier_limits[current_user.tier]} documentos/mes alcanzado"
            )
        
        # Generar ID único para el documento
        document_id = str(uuid4())
        blob_name = f"{current_user.citizen_id}/{document_id}/{upload_request.filename}"
        
        # Generar SAS URL de escritura (PUT) válida por 15 minutos
        sas_token = generate_blob_sas(
            account_name=settings.AZURE_STORAGE_ACCOUNT,
            container_name="documents",
            blob_name=blob_name,
            account_key=settings.AZURE_STORAGE_KEY,
            permission=BlobSasPermissions(write=True),
            expiry=datetime.utcnow() + timedelta(minutes=15)
        )
        
        sas_url = f"https://{settings.AZURE_STORAGE_ACCOUNT}.blob.core.windows.net/documents/{blob_name}?{sas_token}"
        
        # Crear registro pendiente en base de datos
        pending_doc = PendingDocument(
            document_id=document_id,
            citizen_id=current_user.citizen_id,
            filename=upload_request.filename,
            content_type=upload_request.content_type,
            file_size=upload_request.file_size,
            document_type=upload_request.document_type,
            blob_name=blob_name,
            status="PENDING_UPLOAD",
            created_at=datetime.now()
        )
        db.add(pending_doc)
        db.commit()
        
        return {
            "document_id": document_id,
            "sas_url": sas_url,
            "expires_at": (datetime.utcnow() + timedelta(minutes=15)).isoformat(),
            "blob_name": blob_name,
            "upload_instructions": {
                "method": "PUT",
                "headers": {
                    "x-ms-blob-type": "BlockBlob",
                    "x-ms-blob-content-type": upload_request.content_type
                }
            }
        }
```
y el frontend recibe la SAS URL y sube el archivo directamente a Azure Blob:
```typescript
    // Upload directo a Blob Storage (bypassing backend)
    const uploadToBlob = async (file: File, sasUrl: string) => {
      const response = await fetch(sasUrl, {
        method: 'PUT',
        headers: {
          'x-ms-blob-type': 'BlockBlob',
          'x-ms-blob-content-type': file.type,
          'Content-Length': file.size.toString()
        },
        body: file
      })
      
      if (!response.ok) {
        throw new Error(`Upload failed: ${response.statusText}`)
      }
      
      return response
    }
```
y muestra barra de progreso del upload
cuando el upload se completa exitosamente
entonces el frontend confirma el upload al backend:
```typescript
    const confirmResponse = await fetch('/api/documents/confirm-upload', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        document_id: documentId
      })
    })
```
y el servicio `ingestion` procesa la confirmación:
```python
    # File: services/ingestion/app/routers/documents.py
    @router.post("/confirm-upload")
    async def confirm_upload(
        confirm: ConfirmUploadRequest,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
        redis: Redis = Depends(get_redis),
        blob_service: BlobServiceClient = Depends(get_blob_service)
    ):
        # Obtener documento pendiente
        pending_doc = db.query(PendingDocument).filter(
            PendingDocument.document_id == confirm.document_id,
            PendingDocument.citizen_id == current_user.citizen_id,
            PendingDocument.status == "PENDING_UPLOAD"
        ).first()
        
        if not pending_doc:
            raise HTTPException(status_code=404, detail="Documento no encontrado")
        
        # Verificar que el blob existe en Azure Storage
        blob_client = blob_service.get_blob_client(
            container="documents",
            blob=pending_doc.blob_name
        )
        
        if not blob_client.exists():
            raise HTTPException(status_code=400, detail="Archivo no encontrado en storage")
        
        # Descargar blob y calcular hash SHA-256
        blob_data = blob_client.download_blob().readall()
        file_hash = hashlib.sha256(blob_data).hexdigest()
        
        # Obtener metadata del blob
        blob_properties = blob_client.get_blob_properties()
        actual_size = blob_properties.size
        
        # Crear documento permanente
        document = Document(
            document_id=pending_doc.document_id,
            citizen_id=current_user.citizen_id,
            filename=pending_doc.filename,
            content_type=pending_doc.content_type,
            file_size=actual_size,
            document_type=pending_doc.document_type,
            blob_name=pending_doc.blob_name,
            file_hash=file_hash,
            status="UPLOADED",
            is_signed=False,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        db.add(document)
        
        # Eliminar registro pendiente
        db.delete(pending_doc)
        
        # Incrementar contador de uploads del mes
        rate_limit_key = f"upload:{current_user.citizen_id}:month"
        await redis.incr(rate_limit_key)
        await redis.expire(rate_limit_key, get_seconds_until_end_of_month())
        
        db.commit()
        
        # Publicar evento document.uploaded a Service Bus
        await publish_event(
            topic="document-events",
            event={
                "event_type": "document.uploaded",
                "document_id": document.document_id,
                "citizen_id": current_user.citizen_id,
                "filename": document.filename,
                "document_type": document.document_type,
                "file_size": document.file_size,
                "file_hash": file_hash,
                "timestamp": datetime.now().isoformat()
            }
        )
        
        # Llamar al servicio metadata para indexar
        await index_document_metadata(document)
        
        return {
            "status": "success",
            "document": {
                "document_id": document.document_id,
                "filename": document.filename,
                "file_hash": file_hash,
                "uploaded_at": document.created_at.isoformat(),
                "status": "UPLOADED"
            }
        }
```
y el servicio `metadata` consume el evento y crea el índice:
```python
    # File: services/metadata/app/main.py
    @router.post("/index")
    async def index_document(
        document_data: DocumentIndexRequest,
        db: Session = Depends(get_db)
    ):
        metadata = DocumentMetadata(
            document_id=document_data.document_id,
            citizen_id=document_data.citizen_id,
            filename=document_data.filename,
            document_type=document_data.document_type,
            file_hash=document_data.file_hash,
            tags=extract_tags(document_data.filename),
            searchable_content=extract_text_from_pdf(document_data.blob_name),
            indexed_at=datetime.now()
        )
        db.add(metadata)
        db.commit()
        
        return {"status": "indexed"}
```
y registra en Application Insights:
```python
    telemetry_client.track_event(
        "DocumentUploaded",
        properties={
            "document_id": document.document_id,
            "citizen_id": current_user.citizen_id,
            "document_type": document.document_type,
            "file_size": document.file_size
        },
        measurements={
            "upload_duration_ms": (datetime.now() - start_time).total_seconds() * 1000
        }
    )
```
Entonces Marta recibe confirmación:
```json
    {
      "status": "success",
      "message": "Documento cargado exitosamente",
      "document": {
        "document_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "filename": "Cedula_Ciudadania.pdf",
        "file_hash": "5d41402abc4b2a76b9719d911017c592",
        "uploaded_at": "2025-11-07T14:30:00Z"
      }
    }
```
y ve el mensaje: "✅ Documento 'Cedula_Ciudadania.pdf' cargado exitosamente"
y el documento aparece en su lista de documentos con estado "Cargado"

### 2. Escenario: Registro exitoso de un nuevo ciudadano a la carpeta ciudadana.

**Dado que** Ana María es una operadora certificada autenticada en el sistema  
**Y** está en la sección "Gestión de Ciudadanos" del panel de administración  
**Cuando** Ana selecciona "Registrar Nuevo Ciudadano"  
**Y** ingresa los siguientes datos:

| Campo              | Valor                           |
|--------------------|--------------------------------|
| Cédula             | 1234567890                      |
| Nombre Completo    | Juan Carlos Pérez Gómez         |
| Email              | juan.perez@gmail.com            |
| Teléfono           | +57 300 123 4567                |
| Fecha Nacimiento   | 1985-05-15                      |
| Dirección          | Calle 123 #45-67, Bogotá        |

**Y** hace clic en "Registrar Ciudadano"

**Entonces** el frontend envía la petición:

```typescript
// File: apps/frontend/src/app/admin/users/page.tsx
const registerCitizen = async (citizenData: CitizenRegistration) => {
  const response = await fetch('/api/citizen/register', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${session?.accessToken}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      citizen_id: citizenData.citizenId,
      full_name: citizenData.fullName,
      email: citizenData.email,
      phone: citizenData.phone,
      birth_date: citizenData.birthDate,
      address: citizenData.address,
      operator_id: session?.user?.operatorId
    })
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Error al registrar ciudadano')
  }

  return response.json()
}
```
Y el servicio citizen recibe y procesa la petición:
```typescript
# File: services/citizen/app/routers/citizens.py
@router.post("/register", response_model=CitizenResponse)
async def register_citizen(
    citizen_data: CitizenCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_operator)
):
    # 1. Validar duplicados
    existing_citizen = db.query(Citizen).filter(
        (Citizen.citizen_id == citizen_data.citizen_id) |
        (Citizen.email == citizen_data.email)
    ).first()
    
    if existing_citizen:
        raise HTTPException(
            status_code=409,
            detail={
                "error_code": "CITIZEN_ALREADY_EXISTS",
                "message": f"Ya existe un ciudadano con cédula {citizen_data.citizen_id}",
                "existing_citizen_id": existing_citizen.citizen_id
            }
        )
    
    # 2. Crear ciudadano localmente
    new_citizen = Citizen(
        citizen_id=citizen_data.citizen_id,
        full_name=citizen_data.full_name,
        email=citizen_data.email,
        phone=citizen_data.phone,
        birth_date=citizen_data.birth_date,
        address=citizen_data.address,
        status="PENDING_SYNC",
        tier="FREE",
        created_by=current_user.operator_id,
        created_at=datetime.now()
    )
    db.add(new_citizen)
    db.commit()
    
    # 3. Sincronizar con Hub MinTIC
    try:
        mintic_response = await sync_with_mintic_hub(
            citizen_id=new_citizen.citizen_id,
            citizen_data={
                "citizen_id": new_citizen.citizen_id,
                "full_name": new_citizen.full_name,
                "email": new_citizen.email,
                "operator_id": current_user.operator_id
            }
        )
        
        new_citizen.mintic_reference = mintic_response["citizen_reference"]
        new_citizen.sync_status = "SYNCED"
        new_citizen.status = "ACTIVE"
        db.commit()
        
    except Exception as e:
        # Programar reintento
        await publish_event(
            topic="citizen-events",
            event={
                "event_type": "citizen.sync_retry",
                "citizen_id": new_citizen.citizen_id,
                "retry_count": 1
            }
        )
    
    # 4. Publicar evento
    await publish_event(
        topic="citizen-events",
        event={
            "event_type": "citizen.registered",
            "citizen_id": new_citizen.citizen_id,
            "email": new_citizen.email,
            "mintic_reference": new_citizen.mintic_reference
        }
    )
    
    return {
        "status": "success",
        "citizen": {
            "citizen_id": new_citizen.citizen_id,
            "full_name": new_citizen.full_name,
            "status": new_citizen.status,
            "mintic_reference": new_citizen.mintic_reference
        }
    }
```

Y el servicio mintic_client envía al Hub MinTIC:

```typescript
# File: services/mintic_client/app/routers/citizens.py
@router.post("/citizens/register")
async def register_citizen_to_hub(citizen_data: dict):
    # Verificar Circuit Breaker
    if circuit_breaker.is_open():
        raise HTTPException(
            status_code=503,
            detail="Hub MinTIC temporalmente no disponible"
        )
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{settings.HUB_MINTIC_URL}/apis/createCitizen",
                json={
                    "citizenId": citizen_data["citizen_id"],
                    "fullName": citizen_data["full_name"],
                    "email": citizen_data["email"],
                    "operatorId": citizen_data["operator_id"]
                },
                headers={
                    "X-API-Key": settings.MINTIC_API_KEY
                }
            )
            
            if response.status_code == 200:
                circuit_breaker.record_success()
                return response.json()
            else:
                circuit_breaker.record_failure()
                raise HTTPException(status_code=response.status_code)
                
    except httpx.TimeoutException:
        circuit_breaker.record_failure()
        raise HTTPException(status_code=504, detail="Timeout con Hub MinTIC")
```

Y el servicio notification consume el evento y envía email:

```typescript
# File: services/notification/app/main.py
async def process_citizen_registered(message_data: dict):
    citizen_id = message_data["citizen_id"]
    email = message_data["email"]
    full_name = message_data["full_name"]
    
    email_html = f"""
    <h1>¡Bienvenido a Carpeta Ciudadana!</h1>
    <p>Hola {full_name},</p>
    <p>Tu cuenta ha sido creada exitosamente.</p>
    <p><strong>ID:</strong> {citizen_id}</p>
    <a href="https://carpeta-ciudadana.gov.co/activate/{citizen_id}">
        Activar Cuenta
    </a>
    """
    
    await send_email(
        to_email=email,
        subject="¡Bienvenido a Carpeta Ciudadana!",
        html_content=email_html
    )
```

Entonces Ana recibe confirmación:

```json
{
  "status": "success",
  "message": "Ciudadano registrado exitosamente",
  "citizen": {
    "citizen_id": "1234567890",
    "full_name": "Juan Carlos Pérez Gómez",
    "status": "ACTIVE",
    "mintic_reference": "MINTIC-2025-123456"
  }
}
```
Y ve el mensaje: "Ciudadano Juan Carlos Pérez Gómez registrado exitosamente. ID: 1234567890"
Y Juan recibe un email de bienvenida con instrucciones de activación

### 3.Autenticar documentos a través de GovCarpeta

Dado que Carlos tiene un documento "Cedula_Ciudadania.pdf" cargado
Y el documento tiene ID "doc-123-abc"
Y está en estado "UPLOADED" (sin firmar)
Cuando Carlos hace clic en "Autenticar con Gov Carpeta"

Entonces el frontend muestra confirmación:
```typescript 
// File: apps/frontend/src/app/documents/sign/page.tsx
const handleSignDocument = async (documentId: string) => {
  const confirmed = await showConfirmDialog({
    title: '¿Autenticar este documento?',
    message: 'Se generará firma digital oficial...'
  })
  
  if (!confirmed) return
  
  const response = await fetch('/api/signature/sign', {
    method: 'POST',
    body: JSON.stringify({
      document_id: documentId,
      signature_type: 'GOVERNMENT_AUTH'
    })
  })
  
  const data = await response.json()
  showSuccessToast({
    message: `Referencia: ${data.signature.mintic_reference}`
  })
}
```
Y el servicio signature procesa:
```typescript
# File: services/signature/app/main.py
@router.post("/sign")
async def sign_document(
    sign_request: dict,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
    blob_service: BlobServiceClient = Depends(get_blob_service)
):
    # 1. Verificar documento
    document = db.query(Document).filter(
        Document.document_id == sign_request["document_id"],
        Document.citizen_id == current_user.citizen_id
    ).first()
    
    if document.is_signed:
        raise HTTPException(400, detail="Ya está firmado")
    
    # 2. Descargar y verificar integridad
    blob_data = blob_client.download_blob().readall()
    current_hash = hashlib.sha256(blob_data).hexdigest()
    
    if current_hash != document.file_hash:
        raise HTTPException(400, detail="Documento modificado")
    
    # 3. Generar firma RSA
    signature_bytes = private_key.sign(blob_data, padding.PSS(...), hashes.SHA256())
    signature_b64 = base64.b64encode(signature_bytes).decode()
    
    # 4. Generar SAS URL para Hub MinTIC
    sas_url = generate_blob_sas(..., permission=BlobSasPermissions(read=True))
    
    # 5. Enviar a Hub MinTIC
    mintic_response = await authenticate_with_hub(
        document_id=document.document_id,
        document_url=sas_url,
        signature=signature_b64
    )
    
    # 6. Crear registro de firma
    signature_record = SignatureRecord(
        document_id=document.document_id,
        mintic_reference=mintic_response["authentication_reference"],
        certificate_url=mintic_response["certificate_url"],
        valid_until=mintic_response["valid_until"]
    )
    db.add(signature_record)
    
    # 7. Marcar documento como firmado
    document.is_signed = True
    document.status = "SIGNED"
    db.commit()
    
    # 8. Aplicar WORM
    blob_client.set_immutability_policy(
        immutability_policy_mode=ImmutabilityPolicyMode.Locked,
        immutability_period_since_creation_in_days=1825
    )
    
    # 9. Publicar evento
    await publish_event(
        topic="document-events",
        event={"event_type": "document.authenticated", ...}
    )
    
    return {"status": "success", "signature": {...}}
```
Entonces Carlos recibe:
```json
{
  "status": "success",
  "signature": {
    "mintic_reference": "MINTIC-AUTH-2025-789456",
    "certificate_url": "https://mintic.gov.co/certificates/...",
    "valid_until": "2030-11-07T15:45:30Z"
  }
}
```
y ve la pantalla: 

Documento autenticado exitosamente

Referencia MinTIC: MINTIC-AUTH-2025-789456
Válido hasta: 07/11/2030

[Descargar Certificado]

### 4. Autenticación en el Operador (Login)

Dado que Luis Fernando es un ciudadano registrado 
entonces accede a https://carpeta-ciudadana.gov.co
Cuando Luis hace clic en "Iniciar Sesión"

Entonces el frontend redirige a Azure AD B2C:
```typescript
// File: apps/frontend/src/app/api/auth/[...nextauth]/route.ts
export const authOptions: NextAuthOptions = {
  providers: [
    {
      id: 'azure-ad-b2c',
      name: 'Azure AD B2C',
      type: 'oauth',
      wellKnown: `https://${process.env.AZURE_AD_B2C_TENANT_NAME}.b2clogin.com/${process.env.AZURE_AD_B2C_TENANT_NAME}.onmicrosoft.com/v2.0/.well-known/openid-configuration?p=${process.env.AZURE_AD_B2C_PRIMARY_USER_FLOW}`,
      authorization: {
        params: {
          scope: 'openid profile email offline_access',
          response_type: 'code'
        }
      },
      clientId: process.env.AZURE_AD_B2C_CLIENT_ID!,
      clientSecret: process.env.AZURE_AD_B2C_CLIENT_SECRET!
    }
  ],
  callbacks: {
    async jwt({ token, account, profile }) {
      if (account && profile) {
        token.accessToken = account.access_token
        token.idToken = account.id_token
        token.oid = profile.oid
      }
      return token
    },
    async session({ session, token }) {
      // Validar con backend
      const response = await fetch(`${process.env.AUTH_SERVICE_URL}/validate`, {
        method: 'POST',
        body: JSON.stringify({
          id_token: token.idToken,
          access_token: token.accessToken
        })
      })
      
      const data = await response.json()
      session.user.citizen_id = data.user.citizen_id
      session.user.tier = data.user.tier
      session.accessToken = data.access_token
      
      return session
    }
  }
}
```
Cuando Luis ingresa sus credenciales
Y Azure AD B2C valida exitosamente

Entonces redirige con authorization code
Y el frontend intercambia el code por tokens:
```bash
POST https://carpetaciudadana.b2clogin.com/.../oauth2/v2.0/token
grant_type=authorization_code
&code=0.AXEA...
&client_id={CLIENT_ID}
&client_secret={CLIENT_SECRET}
```
y recibe tokens:
```json
{
  "token_type": "Bearer",
  "expires_in": 3600,
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "id_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "0.AXEA..."
}
```
Y el servicio auth valida y genera tokens internos:

```typescript
# File: services/auth/app/routers/auth.py
@router.post("/validate")
async def validate_oidc_token(
    token_data: dict,
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis)
):
    # 1. Decodificar id_token
    decoded = jwt.decode(
        token_data["id_token"],
        key=get_jwks_key(),
        algorithms=["RS256"],
        audience=settings.AZURE_AD_B2C_CLIENT_ID
    )
    
    user_email = decoded.get("emails")[0]
    user_oid = decoded.get("oid")
    
    # 2. Buscar o crear usuario
    user = db.query(User).filter(
        (User.email == user_email) | (User.azure_oid == user_oid)
    ).first()
    
    if not user:
        user = User(
            citizen_id=generate_citizen_id(),
            email=user_email,
            azure_oid=user_oid,
            tier="FREE",
            roles=["CITIZEN"]
        )
        db.add(user)
        db.commit()
    
    # 3. Generar JWT interno
    internal_jwt = create_access_token(
        data={
            "sub": user.citizen_id,
            "email": user.email,
            "roles": user.roles,
            "tier": user.tier
        },
        expires_delta=timedelta(hours=12)
    )
    
    # 4. Crear sesión en Redis
    session_id = str(uuid4())
    session_key = f"session:{user.citizen_id}:{session_id}"
    
    await redis.setex(
        session_key,
        43200,  # 12 horas
        json.dumps({
            "citizen_id": user.citizen_id,
            "email": user.email,
            "roles": user.roles,
            "tier": user.tier
        })
    )
    
    # 5. Auditoría
    await audit_logger.log_event(
        event_type="USER_LOGIN",
        user_id=user.citizen_id,
        details={
            "auth_method": "azure_ad_b2c",
            "ip_address": request.client.host
        }
    )
    
    return {
        "access_token": internal_jwt,
        "user": {
            "citizen_id": user.citizen_id,
            "email": user.email,
            "tier": user.tier
        }
    }
```
Entonces Luis es redirigido a /dashboard
Y ve su panel con opciones de ver sus documentos, cargar documentos, etc.