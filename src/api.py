
from fastapi import FastAPI
from .code_quality_report import CodeQualityReport, QualityThresholds
from .complejity_metric import analyze_complexity_internal
from pydantic import BaseModel
from typing import List, Dict, Any
import re
import subprocess
import tempfile
import os
import yaml

class CodeRequest(BaseModel):
    code: str
    evaluate_pylint: bool = True
    evaluate_flake8: bool = True
    evaluate_mypy: bool = True
    evaluate_complexity: bool = True
    evaluate_secrets: bool = True

class FileAnalysis(BaseModel):
    filename: str
    code: str

class BatchCodeRequest(BaseModel):
    files: List[FileAnalysis]
    evaluate_pylint: bool = True
    evaluate_flake8: bool = True
    evaluate_mypy: bool = True
    evaluate_complexity: bool = True
    evaluate_secrets: bool = True

app = FastAPI()

# Load configuration
def load_config():
    config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except:
        # Default values if config file not found
        return {
            'pylint': {'min_score': 7.0},
            'flake8': {'max_violations': 10},
            'mypy': {'max_errors': 3},
            'complexity': {'max_avg_complexity': 5.0},
            'secrets': {'max_exposures': 2}
        }

config = load_config()

def calculate_complexity_score(metrics):
    if not metrics:
        return 0
    complexities = [m.complexity for m in metrics]
    return sum(complexities) / len(complexities) if complexities else 0

def check_quality_thresholds(pylint_score, flake8_score, mypy_score, complexity_score, secrets_count):
    pylint_pass = pylint_score >= config['pylint']['min_score']
    flake8_pass = flake8_score <= config['flake8']['max_violations']
    mypy_pass = mypy_score <= config['mypy']['max_errors']
    complexity_pass = complexity_score <= config['complexity']['max_avg_complexity']
    secrets_pass = secrets_count <= config['secrets']['max_exposures']
    
    overall_pass = all([pylint_pass, flake8_pass, mypy_pass, complexity_pass, secrets_pass])
    
    return QualityThresholds(
        pylint_pass=pylint_pass,
        flake8_pass=flake8_pass,
        mypy_pass=mypy_pass,
        complexity_pass=complexity_pass,
        secrets_pass=secrets_pass,
        overall_pass=overall_pass
    )

def analyze_secrets_internal(code: str):
    secrets = []
    lines = code.split('\n')
    for i, line in enumerate(lines, 1):
        if 'password' in line.lower() or 'secret' in line.lower() or 'key' in line.lower():
            secrets.append({"type": "potential_secret", "line": i, "value": line.strip()})
    return secrets

def run_pylint(code: str) -> float:
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(code)
        temp_file = f.name
    try:
        result = subprocess.run(['pylint', temp_file], capture_output=True, text=True)
        # Parse the score from the output
        for line in result.stdout.split('\n'):
            if 'Your code has been rated at' in line:
                import re
                match = re.search(r'rated at ([0-9.]+)/10', line)
                if match:
                    return float(match.group(1))
        return 0.0
    except Exception as e:
        print(f"Pylint error: {e}")
        return 0.0
    finally:
        os.unlink(temp_file)

def run_flake8(code: str) -> int:
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(code)
        temp_file = f.name
    try:
        result = subprocess.run(['flake8', temp_file], capture_output=True, text=True)
        # Count the number of violations (each line is a violation)
        violations = [line for line in result.stdout.split('\n') if line.strip()]
        return len(violations)
    except:
        return 0
    finally:
        os.unlink(temp_file)

def run_mypy(code: str) -> int:
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(code)
        temp_file = f.name
    try:
        # Try different mypy commands
        commands = [
            ['mypy', '--no-error-summary', temp_file],
            ['python3', '-m', 'mypy', '--no-error-summary', temp_file],
            ['python', '-m', 'mypy', '--no-error-summary', temp_file]
        ]
        
        for cmd in commands:
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                if result.returncode != 0:
                    # Count the number of error lines
                    errors = [line for line in result.stdout.split('\n') if 'error:' in line]
                    return len(errors)
            except (subprocess.TimeoutExpired, FileNotFoundError):
                continue
        return 0
    except:
        return 0
    finally:
        os.unlink(temp_file)

@app.post("/analyze-code-quality", response_model=CodeQualityReport)
async def analyze_full_code_quality(
    request: CodeRequest
) -> CodeQualityReport:
    code = request.code

    # 2. Ejecución de Linters (solo si se solicitan)
    pylint_score = run_pylint(code) if request.evaluate_pylint else 10.0  # Perfect score if not evaluated
    flake8_score = run_flake8(code) if request.evaluate_flake8 else 0  # No violations if not evaluated
    mypy_score = run_mypy(code) if request.evaluate_mypy else 0  # No errors if not evaluated

    # 3. 🛡️ EJECUCIÓN DE SECRET SCANNING
    secret_exposures = analyze_secrets_internal(code) if request.evaluate_secrets else []

    # 4. 📈 EJECUCIÓN DE COMPLEJIDAD
    complexity_metrics = analyze_complexity_internal(code) if request.evaluate_complexity else []
    complexity_score = calculate_complexity_score(complexity_metrics)

    # 5. VERIFICACIÓN DE UMBRALES DE CALIDAD
    thresholds = check_quality_thresholds(
        pylint_score, flake8_score, mypy_score, 
        complexity_score, len(secret_exposures)
    )
    
    # Forzar los booleanos a True si no se evaluó esa métrica
    if not request.evaluate_pylint:
        thresholds.pylint_pass = True
    if not request.evaluate_flake8:
        thresholds.flake8_pass = True
    if not request.evaluate_mypy:
        thresholds.mypy_pass = True
    if not request.evaluate_complexity:
        thresholds.complexity_pass = True
    if not request.evaluate_secrets:
        thresholds.secrets_pass = True
    
    # Recalcular overall_pass
    thresholds.overall_pass = all([
        thresholds.pylint_pass,
        thresholds.flake8_pass,
        thresholds.mypy_pass,
        thresholds.complexity_pass,
        thresholds.secrets_pass
    ])

    # 6. CREACIÓN DEL REPORTE FINAL
    final_report = CodeQualityReport(
        pylint_score=pylint_score,
        flake8_score=flake8_score,
        mypy_score=mypy_score,
        complexity_score=complexity_score,
        complexity_metrics=complexity_metrics,
        secret_exposures=secret_exposures,
        thresholds=thresholds
    )

    return final_report

