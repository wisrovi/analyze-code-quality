import requests
import re
import shutil
import json
import zipfile
import io
from pathlib import Path
from urllib.parse import urlparse
from typing import List, Dict, Optional
from loguru import logger

class GitHubAPI:
    def __init__(self):
        self.github_api = None
        self.session = requests.Session()
    
    def __call__(self, args_dict: Dict) -> tuple[List[Dict], bool]:
        """Obtiene PRs abiertos y descarga archivos del PR especificado"""
        # Inicializar configuración si no está hecha
        if self.github_api is None:
            config = args_dict.get("config", {})
            self.github_api = config['api']['github']
        
        # Si solo se está inicializando, devolver valores vacíos
        if "repo_url" not in args_dict:
            return [], True
        
        repo_url = args_dict["repo_url"]
        pr_url = args_dict["pr_url"]
        target_dir = args_dict["target_dir"]
        
        prs_data = self.get_open_prs(repo_url)
        download_success = self.download_pr_files(pr_url, target_dir)
        return prs_data, download_success
    
    def parse_repo_url(self, repo_url: str) -> tuple[str, str]:
        """Extrae empresa y proyecto de una URL de GitHub/GitLab"""
        parsed = urlparse(repo_url)
        path_parts = parsed.path.strip('/').split('/')
        
        if len(path_parts) >= 2:
            empresa = path_parts[0]
            proyecto = path_parts[1]
            return empresa, proyecto
        else:
            raise ValueError(f"URL de repositorio inválida: {repo_url}")
    
    def get_open_prs(self, repo_url: str) -> List[Dict]:
        """Obtiene PRs abiertos usando el primer endpoint"""
        if self.github_api is None:
            logger.error("GitHub API no configurada. Llame a __call__ primero.")
            return []
        
        try:
            response = self.session.post(
                f"{self.github_api['base_url']}{self.github_api['endpoints']['get_prs']}",
                data={"repo_url": repo_url},
                timeout=self.github_api['timeout']['connection']
            )
            response.raise_for_status()
            result = response.json()
            # Asumir que la respuesta contiene una lista de URLs o objetos con URLs
            if isinstance(result, list):
                return result
            elif isinstance(result, dict) and 'pr_urls' in result:
                return result['pr_urls']
            else:
                return [result] if result else []
        except requests.RequestException as e:
            logger.error(f"Error obteniendo PRs abiertos de {repo_url}: {e}")
            return []
    
    def clean_directory(self, directory: Path) -> None:
        """Limpia el contenido de un directorio sin eliminar el directorio"""
        if directory.exists():
            for item in directory.iterdir():
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)
            logger.info(f"Directorio limpiado: {directory}")
    
    def download_pr_files(self, pr_url: str, target_dir: Path) -> bool:
        """Descarga archivos cambiados de un PR usando el segundo endpoint"""
        if self.github_api is None:
            logger.error("GitHub API no configurada. Llame a __call__ primero.")
            return False
            
        try:
            # Limpiar directorio antes de descargar
            self.clean_directory(target_dir)
            
            response = self.session.post(
                f"{self.github_api['base_url']}{self.github_api['endpoints']['download_files']}",
                data={"pr_url": pr_url},
                timeout=self.github_api['timeout']['download']
            )
            response.raise_for_status()
            
            # Verificar si la respuesta tiene contenido
            if not response.text.strip():
                logger.error(f"Respuesta vacía de la API para {pr_url}")
                return False
            
            # Guardar archivos descargados
            files_data = {}
            
            # Verificar si la respuesta es un ZIP
            if response.text.startswith('PK'):
                try:
                    # Extraer el ZIP
                    with zipfile.ZipFile(io.BytesIO(response.content)) as zip_ref:
                        for file_info in zip_ref.infolist():
                            if not file_info.is_dir():
                                file_content = zip_ref.read(file_info.filename)
                                file_path = target_dir / file_info.filename
                                file_path.parent.mkdir(parents=True, exist_ok=True)
                                file_path.write_bytes(file_content)
                                logger.info(f"Archivo extraído: {file_path}")
                    
                    # Buscar el archivo JSON principal
                    json_files = list(target_dir.glob("*download_info.json"))
                    if json_files:
                        files_data = json.loads(json_files[0].read_text(encoding='utf-8'))
                    else:
                        logger.warning("No se encontró archivo JSON en el ZIP")
                        files_data = {"files": []}
                        
                except Exception as e:
                    logger.error(f"Error extrayendo ZIP de {pr_url}: {e}")
                    return False
            else:
                # Intentar parsear como JSON
                try:
                    files_data = response.json()
                except json.JSONDecodeError as e:
                    logger.error(f"Error parseando JSON de {pr_url}: {e}")
                    logger.error(f"Respuesta recibida: {response.text[:500]}...")
                    return False
            
            if isinstance(files_data, dict) and 'files' in files_data:
                for file_info in files_data['files']:
                    if isinstance(file_info, dict):
                        file_path = file_info.get('path', file_info.get('filename', ''))
                        content = file_info.get('content', '')
                        if file_path and content:
                            file_full_path = target_dir / file_path
                            file_full_path.parent.mkdir(parents=True, exist_ok=True)
                            file_full_path.write_text(content, encoding='utf-8')
                            logger.info(f"Archivo guardado: {file_full_path}")
                        elif file_path:
                            # Si no hay contenido pero hay ruta, crear el archivo vacío o registrar
                            file_full_path = target_dir / file_path
                            file_full_path.parent.mkdir(parents=True, exist_ok=True)
                            file_full_path.touch()
                            logger.info(f"Archivo vacío creado: {file_full_path}")
            
            # Guardar información de la respuesta
            (target_dir / 'download_info.json').write_text(
                json.dumps(files_data, indent=2, ensure_ascii=False),
                encoding='utf-8'
            )
            
            return True
        except requests.RequestException as e:
            logger.error(f"Error descargando archivos de {pr_url}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error procesando archivos de {pr_url}: {e}")
            return False
    
    def analyze_pr_metadata(self, pr_url: str, pr_dir: Path) -> Dict:
        """Analiza metadata del PR usando la API de GitHub"""
        if self.github_api is None:
            logger.error("GitHub API no configurada. Llame a __call__ primero.")
            return {"error": "API no configurada"}
            
        try:
            response = self.session.post(
                f"{self.github_api['base_url']}{self.github_api['endpoints']['analyze_pr']}",
                data={"pr_url": pr_url},
                timeout=self.github_api['timeout']['analysis']
            )
            response.raise_for_status()
            
            pr_metadata = response.json()
            
            # Guardar metadata del PR
            (pr_dir / 'pr_metadata.json').write_text(
                json.dumps(pr_metadata, indent=2, ensure_ascii=False),
                encoding='utf-8'
            )
            
            logger.info(f"Metadata del PR analizada exitosamente")
            return pr_metadata
            
        except requests.RequestException as e:
            logger.error(f"Error analizando metadata del PR {pr_url}: {e}")
            return {"error": str(e)}
        except Exception as e:
            logger.error(f"Error procesando metadata del PR: {e}")
            return {"error": str(e)}