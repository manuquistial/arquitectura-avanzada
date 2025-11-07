-- Script para actualizar retención de documentos firmados
-- Documentos firmados (SIGNED) deben tener retention_until = NULL (ETERNAL)
-- Documentos no firmados (UNSIGNED) deben tener retention_until = created_at + 30 días

-- Actualizar documentos firmados existentes a retención ETERNA
UPDATE document_metadata 
SET retention_until = NULL 
WHERE state = 'SIGNED' 
  AND retention_until IS NOT NULL;

-- Verificar documentos actualizados
SELECT 
    state,
    COUNT(*) as total,
    COUNT(CASE WHEN retention_until IS NULL THEN 1 END) as eternal,
    COUNT(CASE WHEN retention_until IS NOT NULL THEN 1 END) as with_date
FROM document_metadata
WHERE state = 'SIGNED'
GROUP BY state;

-- Actualizar documentos no firmados que no tengan retención
UPDATE document_metadata 
SET retention_until = created_at::date + INTERVAL '30 days'
WHERE state = 'UNSIGNED' 
  AND retention_until IS NULL;

-- Verificar documentos no firmados
SELECT 
    state,
    COUNT(*) as total,
    COUNT(CASE WHEN retention_until IS NULL THEN 1 END) as without_retention,
    COUNT(CASE WHEN retention_until IS NOT NULL THEN 1 END) as with_retention
FROM document_metadata
WHERE state = 'UNSIGNED'
GROUP BY state;

