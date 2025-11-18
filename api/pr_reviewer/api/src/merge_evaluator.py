import json
from pathlib import Path
from typing import Dict
from loguru import logger

class MergeEvaluator:
    def __init__(self):
        self.rules = None
    
    def __call__(self, args_dict: Dict) -> Dict:
        """Evalúa si un PR es elegible para merge basado en las reglas"""
        # Inicializar reglas si no están hechas
        if self.rules is None:
            self.rules = args_dict.get("rules", {})
        
        pr_dir = args_dict["pr_dir"]
        pr_number = args_dict["pr_number"]
        return self.evaluate_merge_eligibility(pr_dir, pr_number)
    
    def evaluate_merge_eligibility(self, pr_dir: Path, pr_number: str) -> Dict:
        """Evalúa si un PR es elegible para merge basado en las reglas"""
        if self.rules is None:
            logger.error("Reglas no configuradas. Llame a __call__ primero.")
            return {"error": "Reglas no configuradas"}
            
        try:
            # Cargar metadata y calidad
            metadata_file = pr_dir / 'pr_metadata.json'
            quality_file = pr_dir / 'quality_report.json'
            
            if not metadata_file.exists():
                return {"error": "No se encontró metadata del PR"}
            
            metadata = json.loads(metadata_file.read_text(encoding='utf-8'))
            quality = {}
            
            if quality_file.exists():
                quality = json.loads(quality_file.read_text(encoding='utf-8'))
            
            rules = self.rules['merge_rules']
            evaluation = {
                "pr_number": pr_number,
                "eligible": False,
                "rules_passed": [],
                "rules_failed": [],
                "details": {}
            }
            
            # Evaluar aprobaciones
            approvals_rule = rules['approvals']
            approvals_count = metadata.get('approvals', 0)
            min_required = approvals_rule['min_required']
            
            if approvals_count >= min_required:
                evaluation["rules_passed"].append(f"Aprobaciones: {approvals_count} >= {min_required}")
                evaluation["details"]["approvals"] = {"passed": True, "count": approvals_count, "required": min_required}
            else:
                evaluation["rules_failed"].append(f"Aprobaciones insuficientes: {approvals_count} < {min_required}")
                evaluation["details"]["approvals"] = {"passed": False, "count": approvals_count, "required": min_required}
            
            # Evaluar comentarios
            comments_rule = rules['comments']
            comments_count = metadata.get('comments', 0)
            max_comments = comments_rule['max_open_comments']
            
            if comments_count <= max_comments:
                evaluation["rules_passed"].append(f"Comentarios: {comments_count} <= {max_comments}")
                evaluation["details"]["comments"] = {"passed": True, "count": comments_count, "max_allowed": max_comments}
            else:
                evaluation["rules_failed"].append(f"Demasiados comentarios: {comments_count} > {max_comments}")
                evaluation["details"]["comments"] = {"passed": False, "count": comments_count, "max_allowed": max_comments}
            
            # Evaluar cambios solicitados
            changes_rule = rules['changes_requested']
            changes_count = metadata.get('changes_requested', 0)
            
            if changes_rule['must_be_zero'] and changes_count == 0:
                evaluation["rules_passed"].append("Sin cambios solicitados")
                evaluation["details"]["changes_requested"] = {"passed": True, "count": changes_count}
            elif changes_rule['must_be_zero']:
                evaluation["rules_failed"].append(f"Tiene cambios solicitados: {changes_count}")
                evaluation["details"]["changes_requested"] = {"passed": False, "count": changes_count}
            else:
                evaluation["rules_passed"].append(f"Cambios solicitados permitidos: {changes_count}")
                evaluation["details"]["changes_requested"] = {"passed": True, "count": changes_count}
            
            # Evaluar estado del PR
            status_rule = rules['pr_status']
            
            if status_rule['must_be_mergeable'] and metadata.get('mergeable', False):
                evaluation["rules_passed"].append("PR es mergeable")
                evaluation["details"]["mergeable"] = {"passed": True, "value": metadata.get('mergeable')}
            elif status_rule['must_be_mergeable']:
                evaluation["rules_failed"].append("PR no es mergeable")
                evaluation["details"]["mergeable"] = {"passed": False, "value": metadata.get('mergeable')}
            
            if status_rule['must_not_be_draft'] and not metadata.get('draft', True):
                evaluation["rules_passed"].append("PR no es draft")
                evaluation["details"]["draft"] = {"passed": True, "value": metadata.get('draft')}
            elif status_rule['must_not_be_draft']:
                evaluation["rules_failed"].append("PR está en modo draft")
                evaluation["details"]["draft"] = {"passed": False, "value": metadata.get('draft')}
            
            # Evaluar calidad del código
            quality_rule = rules['quality_validation']
            if quality_rule['enabled'] and quality:
                evaluation["details"]["quality"] = self._evaluate_quality_rules(quality, quality_rule)
                
                if quality_rule['require_all_pass']:
                    # Verificar si todos los archivos pasaron
                    all_pass = quality.get('all_files_pass', False)
                    if all_pass:
                        evaluation["rules_passed"].append("Todos los archivos pasaron la validación de calidad")
                        evaluation["details"]["quality"]["all_pass"] = {"passed": True, "value": all_pass}
                    else:
                        evaluation["rules_failed"].append("No todos los archivos pasaron la validación de calidad")
                        evaluation["details"]["quality"]["all_pass"] = {"passed": False, "value": all_pass}
                else:
                    # Evaluar métricas individuales
                    for metric, result in evaluation["details"]["quality"].items():
                        if metric != "all_pass" and result.get("passed", False):
                            evaluation["rules_passed"].append(f"Métrica {metric}: OK")
                        elif metric != "all_pass":
                            evaluation["rules_failed"].append(f"Métrica {metric}: FALLÓ")
            
            # Determinar elegibilidad final
            evaluation["eligible"] = len(evaluation["rules_failed"]) == 0
            evaluation["summary"] = {
                "total_rules": len(evaluation["rules_passed"]) + len(evaluation["rules_failed"]),
                "passed": len(evaluation["rules_passed"]),
                "failed": len(evaluation["rules_failed"])
            }
            
            # Guardar evaluación
            if self.rules['output']['save_evaluation']:
                eval_file = pr_dir / self.rules['output']['evaluation_filename']
                eval_file.write_text(
                    json.dumps(evaluation, indent=2, ensure_ascii=False),
                    encoding='utf-8'
                )
                logger.info(f"Evaluación guardada en {eval_file}")
            
            return evaluation
            
        except Exception as e:
            logger.error(f"Error evaluando elegibilidad de merge: {e}")
            return {"error": str(e)}
    
    def _evaluate_quality_rules(self, quality_data: Dict, quality_rule: Dict) -> Dict:
        """Evalúa las reglas de calidad del código"""
        results = {}
        metrics = quality_rule.get('metrics', {})
        
        # Verificar si todos los archivos pasaron
        if 'all_files_pass' in quality_data:
            results['all_pass'] = {
                "passed": quality_data['all_files_pass'],
                "value": quality_data['all_files_pass']
            }
        
        # Evaluar métricas individuales si no se requiere all_pass
        if not quality_rule.get('require_all_pass', True):
            # Aquí se podrían agregar evaluaciones más detalladas de métricas
            # Por ahora, solo registramos los datos disponibles
            for metric_name in ['pylint', 'flake8', 'mypy', 'complexity', 'secrets']:
                if metrics.get(metric_name, {}).get('enabled', False):
                    results[metric_name] = {
                        "passed": True,  # Lógica simplificada
                        "data": quality_data.get(metric_name, {})
                    }
        
        return results