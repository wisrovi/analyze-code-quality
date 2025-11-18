#!/usr/bin/env python3
import json
from wpipe.pipe import Pipeline
from loguru import logger

from src.config_loader import ConfigLoader
from src.github_api import GitHubAPI
from src.quality_analyzer import QualityAnalyzer
from src.merge_evaluator import MergeEvaluator
from src.report_generator import ReportGenerator
from src.csv_exporter import CSVExporter


class PRPipeline(Pipeline):
    def __init__(
        self, config_file: str = "config.yaml", rules_file: str = "rules.yaml"
    ):
        super().__init__(
            worker_id="pr_reviewer", worker_name="PR Reviewer Pipeline", verbose=True
        )

        # Inicializar componentes
        self.config_loader = ConfigLoader()
        self.github_api = GitHubAPI()
        self.quality_analyzer = QualityAnalyzer()
        self.merge_evaluator = MergeEvaluator()
        self.report_generator = ReportGenerator()
        self.csv_exporter = CSVExporter()

        # Cargar configuración y reglas
        config_args = {"config_file": config_file, "rules_file": rules_file}
        self.config, self.rules = self.config_loader(config_args)

        # Definir pasos del pipeline manualmente
        self.steps = [
            (self.load_config, "Cargar configuración y reglas"),
            (self.get_prs, "Obtener PRs abiertos"),
            (self.process_prs, "Procesar todos los PRs"),
            (self.export_results, "Exportar resultados CSV"),
        ]

    def load_config(self, args_dict: dict) -> dict:
        """Paso 1: Cargar configuración y reglas"""
        logger.info("🔧 Cargando configuración y reglas...")

        # Inicializar APIs con configuración
        init_args = {"config": self.config}
        self.github_api(init_args)

        return {
            "config": self.config,
            "rules": self.rules,
            "repo_url": args_dict["repo_url"],
            "base_dir": args_dict["base_dir"],
        }

    def get_prs(self, args_dict: dict) -> dict:
        """Paso 2: Obtener PRs abiertos del repositorio"""
        logger.info("🔍 Obteniendo PRs abiertos...")

        repo_url = args_dict["repo_url"]

        # Obtener PRs abiertos
        prs_data = self.github_api.get_open_prs(repo_url)
        pr_urls = (
            prs_data.get("pr_urls", []) if isinstance(prs_data, dict) else prs_data
        )

        logger.info(f"Se encontraron {len(pr_urls)} PRs abiertos")

        # Extraer empresa y proyecto
        empresa, proyecto = self.github_api.parse_repo_url(repo_url)
        repo_dir = args_dict["base_dir"] / empresa / proyecto
        repo_dir.mkdir(parents=True, exist_ok=True)

        return {
            **args_dict,
            "pr_urls": pr_urls,
            "empresa": empresa,
            "proyecto": proyecto,
            "repo_dir": repo_dir,
        }

    def process_prs(self, args_dict: dict) -> dict:
        """Paso 3: Procesar todos los PRs"""
        logger.info("⚙️ Procesando todos los PRs...")

        pr_urls = args_dict["pr_urls"]
        repo_dir = args_dict["repo_dir"]

        processed_prs = []

        for i, pr in enumerate(pr_urls):
            # Manejar diferentes formatos de respuesta
            if isinstance(pr, str):
                pr_url = pr
                # Extraer número de PR de la URL
                import re

                match = re.search(r"/pull/(\d+)", pr_url)
                pr_number = match.group(1) if match else "unknown"
            elif isinstance(pr, dict):
                pr_number = pr.get("number", pr.get("id", "unknown"))
                pr_url = pr.get("url", pr.get("pr_url", ""))
            else:
                logger.warning(f"Formato de PR no soportado: {pr}")
                continue

            if not pr_url:
                logger.warning(f"PR sin URL: {pr}")
                continue

            logger.info(f"Procesando PR #{pr_number} ({i + 1}/{len(pr_urls)})")

            # Crear carpeta para el PR
            pr_dir = repo_dir / str(pr_number)
            pr_dir.mkdir(exist_ok=True)

            # Guardar información del PR
            import json

            pr_info = {
                "number": pr_number,
                "title": pr.get("title", "") if isinstance(pr, dict) else "",
                "url": pr_url,
                "author": pr.get("author", "") if isinstance(pr, dict) else "",
                "created_at": pr.get("created_at", "") if isinstance(pr, dict) else "",
                "updated_at": pr.get("updated_at", "") if isinstance(pr, dict) else "",
            }

            (pr_dir / "pr_info.json").write_text(
                json.dumps(pr_info, indent=2, ensure_ascii=False), encoding="utf-8"
            )

            # Descargar archivos cambiados
            github_args = {
                "config": self.config,
                "repo_url": args_dict["repo_url"],
                "pr_url": pr_url,
                "target_dir": pr_dir,
            }
            _, download_success = self.github_api(github_args)

            downloaded_files_list = []
            if download_success:
                logger.info(f"✅ PR #{pr_number} procesado exitosamente")

                # Leer download_info.json para obtener la lista de archivos descargados
                download_info_path = pr_dir / 'download_info.json'
                if download_info_path.exists():
                    try:
                        with open(download_info_path, 'r', encoding='utf-8') as f:
                            download_info = json.load(f)
                            # Asumir que 'files' contiene una lista de diccionarios con 'path'
                            downloaded_files_list = [f_info['path'] for f_info in download_info.get('files', []) if 'path' in f_info]
                        logger.info(f"Se cargaron {len(downloaded_files_list)} archivos de download_info.json")
                    except json.JSONDecodeError as e:
                        logger.error(f"Error decodificando download_info.json para PR #{pr_number}: {e}")
                    except Exception as e:
                        logger.error(f"Error leyendo download_info.json para PR #{pr_number}: {e}")
                else:
                    logger.warning(f"No se encontró download_info.json para PR #{pr_number}")


                # Analizar calidad del código
                quality_args = {"config": self.config, "pr_dir": pr_dir, "downloaded_files": downloaded_files_list}
                quality_result = self.quality_analyzer(quality_args)

                if "error" not in quality_result:
                    logger.info(
                        f"✅ Análisis de calidad completado para PR #{pr_number}"
                    )
                    # Generar reporte visual
                    report_args = {
                        "pr_dir": pr_dir,
                        "quality_data": quality_result,
                        "pr_number": pr_number,
                        "downloaded_files": downloaded_files_list, # Add this line
                    }
                    self.report_generator(report_args)
                else:
                    logger.warning(
                        f"⚠️ Error en análisis de calidad para PR #{pr_number}: {quality_result['error']}"
                    )

                # Analizar metadata del PR
                metadata_result = self.github_api.analyze_pr_metadata(pr_url, pr_dir)

                if "error" not in metadata_result:
                    logger.info(
                        f"✅ Metadata del PR #{pr_number} analizada exitosamente"
                    )
                else:
                    logger.warning(
                        f"⚠️ Error en análisis de metadata para PR #{pr_number}: {metadata_result['error']}"
                    )

                # Evaluar elegibilidad para merge
                merge_args = {
                    "rules": self.rules,
                    "pr_dir": pr_dir,
                    "pr_number": pr_number,
                }
                merge_evaluation = self.merge_evaluator(merge_args)

                if "error" not in merge_evaluation:
                    if merge_evaluation.get("eligible", False):
                        logger.info(f"✅ PR #{pr_number} es elegible para merge")
                    else:
                        logger.warning(f"❌ PR #{pr_number} NO es elegible para merge")
                else:
                    logger.error(
                        f"❌ Error evaluando elegibilidad del PR #{pr_number}: {merge_evaluation['error']}"
                    )

                processed_prs.append(
                    {
                        "pr_number": pr_number,
                        "pr_url": pr_url,
                        "eligible": merge_evaluation.get("eligible", False)
                        if "error" not in merge_evaluation
                        else False,
                    }
                )
            else:
                logger.error(f"❌ Error procesando PR #{pr_number}")

        return {**args_dict, "processed_prs": processed_prs}

    def export_results(self, args_dict: dict) -> dict:
        """Paso 4: Exportar resultados a CSV"""
        logger.info("📊 Exportando resultados a CSV...")

        csv_args = {
            "results_dir": "results",
            "repo_dir": args_dict["repo_dir"],
            "empresa": args_dict["empresa"],
            "proyecto": args_dict["proyecto"],
        }
        csv_path = self.csv_exporter(csv_args)

        if csv_path:
            logger.info(f"✅ CSV exportado exitosamente: {csv_path}")
        else:
            logger.warning(f"⚠️ No se pudo exportar CSV")

        return {**args_dict, "csv_path": csv_path}

    def run(self, args_dict: dict) -> dict:
        """Ejecutar el pipeline completo"""
        logger.info("🚀 Iniciando pipeline de revisión de PRs")

        # Ejecutar pasos manualmente
        current_args = args_dict
        for step_func, step_name in self.steps:
            logger.info(f"📋 Ejecutando: {step_name}")
            try:
                current_args = step_func(current_args)
            except Exception as e:
                logger.error(f"❌ Error en paso '{step_name}': {e}")
                return {
                    "repo_url": args_dict["repo_url"],
                    "base_dir": args_dict["base_dir"],
                    "status": "failed",
                    "error": str(e),
                    "failed_at": step_name,
                }

        # Resultado final
        final_result = {
            "repo_url": args_dict["repo_url"],
            "base_dir": args_dict["base_dir"],
            "status": "completed",
            "processed_count": len(current_args.get("processed_prs", [])),
            "csv_path": current_args.get("csv_path", ""),
        }

        logger.info("🎉 Pipeline completado exitosamente!")
        return final_result


