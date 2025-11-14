from pydantic import BaseModel, Field
from typing import List

class SecretExposure(BaseModel):
    """Representa una credencial o secreto potencialmente expuesto."""
    line: int
    pattern_name: str = Field(description="Nombre del patrón coincidente (ej: 'AWS_ACCESS_KEY', 'Password_Keyword').")
    context: str = Field(description="El fragmento de código que contiene la posible exposición.")