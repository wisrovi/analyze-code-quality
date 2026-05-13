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

def get_batch_api_response(files_data):
    """Get batch API response for multiple files."""
    response = requests.post("http://localhost:8032/analyze-batch-code-quality", json={"files": files_data})
    if response.status_code == 200:
        return response.json()
    return {"table_data": [], "global_validator": {"all_files_pass": False}}

def calculate_complexity_score(metrics):
    if not metrics:
        return 0
    complexities = [m["complexity"] for m in metrics]
    return sum(complexities) / len(complexities) if complexities else 0

def main():
    files = [f for f in os.listdir(TEST_DIR) if f.endswith(".py")]
    
    # Prepare files data for batch API
    files_data = []
    for file in files:
        file_path = os.path.join(TEST_DIR, file)
        with open(file_path, "r") as f:
            code = f.read()
        files_data.append({"filename": file, "code": code})
    
    # Get batch API response
    batch_response = get_batch_api_response(files_data)
    
    # Extract data from response
    table_data = batch_response.get("table_data", [])
    headers = batch_response.get("headers", [])
    global_validator = batch_response.get("global_validator", {})
    
    # Debug info
    print(f"📊 API Response: {len(table_data)} filas, {len(headers)} columnas")
    print(f"🔍 Global validator: {global_validator}")
    
    # Print table to console
    print(tabulate(table_data, headers=headers, tablefmt="grid"))
    
    # Save quality summary as JSON
    save_batch_quality_summary_json(batch_response)
    
    # Save table as image
    save_table_as_image(table_data, headers, global_validator)

def save_batch_quality_summary_json(batch_response):
    """Save batch quality summary as JSON file."""
    try:
        global_validator = batch_response.get("global_validator", {})
        all_files_pass = global_validator.get("all_files_pass", False)
        
        # Create summary data with only the required field
        summary = {
            "group_files_authorized": all_files_pass
        }
        
        # Save JSON file (overwrite existing)
        filename = "batch_quality_summary.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        print(f"\n📄 Resumen batch guardado como JSON: {filename}")
        print(f"📊 Estado global: {global_validator.get('status', 'Unknown')} ({global_validator.get('passing_count', 0)}/{global_validator.get('total_count', 0)})")
        
    except Exception as e:
        print(f"\n❌ Error al guardar JSON batch: {e}")

def save_table_as_image(table_data, headers, global_validator=None):
    """Save quality report table as an image file."""
    try:
        # Calculate overall quality status
        if global_validator:
            all_pass = global_validator.get("all_files_pass", False)
            quality_status = global_validator.get("status", "❌ ALGUNOS FALLAN CALIDAD")
        else:
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
        if headers:  # Check if headers is not empty
            for i in range(len(headers)):
                table[(0, i)].set_facecolor('#2E7D32')
                table[(0, i)].set_text_props(weight='bold', color='white')
        
        # Color coding for rows based on quality status
        if table_data:  # Check if table_data is not empty
            for i, row in enumerate(table_data):
                col_idx = len(headers) - 1  # Last column (Calidad General)
                if "✅" in str(row[col_idx]):
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
        if global_validator:
            passing_count = global_validator.get("passing_count", 0)
            total_count = global_validator.get("total_count", 0)
        else:
            passing_count = sum(1 for row in table_data if "✅" in row[-1])
            total_count = len(table_data)
        
        summary_text = f"Resumen: {passing_count}/{total_count} archivos pasan la calidad general"
        fig.text(0.5, 0.02, summary_text, ha='center', fontsize=12, 
                 bbox=dict(boxstyle="round,pad=0.3", facecolor='#E3F2FD' if all_pass else '#FFEBEE'))
        
        # Save image (overwrite existing)
        filename = "quality_report.png"
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