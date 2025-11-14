from radon.complexity import cc_visit, cc_rank
from typing import List
from .code_quality_report import ComplexityMetric

def analyze_complexity_internal(code: str) -> List[ComplexityMetric]:
    metrics = []
    try:
        # cc_visit devuelve una lista de objetos Function
        analysis_results = cc_visit(code)
        
        for func in analysis_results:
            metrics.append(ComplexityMetric(
                name=func.name,
                complexity=func.complexity,
                rank=cc_rank(func.complexity), # Convierte el número CC a un rango A-F
                start_line=func.lineno
            ))
    except Exception as e:
        # Es robusto ante código malformado, devolviendo una lista vacía si falla
        pass
        
    return metrics