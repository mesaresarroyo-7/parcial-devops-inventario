#!/usr/bin/env python3
"""Proyecto parcial DevOps: inventario, análisis de datos y REST API HTTPS."""

import csv
import json
from pathlib import Path
from typing import Any, Dict, List

import requests
import yaml

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
REPORTS_DIR = BASE_DIR / "reports"


def load_json_inventory() -> List[Dict[str, Any]]:
    with open(DATA_DIR / "inventory.json", "r", encoding="utf-8") as file:
        inventory = json.load(file)
    if not isinstance(inventory, list):
        raise ValueError("El inventario JSON debe contener una lista de dispositivos")
    return inventory


def load_csv_services() -> List[Dict[str, str]]:
    with open(DATA_DIR / "services.csv", "r", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def load_yaml_config() -> Dict[str, Any]:
    with open(DATA_DIR / "config.yaml", "r", encoding="utf-8") as file:
        config = yaml.safe_load(file)
    required_keys = {"organization", "environment", "admin", "api_url"}
    missing = required_keys.difference(config)
    if missing:
        raise ValueError(f"Faltan claves en config.yaml: {', '.join(sorted(missing))}")
    return config


def check_rest_api(api_url: str) -> Dict[str, Any]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "devops-parcial-project",
    }
    try:
        response = requests.get(api_url, headers=headers, timeout=10)
        return {
            "url": api_url,
            "status_code": response.status_code,
            "success": response.ok,
            "content_type": response.headers.get("Content-Type", "unknown"),
            "message": "Solicitud completada",
        }
    except requests.exceptions.Timeout:
        return {"url": api_url, "status_code": None, "success": False, "error": "Tiempo de espera agotado"}
    except requests.exceptions.ConnectionError:
        return {"url": api_url, "status_code": None, "success": False, "error": "Error de conexión"}
    except requests.exceptions.RequestException as error:
        return {"url": api_url, "status_code": None, "success": False, "error": str(error)}


def diagnose_api_status(status_code: Any) -> str:
    if status_code is None:
        return "Sin respuesta HTTP: revisar conexión, DNS o disponibilidad del servicio."
    if 200 <= status_code <= 299:
        return "Solicitud correcta: el endpoint respondió exitosamente."
    if status_code == 400:
        return "400 Bad Request: revisar parámetros, payload o formato de la solicitud."
    if status_code == 401:
        return "401 Unauthorized: revisar token, API key o credenciales."
    if status_code == 403:
        return "403 Forbidden: revisar permisos o límites de consumo de la API."
    if status_code == 404:
        return "404 Not Found: revisar URL o endpoint solicitado."
    if 500 <= status_code <= 599:
        return "Error 5xx: falla del servidor, revisar logs o reintentar más tarde."
    return "Código no esperado: revisar documentación de la API."


def generate_report(inventory, services, config, api_result, invalid_api_result) -> Path:
    REPORTS_DIR.mkdir(exist_ok=True)
    report_path = REPORTS_DIR / "inventory_report.txt"
    active_devices = [device for device in inventory if device.get("status") == "active"]
    maintenance_devices = [device for device in inventory if device.get("status") == "maintenance"]

    with open(report_path, "w", encoding="utf-8") as report:
        report.write("REPORTE DE AUTOMATIZACIÓN DEVOPS\n")
        report.write("=" * 50 + "\n\n")
        report.write(f"Organización: {config['organization']}\n")
        report.write(f"Entorno: {config['environment']}\n")
        report.write(f"Administrador: {config['admin']}\n\n")

        report.write("DISPOSITIVOS INVENTARIADOS\n")
        report.write("-" * 50 + "\n")
        for device in inventory:
            report.write(f"{device['hostname']} | {device['ip']} | {device['type']} | {device['status']}\n")

        report.write("\nSERVICIOS REGISTRADOS\n")
        report.write("-" * 50 + "\n")
        for service in services:
            report.write(f"{service['service']} | Puerto {service['port']} | {service['protocol']} | {service['status']}\n")

        report.write("\nRESUMEN\n")
        report.write("-" * 50 + "\n")
        report.write(f"Total de dispositivos: {len(inventory)}\n")
        report.write(f"Dispositivos activos: {len(active_devices)}\n")
        report.write(f"Dispositivos en mantenimiento: {len(maintenance_devices)}\n")
        report.write(f"Total de servicios: {len(services)}\n\n")

        report.write("PRUEBA REST API HTTPS\n")
        report.write("-" * 50 + "\n")
        for label, result in (("Endpoint válido", api_result), ("Endpoint inválido controlado", invalid_api_result)):
            report.write(f"{label}\n")
            report.write(f"URL consultada: {result['url']}\n")
            report.write(f"Código HTTP: {result.get('status_code')}\n")
            report.write(f"Solicitud exitosa: {result['success']}\n")
            report.write(f"Tipo de contenido: {result.get('content_type', 'N/A')}\n")
            report.write(f"Diagnóstico: {diagnose_api_status(result.get('status_code'))}\n")
            if "error" in result:
                report.write(f"Error detectado: {result['error']}\n")
            report.write("\n")

    return report_path


def main() -> None:
    print("Iniciando automatización de inventario...")
    inventory = load_json_inventory()
    services = load_csv_services()
    config = load_yaml_config()
    api_result = check_rest_api(config["api_url"])
    invalid_api_result = check_rest_api(config["invalid_api_url"])
    report_path = generate_report(inventory, services, config, api_result, invalid_api_result)
    print("Automatización finalizada correctamente.")
    print(f"Reporte generado en: {report_path}")
    print(f"API principal: HTTP {api_result.get('status_code')} success={api_result['success']}")
    print(f"API de error controlado: HTTP {invalid_api_result.get('status_code')} success={invalid_api_result['success']}")


if __name__ == "__main__":
    main()
