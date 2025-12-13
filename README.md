# EleccionesCR 2026

Monorepo que contiene los componentes para el asistente RAG de planes de gobierno de Costa Rica 2026.

Licencia: Este proyecto se distribuye bajo una licencia de uso NO COMERCIAL (PolyForm Noncommercial 1.0.0). El código puede analizarse, modificarse y compartirse para fines personales, académicos o de colaboración abierta, pero cualquier uso comercial requiere autorización expresa. Consulta el archivo `LICENSE` para detalles y cómo solicitar permiso.

Contenido:

- `backend-py/` - Backend en Python (FastAPI) que expone la API y orquesta embeddings + Qdrant + LLM.
- `frontend/` - UI en Astro servida por Nginx (Docker) que consume la API del backend.
- `ingest/` - Scripts y utilidades para procesar PDFs y poblar Qdrant con embeddings.
- `docker-compose.yml` - Orquestador para ejecutar `qdrant`, `backend`, `frontend` y `ingest` para desarrollo.

Quick start (desarrollo, en la raíz del repo):

1. Copia variables de ejemplo:

```bash
cp .env.example .env
# Edita `.env` y agrega `GOOGLE_API_KEY` u otras variables necesarias
```

2. Levanta todos los servicios (requiere Docker Desktop):

```bash
docker compose --env-file .env up --build
```

3. Accede a:

- Frontend: `http://localhost` (puerto 80)
- Backend API: `http://localhost:8000`
- Backend docs (Swagger): `http://localhost:8000/docs`
- Qdrant: `http://localhost:6333`

4. **Verifica la calidad de los datos ingestados:**

```bash
cd ingest
python verify_quality.py
```

Este script detecta problemas de encoding o texto corrupto en los PDFs ingestados y te alertará si algún partido tiene datos de baja calidad.

Desarrollo local (sin docker-compose)

- Backend: entra a `backend-py/` y usa `uv sync` (revisa `pyproject.toml`), luego `uv run uvicorn app.main:app --reload`.
- Frontend: entra a `frontend/` y ejecuta `npm install` y `npm run dev`.
- Ingest: entra a `ingest/` y ejecuta `python main.py` (asegúrate de que Qdrant esté corriendo).

CI/CD y Verificación de Calidad

El proyecto utiliza múltiples capas de verificación de código:

**Verificación local rápida:**
```bash
./scripts/ci-check.sh  # Ejecuta todos los checks de backend y frontend
```

**Pre-commit hooks automáticos:**
- Se ejecutan automáticamente en cada `git commit`
- Incluyen: ruff, eslint, prettier, bandit, detect-secrets, yamllint, hadolint, shellcheck

**GitHub Actions CI/CD:**
- Backend CI: tests, linting, security checks
- Frontend CI: build, linting, format checks
- Security scanning: CodeQL, Trivy
- Automático en cada push/PR

Ver [scripts/README.md](./scripts/README.md) para más detalles sobre el sistema de CI.

Despliegue en Railway

Para desplegar este proyecto en Railway (o cualquier otro servicio cloud), consulta la guía completa en [RAILWAY_DEPLOYMENT.md](./RAILWAY_DEPLOYMENT.md). El proyecto está configurado para desplegar el frontend y backend con variables de entorno para configuración flexible.

Buenas prácticas

- No comitear archivos sensibles: utiliza `.env` y no lo subas (hay `.gitignore`).
- Para producción, adapta `docker-compose.yml` y evita montar volúmenes de código en producción.
- Configura `PUBLIC_BACKEND_URL` en el frontend para apuntar a tu backend en producción.
- Ejecuta `./scripts/ci-check.sh` antes de hacer push.

Más documentación está disponible en los `README.md` dentro de cada subdirectorio.

Contribuciones

Revisa `CONTRIBUTING.md` para el flujo de trabajo recomendado, requisitos técnicos y cómo proponer cambios.
