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

Entonces el frontend muestra el formulario de login:
```typescript
// File: apps/frontend/src/app/api/auth/[...nextauth]/route.ts
// File: apps/frontend/src/app/login/page.tsx
'use client'

import { useState } from 'react'
import { signIn } from 'next-auth/react'
import { useRouter } from 'next/navigation'

export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const router = useRouter()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      // Autenticación con servicio auth interno
      const result = await signIn('credentials', {
        email,
        password,
        redirect: false
      })

      if (result?.error) {
        setError('Email o contraseña incorrectos')
        setLoading(false)
        return
      }

      // Redireccionar al dashboard
      router.push('/dashboard')
    } catch (err) {
      setError('Error al iniciar sesión. Intenta de nuevo.')
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full space-y-8 p-8 bg-white rounded-lg shadow">
        <div>
          <h2 className="text-center text-3xl font-bold text-gray-900">
            Carpeta Ciudadana
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600">
            Inicia sesión con tu cuenta
          </p>
        </div>

        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
              {error}
            </div>
          )}

          <div>
            <label htmlFor="email" className="block text-sm font-medium text-gray-700">
              Email
            </label>
            <input
              id="email"
              name="email"
              type="email"
              required
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={loading}
            />
          </div>

          <div>
            <label htmlFor="password" className="block text-sm font-medium text-gray-700">
              Contraseña
            </label>
            <input
              id="password"
              name="password"
              type="password"
              required
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={loading}
            />
          </div>

          <div className="flex items-center justify-between">
            <div className="flex items-center">
              <input
                id="remember-me"
                name="remember-me"
                type="checkbox"
                className="h-4 w-4 text-blue-600 rounded"
              />
              <label htmlFor="remember-me" className="ml-2 block text-sm text-gray-900">
                Recordarme
              </label>
            </div>

            <div className="text-sm">
              <a href="/reset-password" className="text-blue-600 hover:text-blue-500">
                ¿Olvidaste tu contraseña?
              </a>
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400"
          >
            {loading ? 'Iniciando sesión...' : 'Iniciar sesión'}
          </button>

          <div className="text-center text-sm">
            <span className="text-gray-600">¿No tienes cuenta? </span>
            <a href="/register" className="text-blue-600 hover:text-blue-500">
              Regístrate aquí
            </a>
          </div>
        </form>
      </div>
    </div>
  )
}
```
Cuando Luis ingresa sus credenciales:

Email: luis.fernando@gmail.com
Password: MiPassword123!
Y hace clic en "Iniciar sesión"

