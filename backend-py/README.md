# EleccionesCR 2026 - Backend con Agentes

Backend inteligente basado en agentes con LangGraph para el chatbot RAG de planes de gobierno.

## 🤖 Sistema de Agentes

El backend utiliza **LangGraph** para orquestar un flujo inteligente de agentes:

```
User Question
     ↓
[Intent Classifier] ← Detecta si es pregunta específica o general
     ↓
  ┌──────────────────┐
  │                  │
[Specific]      [General]
     ↓                ↓
[Party Extractor]  [RAG sin filtro]
     ↓                ↓
[RAG filtrado]       │
     ↓                ↓
[Response Generator] ←┘
     ↓
  Response + Trace
```

## ✨ Características

- ✅ **Routing inteligente**: Identifica automáticamente si la pregunta es sobre un partido específico
- ✅ **Extracción de entidades**: Detecta nombres de partidos (PLN, PUSC, PNR, FA, etc.)
- ✅ **RAG contextual**: Búsquedas filtradas cuando es apropiado
- ✅ **Trazabilidad completa**: Cada respuesta incluye el trace del agente
- ✅ **LangChain + LangGraph**: Orquestación profesional de agentes
- ✅ **100% local**: No requiere servicios externos para desarrollo

## 🚀 Setup

### 1. Instalar dependencias

```bash
uv sync
```

### 2. Configurar variables de entorno

```bash
cp .env.example .env
# Edita .env y configura GOOGLE_API_KEY
```

### 3. Asegurar que Qdrant esté corriendo

```bash
docker ps | grep qdrant
```

### 4. Iniciar el servidor

```bash
uv run python run.py
```

El servidor estará en `http://localhost:8000`

## 📝 Uso

### Pregunta específica de partido

```bash
curl -X POST http://localhost:8000/api/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "¿Qué propone el PLN sobre educación?"
  }'
```

**Trace del agente:**
```json
{
  "agent_trace": {
    "intent": "specific_party",
    "parties_detected": ["PLN"],
    "chunks_retrieved": 5,
    "steps": [
      "Intent: specific_party",
      "Parties: ['PLN']",
      "Retrieved 5 chunks",
      "Response generated"
    ]
  }
}
```

### Pregunta general/comparativa

```bash
curl -X POST http://localhost:8000/api/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "¿Qué proponen los partidos sobre salud?"
  }'
```

**Trace del agente:**
```json
{
  "agent_trace": {
    "intent": "general_comparison",
    "parties_detected": [],
    "chunks_retrieved": 5,
    "steps": [
      "Intent: general_comparison",
      "Retrieved 5 chunks",
      "Response generated"
    ]
  }
}
```

## 📚 Documentación Interactiva

Visita `http://localhost:8000/docs` para la documentación Swagger UI.

## 🏗️ Arquitectura de Agentes

### Intent Classifier Agent
Clasifica la pregunta en:
- `specific_party`: Pregunta sobre un partido específico
- `general_comparison`: Pregunta general o comparativa
- `unclear`: No está claro

### Party Extractor Agent
Extrae nombres de partidos mencionados usando LLM con few-shot examples.

Partidos conocidos: PLN, PUSC, PNR, FA, PLP, PPSO, CAC

### RAG Agent
Ejecuta búsqueda vectorial con:
- **Filtro por partido** si intent = specific_party
- **Sin filtro** si intent = general_comparison

### Response Generator Agent
Genera respuesta final con:
- Citas de fuentes
- Formato estructurado
- Validación de información

## 🔧 Configuración

Variables en `.env`:

```bash
QDRANT_URL=http://localhost:6333
PORT=8000
DEBUG=true

# LLM Provider Selection: "google" or "openai"
LLM_PROVIDER=google

# Google AI (required if LLM_PROVIDER=google)
GOOGLE_API_KEY=tu_key_aqui
GOOGLE_MODEL=gemini-2.5-flash
# Safety threshold: BLOCK_NONE, BLOCK_ONLY_HIGH, BLOCK_MEDIUM_AND_ABOVE (default), BLOCK_LOW_AND_ABOVE
GOOGLE_SAFETY_THRESHOLD=BLOCK_MEDIUM_AND_ABOVE

# OpenAI (required if LLM_PROVIDER=openai)
OPENAI_API_KEY=tu_openai_key_aqui
OPENAI_MODEL=gpt-4o-mini
```

