# Test de Configuración de Database (Estilo Ingestion)

Este script prueba la configuración de database usando exactamente la misma configuración que `ingestion/database.py` usa (sin parámetros de pool).

## Propósito

Verificar que la configuración mínima de database funciona correctamente dentro del pod de Kubernetes, para luego aplicar la misma configuración a los servicios problemáticos (metadata, signature, notification).

## Cómo ejecutar en el pod de ingestion

### 1. Obtener el nombre del pod

```bash
kubectl get pods -l app=ingestion -n <namespace>
```

### 2. Copiar el script al pod (si no está en la imagen)

```bash
kubectl cp services/ingestion/test_db_config.py <namespace>/<pod-name>:/app/test_db_config.py
```

### 3. Ejecutar el script dentro del pod

```bash
kubectl exec -it <pod-name> -n <namespace> -- python /app/test_db_config.py
```

### O ejecutar directamente desde el código del servicio

Si el script está incluido en la imagen del servicio:

```bash
kubectl exec -it <pod-name> -n <namespace> -- python services/ingestion/test_db_config.py
```

## Qué prueba el script

1. **Verificación del engine**: Comprueba que el engine SQLAlchemy se creó correctamente
2. **Prueba de conexión básica**: Usa `test_connection()` para verificar conectividad
3. **Obtención de información**: Usa `get_database_info()` para obtener detalles de la DB
4. **Inicialización**: Ejecuta `init_db()` como lo haría el servicio al iniciar
5. **Múltiples conexiones**: Prueba hacer 3 conexiones simultáneas

## Configuración que se prueba

El script usa exactamente la misma configuración que `ingestion/database.py`:

```python
engine_config = {
    "echo": config.debug,
}

if config.is_azure_environment():
    engine_config["connect_args"] = {
        "ssl": "require"
    }
else:
    engine_config["connect_args"] = {
        "ssl": "require" if config.database_sslmode == "require" else "disable"
    }

engine = create_async_engine(DATABASE_URL, **engine_config)
```

**Nota importante**: NO se incluyen parámetros de pool como `pool_size`, `max_overflow`, `pool_pre_ping`, o `pool_recycle`. SQLAlchemy usa sus valores por defecto.

## Resultados esperados

Si todas las pruebas pasan:
- ✅ El engine se crea correctamente
- ✅ La conexión básica funciona
- ✅ Se puede obtener información de la DB
- ✅ La inicialización funciona
- ✅ Múltiples conexiones funcionan

Si alguna prueba falla:
- ❌ Revisar los logs para identificar el error específico
- ❌ Verificar variables de entorno del pod
- ❌ Verificar configuración de red/firewall
- ❌ Verificar credenciales de base de datos

## Uso después de la prueba

Una vez verificado que esta configuración funciona:

1. Los servicios `metadata`, `signature`, y `notification` deberían usar exactamente la misma configuración
2. Verificar que sus archivos `database.py` tengan la misma estructura que `ingestion/database.py`
3. Asegurarse de que NO tengan parámetros de pool adicionales