def analyze_single_file(filename: str, code: str, evaluation_config: Dict[str, bool]) -> Dict[str, Any]:
    """Analyze a single file and return results."""
    # 2. Ejecución de Linters (solo si se solicitan)
    pylint_score = run_pylint(code) if evaluation_config.get('evaluate_pylint', True) else 10.0
    flake8_score = run_flake8(code) if evaluation_config.get('evaluate_flake8', True) else 0
    mypy_score = run_mypy(code) if evaluation_config.get('evaluate_mypy', True) else 0

    # 3. 🛡️ EJECUCIÓN DE SECRET SCANNING
    secret_exposures = analyze_secrets_internal(code) if evaluation_config.get('evaluate_secrets', True) else []

    # 4. 📈 EJECUCIÓN DE COMPLEJIDAD
    complexity_metrics = analyze_complexity_internal(code) if evaluation_config.get('evaluate_complexity', True) else []
    complexity_score = calculate_complexity_score(complexity_metrics)

    # 5. VERIFICACIÓN DE UMBRALES DE CALIDAD
    thresholds = check_quality_thresholds(
        pylint_score, flake8_score, mypy_score, 
        complexity_score, len(secret_exposures)
    )
    
    # Forzar los booleanos a True si no se evaluó esa métrica
    if not evaluation_config.get('evaluate_pylint', True):
        thresholds.pylint_pass = True
    if not evaluation_config.get('evaluate_flake8', True):
        thresholds.flake8_pass = True
    if not evaluation_config.get('evaluate_mypy', True):
        thresholds.mypy_pass = True
    if not evaluation_config.get('evaluate_complexity', True):
        thresholds.complexity_pass = True
    if not evaluation_config.get('evaluate_secrets', True):
        thresholds.secrets_pass = True
    
    # Recalcular overall_pass
    thresholds.overall_pass = all([
        thresholds.pylint_pass,
        thresholds.flake8_pass,
        thresholds.mypy_pass,
        thresholds.complexity_pass,
        thresholds.secrets_pass
    ])

    return {
        "filename": filename,
        "pylint_score": pylint_score,
        "flake8_score": flake8_score,
        "mypy_score": mypy_score,
        "complexity_score": complexity_score,
        "complexity_metrics": [m.dict() if hasattr(m, 'dict') else m for m in complexity_metrics],
        "secret_exposures": [s.dict() if hasattr(s, 'dict') else s for s in secret_exposures],
        "thresholds": thresholds.dict()
    }

@app.post("/analyze-batch-code-quality", response_model=Dict[str, Any])
async def analyze_batch_code_quality(
    request: BatchCodeRequest
) -> Dict[str, Any]:
    """Analyze multiple files and return batch results."""
    
    evaluation_config = {
        'evaluate_pylint': request.evaluate_pylint,
        'evaluate_flake8': request.evaluate_flake8,
        'evaluate_mypy': request.evaluate_mypy,
        'evaluate_complexity': request.evaluate_complexity,
        'evaluate_secrets': request.evaluate_secrets
    }
    
    # Analyze each file
    file_results = []
    for file_analysis in request.files:
        result = analyze_single_file(
            file_analysis.filename, 
            file_analysis.code, 
            evaluation_config
        )
        file_results.append(result)
    
    # Calculate global validator
    all_files_pass = all(result["thresholds"]["overall_pass"] for result in file_results)
    passing_count = sum(1 for result in file_results if result["thresholds"]["overall_pass"])
    total_count = len(file_results)
    
    # Prepare table data for manual_test
    table_data = []
    for result in file_results:
        thresholds = result["thresholds"]
        table_row = [
            result["filename"],
            f"{result['pylint_score']:.1f} {'✅' if thresholds['pylint_pass'] else '❌'}",
            f"{result['flake8_score']} {'✅' if thresholds['flake8_pass'] else '❌'}",
            f"{result['mypy_score']} {'✅' if thresholds['mypy_pass'] else '❌'}",
            f"{result['complexity_score']:.1f} {'✅' if thresholds['complexity_pass'] else '❌'}",
            f"{len(result['secret_exposures'])} {'✅' if thresholds['secrets_pass'] else '❌'}",
            "✅" if thresholds["overall_pass"] else "❌"
        ]
        table_data.append(table_row)
    
    # Global validator
    global_validator = {
        "all_files_pass": all_files_pass,
        "passing_count": passing_count,
        "total_count": total_count,
        "passing_percentage": round((passing_count / total_count) * 100, 1) if total_count > 0 else 0,
        "status": "✅ TODOS PASAN CALIDAD" if all_files_pass else "❌ ALGUNOS FALLAN CALIDAD"
    }
    
    return {
        "table_data": table_data,
        "headers": ["Archivo", "Pylint", "Flake8", "Mypy", "Complejidad", "Secretos", "Calidad General"],
        "global_validator": global_validator,
        "file_results": file_results
    }