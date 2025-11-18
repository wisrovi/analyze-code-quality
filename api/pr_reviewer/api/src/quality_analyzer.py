import requests
import json
from pathlib import Path
from typing import Dict
from loguru import logger

class QualityAnalyzer:
    def __init__(self):
        self.quality_api = None
        self.session = requests.Session()
    
    def __call__(self, args_dict: Dict) -> Dict:
        """Analiza la calidad del código Python usando la API de calidad"""
        # Inicializar configuración si no está hecha
        if self.quality_api is None:
            config = args_dict.get("config", {})
            self.quality_api = config['api']['quality']
        
        pr_dir = args_dict["pr_dir"]
        downloaded_files = args_dict.get("downloaded_files", [])
        return self.analyze_code_quality(pr_dir, downloaded_files)
    
    def analyze_code_quality(self, pr_dir: Path, downloaded_files: list) -> Dict:
        """Analiza la calidad de todos los archivos usando la API de calidad"""
        if self.quality_api is None:
            logger.error("Quality API no configurada. Llame a __call__ primero.")
            return {"error": "API no configurada"}
            
        try:
            # Buscar todos los archivos en el directorio del PR (excluyendo JSON de metadatos)
            all_files = []
            excluded_files = {
                'download_info.json', 'pr_info.json', 'quality_report.json', 
                'merge_evaluation.json', 'pr_metadata.json'
            }
            
            # Extensiones de archivos que se pueden analizar
            analyzable_extensions = [
                '.py', '.js', '.jsx', '.ts', '.tsx',  # Código
                '.java', '.cpp', '.c', '.h', '.hpp',  # Más código
                '.go', '.rs', '.rb', '.php',  # Más código
                '.yaml', '.yml',  # Configuración (sin .json)
                '.xml', '.html', '.css', '.scss',  # Web
                '.sql', '.sh', '.bash',  # Scripts y SQL
                '.md', '.txt', '.rst',  # Documentación
                '.csv', '.dvc',  # Datos y versionado
            ]
            
            excluded_extensions = [
                '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg',  # Imágenes
                '.pt', '.pth', '.h5', '.pkl', '.pickle',  # Modelos
                '.zip', '.tar', '.gz', '.rar',  # Archivos comprimidos
                '.json',  # Excluir todos los JSON
            ]
            
            max_file_size = 5 * 1024 * 1024  # 5 MB máximo por archivo
            
            for file_path in pr_dir.rglob("*"):
                if file_path.is_file():
                    # Excluir archivos de metadatos específicos
                    if file_path.name in excluded_files:
                        continue
                    
                    # Excluir archivos JSON que terminen con download_info.json
                    if file_path.name.endswith('download_info.json'):
                        continue
                    
                    # Excluir extensiones no analizables
                    if file_path.suffix.lower() in excluded_extensions:
                        logger.debug(f"Omitiendo archivo no analizable: {file_path.name}")
                        continue
                    
                    # Solo incluir extensiones analizables si están en la lista
                    if file_path.suffix and file_path.suffix.lower() not in analyzable_extensions:
                        logger.debug(f"Omitiendo archivo con extensión no reconocida: {file_path.name}")
                        continue
                    
                    # Verificar tamaño del archivo
                    try:
                        file_size = file_path.stat().st_size
                        if file_size == 0:
                            logger.debug(f"Omitiendo archivo vacío: {file_path.name}")
                            continue
                        if file_size > max_file_size:
                            logger.warning(f"Archivo demasiado grande ({file_size / 1024 / 1024:.2f} MB), omitiendo: {file_path.name}")
                            continue
                        all_files.append(file_path)
                    except Exception as e:
                        logger.warning(f"No se pudo procesar el archivo {file_path}: {e}")
            
            if not all_files:
                logger.warning(f"No se encontraron archivos en {pr_dir}")
                return {"error": "No files found"}
            
            logger.info(f"Preparando {len(all_files)} archivos para análisis de calidad")
            
            # Preparar archivos para multipart/form-data
            files = []
            for file_path in all_files:
                try:
                    with open(file_path, 'rb') as f:
                        # Usar el nombre relativo para evitar conflictos
                        relative_name = str(file_path.relative_to(pr_dir))
                        file_content = f.read()
                        files.append(('files', (relative_name, file_content, 'application/octet-stream')))
                        logger.debug(f"Preparado archivo: {relative_name} ({len(file_content)} bytes)")
                except Exception as e:
                    logger.warning(f"No se pudo leer el archivo {file_path}: {e}")
            
            if not files:
                logger.warning(f"No se pudieron preparar los archivos en {pr_dir}")
                return {"error": "Could not prepare files"}
            
            # Parámetros de consulta
            params = {
                "evaluate_pylint": True,
                "evaluate_flake8": True,
                "evaluate_mypy": True,
                "evaluate_complexity": True,
                "evaluate_secrets": True
            }
            
            response = self.session.post(
                f"{self.quality_api['base_url']}{self.quality_api['endpoints']['analyze_batch']}",
                files=files,
                params=params,
                timeout=self.quality_api['timeout']['analysis']
            )
            response.raise_for_status()
            
            quality_report = response.json()
            quality_report['downloaded_files'] = downloaded_files # Add this line
            
            # Guardar reporte de calidad
            (pr_dir / 'quality_report.json').write_text(
                json.dumps(quality_report, indent=2, ensure_ascii=False),
                encoding='utf-8'
            )
            
            logger.info(f"Análisis de calidad completado para {len(all_files)} archivos")
            return quality_report
            
        except requests.RequestException as e:
            logger.error(f"Error en análisis de calidad para {pr_dir}: {e}")
            return {"error": str(e)}
        except Exception as e:
            logger.error(f"Error procesando análisis de calidad: {e}")
            return {"error": str(e)}