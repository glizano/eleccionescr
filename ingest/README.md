(The file `/Users/gabriel/code/eleccionescr2026/ingest/README.md` exists, but is empty)
# Ingest

Scripts para procesar los PDFs de planes de gobierno y poblar la colección de Qdrant con embeddings.

Estructura relevante:

- `data/raw/` - PDFs originales (ya incluidos en el repositorio de ejemplo)
- `ingest.py` - Lógica principal de ingestión
- `quick_query.py` - Script auxiliar para hacer consultas rápidas a Qdrant

Requisitos

- Python 3.13 (revisar `.python-version`)
- Dependencias en `pyproject.toml`
- Qdrant corriendo y accesible (por defecto `http://localhost:6333`)

Uso (local)

```bash
cd ingest
# instalar deps en un venv local
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .

# ejecutar la ingestión
python main.py
```

Uso con Docker (desde la raíz del repo)

```bash
# construye y corre sólo el contenedor de ingest (ejecutará main.py)
docker compose up --build ingest
```

Notas

- Asegúrate de que `QDRANT_URL` apunte al servicio correcto (usa `.env` o variables de entorno).
- Los vectores y el almacenamiento persistente de Qdrant quedan en `qdrant_storage/` (que está ignorado por git)
