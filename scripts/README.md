# CI/CD Scripts

Este directorio contiene scripts de integración continua y verificación de código.

## Scripts Disponibles

### `ci-check.sh` - Master CI Check

Script principal que ejecuta todas las verificaciones de calidad del proyecto.

```bash
./scripts/ci-check.sh
```

Este script:
- 🐍 Ejecuta las verificaciones del backend (Python)
- 🌐 Ejecuta las verificaciones del frontend (TypeScript/Astro)
- 📊 Proporciona un resumen consolidado de resultados

**Cuándo usarlo:**
- Antes de hacer `git push`
- Antes de crear un Pull Request
- Para verificar que todo está en orden localmente

---

## CI Checks por Componente

### Backend Python (`backend-py/scripts/ci-check.sh`)

**Verificaciones realizadas:**
1. ✨ **Ruff Linting** - Detecta errores y problemas de estilo
2. 🎨 **Ruff Formatting** - Aplica formato automáticamente (consistente con pre-commit)
3. 🔒 **Bandit** - Análisis de seguridad (skip B110)
4. 🧪 **Pytest** - Suite completa de tests
5. 📦 **Import Validation** - Verifica que todos los imports funcionen
6. 🔍 **Dependency Check** - Valida consistencia de pyproject.toml

**Nota sobre formato:** El script aplica formato automáticamente (igual que pre-commit). Si hay cambios, debes hacer `git add` antes de commitear.

**Ejecutar solo backend:**
```bash
cd backend-py && ./scripts/ci-check.sh
```

### Frontend Astro (`frontend/scripts/ci-check.sh`)

**Verificaciones realizadas:**
1. ✨ **ESLint** - Linting de JavaScript/TypeScript
2. 🎨 **Prettier** - Verificación de formato
3. 🔍 **Type Check** - Validación de tipos de TypeScript
4. 🏗️ **Build** - Compilación completa del proyecto

**Ejecutar solo frontend:**
```bash
cd frontend && ./scripts/ci-check.sh
```

---

## Alineación con Pre-commit Hooks

Los scripts ci-check están diseñados para ejecutar las **mismas verificaciones** que los pre-commit hooks, asegurando consistencia entre:

- ✅ Verificaciones locales (pre-commit en cada commit)
- ✅ Verificaciones manuales (ci-check scripts)
- ✅ CI/CD automatizado (GitHub Actions)

### Herramientas Utilizadas

| Herramienta | Backend | Frontend | Pre-commit | GitHub Actions |
|-------------|---------|----------|------------|----------------|
| Ruff        | ✅      | ❌       | ✅         | ✅             |
| Bandit      | ✅      | ❌       | ✅         | ✅             |
| ESLint      | ❌      | ✅       | ✅         | ✅             |
| Prettier    | ❌      | ✅       | ✅         | ✅             |
| Pytest      | ✅      | ❌       | ❌         | ✅             |
| Hadolint    | ❌      | ❌       | ✅         | ✅             |
| yamllint    | ❌      | ❌       | ✅         | ✅             |
| shellcheck  | ❌      | ❌       | ✅         | ❌             |

### Configuración de Versiones

Las versiones están sincronizadas en:

- **Pre-commit**: `.pre-commit-config.yaml` (ruff v0.8.4, eslint 9.17, prettier 3.4.2)
- **Backend**: `pyproject.toml` (usa uv para gestionar ruff)
- **Frontend**: `package.json` (eslint 9.17, prettier 3.4.2)

### Comportamiento de Ruff Format

Tanto **pre-commit** como **ci-check** APLICAN formato automáticamente (no solo verifican):

```bash
# Pre-commit hook
ruff-format  # Sin --check = aplica formato

# CI-check script
uv run ruff format .  # Sin --check = aplica formato
```

**¿Por qué?** Para mantener consistencia:
- Si pre-commit aplica formato automáticamente al commitear
- Entonces ci-check también debe aplicarlo antes de verificar tests
- Esto evita que ci-check falle por formato cuando pre-commit ya lo corrigió

**Workflow:**
1. Modificas código
2. `git add` tus cambios
3. `git commit` → pre-commit aplica formato automáticamente
4. `./scripts/ci-check.sh` → aplica formato si hay algo pendiente
5. Si hay cambios de formato, haz `git add` y `git commit --amend`

---

## Flujo de Desarrollo Recomendado

1. **Durante desarrollo**: Los pre-commit hooks se ejecutan automáticamente
2. **Antes de push**: Ejecutar `./scripts/ci-check.sh` manualmente
3. **En CI/CD**: GitHub Actions ejecuta workflows equivalentes

```bash
# Workflow típico
git add .
git commit -m "feat: nueva funcionalidad"  # ← Pre-commit hooks se ejecutan aquí
./scripts/ci-check.sh                       # ← Verificación completa manual
git push                                     # ← GitHub Actions se ejecuta aquí
```

---

## Solución de Problemas

### "ci-check fails but pre-commit passes"

Posibles causas:
- Tests fallando (pytest no está en pre-commit)
- Build del frontend fallando
- Dependencias desactualizadas

### "pre-commit fails but ci-check passes"

Posibles causas:
- Versiones de herramientas desincronizadas
- Archivos no tracked por git que ci-check no ve

### Regenerar todo

```bash
# Backend
cd backend-py
uv sync
./scripts/ci-check.sh

# Frontend  
cd frontend
npm install
./scripts/ci-check.sh

# Todo junto
./scripts/ci-check.sh
```

---

## Mantenimiento

### Actualizar versiones de herramientas

1. Actualizar `.pre-commit-config.yaml`
2. Actualizar `pyproject.toml` (backend)
3. Actualizar `package.json` (frontend)
4. Ejecutar `pre-commit autoupdate`
5. Verificar con `./scripts/ci-check.sh`

### Agregar nuevas verificaciones

1. Agregar hook en `.pre-commit-config.yaml`
2. Agregar comando en `ci-check.sh` correspondiente
3. Agregar job en GitHub Actions workflow
4. Documentar en este README