class SinglePRPipeline(Pipeline):
    """Pipeline para validar un único PR a partir de su URL"""
    
    def __init__(
        self, config_file: str = "config.yaml", rules_file: str = "rules.yaml"
    ):
        super().__init__(
            worker_id="single_pr_reviewer", 
            worker_name="Single PR Reviewer Pipeline", 
            verbose=True
        )
        
        # Inicializar componentes
        self.config_loader = ConfigLoader()
        self.github_api = GitHubAPI()
        self.quality_analyzer = QualityAnalyzer()
        self.merge_evaluator = MergeEvaluator()
        self.report_generator = ReportGenerator()
        self.csv_exporter = CSVExporter()
        
        # Cargar configuración y reglas
        config_args = {"config_file": config_file, "rules_file": rules_file}
        self.config, self.rules = self.config_loader(config_args)
        
    def set_steps(self):
        """Definir pasos del pipeline para validar un PR"""
        self.steps = [
            (self.load_config, "Cargar configuración y reglas"),
            (self.parse_pr_url, "Parsear URL del PR"),
            (self.download_pr_files, "Descargar archivos del PR"),
            (self.analyze_quality, "Analizar calidad del código"),
            (self.analyze_metadata, "Analizar metadata del PR"),
            (self.evaluate_merge, "Evaluar elegibilidad para merge"),
            (self.generate_report, "Generar reporte"),
        ]
    
    def load_config(self, args_dict: dict) -> dict:
        """Paso 1: Cargar configuración y reglas"""
        logger.info("🔧 Cargando configuración y reglas...")
        
        # Inicializar APIs con configuración
        init_args = {"config": self.config}
        self.github_api(init_args)
        
        return {
            "config": self.config,
            "rules": self.rules,
            "pr_url": args_dict["pr_url"],
            "base_dir": args_dict.get("base_dir", "repos_output"),
        }
    
    def parse_pr_url(self, args_dict: dict) -> dict:
        """Paso 2: Parsear URL del PR y extraer información"""
        logger.info("🔍 Parseando URL del PR...")
        
        pr_url = args_dict["pr_url"]
        
        # Extraer información del PR desde la URL
        import re
        from pathlib import Path
        
        # Formato: https://github.com/owner/repo/pull/123
        match = re.search(r"github\.com/([^/]+)/([^/]+)/pull/(\d+)", pr_url)
        if not match:
            raise ValueError(f"URL de PR inválida: {pr_url}")
        
        empresa = match.group(1)
        proyecto = match.group(2)
        pr_number = match.group(3)
        repo_url = f"https://github.com/{empresa}/{proyecto}"
        
        logger.info(f"PR #{pr_number} de {empresa}/{proyecto}")
        
        # Crear directorio para el PR
        base_dir = Path(args_dict["base_dir"])
        repo_dir = base_dir / empresa / proyecto
        pr_dir = repo_dir / pr_number
        pr_dir.mkdir(parents=True, exist_ok=True)
        
        return {
            **args_dict,
            "empresa": empresa,
            "proyecto": proyecto,
            "repo_url": repo_url,
            "pr_number": pr_number,
            "repo_dir": repo_dir,
            "pr_dir": pr_dir,
        }
    
    def download_pr_files(self, args_dict: dict) -> dict:
        """Paso 3: Descargar archivos cambiados del PR"""
        logger.info("📥 Descargando archivos del PR...")
        
        pr_url = args_dict["pr_url"]
        pr_dir = args_dict["pr_dir"]
        pr_number = args_dict["pr_number"]
        
        # Guardar información del PR
        pr_info = {
            "number": pr_number,
            "url": pr_url,
        }
        
        (pr_dir / "pr_info.json").write_text(
            json.dumps(pr_info, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        
        # Descargar archivos cambiados
        github_args = {
            "config": self.config,
            "repo_url": args_dict["repo_url"],
            "pr_url": pr_url,
            "target_dir": pr_dir,
        }
        _, download_success = self.github_api(github_args)
        
        if not download_success:
            raise Exception(f"Error descargando archivos del PR #{pr_number}")
        
        logger.info(f"✅ Archivos descargados exitosamente")
        
        # Leer lista de archivos descargados
        downloaded_files_list = []
        download_info_path = pr_dir / 'download_info.json'
        if download_info_path.exists():
            try:
                with open(download_info_path, 'r', encoding='utf-8') as f:
                    download_info = json.load(f)
                    downloaded_files_list = [
                        f_info['filename'] for f_info in download_info.get('files', []) 
                        if 'filename' in f_info
                    ]
                logger.info(f"Se cargaron {len(downloaded_files_list)} archivos")
            except Exception as e:
                logger.error(f"Error leyendo download_info.json: {e}")
        
        return {**args_dict, "downloaded_files": downloaded_files_list}
    
    def analyze_quality(self, args_dict: dict) -> dict:
        """Paso 4: Analizar calidad del código"""
        logger.info("🔬 Analizando calidad del código...")
        
        quality_args = {
            "config": self.config,
            "pr_dir": args_dict["pr_dir"],
            "downloaded_files": args_dict["downloaded_files"],
        }
        quality_result = self.quality_analyzer(quality_args)
        
        if "error" in quality_result:
            logger.warning(f"⚠️ Error en análisis de calidad: {quality_result['error']}")
        else:
            logger.info("✅ Análisis de calidad completado")
        
        return {**args_dict, "quality_result": quality_result}
    
    def analyze_metadata(self, args_dict: dict) -> dict:
        """Paso 5: Analizar metadata del PR"""
        logger.info("📋 Analizando metadata del PR...")
        
        pr_url = args_dict["pr_url"]
        pr_dir = args_dict["pr_dir"]
        pr_number = args_dict["pr_number"]
        
        metadata_result = self.github_api.analyze_pr_metadata(pr_url, pr_dir)
        
        if "error" in metadata_result:
            logger.warning(f"⚠️ Error en análisis de metadata: {metadata_result['error']}")
        else:
            logger.info("✅ Metadata analizada exitosamente")
        
        return {**args_dict, "metadata_result": metadata_result}
    
    def evaluate_merge(self, args_dict: dict) -> dict:
        """Paso 6: Evaluar elegibilidad para merge"""
        logger.info("⚖️ Evaluando elegibilidad para merge...")
        
        merge_args = {
            "rules": self.rules,
            "pr_dir": args_dict["pr_dir"],
            "pr_number": args_dict["pr_number"],
        }
        merge_evaluation = self.merge_evaluator(merge_args)
        
        if "error" in merge_evaluation:
            logger.error(f"❌ Error evaluando elegibilidad: {merge_evaluation['error']}")
            eligible = False
        else:
            eligible = merge_evaluation.get("eligible", False)
            if eligible:
                logger.info(f"✅ PR #{args_dict['pr_number']} es elegible para merge")
            else:
                logger.warning(f"❌ PR #{args_dict['pr_number']} NO es elegible para merge")
        
        return {**args_dict, "merge_evaluation": merge_evaluation, "eligible": eligible}
    
    def generate_report(self, args_dict: dict) -> dict:
        """Paso 7: Generar reporte visual"""
        logger.info("📊 Generando reporte...")
        
        quality_result = args_dict.get("quality_result", {})
        
        if "error" not in quality_result:
            report_args = {
                "pr_dir": args_dict["pr_dir"],
                "quality_data": quality_result,
                "pr_number": args_dict["pr_number"],
                "downloaded_files": args_dict["downloaded_files"],
            }
            self.report_generator(report_args)
            logger.info("✅ Reporte generado exitosamente")
        else:
            logger.warning("⚠️ No se pudo generar reporte debido a errores en análisis")
        
        return args_dict
    
    def run(self, args_dict: dict) -> dict:
        """Ejecutar el pipeline completo para un PR"""
        logger.info(f"🚀 Iniciando validación de PR: {args_dict['pr_url']}")
        
        # Definir pasos
        self.set_steps()
        
        # Ejecutar pasos
        current_args = args_dict
        for step_func, step_name in self.steps:
            logger.info(f"📋 Ejecutando: {step_name}")
            try:
                current_args = step_func(current_args)
            except Exception as e:
                logger.error(f"❌ Error en paso '{step_name}': {e}")
                return {
                    "pr_url": args_dict["pr_url"],
                    "status": "failed",
                    "error": str(e),
                    "failed_at": step_name,
                }
        
        # Resultado final
        final_result = {
            "pr_url": args_dict["pr_url"],
            "pr_number": current_args["pr_number"],
            "empresa": current_args["empresa"],
            "proyecto": current_args["proyecto"],
            "status": "completed",
            "eligible": current_args.get("eligible", False),
            "pr_dir": str(current_args["pr_dir"]),
        }
        
        logger.info("🎉 Validación de PR completada exitosamente!")
        return final_result
