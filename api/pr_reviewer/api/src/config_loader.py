import yaml
from loguru import logger
from typing import Dict


class ConfigLoader:
    def __init__(self):
        pass

    def __call__(self, args_dict: Dict) -> tuple[Dict, Dict]:
        """Carga configuración y reglas desde archivos YAML"""
        config_file = args_dict.get("config_file", "config.yaml")
        rules_file = args_dict.get("rules_file", "rules.yaml")

        config = self._load_config(config_file)
        rules = self._load_rules(rules_file)

        return config, rules

    def _load_config(self, config_file: str) -> Dict:
        """Carga configuración desde archivo YAML"""
        try:
            with open(config_file, "r", encoding="utf-8") as file:
                return yaml.safe_load(file)
        except FileNotFoundError:
            logger.warning(
                f"Archivo de configuración {config_file} no encontrado, usando valores por defecto"
            )
            return self._get_default_config()
        except yaml.YAMLError as e:
            logger.error(f"Error leyendo configuración: {e}")
            return self._get_default_config()

    def _load_rules(self, rules_file: str) -> Dict:
        """Carga reglas de evaluación desde archivo YAML"""
        try:
            with open(rules_file, "r", encoding="utf-8") as file:
                return yaml.safe_load(file)
        except FileNotFoundError:
            logger.warning(
                f"Archivo de reglas {rules_file} no encontrado, usando valores por defecto"
            )
            return self._get_default_rules()
        except yaml.YAMLError as e:
            logger.error(f"Error leyendo reglas: {e}")
            return self._get_default_rules()

    def _get_default_rules(self) -> Dict:
        """Reglas por defecto"""
        return {
            "merge_rules": {
                "approvals": {"min_required": 1, "require_all_reviewers": False},
                "comments": {"max_open_comments": 10},
                "changes_requested": {"must_be_zero": True},
                "pr_status": {"must_be_mergeable": True, "must_not_be_draft": True},
                "quality_validation": {
                    "enabled": True,
                    "require_all_pass": True,
                    "metrics": {
                        "pylint": {"enabled": True, "min_score": 7.0},
                        "flake8": {"enabled": True, "max_violations": 5},
                        "mypy": {"enabled": True, "max_errors": 3},
                        "complexity": {"enabled": True, "max_average": 10.0},
                        "secrets": {"enabled": True, "max_exposures": 0},
                    },
                },
            },
            "output": {
                "save_evaluation": True,
                "evaluation_filename": "merge_evaluation.json",
            },
        }

    def _get_default_config(self) -> Dict:
        """Configuración por defecto"""
        return {
            "api": {
                "github": {
                    "base_url": "http://analyze-code-quality-github_download_api-1:8000",
                    "endpoints": {
                        "get_prs": "/api/v1/github/repos/pr-urls",
                        "download_files": "/api/v1/pr/download-pr-files",
                        "analyze_pr": "/api/v1/pr/analyze",
                    },
                    "timeout": {"connection": 30, "download": 60, "analysis": 60},
                },
                "quality": {
                    "base_url": "http://localhost:8032",
                    "endpoints": {"analyze_batch": "/analyze-batch-code-quality"},
                    "timeout": {"analysis": 120},
                },
            },
            "processing": {
                "output_directory": "repos_output",
                "clean_before_download": True,
                "max_retries": 3,
            },
            "logging": {
                "level": "INFO",
                "format": "%(asctime)s - %(levelname)s - %(message)s",
            },
        }
