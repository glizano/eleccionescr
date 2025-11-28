# Docker Compose - EleccionesCR 2026

Este archivo `docker-compose.yml` orquesta todos los componentes del proyecto (ingest, backend y frontend) para ejecutarlos juntos.

## Componentes

- **Qdrant**: Vector database compartida por todos los servicios
- **Backend**: API FastAPI en puerto 8000
- **Frontend**: Aplicación Astro + Nginx en puerto 80
- **Ingest**: Servicio para poblar la base de datos vectorial

## Requisitos previos

- Docker y Docker Compose instalados
- Variable de entorno `GOOGLE_API_KEY` configurada

## Instalación y uso

### 1. Configurar variables de entorno

```bash
# Copiar el archivo de ejemplo
cp .env.example .env

# Editar .env con tus valores
export GOOGLE_API_KEY=tu_api_key_aqui
```

### 2. Iniciar todos los servicios

```bash
# Construir e iniciar todos los contenedores
docker-compose up --build

# O en modo background
docker-compose up -d --build
```

### 3. Acceder a los servicios

- **Frontend**: http://localhost:80 (o http://localhost)
- **Backend API**: http://localhost:8000
- **Backend API Docs**: http://localhost:8000/docs
- **Qdrant Admin**: http://localhost:6333

### 4. Ver logs

```bash
# Todos los servicios
docker-compose logs -f

# Servicio específico
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f qdrant
```

### 5. Detener los servicios

```bash
docker-compose down

# Incluir volúmenes (eliminar datos)
docker-compose down -v
```

## Servicio Ingest

El servicio ingest se ejecuta una sola vez al iniciar para poblar la base de datos vectorial.

```bash
# Ejecutar solo el ingest
docker-compose run ingest

# Ver logs del ingest
docker-compose logs ingest
```

## Desarrollo

Todas las carpetas de código están montadas como volúmenes, permitiendo cambios en tiempo real:

- Backend: `./backend-py` → `/app` en el contenedor
- Frontend: `./frontend` → `/app` en el contenedor
- Ingest: `./ingest` → `/app` en el contenedor

Para cambios en dependencias, reconstruir:

```bash
docker-compose up --build
```

## Troubleshooting

### Puerto ya en uso
```bash
# Liberar puertos específicos
lsof -i :8000   # Backend
lsof -i :80     # Frontend
lsof -i :6333   # Qdrant

# O cambiar puertos en docker-compose.yml
```

### Qdrant no está listo
El backend espera a que Qdrant esté healthy antes de iniciar. Ver logs:
```bash
docker-compose logs qdrant
```

### Reiniciar servicio específico
```bash
docker-compose restart backend
docker-compose restart frontend
docker-compose restart qdrant
```

## Production

Para producción, comentar o remover los volúmenes de código en `docker-compose.yml`:

```yaml
backend:
  volumes: []  # Remover volúmenes de desarrollo
```

Y ajustar las variables de entorno.
