import os
import requests
import json
from tabulate import tabulate
import matplotlib.pyplot as plt
import matplotlib.table as tbl
from datetime import datetime

API_URL = "http://localhost:8032/analyze-code-quality"
TEST_DIR = "local"

def get_api_response(code):
    response = requests.post(API_URL, json={"code": code})
    if response.status_code == 200:
        return response.json()
    return {"pylint_score": 0, "flake8_score": 0, "complexity_metrics": [], "secret_exposures": []}

def calculate_complexity_score(metrics):
    if not metrics:
        return 0
    complexities = [m["complexity"] for m in metrics]
    return sum(complexities) / len(complexities) if complexities else 0

def main():
    files = [f for f in os.listdir(TEST_DIR) if f.endswith(".py")]
    table_data = []

    for file in files:
        file_path = os.path.join(TEST_DIR, file)
        with open(file_path, "r") as f:
            code = f.read()

        api_response = get_api_response(code)
        pylint_score = api_response.get("pylint_score", 0)
        flake8_score = api_response.get("flake8_score", 0)
        mypy_score = api_response.get("mypy_score", 0)
        complexity_score = api_response.get("complexity_score", 0)
        secrets_score = len(api_response.get("secret_exposures", []))
        
        # Get quality thresholds
        thresholds = api_response.get("thresholds", {})
        overall_pass = thresholds.get("overall_pass", False)
        
        # Individual quality checks
        pylint_pass = "✅" if thresholds.get("pylint_pass", False) else "❌"
        flake8_pass = "✅" if thresholds.get("flake8_pass", False) else "❌"
        mypy_pass = "✅" if thresholds.get("mypy_pass", False) else "❌"
        complexity_pass = "✅" if thresholds.get("complexity_pass", False) else "❌"
        secrets_pass = "✅" if thresholds.get("secrets_pass", False) else "❌"
        overall_pass_emoji = "✅" if overall_pass else "❌"

        table_data.append([
            file, 
            f"{pylint_score:.1f} {pylint_pass}", 
            f"{flake8_score} {flake8_pass}", 
            f"{mypy_score} {mypy_pass}", 
            f"{complexity_score:.1f} {complexity_pass}", 
            f"{secrets_score} {secrets_pass}",
            overall_pass_emoji
        ])

    headers = ["Archivo", "Pylint", "Flake8", "Mypy", "Complejidad", "Secretos", "Calidad General"]
    
    # Print table to console
    print(tabulate(table_data, headers=headers, tablefmt="grid"))
    
    # Save quality summary as JSON
    save_quality_summary_json(table_data)
    
    # Save table as image
    save_table_as_image(table_data, headers)

def save_quality_summary_json(table_data):
    """Save quality summary as JSON file."""
    try:
        # Calculate overall quality status
        all_pass = all("✅" in row[-1] for row in table_data)
        passing_count = sum(1 for row in table_data if "✅" in row[-1])
        total_count = len(table_data)
        
        # Create summary data
        summary = {
            "timestamp": datetime.now().isoformat(),
            "overall_quality": {
                "all_files_pass": all_pass,
                "passing_count": passing_count,
                "total_count": total_count,
                "passing_percentage": round((passing_count / total_count) * 100, 1)
            },
            "file_details": []
        }
        
        # Add individual file details
        for row in table_data:
            file_name = row[0]
            overall_pass = "✅" in row[-1]
            
            # Parse scores from the formatted strings
            pylint_score = float(row[1].split()[0])
            flake8_score = int(row[2].split()[0])
            mypy_score = int(row[3].split()[0])
            complexity_score = float(row[4].split()[0])
            secrets_score = int(row[5].split()[0])
            
            summary["file_details"].append({
                "file": file_name,
                "scores": {
                    "pylint": pylint_score,
                    "flake8": flake8_score,
                    "mypy": mypy_score,
                    "complexity": complexity_score,
                    "secrets": secrets_score
                },
                "passes_quality": overall_pass
            })
        
        # Save JSON file
        filename = f"quality_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        print(f"\n📄 Resumen guardado como JSON: {filename}")
        print(f"📊 Estado general: {'✅ Todos pasan' if all_pass else '❌ Algunos fallan'} ({passing_count}/{total_count})")
        
    except Exception as e:
        print(f"\n❌ Error al guardar JSON: {e}")

def save_table_as_image(table_data, headers):
    """Save quality report table as an image file."""
    try:
        # Calculate overall quality status
        all_pass = all("✅" in row[-1] for row in table_data)
        quality_status = "✅ TODOS PASAN CALIDAD" if all_pass else "❌ ALGUNOS FALLAN CALIDAD"
        
        # Set matplotlib to use non-interactive backend
        plt.switch_backend('Agg')
        
        # Create figure
        fig, ax = plt.subplots(figsize=(16, 10))
        ax.axis('tight')
        ax.axis('off')
        
        # Create table
        table = ax.table(cellText=table_data, colLabels=headers, cellLoc='center', loc='center')
        
        # Style the table
        table.auto_set_font_size(False)
        table.set_fontsize(9)
        table.scale(1.2, 1.5)
        
        # Color coding for headers
        for i in range(len(headers)):
            table[(0, i)].set_facecolor('#2E7D32')
            table[(0, i)].set_text_props(weight='bold', color='white')
        
        # Color coding for rows based on quality status
        for i, row in enumerate(table_data):
            col_idx = len(headers) - 1  # Last column (Calidad General)
            if "✅" in row[col_idx]:
                # Green tint for passing rows
                for j in range(len(headers)):
                    table[(i + 1, j)].set_facecolor('#E8F5E8')
                table[(i + 1, col_idx)].set_facecolor('#4CAF50')  # Darker green for status
                # Make text white for better contrast
                table[(i + 1, col_idx)].set_text_props(color='white', weight='bold')
            else:
                # Red tint for failing rows
                for j in range(len(headers)):
                    table[(i + 1, j)].set_facecolor('#FFEBEE')
                table[(i + 1, col_idx)].set_facecolor('#F44336')  # Darker red for status
                # Make text white for better contrast
                table[(i + 1, col_idx)].set_text_props(color='white', weight='bold')
        
        # Add title with quality status
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        title_color = '#2E7D32' if all_pass else '#D32F2F'
        title = f"Reporte de Calidad de Código\n{quality_status}\n{timestamp}"
        plt.title(title, fontsize=16, fontweight='bold', color=title_color, pad=20)
        
        # Add summary text
        passing_count = sum(1 for row in table_data if "✅" in row[-1])
        total_count = len(table_data)
        summary_text = f"Resumen: {passing_count}/{total_count} archivos pasan la calidad general"
        fig.text(0.5, 0.02, summary_text, ha='center', fontsize=12, 
                 bbox=dict(boxstyle="round,pad=0.3", facecolor='#E3F2FD' if all_pass else '#FFEBEE'))
        
        # Save image
        filename = f"quality_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        plt.savefig(filename, dpi=200, bbox_inches='tight', facecolor='white', 
                   edgecolor='none', pad_inches=0.3)
        print(f"\n📸 Tabla guardada como imagen: {filename}")
        print(f"📊 Resumen: {passing_count}/{total_count} archivos ({passing_count/total_count*100:.1f}%) pasan calidad")
        
        plt.close()
        
    except ImportError:
        print("\n⚠️  matplotlib no está instalado. No se puede guardar la tabla como imagen.")
        print("   Para instalar: pip install matplotlib")
    except Exception as e:
        print(f"\n❌ Error al guardar la tabla como imagen: {e}")

if __name__ == "__main__":
    main()