Entonces NextAuth.js envía las credenciales al provider custom:
```typescript
// File: apps/frontend/src/app/api/auth/[...nextauth]/route.ts
import NextAuth, { NextAuthOptions } from "next-auth"
import CredentialsProvider from "next-auth/providers/credentials"
import { JWT } from "next-auth/jwt"

export const authOptions: NextAuthOptions = {
  providers: [
    CredentialsProvider({
      id: 'credentials',
      name: 'Credentials',
      credentials: {
        email: { 
          label: "Email", 
          type: "email", 
          placeholder: "tu@email.com" 
        },
        password: { 
          label: "Password", 
          type: "password" 
        }
      },
      
      async authorize(credentials, req) {
        if (!credentials?.email || !credentials?.password) {
          throw new Error('Email y contraseña son requeridos')
        }

        try {
          // Llamar al servicio auth interno
          const response = await fetch(`${process.env.AUTH_SERVICE_URL}/auth/login`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              email: credentials.email,
              password: credentials.password
            })
          })

          if (!response.ok) {
            const error = await response.json()
            throw new Error(error.detail || 'Credenciales inválidas')
          }

          const data = await response.json()

          // Retornar usuario con tokens
          return {
            id: data.user.citizen_id,
            email: data.user.email,
            name: data.user.full_name,
            tier: data.user.tier,
            roles: data.user.roles,
            accessToken: data.access_token,
            refreshToken: data.refresh_token
          }
        } catch (error) {
          console.error('Error en authorize:', error)
          return null
        }
      }
    })
  ],

  callbacks: {
    async jwt({ token, user, account }) {
      // Primera vez que el usuario inicia sesión
      if (user) {
        token.accessToken = user.accessToken
        token.refreshToken = user.refreshToken
        token.citizen_id = user.id
        token.email = user.email
        token.name = user.name
        token.tier = user.tier
        token.roles = user.roles
        token.accessTokenExpires = Date.now() + 12 * 60 * 60 * 1000 // 12 horas
      }

      // Token todavía válido
      if (Date.now() < token.accessTokenExpires) {
        return token
      }

      // Token expirado, intentar refresh
      return refreshAccessToken(token)
    },

    async session({ session, token }) {
      session.user = {
        ...session.user,
        citizen_id: token.citizen_id,
        email: token.email,
        name: token.name,
        tier: token.tier,
        roles: token.roles
      }
      
      session.accessToken = token.accessToken
      session.error = token.error

      return session
    }
  },

  pages: {
    signIn: '/login',
    error: '/auth/error',
    signOut: '/login'
  },

  session: {
    strategy: 'jwt',
    maxAge: 12 * 60 * 60, // 12 horas
  },

  secret: process.env.NEXTAUTH_SECRET,
}

async function refreshAccessToken(token: JWT) {
  try {
    const response = await fetch(`${process.env.AUTH_SERVICE_URL}/auth/refresh`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        refresh_token: token.refreshToken
      })
    })

    if (!response.ok) {
      throw new Error('Refresh token inválido')
    }

    const data = await response.json()

    return {
      ...token,
      accessToken: data.access_token,
      accessTokenExpires: Date.now() + 12 * 60 * 60 * 1000,
      refreshToken: data.refresh_token ?? token.refreshToken
    }
  } catch (error) {
    console.error('Error refreshing token:', error)
    return {
      ...token,
      error: 'RefreshAccessTokenError'
    }
  }
}

const handler = NextAuth(authOptions)
export { handler as GET, handler as POST }
```
Y el servicio auth recibe y valida las credenciales:

