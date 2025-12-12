# Despliegue en Railway

Esta guía describe cómo desplegar EleccionesCR 2026 en Railway.

## 🚂 Arquitectura en Railway

El proyecto se despliega como servicios separados en Railway:

1. **Backend (FastAPI)** - API Python con FastAPI
2. **Frontend (Astro/Nginx)** - Interfaz de usuario
3. **Qdrant** - Base de datos vectorial (opcional: puedes usar Qdrant Cloud)

**Nota:** La ingesta de datos se ejecuta mediante GitHub Actions, no como servicio de Railway.

## 📋 Pre-requisitos

- Cuenta en [Railway.app](https://railway.app)
- Código del proyecto en un repositorio de GitHub
- API Key de Google Gemini o OpenAI

## 🚀 Pasos de Despliegue

### 1. Crear un Nuevo Proyecto en Railway

1. Ve a [Railway.app](https://railway.app) e inicia sesión
2. Crea un nuevo proyecto: "New Project" → "Deploy from GitHub repo"
3. Selecciona el repositorio `glizano/eleccionescr`

### 2. Desplegar Qdrant (Base de Datos Vectorial)

**Opción A: Usar Qdrant en Railway**

1. En tu proyecto de Railway, haz clic en "New" → "Database" → "Add Qdrant"
2. Railway creará una instancia de Qdrant
3. Anota la URL interna (será algo como `qdrant.railway.internal:6333`)

**Opción B: Usar Qdrant Cloud (Recomendado para producción)**

1. Crea una cuenta en [cloud.qdrant.io](https://cloud.qdrant.io)
2. Crea un cluster gratuito
3. Obtén la URL y API Key de tu cluster

### 3. Desplegar el Backend

1. En Railway, haz clic en "New" → "GitHub Repo"
2. Selecciona el repositorio y configura:
   - **Root Directory**: `backend-py`
   - **Build Command**: Se detectará automáticamente del Dockerfile
   - **Start Command**: Se detectará automáticamente del Dockerfile

3. Configura las variables de entorno (Settings → Variables):

```bash
# LLM Provider
LLM_PROVIDER=google
GOOGLE_API_KEY=tu_google_api_key_aqui
GOOGLE_MODEL=gemini-2.5-flash
GOOGLE_SAFETY_THRESHOLD=BLOCK_MEDIUM_AND_ABOVE

# O si usas OpenAI
# LLM_PROVIDER=openai
# OPENAI_API_KEY=tu_openai_api_key_aqui
# OPENAI_MODEL=gpt-4o-mini

# Qdrant Configuration
QDRANT_URL=https://tu-cluster.qdrant.io
QDRANT_API_KEY=tu_qdrant_api_key

# Embedding Configuration
EMBEDDING_PROVIDER=sentence_transformers
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2

# Rate Limiting
MAX_REQUESTS_PER_MINUTE=10
MAX_REQUESTS_PER_HOUR=30
MAX_REQUESTS_PER_DAY=100

# Configuración del servicio
PORT=8000
DEBUG=false

# Langfuse (opcional, para observabilidad)
LANGFUSE_ENABLED=false
# LANGFUSE_PUBLIC_KEY=pk-lf-...
# LANGFUSE_SECRET_KEY=sk-lf-...
# LANGFUSE_HOST=https://cloud.langfuse.com
```

4. Railway generará una URL pública para tu backend (ej: `https://backend-production-xxxx.railway.app`)
5. Anota esta URL - la necesitarás para el frontend

### 4. Ingesta de Datos

La ingesta de datos se ejecuta mediante **GitHub Actions**, no como un servicio de Railway. Esto permite:

- Ejecutar la ingesta de forma programada o bajo demanda
- Evitar costos de mantener un servicio corriendo permanentemente
- Mejor control y trazabilidad del proceso de ingesta

Para configurar la ingesta con GitHub Actions, consulta la documentación del workflow en `.github/workflows/`.

### 5. Desplegar el Frontend

1. En Railway, haz clic en "New" → "GitHub Repo"
2. Selecciona el repositorio y configura:
   - **Root Directory**: `frontend`
   - **Build Command**: `docker build --build-arg PUBLIC_BACKEND_URL=$PUBLIC_BACKEND_URL -t frontend .`
   - **Start Command**: Se detectará del Dockerfile

3. Configura las variables de entorno:

```bash
# URL del backend (usa la URL que Railway generó para tu servicio backend)
PUBLIC_BACKEND_URL=https://backend-production-xxxx.railway.app
```

4. Railway generará una URL pública para tu frontend (ej: `https://frontend-production-xxxx.railway.app`)

### 6. Verificar el Despliegue

1. Visita la URL del frontend en tu navegador
2. Prueba hacer una pregunta en el chat
3. Verifica que se conecte correctamente al backend
4. Revisa los logs en Railway si hay algún error

## 🔧 Configuración Adicional

### Dominios Personalizados

Para usar tu propio dominio:

1. En Railway, ve al servicio (frontend o backend)
2. Ve a Settings → Domains
3. Haz clic en "Add Domain"
4. Sigue las instrucciones para configurar tu DNS

### Variables de Entorno Compartidas

Puedes usar "Shared Variables" en Railway para variables que se usan en múltiples servicios:

1. Ve a tu proyecto en Railway
2. Haz clic en "Variables" en el menú lateral
3. Agrega variables compartidas como `QDRANT_URL`, `QDRANT_API_KEY`, etc.

### Monitoreo y Logs

- **Logs en tiempo real**: Haz clic en cualquier servicio para ver sus logs
- **Métricas**: Railway proporciona métricas de CPU, memoria y red
- **Alertas**: Configura alertas en Settings → Notifications

### Escalar el Backend

Si necesitas más capacidad:

1. Ve a Settings del servicio backend
2. Ajusta los recursos en "Resources"
3. Railway cobra según el uso de recursos

## 💰 Costos Estimados

Railway ofrece:

- **Plan Hobby**: $5/mes de crédito gratuito (suficiente para desarrollo/pruebas)
- **Plan Pro**: $20/mes + uso adicional (recomendado para producción)

Costos adicionales:

- **Google Gemini**: Según uso de API (gemini-2.5-flash tiene tier gratuito generoso)
- **Qdrant Cloud**: Plan gratuito disponible (1GB), planes pagos desde $25/mes
- **OpenAI** (opcional): Según uso de API

## 🔐 Seguridad

### Secretos y Variables de Entorno

- ❌ **NUNCA** comitees API keys o secretos al repositorio
- ✅ Usa las variables de entorno de Railway
- ✅ Configura `DEBUG=false` en producción
- ✅ Habilita rate limiting para controlar costos de LLM

### CORS y Seguridad del Backend

El backend de FastAPI tiene configuración de CORS. Si necesitas restringir el acceso:

1. Edita `backend-py/app/main.py`
2. Actualiza la configuración de CORS con tus dominios

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://tu-dominio.com",
        "https://frontend-production-xxxx.railway.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## 🐛 Troubleshooting

### Error: "Failed to connect to backend"

1. Verifica que `PUBLIC_BACKEND_URL` en el frontend apunte a la URL correcta del backend
2. Revisa los logs del backend para ver si hay errores
3. Verifica que el backend esté funcionando visitando `https://tu-backend.railway.app/docs`

### Error: "Qdrant connection failed"

1. Verifica que `QDRANT_URL` y `QDRANT_API_KEY` estén configurados correctamente
2. Si usas Qdrant Cloud, verifica que el cluster esté activo
3. Prueba la conexión desde el backend con curl o wget

### Frontend muestra página en blanco

1. Revisa los logs del build del frontend
2. Verifica que `PUBLIC_BACKEND_URL` esté configurado correctamente en tiempo de build
3. Asegúrate de que el build se completó sin errores

### Rate limiting muy restrictivo

Ajusta las variables de entorno en el backend:

```bash
MAX_REQUESTS_PER_MINUTE=20
MAX_REQUESTS_PER_HOUR=60
MAX_REQUESTS_PER_DAY=200
```

## 📚 Recursos Adicionales

- [Documentación de Railway](https://docs.railway.app)
- [Documentación de Qdrant](https://qdrant.tech/documentation/)
- [Documentación de Google Gemini](https://ai.google.dev/docs)
- [Documentación de FastAPI](https://fastapi.tiangolo.com/)
- [Documentación de Astro](https://docs.astro.build/)

## 🤝 Soporte

Si encuentras problemas:

1. Revisa los logs en Railway
2. Consulta esta documentación
3. Abre un issue en el repositorio de GitHub
4. Contacta al equipo de desarrollo
