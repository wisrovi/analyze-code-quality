#!/usr/bin/env python3
from fastapi import FastAPI, Form, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, HttpUrl
from pathlib import Path
from loguru import logger
import json
from typing import Optional, List, Dict
import uvicorn

import sys

sys.path.append("/home/wisrovi/Documentos/analyze-code-quality/api/pr_reviewer/api")
from main import SinglePRPipeline

# Configurar logger
logger.add("logs/api.log", rotation="500 MB", retention="10 days", level="INFO")

app = FastAPI(
    title="PR Reviewer API",
    description="API para analizar y validar Pull Requests de GitHub",
    version="1.0.0",
)


class PRResponse(BaseModel):
    status: str
    pr_number: str
    empresa: str
    proyecto: str
    eligible: bool
    quality_report: dict
    quality_image: Optional[str]
    pr_dir: str


class RepoResponse(BaseModel):
    status: str
    repo_url: str
    processed_count: int
    csv_path: str
    processed_prs: Optional[List[Dict]] = None
    csv_data: Optional[Dict] = None


class OpenPRsRequest(BaseModel):
    repo_url: HttpUrl


class OpenPRsResponse(BaseModel):
    status: str
    repo_url: str
    open_prs: List[Dict]


@app.get("/")
async def root():
    """Endpoint raíz de la API"""
    return {
        "message": "PR Reviewer API",
        "version": "1.0.0",
        "endpoints": {
            "/analyze-pr": "POST - Analizar un Pull Request (form data)",
            "/analyze-repo": "POST - Analizar todos los PRs de un repositorio (form data)",
            "/open-prs": "POST - Obtener PRs abiertos de un repositorio (form data)",
            "/health": "GET - Health check",
        },
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.post("/analyze-pr", response_model=PRResponse)
async def analyze_pr(pr_url: str = Form(...), base_dir: str = Form("repos_output")):
    """
    Analiza un Pull Request de GitHub y devuelve el reporte de calidad

    Args:
        pr_url: URL del Pull Request de GitHub
        base_dir: Directorio base para guardar resultados (opcional)

    Returns:
        PRResponse con el análisis completo del PR
    """
    try:
        logger.info(f"📥 Recibida solicitud para analizar PR: {pr_url}")

        # Crear instancia del pipeline
        pipeline = SinglePRPipeline("config/config.yaml", "config/rules.yaml")

        # Preparar argumentos
        base_path = Path(base_dir)
        pipeline_args = {"pr_url": pr_url, "base_dir": base_path}

        # Ejecutar pipeline
        logger.info(f"🚀 Ejecutando pipeline para PR: {pr_url}")
        result = pipeline.run(pipeline_args)

        # Verificar si el pipeline fue exitoso
        if result.get("status") != "completed":
            error_msg = result.get("error", "Error desconocido")
            failed_at = result.get("failed_at", "unknown")
            logger.error(f"❌ Pipeline falló en: {failed_at} - {error_msg}")
            raise HTTPException(
                status_code=500,
                detail=f"Error ejecutando pipeline: {error_msg} (failed at: {failed_at})",
            )

        # Leer el quality_report.json
        pr_dir = Path(result["pr_dir"])
        quality_report_path = pr_dir / "quality_report.json"

        if not quality_report_path.exists():
            logger.error(f"❌ No se encontró quality_report.json en {pr_dir}")
            raise HTTPException(
                status_code=500, detail="No se pudo generar el reporte de calidad"
            )

        # Cargar el reporte de calidad
        with open(quality_report_path, "r", encoding="utf-8") as f:
            quality_report = json.load(f)

        # Verificar si existe la imagen del reporte
        quality_image_path = pr_dir / "quality_report.png"
        quality_image_base64 = None

        if quality_image_path.exists():
            try:
                import base64

                with open(quality_image_path, "rb") as img_file:
                    quality_image_base64 = base64.b64encode(img_file.read()).decode(
                        "utf-8"
                    )
                logger.info(f"✅ Imagen de reporte encontrada: {quality_image_path}")
            except Exception as e:
                logger.warning(f"⚠️ No se pudo leer la imagen: {e}")
        else:
            logger.warning(f"⚠️ No se encontró imagen de reporte: {quality_image_path}")

        logger.info(
            f"✅ Análisis completado exitosamente para PR #{result['pr_number']}"
        )

        # Construir respuesta
        response = PRResponse(
            status=result["status"],
            pr_number=result["pr_number"],
            empresa=result["empresa"],
            proyecto=result["proyecto"],
            eligible=result["eligible"],
            quality_report=quality_report,
            quality_image=quality_image_base64,
            pr_dir=str(result["pr_dir"]),
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error inesperado: {e}")
        import traceback

        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500, detail=f"Error interno del servidor: {str(e)}"
        )


@app.post("/analyze-repo", response_model=RepoResponse)
async def analyze_repo(repo_url: str = Form(...), base_dir: str = Form("repos_output")):
    """
    Analiza todos los PRs abiertos de un repositorio de GitHub

    Args:
        repo_url: URL del repositorio de GitHub
        base_dir: Directorio base para guardar resultados (opcional)

    Returns:
        RepoResponse con el análisis completo del repositorio
    """
    try:
        logger.info(f"📥 Recibida solicitud para analizar repositorio: {repo_url}")

        # Crear instancia del pipeline
        import sys

        sys.path.append(
            "/home/wisrovi/Documentos/analyze-code-quality/api/pr_reviewer/api"
        )
        from main import PRPipeline

        pipeline = PRPipeline("config/config.yaml", "config/rules.yaml")

        # Preparar argumentos
        base_path = Path(base_dir)
        pipeline_args = {"repo_url": repo_url, "base_dir": base_path}

        # Ejecutar pipeline
        logger.info(f"🚀 Ejecutando pipeline para repositorio: {repo_url}")
        result = pipeline.run(pipeline_args)

        # Verificar si el pipeline fue exitoso
        if result.get("status") != "completed":
            error_msg = result.get("error", "Error desconocido")
            failed_at = result.get("failed_at", "unknown")
            logger.error(f"❌ Pipeline falló en: {failed_at} - {error_msg}")
            raise HTTPException(
                status_code=500,
                detail=f"Error ejecutando pipeline: {error_msg} (failed at: {failed_at})",
            )

        logger.info(f"✅ Análisis completado exitosamente para repositorio: {repo_url}")

        # Construir respuesta
        response = RepoResponse(
            status=result["status"],
            repo_url=result["repo_url"],
            processed_count=result.get("processed_count", 0),
            csv_path=result.get("csv_path", ""),
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error inesperado: {e}")
        import traceback

        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500, detail=f"Error interno del servidor: {str(e)}"
        )


@app.post("/open-prs", response_model=OpenPRsResponse)
async def get_open_prs(request: OpenPRsRequest):
    """
    Obtiene la lista de PRs abiertos que no están en draft

    Args:
        request: Objeto con la URL del repositorio

    Returns:
        OpenPRsResponse con la lista de PRs abiertos
    """
    try:
        logger.info(
            f"📥 Recibida solicitud para obtener PRs abiertos de: {request.repo_url}"
        )

        # Importar aquí para evitar problemas de importación circular
        import sys

        sys.path.append(
            "/home/wisrovi/Documentos/analyze-code-quality/api/pr_reviewer/api"
        )
        from src.github_api import GitHubAPI

        # Crear instancia del GitHubAPI y configurarla
        github_api = GitHubAPI()

        # Cargar configuración
        import sys

        sys.path.append(
            "/home/wisrovi/Documentos/analyze-code-quality/api/pr_reviewer/api"
        )
        from src.config_loader import ConfigLoader

        config_loader = ConfigLoader()
        config, _ = config_loader(
            {"config_file": "config/config.yaml", "rules_file": "config/rules.yaml"}
        )

        # Inicializar GitHubAPI con configuración
        github_api({"config": config})

        # Obtener PRs abiertos
        repo_url = str(request.repo_url)
        prs_data = github_api.get_open_prs(repo_url)

        # Filtrar PRs que no estén en draft
        open_prs = []
        if isinstance(prs_data, list):
            for pr in prs_data:
                if isinstance(pr, dict):
                    # Verificar que no sea draft
                    if not pr.get("draft", False):
                        open_prs.append(
                            {
                                "number": pr.get("number", pr.get("id", "")),
                                "title": pr.get("title", ""),
                                "url": pr.get("url", pr.get("html_url", "")),
                                "author": pr.get("user", {}).get(
                                    "login", pr.get("author", "")
                                ),
                                "created_at": pr.get("created_at", ""),
                                "updated_at": pr.get("updated_at", ""),
                                "state": pr.get("state", "open"),
                                "draft": pr.get("draft", False),
                            }
                        )
                elif isinstance(pr, str):
                    # Si es solo URL, agregar información básica
                    open_prs.append(
                        {
                            "url": pr,
                            "title": f"PR from {pr}",
                            "author": "unknown",
                            "state": "open",
                            "draft": False,
                        }
                    )

        logger.info(f"✅ Se encontraron {len(open_prs)} PRs abiertos (no draft)")

        response = OpenPRsResponse(
            status="success", repo_url=repo_url, open_prs=open_prs
        )

        return response

    except Exception as e:
        logger.error(f"❌ Error obteniendo PRs abiertos: {e}")
        import traceback

        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500, detail=f"Error interno del servidor: {str(e)}"
        )


if __name__ == "__main__":
    # Crear directorio de logs si no existe
    Path("logs").mkdir(exist_ok=True)

    # Ejecutar servidor
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
