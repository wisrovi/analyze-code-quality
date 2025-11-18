import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from pathlib import Path
from typing import Dict
from loguru import logger

# Configurar fuente estándar
plt.rcParams["font.family"] = "DejaVu Sans"


class ReportGenerator:
    def __init__(self):
        pass

    def __call__(self, args_dict: Dict) -> bool:
        """Crea una imagen con una tabla de resultados de calidad ajustada al contenido"""
        pr_dir = args_dict["pr_dir"]
        quality_data = args_dict["quality_data"]
        pr_number = args_dict["pr_number"]
        return self.create_quality_table_image(pr_dir, quality_data, pr_number)

    def create_quality_table_image(
        self, pr_dir: Path, quality_data: Dict, pr_number: str
    ) -> bool:
        """Crea una imagen con una tabla de resultados de calidad ajustada al contenido"""
        try:
            if not quality_data or "table_data" not in quality_data:
                logger.warning(
                    f"No hay datos de tabla para crear imagen en PR #{pr_number}"
                )
                return False

            table_data = quality_data["table_data"]
            if not table_data:
                logger.warning(f"Datos de tabla vacíos para PR #{pr_number}")
                return False

            # Crear imagen con más ancho para acomodar nombres de archivo largos
            fig, ax = plt.subplots(figsize=(16, 6))
            ax.axis("tight")
            ax.axis("off")

            # Crear tabla simple
            headers = [
                "Archivo",
                "Pylint",
                "Flake8",
                "Mypy",
                "Complejidad",
                "Secretos",
                "Estado",
            ]

            # Procesar datos y colorear celdas según estado
            processed_data = []
            cell_colors = []
            for row in table_data:
                processed_row = []
                row_colors = ["#f8f9fa"] * len(headers)

                for i, cell in enumerate(row):
                    if isinstance(cell, str):
                        # Limpiar texto: remover emojis y dejar solo los valores
                        clean_cell = cell.replace("✅", "").replace("❌", "").strip()

                        # Determinar color según el emoji original
                        if "✅" in cell:
                            row_colors[i] = "#d4edda"  # Verde claro
                        elif "❌" in cell:
                            row_colors[i] = "#f8d7da"  # Rojo claro

                        processed_row.append(clean_cell)
                    else:
                        processed_row.append(cell)

                processed_data.append(processed_row)
                cell_colors.append(row_colors)

            table = ax.table(
                cellText=processed_data,
                colLabels=headers,
                cellLoc="center",
                loc="center",
                cellColours=cell_colors,
            )

            table.auto_set_font_size(False)
            table.set_fontsize(9)

            # Ajustar anchos de columna manualmente
            table.scale(1, 1.2)

            # Hacer la primera columna (archivo) más ancha
            cells = table.get_celld()
            for i in range(len(headers)):
                for j in range(len(table_data) + 1):  # +1 para header
                    cell = cells[(j, i)]
                    if i == 0:  # Primera columna (archivo)
                        cell.set_width(0.4)  # 40% del ancho
                    else:  # Otras columnas
                        cell.set_width(0.1)  # 10% del ancho cada una

            # Guardar imagen
            image_path = pr_dir / "quality_report.png"
            plt.savefig(image_path, dpi=150, bbox_inches="tight", facecolor="white")
            plt.close()

            logger.info(f"Imagen de tabla de calidad guardada en {image_path}")
            return True

        except Exception as e:
            logger.error(f"Error creando imagen de tabla de calidad: {e}")
            return False
