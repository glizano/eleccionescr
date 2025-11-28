# Frontend (Astro)

UI construida con Astro. Esta carpeta contiene la aplicación estática que se sirve por Nginx en el contenedor `frontend`.

Rápido (desde la raíz del monorepo):

```bash
cd frontend
npm install
npm run dev    # desarrollo local (puerto por defecto 4321)
npm run build  # genera la carpeta `dist/` que usa el Dockerfile
```

Uso con `docker-compose` (recomendado en desarrollo conjunto):

```bash
# Desde la raíz del repo
docker compose up --build frontend
```

Variables y API

- `BACKEND_URL` en el `docker-compose.yml` apunta al servicio `backend` (por defecto `http://backend:8000`).

Estructura importante:

- `src/` - Código fuente (pages, components, layouts)
- `public/` - Activos estáticos
- `package.json` / `package-lock.json`
- `Dockerfile` - construye y sirve `dist/` con `nginx`

Consejo

- Para pruebas rápidas usa `npm run dev`; para producción usa la imagen Nginx que ya está configurada en `Dockerfile` y `nginx.conf`.
