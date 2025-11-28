# Frontend (Astro) — Proyecto EleccionesCR 2026

Este README es un borrador actualizado para el frontend. Si quieres, puedo reemplazar `frontend/README.md` por este contenido.

Descripción rápida

- UI hecha con Astro.
- Se construye en `dist/` y se sirve por `nginx` en el contenedor `frontend`.

Desarrollo local

```bash
cd frontend
npm install
npm run dev    # servidor de desarrollo (por defecto en 4321)
```

Build para producción

```bash
npm run build
# sirve el contenido de dist/ localmente para pruebas
npm run preview
```

Uso con Docker (desde la raíz del repo)

```bash
docker compose up --build frontend
```

Integración con backend

- La app consulta la API del backend. En `docker-compose.yml` la variable `BACKEND_URL` apunta a `http://backend:8000`.

Archivos importantes

- `src/` - Código fuente (pages, components, layouts)
- `public/` - Activos estáticos
- `Dockerfile` - Construye `dist/` y lo sirve con `nginx`
- `nginx.conf` - Configuración de Nginx incluida en la imagen

Notas

- Si quieres que reemplace el README actual (`frontend/README.md`) con este borrador, dime y lo hago.
