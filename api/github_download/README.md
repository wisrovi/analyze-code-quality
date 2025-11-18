# GitHub Download API

API FastAPI para obtener URLs de pull requests de repositorios GitHub.

## Estructura del Proyecto

```
github_download/
├── src/
│   ├── config/           # Configuración y settings
│   └── github_client/    # Cliente GitHub API y rutas
├── main.py              # Aplicación principal FastAPI
├── requirements.txt     # Dependencias Python
├── .env.example        # Variables de entorno ejemplo
└── start.sh            # Script para iniciar la API
```

## Instalación

1. Copiar el archivo de entorno:
```bash
cp .env.example .env
```

2. Editar `.env` con tu GitHub token (opcional para repos privados):
```
GITHUB_TOKEN=your_github_token_here
```

3. Instalar dependencias:
```bash
pip install -r requirements.txt
```

## Ejecución

```bash
./start.sh
```

O manualmente:
```bash
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## Endpoints

### GitHub Client
- `POST /api/v1/github/repos/pr-urls` - Obtener URLs de PRs abiertos de un repo

### General
- `GET /` - Mensaje de bienvenida
- `GET /health` - Health check

## Ejemplo de Uso

```bash
# Obtener URLs de PRs abiertos (repositorio público)
curl -X POST "http://localhost:8000/api/v1/github/repos/pr-urls" \
  -H "Content-Type: application/json" \
  -d '{"repo_url": "https://github.com/cimacorporate/core-python"}'

# Obtener URLs de PRs abiertos (repositorio privado)
curl -X POST "http://localhost:8000/api/v1/github/repos/pr-urls" \
  -H "Content-Type: application/json" \
  -d '{"repo_url": "https://github.com/my-org/my-private-repo"}'
```

## Características

- Soporte para repositorios públicos y privados
- Detección automática de visibilidad del repositorio
- Uso de token solo para repositorios privados
- Parseo de URLs HTTPS y SSH
- API RESTful con FastAPI
- Configuración mediante variables de entorno