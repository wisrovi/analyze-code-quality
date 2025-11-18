import json
import pandas as pd
from pathlib import Path
from typing import Dict, List
from loguru import logger


class CSVExporter:
    def __init__(self):
        self.results_dir = None

    def __call__(self, args_dict: Dict) -> str:
        """Crea un CSV con los resultados de evaluación de PRs de un repositorio"""
        # Inicializar directorio de resultados si no está hecho
        if self.results_dir is None:
            results_dir = args_dict.get("results_dir", "results")
            self.results_dir = Path(results_dir)
            self.results_dir.mkdir(exist_ok=True)

        repo_dir = args_dict["repo_dir"]
        empresa = args_dict["empresa"]
        proyecto = args_dict["proyecto"]
        return self.export_repo_results(repo_dir, empresa, proyecto)

    def export_repo_results(self, repo_dir: Path, empresa: str, proyecto: str) -> str:
        """Exporta los resultados de evaluación de PRs a un CSV usando pandas"""
        if self.results_dir is None:
            logger.error(
                "Directorio de resultados no configurado. Llame a __call__ primero."
            )
            return ""

        try:
            # Nombre del archivo CSV basado en el repositorio
            csv_filename = f"{empresa}_{proyecto}_results.csv"
            csv_path = self.results_dir / csv_filename

            # Recolectar datos de todos los PRs
            pr_results = []

            # Buscar todas las carpetas de PRs (números)
            for pr_dir in repo_dir.iterdir():
                if pr_dir.is_dir() and pr_dir.name.isdigit():
                    pr_data = self._extract_pr_data(pr_dir)
                    if pr_data:
                        pr_results.append(pr_data)

            if not pr_results:
                logger.warning(
                    f"No se encontraron PRs con datos para {empresa}/{proyecto}"
                )
                return ""

            # Crear DataFrame con pandas
            df = pd.DataFrame(pr_results)

            # Definir orden de columnas base
            base_columns = [
                "evaluation_date",
                "pr_url",
                "pr_number",
                "title",
                "author",
                "reviewers",
                "rules_passed",
                "rules_failed",
            ]

            # Columnas de reglas (ordenadas alfabéticamente)
            rule_columns = [col for col in df.columns if col.startswith("rule_")]
            rule_columns.sort()

            # Columna final de elegibilidad
            final_columns = ["eligible_for_merge"]

            # Combinar todas las columnas en orden
            all_columns = base_columns + rule_columns + final_columns

            # Asegurar que todas las columnas existan en el DataFrame
            for col in all_columns:
                if col not in df.columns:
                    df[col] = (
                        False
                        if col.startswith("rule_") or col == "eligible_for_merge"
                        else ""
                    )

            df = df[all_columns]

            # Exportar a CSV
            df.to_csv(csv_path, index=False, encoding="utf-8")

            logger.info(f"CSV exportado: {csv_path} con {len(pr_results)} PRs")
            return str(csv_path)

        except Exception as e:
            logger.error(f"Error exportando CSV para {empresa}/{proyecto}: {e}")
            return ""

    def _extract_pr_data(self, pr_dir: Path) -> Dict:
        """Extrae datos de un PR desde sus archivos JSON"""
        try:
            # Cargar información básica del PR
            pr_info_file = pr_dir / "pr_info.json"
            pr_info = {}
            if pr_info_file.exists():
                pr_info = json.loads(pr_info_file.read_text(encoding="utf-8"))

            # Cargar metadata del PR
            pr_metadata_file = pr_dir / "pr_metadata.json"
            pr_metadata = {}
            if pr_metadata_file.exists():
                pr_metadata = json.loads(pr_metadata_file.read_text(encoding="utf-8"))

            # Cargar información del download_info para obtener más datos
            download_info_file = pr_dir / "download_info.json"
            download_info = {}
            if download_info_file.exists():
                download_info = json.loads(
                    download_info_file.read_text(encoding="utf-8")
                )

            # Cargar evaluación de merge
            merge_eval_file = pr_dir / "merge_evaluation.json"
            merge_eval = {}
            if merge_eval_file.exists():
                merge_eval = json.loads(merge_eval_file.read_text(encoding="utf-8"))

            # Obtener URL del PR desde metadata o construir
            pr_url = pr_metadata.get("pr_url", pr_info.get("url", ""))
            if not pr_url and pr_info.get("number"):
                # Construir URL base (asumiendo GitHub)
                pr_url = f"https://github.com/{pr_dir.parent.parent.name}/{pr_dir.parent.name}/pull/{pr_info['number']}"

            # Determinar elegibilidad
            eligible = merge_eval.get("eligible", False)

            # Extraer resultados de reglas individuales como booleanos
            rule_results = self._extract_rule_results(merge_eval)

            # Extraer title y author desde diferentes fuentes
            title = (
                pr_info.get("title")
                or pr_metadata.get("title")
                or download_info.get("title")
                or f"PR #{pr_info.get('number', pr_dir.name)}"
            )

            author = (
                pr_info.get("author")
                or pr_metadata.get("author")
                or download_info.get("author")
                or download_info.get("owner")
                or "Unknown"
            )

            # Extraer revisores (nombres de usuario)
            reviewers_data = pr_metadata.get("reviewers", [])
            reviewers_list = []
            for reviewer in reviewers_data:
                if isinstance(reviewer, dict):
                    username = reviewer.get("username", "")
                    if username:
                        reviewers_list.append(username)
                elif isinstance(reviewer, str):
                    reviewers_list.append(reviewer)
            reviewers_str = ", ".join(reviewers_list) if reviewers_list else ""

            # Fecha de evaluación actual
            from datetime import datetime

            evaluation_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Base del resultado
            result = {
                "pr_url": pr_url,
                "pr_number": pr_info.get("number", pr_dir.name),
                "title": title,
                "author": author,
                "reviewers": reviewers_str,
                "evaluation_date": evaluation_date,
                "rules_passed": len(merge_eval.get("rules_passed", [])),
                "rules_failed": len(merge_eval.get("rules_failed", [])),
                "eligible_for_merge": eligible,
            }

            # Agregar resultados de reglas individuales
            result.update(rule_results)

            return result

        except Exception as e:
            logger.warning(f"Error extrayendo datos del PR en {pr_dir}: {e}")
            return {}

    def _extract_rule_results(self, merge_eval: Dict) -> Dict:
        """Extrae resultados de reglas individuales como booleanos"""
        rule_results = {}

        if "details" not in merge_eval:
            return rule_results

        details = merge_eval["details"]

        # Regla de aprobaciones
        if "approvals" in details:
            rule_results["rule_approvals"] = details["approvals"].get("passed", False)

        # Regla de comentarios
        if "comments" in details:
            rule_results["rule_comments"] = details["comments"].get("passed", False)

        # Regla de cambios solicitados
        if "changes_requested" in details:
            rule_results["rule_changes_requested"] = details["changes_requested"].get(
                "passed", False
            )

        # Regla de mergeable
        if "mergeable" in details:
            rule_results["rule_mergeable"] = details["mergeable"].get("passed", False)

        # Regla de draft
        if "draft" in details:
            rule_results["rule_not_draft"] = details["draft"].get("passed", False)

        # Regla de calidad
        if "quality" in details:
            quality_details = details["quality"]
            if "all_pass" in quality_details:
                rule_results["rule_quality_all_pass"] = quality_details["all_pass"].get(
                    "passed", False
                )
            else:
                rule_results["rule_quality_all_pass"] = False

        return rule_results