### Proveedores de LLM Soportados

El sistema soporta múltiples proveedores de LLM:

| Proveedor | Variable de entorno | Modelos disponibles |
|-----------|---------------------|---------------------|
| Google Gemini | `LLM_PROVIDER=google` | gemini-2.5-flash (default), gemini-1.5-pro, etc. |
| OpenAI | `LLM_PROVIDER=openai` | gpt-4o-mini (default), gpt-4o, gpt-4-turbo, etc. |

Para cambiar de proveedor, simplemente modifica `LLM_PROVIDER` en tu archivo `.env` y proporciona la API key correspondiente.

### Configuración de Seguridad (Google Gemini)

Para Google Gemini, puedes configurar el nivel de filtros de seguridad con `GOOGLE_SAFETY_THRESHOLD`:

- `BLOCK_MEDIUM_AND_ABOVE` (default): Bloquea contenido con nivel medio o superior (recomendado)
- `BLOCK_ONLY_HIGH`: Solo bloquea contenido de alto riesgo
- `BLOCK_LOW_AND_ABOVE`: Bloquea incluso contenido de bajo riesgo (más restrictivo)
- `BLOCK_NONE`: Desactiva los filtros de seguridad (no recomendado para producción)

## 📊 Ventajas vs Versión Anterior

✅ **Inteligencia real**: Los agentes toman decisiones contextuales  
✅ **Filtrado automático**: No más sources de partidos incorrectos  
✅ **Trazabilidad**: Cada decisión es visible en el trace  
✅ **Escalable**: Fácil agregar nuevos agentes  
✅ **Debuggeable**: Logs detallados de cada paso  

## 🧪 Testing

```bash
# Health check
curl http://localhost:8000/health

# List known parties
curl http://localhost:8000/api/parties
```

## 🧪 Testing

### Ejecutar tests localmente

```bash
# Instalar dependencias de desarrollo
uv sync --group dev

# Ejecutar todos los tests
uv run pytest

# Con cobertura
uv run pytest --cov=app --cov-report=html

# Ver reporte de cobertura
open htmlcov/index.html
```

### Ejecutar checks de CI localmente

```bash
# Ejecutar todos los checks que se ejecutan en CI
./scripts/ci-check.sh
```

## 🔍 Linting y Formateo

Este proyecto usa **ruff** para linting y formateo:

```bash
# Check linting
uv run ruff check .

# Fix automáticamente
uv run ruff check --fix .

# Check formato
uv run ruff format --check .

# Formatear código
uv run ruff format .
```

## 🐳 Docker

### Desarrollo con Docker Compose

```bash
# Iniciar todos los servicios (backend + Qdrant)
docker-compose up -d

# Ver logs
docker-compose logs -f backend

# Detener servicios
docker-compose down
```

### Build manual de imagen Docker

```bash
# Build
docker build -t backend-py:latest .

# Run
docker run -p 8000:8000 \
  -e QDRANT_URL=http://qdrant:6333 \
  -e GOOGLE_API_KEY=your_key \
  backend-py:latest
```

## 🚀 CI/CD

El proyecto incluye GitHub Actions para:

- ✅ **Linting**: Verifica calidad de código con ruff
- ✅ **Tests**: Ejecuta suite de tests con pytest
- ✅ **Build**: Valida que el código se puede importar
- ✅ **Deploy**: Placeholder para deployment automático

Ver [`.github/workflows/README_BACKEND.md`](../../.github/workflows/README_BACKEND.md) para más detalles.

### Secrets requeridos en GitHub

- `GOOGLE_API_KEY`: Para tests que usan el LLM
- `QDRANT_URL`: URL de Qdrant en producción (para deployment)
- `QDRANT_API_KEY`: API key de Qdrant (para deployment)

## 🔜 Próximos pasos

- [ ] Integrar LangSmith para visualización de traces
- [ ] Agregar agent de fact-checking
- [ ] Implementar memoria conversacional
- [ ] Cache con Redis
- [ ] Métricas de accuracy por agente
