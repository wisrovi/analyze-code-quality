from pathlib import Path
from typing import List, Dict
from loguru import logger
import re

from pipeline import PRPipeline, SinglePRPipeline


def is_pr_url(url: str) -> bool:
    """Determina si la URL es de un PR o de un repositorio"""
    return bool(re.search(r"/pull/\d+", url))


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Procesa un repositorio o un PR usando wpipe pipeline"
    )
    parser.add_argument("url", help="URL del repositorio o PR a procesar")
    parser.add_argument(
        "--output", "-o", help="Directorio de salida (default: repos_output)"
    )
    parser.add_argument(
        "--config",
        "-c",
        default="./config/config.yaml",
        help="Archivo de configuración (default: config.yaml)",
    )
    parser.add_argument(
        "--rules",
        "-r",
        default="./config/rules.yaml",
        help="Archivo de reglas (default: rules.yaml)",
    )

    args = parser.parse_args()

    try:
        # Determinar directorio de salida
        if args.output:
            base_dir = Path(args.output)
        else:
            base_dir = Path("repos_output")

        base_dir.mkdir(exist_ok=True)

        url = args.url.strip()
        if not url:
            logger.error("⚠️ URL no proporcionada.")
            return

        # Detectar si es URL de PR o de repositorio
        if is_pr_url(url):
            logger.info(f"🔍 Detectada URL de PR: {url}")
            
            # Crear instancia del pipeline para PR individual
            pipeline = SinglePRPipeline(args.config, args.rules)
            
            # Preparar argumentos para el pipeline
            pipeline_args = {"pr_url": url, "base_dir": base_dir}
            
            # Ejecutar pipeline
            result = pipeline.run(pipeline_args)
            
            if result.get("status") == "completed":
                logger.info(f"✅ PR procesado exitosamente: {url}")
                logger.info(f"📊 PR #{result.get('pr_number')}")
                logger.info(f"⚖️ Elegible para merge: {result.get('eligible', False)}")
            else:
                logger.error(f"❌ Error procesando PR: {url}")
                
        else:
            logger.info(f"🔍 Detectada URL de repositorio: {url}")
            
            # Crear instancia del pipeline para repositorio
            pipeline = PRPipeline(args.config, args.rules)
            
            # Preparar argumentos para el pipeline
            pipeline_args = {"repo_url": url, "base_dir": base_dir}
            
            # Ejecutar pipeline
            result = pipeline.run(pipeline_args)
            
            if result.get("status") == "completed":
                logger.info(f"✅ Repositorio procesado exitosamente: {url}")
                logger.info(f"📊 PRs procesados: {result.get('processed_count', 0)}")
            else:
                logger.error(f"❌ Error procesando repositorio: {url}")

        logger.info("🎉 Procesamiento completado")

    except Exception as e:
        logger.error(f"❌ Error en la ejecución principal: {e}")
        import traceback

        logger.error(f"Traceback: {traceback.format_exc()}")


if __name__ == "__main__":
    main()
