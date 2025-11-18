from pydantic import BaseModel, Field
from typing import List

class ComplexityMetric(BaseModel):
    name: str
    complexity: int
    rank: str
    start_line: int

class SecretExposure(BaseModel):
    type: str
    line: int
    value: str

class QualityThresholds(BaseModel):
    pylint_pass: bool = Field(description="Pasa el mínimo de Pylint")
    flake8_pass: bool = Field(description="Pasa el máximo de violaciones de Flake8")
    mypy_pass: bool = Field(description="Pasa el máximo de errores de Mypy")
    complexity_pass: bool = Field(description="Pasa la complejidad promedio máxima")
    secrets_pass: bool = Field(description="Pasa el máximo de secretos expuestos")
    overall_pass: bool = Field(description="Pasa todos los criterios de calidad")

class CodeQualityReport(BaseModel):
    pylint_score: float = Field(description="Puntaje de Pylint (0-10).")
    flake8_score: int = Field(description="Número de violaciones de Flake8.")
    mypy_score: int = Field(description="Número de errores de Mypy.")
    complexity_score: float = Field(description="Complejidad ciclomática promedio.")
    
    # Métricas detalladas
    complexity_metrics: List[ComplexityMetric] = Field(description="Métricas de complejidad ciclomática por función/método.")
    secret_exposures: List[SecretExposure] = Field(description="Lista de potenciales credenciales o secretos expuestos.")
    
    # Resultados de calidad
    thresholds: QualityThresholds = Field(description="Resultados de calidad contra umbrales mínimos")