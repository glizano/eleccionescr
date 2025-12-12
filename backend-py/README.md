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

### Pregunta específica de partido (tema concreto)

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

### Pregunta de plan completo de partido (nuevo)

```bash
curl -X POST http://localhost:8000/api/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "¿Qué plantea el plan del PLN?"
  }'
```

**Trace del agente:**
```json
{
  "agent_trace": {
    "intent": "party_general_plan",
    "parties_detected": ["PLN"],
    "chunks_retrieved": 15,
    "steps": [
      "Intent: party_general_plan",
      "Parties: ['PLN']",
      "Retrieved 15 chunks",
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
- `specific_party`: Pregunta sobre un tema específico de un partido (ej: "¿Qué propone el PLN sobre educación?")
- `party_general_plan`: Pregunta que solicita un resumen completo del plan de un partido (ej: "¿Qué plantea el plan del PLN?")
- `general_comparison`: Pregunta general o comparativa entre partidos
- `unclear`: No está claro

### Party Extractor Agent
Extrae nombres de partidos mencionados usando LLM con few-shot examples.

Partidos conocidos (20 partidos): ACRM, CAC, CDS, CR1, FA, PA, PDLCT, PEL, PEN, PIN, PJSC, PLN, PLP, PNG, PNR, PPSO, PSD, PUCD, PUSC, UP

### RAG Agent
Ejecuta búsqueda vectorial con estrategias adaptativas:
- **5 chunks filtrados** por partido si intent = specific_party (temas específicos)
- **15 chunks filtrados** por partido si intent = party_general_plan (resumen completo)
- **10 chunks balanceados** entre partidos si intent = general_comparison (2 por partido)

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

# Rate Limiting (para controlar costos de LLM)
# Límites por dirección IP
MAX_REQUESTS_PER_MINUTE=10
MAX_REQUESTS_PER_HOUR=30
MAX_REQUESTS_PER_DAY=100
```

### Proveedores de LLM Soportados

El sistema usa **LangChain** para abstraer los proveedores de LLM, soportando:

| Proveedor | Variable de entorno | Modelos disponibles | LangChain Class |
|-----------|---------------------|---------------------|-----------------|
| Google Gemini | `LLM_PROVIDER=google` | gemini-2.5-flash (default), gemini-1.5-pro, etc. | `ChatGoogleGenerativeAI` |
| OpenAI | `LLM_PROVIDER=openai` | gpt-4o-mini (default), gpt-4o, gpt-4-turbo, etc. | `ChatOpenAI` |

Para cambiar de proveedor, simplemente modifica `LLM_PROVIDER` en tu archivo `.env` y proporciona la API key correspondiente.

#### Agregar un Nuevo Proveedor

Gracias a las abstracciones de LangChain, es fácil agregar nuevos proveedores (Anthropic Claude, Cohere, etc.):

1. Agrega la dependencia de LangChain para el proveedor (ej: `langchain-anthropic`)
2. Crea una función `create_provider()` en `app/services/llm_providers/`
3. Actualiza la factory en `factory.py`

### Configuración de Seguridad (Google Gemini)

Para Google Gemini, puedes configurar el nivel de filtros de seguridad con `GOOGLE_SAFETY_THRESHOLD`:

- `BLOCK_MEDIUM_AND_ABOVE` (default): Bloquea contenido con nivel medio o superior (recomendado)
- `BLOCK_ONLY_HIGH`: Solo bloquea contenido de alto riesgo
- `BLOCK_LOW_AND_ABOVE`: Bloquea incluso contenido de bajo riesgo (más restrictivo)
- `BLOCK_NONE`: Desactiva los filtros de seguridad (no recomendado para producción)

### Rate Limiting para Servicio Público

Este backend está diseñado para ser **público y accesible** sin barreras de autenticación, pero con **protección contra uso excesivo** para controlar los costos de LLM.

#### Sistema de Rate Limiting por IP

El rate limiting está **siempre habilitado** con múltiples niveles de protección:

- **Por minuto**: `MAX_REQUESTS_PER_MINUTE=10` (default: 10 requests/minuto)
- **Por hora**: `MAX_REQUESTS_PER_HOUR=30` (default: 30 requests/hora)
- **Por día**: `MAX_REQUESTS_PER_DAY=100` (default: 100 requests/día)

El límite se aplica por **dirección IP**, permitiendo acceso público pero previniendo abuso.

#### Cómo Funciona

1. **Sin autenticación requerida**: Los usuarios pueden usar el servicio directamente
2. **Tracking por IP**: Se rastrea el uso por dirección IP del cliente
3. **Múltiples ventanas de tiempo**: Protección a corto (minuto), mediano (hora) y largo plazo (día)
4. **Integrado con Langfuse**: Todo el uso se registra para análisis de costos
5. **Respuesta 429**: Cuando se excede un límite, se retorna HTTP 429 (Too Many Requests)

#### Ejemplo de Uso

```bash
# Uso normal - sin headers especiales requeridos
curl -X POST http://localhost:8000/api/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "¿Qué propone el PLN sobre educación?"}'

# Con session_id para tracking en Langfuse
curl -X POST http://localhost:8000/api/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "¿Qué propone el PLN sobre educación?",
    "session_id": "user-browser-session-123"
  }'
```

#### Ajustar Límites

Para modificar los límites según tu presupuesto de LLM:

```bash
# Para desarrollo/testing (límites más altos)
MAX_REQUESTS_PER_MINUTE=50
MAX_REQUESTS_PER_HOUR=200
MAX_REQUESTS_PER_DAY=1000

# Para producción con presupuesto limitado (más restrictivo)
MAX_REQUESTS_PER_MINUTE=5
MAX_REQUESTS_PER_HOUR=15
MAX_REQUESTS_PER_DAY=50
```

#### Monitoreo con Langfuse

Todos los requests se registran en Langfuse (si está habilitado) con:
- Session ID del usuario
- Metadata de costos por request
- Análisis de uso por IP/sesión
- Métricas de rate limiting

Esto permite monitorear costos reales y ajustar límites según necesidad.

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
