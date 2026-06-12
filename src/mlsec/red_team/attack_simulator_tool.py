import json
import requests
from pydantic import BaseModel, Field
from typing import Type, List, Dict, Any
from crewai.tools import BaseTool

class APISimulatorSchema(BaseModel):
    """Esquema de entrada para la herramienta APISimulatorTool."""
    payloads: List[Dict[str, Any]] = Field(
        ..., 
        description="Lista de payloads maliciosos. Cada diccionario debe tener las claves: 'attack_type', 'payload' y 'target_field'."
    )

class APISimulatorTool(BaseTool):
    name: str = "api_simulator_tool"
    description: str = (
        "Útil para testear un modelo de ML inyectando payloads HTTP maliciosos. "
        "Recibe una lista de payloads, dispara peticiones HTTP contra la API local de predicción, "
        "y devuelve un reporte detallando cuáles ataques fueron bloqueados y cuáles evadieron al modelo (Falsos Negativos)."
    )
    args_schema: Type[BaseModel] = APISimulatorSchema

    def _run(self, payloads: List[Dict[str, Any]]) -> str:
        api_url = "http://localhost:5082/predict/http"
        
        if not payloads:
            return "No se encontraron payloads en la entrada."

        report = []
        total = len(payloads)
        evasions = 0
        blocked = 0
        
        for p in payloads:
            attack_type = p.get("attack_type", "Unknown")
            payload_str = p.get("payload", "")
            target_field = p.get("target_field", "body")
            
            # Construcción de la petición HTTP sintética basada en el target_field
            if target_field.lower() == "url":
                # Simulamos un GET con el payload en la query string
                req_method = "GET"
                req_url = f"http://dummy.com/vulnerable?q={payload_str}"
                req_body = ""
                content_length = 0
            else:
                # Simulamos un POST con el payload en el body
                req_method = "POST"
                req_url = "http://dummy.com/vulnerable"
                req_body = f"q={payload_str}"
                content_length = len(req_body)
                
            # Payload para nuestra API de predicción (predict/http)
            predict_req = {
                "method": req_method,
                "url": req_url,
                "content_length": content_length,
                "content_type": "application/x-www-form-urlencoded" if req_method == "POST" else "",
                "body": req_body
            }
            
            try:
                response = requests.post(api_url, json=predict_req, timeout=5)
                if response.status_code == 200:
                    result = response.json()
                    prediction = result.get("prediction", 0)
                    
                    if prediction == 1:
                        blocked += 1
                        status = "BLOQUEADO"
                    else:
                        evasions += 1
                        status = "EVADIÓ EL MODELO (FALSE NEGATIVE)"
                        
                    report.append(f"[{status}] Tipo: {attack_type} | Target: {target_field} | Payload: {payload_str}")
                else:
                    report.append(f"[ERROR API] HTTP {response.status_code} al testear payload: {payload_str}")
            except Exception as e:
                report.append(f"[ERROR CONEXIÓN] No se pudo contactar a {api_url}: {e}")
                
        # Generar reporte final para el Agente
        summary = (
            f"=== RESULTADOS DE LA SIMULACIÓN ===\n"
            f"Total de payloads testeados: {total}\n"
            f"Ataques Bloqueados (True Positives): {blocked}\n"
            f"Ataques que Evadieron el Modelo (False Negatives): {evasions}\n\n"
            f"Detalle de resultados:\n" + "\n".join(report)
        )
        
        return summary
