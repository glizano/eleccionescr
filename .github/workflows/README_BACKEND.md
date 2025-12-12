# Backend CI/CD Workflow

Este documento describe el workflow de GitHub Actions configurado para el backend de Python.

## 🔄 Workflow Overview

El workflow `backend.yml` se ejecuta automáticamente en los siguientes casos:

- **Push a `main`**: Cuando se hace push a la rama main con cambios en `backend-py/**`
- **Pull Requests**: Cuando se crea o actualiza un PR hacia `main` con cambios en `backend-py/**`
- **Manual**: Usando el botón "Run workflow" en GitHub Actions

## 📋 Jobs

### 1. **Lint & Format Check**

Verifica la calidad del código usando `ruff`:

- ✅ Linting (errores de código, imports, naming conventions)
- ✅ Format check (estilo de código consistente)

**Configuración**: Ver `backend-py/ruff.toml`

### 2. **Run Tests**

Ejecuta la suite de tests con pytest:

- ✅ Levanta un servicio Qdrant en Docker
- ✅ Ejecuta todos los tests en `tests/`
- ✅ Genera reporte de cobertura
- ✅ Sube cobertura a Codecov (opcional)

**Dependencias**:

- pytest
- pytest-asyncio
- pytest-cov
- Qdrant (servicio Docker)

### 3. **Build & Validate**

Valida que el código se puede importar y ejecutar:

- ✅ Verifica imports de la aplicación
- ✅ Valida dependencias con `uv pip check`

### 4. **Deploy to Production**

Se ejecuta solo en push a `main`:

- 🚀 Placeholder para deployment
- Incluye ejemplos comentados para SSH y Docker

## 🔧 Configuración Local

### Instalar dependencias de desarrollo

```bash
cd backend-py
uv sync --group dev
```

### Ejecutar linter

```bash
# Check
uv run ruff check .

# Fix automáticamente
uv run ruff check --fix .
```

### Ejecutar formatter

```bash
# Check
uv run ruff format --check .

# Format automáticamente
uv run ruff format .
```

### Ejecutar tests

```bash
# Asegúrate de que Qdrant esté corriendo
docker ps | grep qdrant

# Ejecutar todos los tests
uv run pytest

# Con cobertura detallada
uv run pytest --cov=app --cov-report=html

# Ver reporte HTML
open htmlcov/index.html
```

## 🔐 Secrets Requeridos

Configura estos secrets en GitHub (Settings → Secrets and variables → Actions):

### Para Tests

- `GOOGLE_API_KEY`: API key de Google Gemini (para LLM)

### Para Deployment (opcional)

- `SERVER_HOST`: Host del servidor de producción
- `SERVER_USER`: Usuario SSH
- `SSH_PRIVATE_KEY`: Llave privada SSH
- `QDRANT_URL`: URL de Qdrant en producción
- `QDRANT_API_KEY`: API key de Qdrant

## 📊 Status Badges

Agrega estos badges al README principal:

```markdown
![Backend CI](https://github.com/tu-usuario/eleccionescr2026/workflows/Backend%20CI%2FCD/badge.svg)
[![codecov](https://codecov.io/gh/tu-usuario/eleccionescr2026/branch/main/graph/badge.svg)](https://codecov.io/gh/tu-usuario/eleccionescr2026)
```

## 🚀 Deployment

### Opción 1: SSH Deployment

Descomenta la sección "Deploy to server" en `backend.yml` y configura:

1. Los secrets necesarios
2. La ruta del servidor
3. El comando de restart del servicio

### Opción 2: Docker Deployment

Descomenta la sección "Build and push Docker image" y:

1. Crea un `Dockerfile` en `backend-py/`
2. Configura Docker registry credentials
3. Actualiza los tags de la imagen

### Opción 3: Cloud Platform

Integra con tu plataforma preferida:

- Google Cloud Run
- AWS ECS/Fargate
- Azure Container Apps
- Railway, Render, Fly.io, etc.

## 🧪 Pre-commit Hooks (Opcional)

Para ejecutar checks antes de cada commit:

```bash
# Instalar pre-commit
uv pip install pre-commit

# Crear .pre-commit-config.yaml
cat > .pre-commit-config.yaml << 'EOF'
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.8.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
EOF

# Instalar hooks
pre-commit install
```

## 📝 Notas

- El workflow usa `uv` para gestión de dependencias (más rápido que pip)
- Los tests requieren que Qdrant esté disponible
- El job de deployment solo corre en push a `main`
- Puedes ejecutar el workflow manualmente desde GitHub Actions

## 🔜 Mejoras Futuras

- [ ] Integrar con LangSmith para traces
- [ ] Agregar tests de integración end-to-end
- [ ] Configurar deployment automático
- [ ] Agregar tests de performance
- [ ] Configurar alertas de Slack/Discord
