# Contributing

Gracias por tu interés en contribuir a este proyecto.

Al enviar una contribución (código, documentación, issue, comentario) aceptas:

1. Que tienes derecho a aportar ese contenido.
2. Que tu contribución se licencia bajo la licencia principal del proyecto (PolyForm Noncommercial 1.0.0) y mantiene la misma restricción de uso no comercial.
3. Que el mantenedor puede adaptar, modificar y distribuir tu contribución bajo dichos términos.

## Flujo de trabajo

1. Crea un fork del repositorio.
2. Crea una rama descriptiva: `feat/<nombre>`, `fix/<bug>`, `docs/<tema>`.
3. Haz tus cambios con commits pequeños y claros.
4. Ejecuta los tests y linters.
5. Abre un Pull Request (PR) explicando el contexto, motivación y cambios.
6. Responde a la retroalimentación en el PR.

## Backend (Python / FastAPI)

```bash
cd backend-py
uv sync --no-dev
pytest -v
ruff check .
```

Para recargar rápido el servidor durante desarrollo:

```bash
uv run uvicorn app.main:app --reload
```

## Ingest

```bash
cd ingest
python -m venv .venv
source .venv/bin/activate
pip install -e .
python main.py
```

## Frontend (Astro)

```bash
cd frontend
npm install
npm run dev
```

## Estilo y Calidad

- Python: ruff para lint, formateo alineado a configuración del repo.
- JavaScript/TypeScript: Prettier / ESLint (añadir configuración si se incorpora).
- Nombrado claro, evitar abreviaturas ambiguas.

## Tests

- Añade tests para nueva lógica crítica.
- Mantén la cobertura existente (no eliminar tests sin justificación).

## Commits

Formato sugerido (no obligatorio):

- `feat: agregar agente de clasificación`
- `fix: corregir timeout en Qdrant client`
- `docs: actualizar README de ingest`
- `chore: limpiar .gitignore`

## Código de Conducta

Respeto mutuo, comunicación clara y retroalimentación constructiva. Si el proyecto escala se puede añadir un archivo CODE_OF_CONDUCT.md formal.

## Preguntas sobre Licencia Comercial

El uso comercial está prohibido sin permiso explícito. Si deseas negociar una licencia distinta:

> Contacto: (agrega tu email aquí)

## Revisión de PR

- Verificar que los tests pasan.
- Revisar que no se introducen dependencias innecesarias.
- Confirmar que no se incluye información sensible.

## Seguridad

- No subir llaves ni secretos (`.env` está ignorado).
- Reporta vulnerabilidades potenciales vía issue con etiqueta `security` (sin publicar exploits completos).

Gracias por ayudar a mejorar el proyecto.