#!/usr/bin/env python3
"""
Script de ejemplo para usar la API de PR Reviewer
"""
import requests
import json
import sys


def analyze_pr(pr_url: str, api_url: str = "http://localhost:8000"):
    """
    Analiza un Pull Request usando la API
    
    Args:
        pr_url: URL del Pull Request a analizar
        api_url: URL base de la API (default: http://localhost:8000)
    
    Returns:
        dict: Resultado del análisis
    """
    endpoint = f"{api_url}/analyze-pr"
    
    payload = {
        "pr_url": pr_url
    }
    
    print(f"🚀 Analizando PR: {pr_url}")
    print(f"📡 Enviando solicitud a {endpoint}...")
    
    try:
        response = requests.post(endpoint, json=payload, timeout=180)
        response.raise_for_status()
        
        result = response.json()
        
        print("\n" + "="*60)
        print("📊 RESULTADO DEL ANÁLISIS")
        print("="*60)
        print(f"Status: {result['status']}")
        print(f"PR: #{result['pr_number']}")
        print(f"Repositorio: {result['empresa']}/{result['proyecto']}")
        print(f"Elegible para merge: {'✅ Sí' if result['eligible'] else '❌ No'}")
        print(f"Archivos analizados: {len(result['quality_report']['file_results'])}")
        print(f"Estado global: {result['quality_report']['global_validator']['status']}")
        print(f"Directorio de salida: {result['pr_dir']}")
        
        print("\n📋 ARCHIVOS ANALIZADOS:")
        print("-" * 60)
        for file_result in result['quality_report']['file_results']:
            status = "✅" if file_result['thresholds']['overall_pass'] else "❌"
            print(f"{status} {file_result['filename']}")
            print(f"   Pylint: {file_result['pylint_score']:.2f} | "
                  f"Flake8: {file_result['flake8_score']} | "
                  f"Mypy: {file_result['mypy_score']}")
        
        print("\n" + "="*60)
        
        return result
        
    except requests.exceptions.Timeout:
        print("❌ Error: Timeout esperando respuesta de la API")
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(f"❌ Error al comunicarse con la API: {e}")
        sys.exit(1)
    except json.JSONDecodeError:
        print("❌ Error: Respuesta de la API no es JSON válido")
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python example_api_usage.py <PR_URL> [API_URL]")
        print("\nEjemplo:")
        print("  python example_api_usage.py https://github.com/owner/repo/pull/123")
        print("  python example_api_usage.py https://github.com/owner/repo/pull/123 http://localhost:8000")
        sys.exit(1)
    
    pr_url = sys.argv[1]
    api_url = sys.argv[2] if len(sys.argv) > 2 else "http://localhost:8000"
    
    result = analyze_pr(pr_url, api_url)
    
    # Guardar resultado completo en archivo
    output_file = f"pr_analysis_{result['pr_number']}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Resultado completo guardado en: {output_file}")
