# GitHub Actions Workflows

Este documento explica los workflows configurados y cómo usarlos.

## Workflows Disponibles

### 1. Backend CI/CD (`backend.yml`)
**Trigger:** Push o PR a `main` con cambios en `backend-py/**`

**Jobs:**
- **Lint:** Valida formato con `ruff format` y linting con `ruff check`
- **Test:** Ejecuta pytest con cobertura (requiere Qdrant service)
- **Build:** Valida imports y dependencias
- **Deploy:** Placeholder para deployment (solo en push a main)

**Secretos requeridos:**
- `GOOGLE_API_KEY` - Para tests que usan el LLM

**Estado:** ✅ Funcionando

### 2. Frontend CI (`frontend-ci.yml`)
**Trigger:** Push o PR a `main` con cambios en `frontend/**`

**Jobs:**
- Type checking con Astro
- Build del proyecto estático
- Cache de dependencias npm

**Estado:** ✅ Funcionando

### 3. Ingest Data (`ingest.yml`)
**Trigger:** Manual (`workflow_dispatch`)

**Por qué es manual:**
- La ingesta de datos debe ser deliberada (no automática)
- Requiere conexión a Qdrant (producción o staging)
- Procesa PDFs del directorio `data/raw/`

**Cómo ejecutar:**
1. Ve a Actions → Ingest Data → Run workflow
2. Proporciona:
   - `qdrant_url`: URL de tu instancia Qdrant
   - `collection_name`: Nombre de la colección (default: `planes_gobierno`)
   - `embedding_provider`: `sentence_transformers` u `openai` (default: `openai`)
   - `embedding_model`: Modelo a usar (default: `text-embedding-3-large`)

**Secretos requeridos:**
- `OPENAI_API_KEY` - Requerido si usas embedding provider `openai`

**Secretos opcionales:**
- `QDRANT_API_KEY` - Solo si usas Qdrant Cloud u otra instancia con autenticación

**Jobs:**
- **Validate:** Verifica imports y sintaxis
- **Ingest:** Ejecuta el proceso de ingesta con extracción mejorada de PDFs
- **Verify Quality:** 🆕 Valida la calidad de los datos ingestados
  - Detecta texto corrupto por partido
  - Falla el workflow si encuentra problemas críticos (>50% corrupción)
  - Muestra estadísticas detalladas y muestras de texto problemático

**Estado:** ✅ Funcionando (manual-only)

## Configuración de Secretos

Para configurar secretos en GitHub:
1. Ve a tu repositorio → Settings → Secrets and variables → Actions
2. Click "New repository secret"
3. Agrega:

| Secret | Requerido | Uso |
|--------|-----------|-----|
| `GOOGLE_API_KEY` | ✅ Sí | Backend tests y API |
| `QDRANT_API_KEY` | ⚠️ Opcional | Solo para Qdrant Cloud |

## Notas Importantes

### Backend
- El workflow incluye un servicio Qdrant para tests
- La cobertura de tests se sube a Codecov (si está configurado)
- El job de deploy está como placeholder - configúralo según tu infraestructura

### Frontend
- Build estático, no requiere secretos
- Usa cache de npm para velocidad
- Solo valida que compile, no despliega

### Ingest
- **No se ejecuta automáticamente** - esto es intencional
- Debes ejecutarlo manualmente cuando:
  - Agregues nuevos PDFs a `data/raw/`
  - Cambies el modelo de embeddings
  - Quieras repoblar la base vectorial
- El workflow acepta la URL de Qdrant como input, así puedes apuntar a diferentes entornos

## Troubleshooting

### Error: "GOOGLE_API_KEY not found"
→ Agrega el secret en Settings → Secrets and variables → Actions

### Error: "Connection refused" en ingest
→ Verifica que la URL de Qdrant sea accesible desde GitHub Actions
→ Si usas `localhost`, no funcionará - necesitas una URL pública o Qdrant Cloud

### Error: "ruff format would reformat"
→ Ejecuta localmente: `cd backend-py && uv run ruff format .`
→ Commitea los cambios

## Próximos Pasos

- [ ] Configurar deployment real en backend (SSH, Docker push, etc.)
- [ ] Agregar workflow para Docker image builds
- [ ] Configurar Dependabot para actualizaciones de dependencias
- [ ] Agregar branch protection rules en GitHub