```typescript
# File: services/auth/app/routers/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional
import bcrypt
import jwt
from uuid import uuid4

from ..database import get_db
from ..models import User, LoginAttempt
from ..config import settings
from carpeta_common.audit_logger import audit_logger
from carpeta_common.observability import telemetry_client
from carpeta_common.redis_client import get_redis
from redis import Redis

router = APIRouter()

class LoginRequest(BaseModel):
    email: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int = 43200  # 12 horas
    user: dict

@router.post("/login", response_model=LoginResponse)
async def login(
    login_data: LoginRequest,
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis)
):
    """
    Autentica un usuario con email y contraseña
    
    Flujo:
    1. Verificar si la cuenta está bloqueada (rate limiting)
    2. Buscar usuario por email
    3. Verificar contraseña con bcrypt
    4. Generar JWT access token (RS256)
    5. Generar refresh token
    6. Crear sesión en Redis
    7. Registrar login exitoso en auditoría
    8. Enviar telemetría
    """
    
    start_time = datetime.now()
    
    # 1. Verificar bloqueo de cuenta (5 intentos fallidos = 15 min bloqueado)
    lock_key = f"account_locked:{login_data.email}"
    is_locked = await redis.get(lock_key)
    
    if is_locked:
        await audit_logger.log_event(
            event_type="LOGIN_BLOCKED",
            user_id=login_data.email,
            details={
                "reason": "too_many_attempts",
                "locked_until": (datetime.now() + timedelta(minutes=15)).isoformat()
            }
        )
        
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "account_locked",
                "message": "Cuenta bloqueada por múltiples intentos fallidos. Intenta en 15 minutos.",
                "locked_until": (datetime.now() + timedelta(minutes=15)).isoformat()
            }
        )
    
    # 2. Buscar usuario
    user = db.query(User).filter(
        User.email == login_data.email.lower()
    ).first()
    
    if not user:
        # Usuario no existe - registrar intento fallido
        await record_failed_attempt(login_data.email, "user_not_found", redis, db)
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos"
        )
    
    # Verificar que el usuario está activo
    if user.status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "account_inactive",
                "message": f"Tu cuenta está {user.status}. Contacta a soporte.",
                "status": user.status
            }
        )
    
    # 3. Verificar contraseña con bcrypt
    password_valid = bcrypt.checkpw(
        login_data.password.encode('utf-8'),
        user.password_hash.encode('utf-8')
    )
    
    if not password_valid:
        # Contraseña incorrecta - registrar intento fallido
        await record_failed_attempt(login_data.email, "invalid_password", redis, db)
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos"
        )
    
    # 4. Generar JWT access token (RS256 para validación distribuida)
    access_token_payload = {
        "sub": user.citizen_id,  # Subject: ID del ciudadano
        "email": user.email,
        "name": user.full_name,
        "roles": user.roles,
        "tier": user.tier,
        "type": "access",
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(hours=12),
        "iss": "carpeta-ciudadana-auth",
        "aud": ["carpeta-ciudadana-services", "carpeta-ciudadana-frontend"]
    }
    
    # Firmar con clave privada RSA desde Key Vault
    private_key = load_private_key_from_keyvault()
    access_token = jwt.encode(
        access_token_payload,
        private_key,
        algorithm="RS256"
    )
    
    # 5. Generar refresh token (UUID opaco guardado en DB)
    refresh_token_id = str(uuid4())
    refresh_token_payload = {
        "sub": user.citizen_id,
        "type": "refresh",
        "jti": refresh_token_id,  # JWT ID único
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(days=30),
        "iss": "carpeta-ciudadana-auth"
    }
    
    refresh_token = jwt.encode(
        refresh_token_payload,
        private_key,
        algorithm="RS256"
    )
    
    # Guardar refresh token en DB para poder revocarlo
    from ..models import RefreshToken
    db_refresh_token = RefreshToken(
        token_id=refresh_token_id,
        citizen_id=user.citizen_id,
        expires_at=datetime.utcnow() + timedelta(days=30),
        created_at=datetime.utcnow(),
        is_revoked=False
    )
    db.add(db_refresh_token)
    
    # 6. Crear sesión en Redis (12 horas TTL)
    session_id = str(uuid4())
    session_key = f"session:{user.citizen_id}:{session_id}"
    
    session_data = {
        "citizen_id": user.citizen_id,
        "email": user.email,
        "full_name": user.full_name,
        "roles": user.roles,
        "tier": user.tier,
        "session_id": session_id,
        "created_at": datetime.now().isoformat(),
        "last_activity": datetime.now().isoformat(),
        "ip_address": request.client.host,
        "user_agent": request.headers.get("User-Agent", "unknown")
    }
    
    await redis.setex(
        session_key,
        43200,  # 12 horas en segundos
        json.dumps(session_data)
    )
    
    # Actualizar último login del usuario
    user.last_login = datetime.now()
    user.last_login_ip = request.client.host
    
    db.commit()
    
    # 7. Registrar login exitoso en auditoría
    await audit_logger.log_event(
        event_type="USER_LOGIN",
        user_id=user.citizen_id,
        details={
            "email": user.email,
            "full_name": user.full_name,
            "ip_address": request.client.host,
            "user_agent": request.headers.get("User-Agent"),
            "session_id": session_id,
            "login_time": datetime.now().isoformat(),
            "tier": user.tier
        }
    )
    
    # Resetear contador de intentos fallidos
    attempts_key = f"login_attempts:{login_data.email}"
    await redis.delete(attempts_key)
    
    # 8. Enviar telemetría a Application Insights
    login_duration = (datetime.now() - start_time).total_seconds() * 1000
    
    telemetry_client.track_event(
        "UserLogin",
        properties={
            "citizen_id": user.citizen_id,
            "email": user.email,
            "tier": user.tier,
            "roles": ",".join(user.roles),
            "ip_address": request.client.host,
            "success": True
        },
        measurements={
            "login_duration_ms": login_duration
        }
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "Bearer",
        "expires_in": 43200,
        "user": {
            "citizen_id": user.citizen_id,
            "email": user.email,
            "full_name": user.full_name,
            "tier": user.tier,
            "roles": user.roles
        }
    }


async def record_failed_attempt(
    email: str, 
    reason: str, 
    redis: Redis, 
    db: Session
):
    """
    Registra un intento de login fallido y bloquea cuenta si excede límite
    """
    attempts_key = f"login_attempts:{email}"
    
    # Incrementar contador de intentos
    attempts = await redis.incr(attempts_key)
    
    if attempts == 1:
        # Primera vez, establecer TTL de 15 minutos
        await redis.expire(attempts_key, 900)
    
    # Registrar en base de datos
    login_attempt = LoginAttempt(
        email=email,
        attempt_time=datetime.now(),
        success=False,
        failure_reason=reason,
        ip_address=request.client.host,
        user_agent=request.headers.get("User-Agent")
    )
    db.add(login_attempt)
    db.commit()
    
    # Si llega a 5 intentos, bloquear cuenta
    if attempts >= 5:
        lock_key = f"account_locked:{email}"
        await redis.setex(lock_key, 900, "locked")  # 15 minutos
        
        await audit_logger.log_event(
            event_type="ACCOUNT_LOCKED",
            user_id=email,
            details={
                "reason": "too_many_failed_attempts",
                "attempts": attempts,
                "locked_for_minutes": 15
            }
        )
    
    # Registrar auditoría
    await audit_logger.log_event(
        event_type="LOGIN_FAILED",
        user_id=email,
        details={
            "reason": reason,
            "attempts_count": attempts,
            "ip_address": request.client.host,
            "user_agent": request.headers.get("User-Agent")
        }
    )


@router.post("/refresh")
async def refresh_token(
    refresh_data: dict,
    db: Session = Depends(get_db)
):
    """
    Genera un nuevo access token usando refresh token válido
    """
    refresh_token = refresh_data.get("refresh_token")
    
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="refresh_token es requerido"
        )
    
    try:
        # Decodificar refresh token
        public_key = load_public_key_from_keyvault()
        payload = jwt.decode(
            refresh_token,
            public_key,
            algorithms=["RS256"],
            issuer="carpeta-ciudadana-auth"
        )
        
        # Verificar que sea refresh token
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido"
            )
        
        # Verificar que no esté revocado
        from ..models import RefreshToken
        db_token = db.query(RefreshToken).filter(
            RefreshToken.token_id == payload["jti"]
        ).first()
        
        if not db_token or db_token.is_revoked:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token revocado"
            )
        
        # Buscar usuario
        user = db.query(User).filter(
            User.citizen_id == payload["sub"]
        ).first()
        
        if not user or user.status != "ACTIVE":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuario inválido"
            )
        
        # Generar nuevo access token
        private_key = load_private_key_from_keyvault()
        new_access_token = jwt.encode(
            {
                "sub": user.citizen_id,
                "email": user.email,
                "name": user.full_name,
                "roles": user.roles,
                "tier": user.tier,
                "type": "access",
                "iat": datetime.utcnow(),
                "exp": datetime.utcnow() + timedelta(hours=12),
                "iss": "carpeta-ciudadana-auth",
                "aud": ["carpeta-ciudadana-services", "carpeta-ciudadana-frontend"]
            },
            private_key,
            algorithm="RS256"
        )
        
        return {
            "access_token": new_access_token,
            "token_type": "Bearer",
            "expires_in": 43200
        }
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token expirado"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token inválido"
        )


@router.post("/logout")
async def logout(
    current_user = Depends(get_current_user),
    redis: Redis = Depends(get_redis),
    db: Session = Depends(get_db)
):
    """
    Cierra sesión del usuario revocando tokens
    """
    # Eliminar todas las sesiones del usuario en Redis
    pattern = f"session:{current_user.citizen_id}:*"
    async for key in redis.scan_iter(match=pattern):
        await redis.delete(key)
    
    # Revocar todos los refresh tokens activos
    from ..models import RefreshToken
    db.query(RefreshToken).filter(
        RefreshToken.citizen_id == current_user.citizen_id,
        RefreshToken.is_revoked == False
    ).update({"is_revoked": True})
    db.commit()
    
    # Auditoría
    await audit_logger.log_event(
        event_type="USER_LOGOUT",
        user_id=current_user.citizen_id,
        details={
            "email": current_user.email,
            "logout_time": datetime.now().isoformat()
        }
    )
    
    return {"message": "Sesión cerrada exitosamente"}


def load_private_key_from_keyvault():
    """Carga la clave privada RSA desde Azure Key Vault"""
    from azure.identity import DefaultAzureCredential
    from azure.keyvault.secrets import SecretClient
    from cryptography.hazmat.primitives import serialization
    
    credential = DefaultAzureCredential()
    client = SecretClient(
        vault_url=settings.AZURE_KEYVAULT_URL,
        credential=credential
    )
    
    secret = client.get_secret("jwt-private-key")
    private_key = serialization.load_pem_private_key(
        secret.value.encode(),
        password=None
    )
    
    return private_key


def load_public_key_from_keyvault():
    """Carga la clave pública RSA desde Azure Key Vault"""
    from azure.identity import DefaultAzureCredential
    from azure.keyvault.secrets import SecretClient
    from cryptography.hazmat.primitives import serialization
    
    credential = DefaultAzureCredential()
    client = SecretClient(
        vault_url=settings.AZURE_KEYVAULT_URL,
        credential=credential
    )
    
    secret = client.get_secret("jwt-public-key")
    public_key = serialization.load_pem_public_key(
        secret.value.encode()
    )
    
    return public_key
```

