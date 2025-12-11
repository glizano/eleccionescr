# Troubleshooting Guide

This guide covers common issues and their solutions for EleccionesCR.

## Table of Contents

- [Backend Issues](#backend-issues)
- [Frontend Issues](#frontend-issues)
- [Ingest Issues](#ingest-issues)
- [Docker Issues](#docker-issues)
- [Database Issues](#database-issues)
- [Performance Issues](#performance-issues)

## Backend Issues

### API Key Errors

**Problem**: Application fails to start with "Missing GOOGLE_API_KEY environment variable"

**Solution**:
```bash
# 1. Copy the example environment file
cp .env.example .env

# 2. Edit .env and add your API key
# For Google Gemini: Get key from https://makersuite.google.com/app/apikey
# For OpenAI: Get key from https://platform.openai.com/api-keys
vim .env

# 3. Restart the application
docker compose restart backend
```

### Qdrant Connection Failed

**Problem**: Backend logs show "Qdrant connection check failed"

**Solution**:
```bash
# Check if Qdrant is running
docker compose ps qdrant

# Check Qdrant logs
docker compose logs qdrant

# Restart Qdrant
docker compose restart qdrant

# Verify connection
curl http://localhost:6333/collections
```

### Import Errors

**Problem**: "ModuleNotFoundError" or import errors

**Solution**:
```bash
cd backend-py

# Re-sync dependencies
uv sync

# Or if using pip
pip install -e .

# Verify imports
uv run python -c "from app.main import app; print('OK')"
```

### LLM Generation Errors

**Problem**: "Error al generar respuesta" or timeout errors

**Solutions**:

1. **Check API key validity**:
   ```bash
   # Test Google API key
   curl -H "Content-Type: application/json" \
     -d '{"contents":[{"parts":[{"text":"Hello"}]}]}' \
     "https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateContent?key=YOUR_KEY"
   ```

2. **Check safety settings**: If getting blocked content, adjust `GOOGLE_SAFETY_THRESHOLD` in `.env`

3. **Increase timeout**: For slow responses, check logs and consider upgrading LLM model

### Rate Limiting

**Problem**: Getting 429 errors or rate limit warnings

**Solution**:
```bash
# Adjust rate limit in .env
MAX_REQUESTS_PER_MINUTE=50

# Or implement Redis-based rate limiting for distributed systems
```

## Frontend Issues

### Cannot Connect to Backend

**Problem**: Frontend shows "Error en la conexión"

**Solutions**:

1. **Check backend is running**:
   ```bash
   curl http://localhost:8000/health
   ```

2. **Check CORS configuration**:
   - Verify `CORS_ORIGINS` in backend `.env`
   - Check browser console for CORS errors
   - Ensure `PUBLIC_BACKEND_URL` is set correctly in frontend

3. **Network inspection**:
   - Open browser DevTools → Network tab
   - Check if requests are being sent to correct URL
   - Look for 404, 500, or network errors

### Build Errors

**Problem**: `npm run build` fails

**Solution**:
```bash
cd frontend

# Clean and reinstall dependencies
rm -rf node_modules package-lock.json
npm install

# Check for TypeScript errors
npx astro check

# Try building again
npm run build
```

### Environment Variables Not Loading

**Problem**: `import.meta.env.PUBLIC_BACKEND_URL` is undefined

**Solution**:
```bash
# Environment variables must be prefixed with PUBLIC_
# in Astro to be accessible in client-side code

# Add to .env
PUBLIC_BACKEND_URL=http://localhost:8000

# Restart dev server
npm run dev
```

## Ingest Issues

### No PDF Files Found

**Problem**: Ingest script shows "No PDF files found in data/raw"

**Solution**:
```bash
cd ingest

# Create data directory if it doesn't exist
mkdir -p data/raw

# Add your PDF files
cp /path/to/your/pdfs/*.pdf data/raw/

# Run ingest again
python main.py
```

### PDF Parsing Errors

**Problem**: "pypdf err" or "No usable text for"

**Solutions**:

1. **Check PDF quality**: Some PDFs are scanned images and need OCR
2. **Try alternative extraction**:
   ```bash
   # Install pdfplumber as alternative
   pip install pdfplumber
   ```
3. **Validate PDF**: Use online tools to check if PDF is valid

### Embedding Generation Slow

**Problem**: Ingest takes very long time

**Solutions**:

1. **Use smaller model**: Switch to faster embedding model in `.env`:
   ```bash
   EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2  # Faster, smaller
   ```

2. **Batch processing**: The ingest script already uses batching, but you can adjust:
   ```python
   # In ingest.py, adjust BATCH size
   BATCH = 128  # Increase for faster processing (uses more memory)
   ```

3. **Use GPU**: If available, ensure PyTorch uses GPU for embeddings

### Qdrant Connection Errors

**Problem**: Cannot connect to Qdrant during ingest

**Solution**:
```bash
# Check Qdrant is running
docker compose ps qdrant

# Check Qdrant URL in .env
QDRANT_URL=http://localhost:6333  # For local development
# or
QDRANT_URL=http://qdrant:6333     # For docker-compose

# Test connection
curl http://localhost:6333/collections
```

## Docker Issues

### Port Already in Use

**Problem**: "Port 8000 is already in use"

**Solution**:
```bash
# Find process using the port
lsof -i :8000  # macOS/Linux
netstat -ano | findstr :8000  # Windows

# Kill the process or change port in docker-compose.yml
docker compose down
docker compose up -d
```

### Out of Disk Space

**Problem**: Docker build fails with "no space left on device"

**Solution**:
```bash
# Clean up Docker resources
docker system prune -a --volumes

# Check disk usage
docker system df

# Remove unused volumes
docker volume prune
```

### Container Keeps Restarting

**Problem**: Container restarts continuously

**Solution**:
```bash
# Check logs for the specific container
docker compose logs backend
docker compose logs frontend
docker compose logs qdrant

# Common causes:
# 1. Missing environment variables
# 2. Port conflicts
# 3. Memory limits
# 4. Application crashes

# Check container health
docker compose ps
```

### Build Cache Issues

**Problem**: Changes not reflected after rebuild

**Solution**:
```bash
# Force rebuild without cache
docker compose build --no-cache

# Or rebuild specific service
docker compose build --no-cache backend

# Then restart
docker compose up -d
```

## Database Issues

### Qdrant Collection Not Found

**Problem**: "Collection 'planes_gobierno' not found"

**Solution**:
```bash
# Collection is created automatically by ingest script
cd ingest
python main.py

# Or manually create collection
curl -X PUT "http://localhost:6333/collections/planes_gobierno" \
  -H "Content-Type: application/json" \
  -d '{
    "vectors": {
      "size": 384,
      "distance": "Cosine"
    }
  }'
```

### Qdrant Performance Slow

**Problem**: Vector searches are slow

**Solutions**:

1. **Check collection size**:
   ```bash
   curl http://localhost:6333/collections/planes_gobierno
   ```

2. **Optimize Qdrant**:
   - Increase `QDRANT_MEMORY_LIMIT` in docker-compose
   - Enable quantization for large collections
   - Use SSD for Qdrant storage

3. **Reduce search limit**: Adjust `limit` parameter in queries

### Langfuse Not Accessible

**Problem**: Cannot access Langfuse UI at http://localhost:3000

**Solution**:
```bash
# Check if Langfuse is enabled in .env
LANGFUSE_ENABLED=true

# Check containers are running
docker compose ps langfuse langfuse-db

# Check logs
docker compose logs langfuse

# Restart Langfuse
docker compose restart langfuse langfuse-db

# Wait for database initialization (first startup takes longer)
```

## Performance Issues

### Slow Response Times

**Problem**: API responses are slow (>5 seconds)

**Solutions**:

1. **Check LLM model**: Faster models produce quicker responses
   ```bash
   # Use faster model
   GOOGLE_MODEL=gemini-2.5-flash  # Faster
   # vs
   GOOGLE_MODEL=gemini-1.5-pro    # More accurate but slower
   ```

2. **Reduce context size**: In `graph.py`, adjust chunk truncation

3. **Enable caching**: Implement response caching for common queries

4. **Monitor resources**:
   ```bash
   docker stats
   ```

### High Memory Usage

**Problem**: Backend container using too much memory

**Solutions**:

1. **Reduce embedding model size**: Use smaller model
2. **Limit concurrent requests**: Implement queue or rate limiting
3. **Set memory limits** in docker-compose.yml:
   ```yaml
   backend:
     deploy:
       resources:
         limits:
           memory: 2G
   ```

## Getting More Help

If your issue isn't covered here:

1. **Check logs**: Always start by examining logs
   ```bash
   docker compose logs -f
   ```

2. **Enable debug mode**:
   ```bash
   DEBUG=true
   LOG_LEVEL=DEBUG
   ```

3. **Search existing issues**: Check [GitHub Issues](https://github.com/glizano/eleccionescr/issues)

4. **Open a new issue**: Provide:
   - Steps to reproduce
   - Error messages and logs
   - Environment details (OS, Docker version)
   - Configuration (sanitized .env)

5. **Community support**: Open a GitHub Discussion

---

Last updated: December 2024
