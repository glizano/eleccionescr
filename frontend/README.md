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

El frontend ahora usa variables de entorno para configurar la URL del backend:

- **`PUBLIC_BACKEND_URL`** - URL del backend API
  - Desarrollo local: `http://localhost:8000`
  - Docker Compose: `http://localhost:8000` (configurado en `.env`)
  - Producción/Railway: `https://your-backend.railway.app` (configurar en tiempo de build)

Para desarrollo local, crea un archivo `.env` en la carpeta `frontend/`:

```bash
PUBLIC_BACKEND_URL=http://localhost:8000
```

Para despliegue en Railway o cualquier plataforma cloud, asegúrate de configurar `PUBLIC_BACKEND_URL` como variable de entorno de build apuntando a tu backend en producción.

Estructura importante:

- `src/` - Código fuente (pages, components, layouts)
- `public/` - Activos estáticos
- `package.json` / `package-lock.json`
- `Dockerfile` - construye y sirve `dist/` con `nginx`

Consejo

- Para pruebas rápidas usa `npm run dev`; para producción usa la imagen Nginx que ya está configurada en `Dockerfile` y `nginx.conf`.