Y el modelo de User en la base de datos:

```typescript

# File: services/auth/app/models.py
from sqlalchemy import Column, String, DateTime, Boolean, JSON, Text
from sqlalchemy.dialects.postgresql import ARRAY
from datetime import datetime
from .database import Base

class User(Base):
    __tablename__ = "users"
    
    citizen_id = Column(String(10), primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(Text, nullable=False)
    full_name = Column(String(255), nullable=False)
    
    # Roles: ["CITIZEN", "OPERATOR", "ADMIN"]
    roles = Column(ARRAY(String), default=["CITIZEN"])
    
    # Tier: "FREE", "BASIC", "PREMIUM"
    tier = Column(String(20), default="FREE")
    
    # Estado: "ACTIVE", "INACTIVE", "SUSPENDED", "PENDING_VERIFICATION"
    status = Column(String(30), default="PENDING_VERIFICATION")
    
    last_login = Column(DateTime, nullable=True)
    last_login_ip = Column(String(45), nullable=True)
    
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Metadata adicional
    metadata = Column(JSON, default={})


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    
    token_id = Column(String(36), primary_key=True)  # UUID
    citizen_id = Column(String(10), nullable=False, index=True)
    
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    
    is_revoked = Column(Boolean, default=False, nullable=False)
    revoked_at = Column(DateTime, nullable=True)
    
    # Metadata: IP, User-Agent del dispositivo
    metadata = Column(JSON, default={})


class LoginAttempt(Base):
    __tablename__ = "login_attempts"
    
    id = Column(String(36), primary_key=True)
    email = Column(String(255), nullable=False, index=True)
    
    attempt_time = Column(DateTime, default=datetime.now, nullable=False)
    success = Column(Boolean, nullable=False)
    
    failure_reason = Column(String(100), nullable=True)  # user_not_found, invalid_password
    
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)

```
Entonces Luis recibe la respuesta exitosa:
```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwiZW1haWwiOiJsdWlzLmZlcm5hbmRvQGdtYWlsLmNvbSIsIm5hbWUiOiJMdWlzIEZlcm5hbmRvIEdvbnphbGV6Iiwicm9sZXMiOlsiQ0lUSVpFTiJdLCJ0aWVyIjoiUFJFTUlVTSIsInR5cGUiOiJhY2Nlc3MiLCJpYXQiOjE3MzExMDAwMDAsImV4cCI6MTczMTE0MzIwMCwiaXNzIjoiY2FycGV0YS1jaXVkYWRhbmEtYXV0aCIsImF1ZCI6WyJjYXJwZXRhLWNpdWRhZGFuYS1zZXJ2aWNlcyIsImNhcnBldGEtY2l1ZGFkYW5hLWZyb250ZW5kIl19.signature_here",
  "refresh_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwidHlwZSI6InJlZnJlc2giLCJqdGkiOiJhMWIyYzNkNC1lNWY2LTc4OTAtYWJjZC1lZjEyMzQ1Njc4OTAiLCJpYXQiOjE3MzExMDAwMDAsImV4cCI6MTczMzcwMDAwMCwiaXNzIjoiY2FycGV0YS1jaXVkYWRhbmEtYXV0aCJ9.signature_here",
  "token_type": "Bearer",
  "expires_in": 43200,
  "user": {
    "citizen_id": "1234567890",
    "email": "luis.fernando@gmail.com",
    "full_name": "Luis Fernando Gonzalez",
    "tier": "PREMIUM",
    "roles": ["CITIZEN"]
  }
}
```
Y NextAuth.js guarda los tokens en el JWT de sesión
Y redirige a Luis al dashboard /dashboard
Y Luis ve su panel personalizado con el que puede interactuar

