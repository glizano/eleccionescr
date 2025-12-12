# Ingest - Extracción Robusta de PDFs

Scripts para procesar los PDFs de planes de gobierno y poblar la colección de Qdrant con embeddings.

## 🔧 Mejoras de Extracción (v2.0)

**Problema resuelto**: Caracteres corruptos en PDFs (especialmente PPSO) causaban respuestas incorrectas.

**Solución**:

- ✅ Múltiples estrategias de extracción (pdfplumber + pypdf)
- ✅ Detección automática de texto corrupto
- ✅ Limpieza y normalización de encoding
- ✅ Script de verificación de calidad

Estructura relevante:

- `data/raw/` - PDFs originales (ya incluidos en el repositorio de ejemplo)
- `ingest.py` - Lógica principal de ingestión con extracción mejorada
- `verify_quality.py` - **NUEVO**: Verifica calidad de datos en Qdrant
- `quick_query.py` - Script auxiliar para hacer consultas rápidas a Qdrant

Requisitos

- Python 3.13 (revisar `.python-version`)
- Dependencias en `pyproject.toml` (incluye `pdfplumber` para mejor extracción)
- Qdrant corriendo y accesible (por defecto `http://localhost:6333`)

Uso (local)

```bash
cd ingest
# instalar deps con uv (recomendado)
uv sync

# Modo incremental (solo actualiza archivos modificados)
python main.py

# Modo recreate (elimina todo y empieza desde cero)
RECREATE_COLLECTION=true python main.py

# verificar calidad de datos
python verify_quality.py
```

## 🔄 Modos de Operación

### Incremental (Default)

```bash
python main.py
```

- Usa hash SHA256 para detectar cambios
- Solo procesa archivos nuevos o modificados
- Más rápido y eficiente
- Perfecto para updates regulares

### Recreate (Reset Completo)

```bash
RECREATE_COLLECTION=true python main.py
```

- **ADVERTENCIA**: Elimina la colección existente
- Crea una colección nueva desde cero
- Procesa TODOS los PDFs
- Útil para: cambios de schema, limpieza, migraciones

## 📊 Verificación de Calidad (OPTIMIZADO)

Después de ingestar, ejecuta el script de verificación:

```bash
# Modo rápido: samplea 10 chunks por partido (¡RECOMENDADO para producción!)
python verify_quality.py

# Modo completo: revisa TODOS los chunks (lento, solo para auditorías)
VERIFY_FULL_SCAN=true python verify_quality.py

# Modo custom: samplea N chunks por partido
VERIFY_SAMPLE_SIZE=20 python verify_quality.py
```

**Esto te mostrará:**

- Chunks analizados vs total estimado
- Corrupción detectada por partido
- Alertas si hay problemas críticos

### 🚀 Optimizaciones Implementadas

| Aspecto | Antes | Después |
|---------|-------|---------|
| **Chunks analizados** | Todos (1000+) | 10 por partido (default) |
| **Tiempo ejecución** | ~30-60s | ~2-5s |
| **Carga en Qdrant** | ✅ Alto | ✅ Mínimo |
| **Costo producción** | Alto | ✅ Bajo |
| **Precisión** | 100% | ✅ ~95% (muestreo) |

### 📌 Cuándo Usar Cada Modo

```bash
# DESARROLLO: Sampleo rápido
python verify_quality.py

# PRODUCCIÓN: Sampleo 5 chunks (más rápido)
VERIFY_SAMPLE_SIZE=5 python verify_quality.py

# AUDITORÍA COMPLETA: Revisa todo (una sola vez)
VERIFY_FULL_SCAN=true python verify_quality.py
```

Uso con Docker (desde la raíz del repo)

```bash
# construye y corre sólo el contenedor de ingest (ejecutará main.py)
docker compose up --build ingest
```

Notas

- Asegúrate de que `QDRANT_URL` apunte al servicio correcto (usa `.env` o variables de entorno).
- Los vectores y el almacenamiento persistente de Qdrant quedan en `qdrant_storage/` (que está ignorado por git)
