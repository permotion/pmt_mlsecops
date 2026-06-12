"""
Módulo del Red Team Automatizado: PayloadHunter
"""
import os
import json
from pydantic import BaseModel, Field
from typing import List

from crewai import Agent, Task, Crew, Process, LLM
from crewai_tools import ScrapeWebsiteTool

# Definición del esquema estricto de salida (JSON) para que el LLM no alucine formatos.
class Payload(BaseModel):
    attack_type: str = Field(description="El tipo de ataque web (ej. SQLi, XSS, Path Traversal)")
    payload: str = Field(description="El payload HTTP malicioso exacto extraído de la fuente")
    source: str = Field(description="La URL o nombre de la fuente de donde se extrajo")
    target_field: str = Field(description="El campo objetivo ideal (ej. url, body, header)")

class PayloadList(BaseModel):
    payloads: List[Payload] = Field(description="Lista de payloads maliciosos encontrados")


def run_payload_hunter_crew():
    """Ejecuta el Crew del PayloadHunter y devuelve un JSON estructurado."""
    
    # 1. Definición del LLM usando la clase nativa de CrewAI (basada en LiteLLM)
    # Como estás usando el proxy de Anthropic de Minimax, configuramos LiteLLM 
    # para que se comunique usando el protocolo de Anthropic.
    anthropic_api_key = os.environ.get("ANTHROPIC_AUTH_TOKEN", "")
    anthropic_base_url = os.environ.get("ANTHROPIC_BASE_URL", "https://api.minimax.io/anthropic")
    anthropic_model = os.environ.get("ANTHROPIC_MODEL", "MiniMax-M2.7")
    
    if not anthropic_api_key:
        print("ADVERTENCIA: ANTHROPIC_AUTH_TOKEN no configurada.")
        
    llm = LLM(
        model=f"anthropic/{anthropic_model}",
        api_key=anthropic_api_key,
        api_base=anthropic_base_url,
        temperature=0.2
    )
    
    # 2. Definición de Herramientas
    scrape_tool = ScrapeWebsiteTool()
    
    # 3. Definición del Agente
    payload_hunter = Agent(
        role="Cyber Threat Intelligence Analyst",
        goal="Identificar y extraer los payloads HTTP maliciosos más recientes y evasivos (SQLi, XSS, Path Traversal) desde fuentes públicas.",
        backstory="""
        Eres un cazador de amenazas de élite especializado en ataques a aplicaciones web y WAF evasion. 
        Te obsesiona estar al día con los últimos Zero-Days. Tienes una habilidad analítica superior 
        para leer repositorios técnicos y extraer exactamente la cadena de texto (el payload HTTP) 
        que el atacante envía en la URL o en el Body para vulnerar el sistema.
        No te interesan los escaneos de red, solo los payloads HTTP puros.
        """,
        verbose=True,
        allow_delegation=False,
        tools=[scrape_tool],
        llm=llm
    )
    
    # 3. Definición de la Tarea
    extraction_task = Task(
        description="""
        Investiga las siguientes fuentes públicas en busca de ejemplos de payloads HTTP maliciosos modernos:
        - https://github.com/swisskyrepo/PayloadsAllTheThings/tree/master/SQL%20Injection
        - https://github.com/swisskyrepo/PayloadsAllTheThings/tree/master/Directory%20Traversal
        - https://github.com/swisskyrepo/PayloadsAllTheThings/tree/master/XSS%20Injection
        
        Extrae al menos 3 payloads altamente evasivos o representativos de cada categoría (SQLi, Path Traversal y XSS).
        Asegúrate de copiar el payload EXACTO que se enviaría en un request HTTP.
        """,
        expected_output="Una lista de objetos JSON que contienen el attack_type, el payload exacto, la source y el target_field.",
        agent=payload_hunter,
        output_json=PayloadList
    )
    
    # 4. Creación del Crew
    crew = Crew(
        agents=[payload_hunter],
        tasks=[extraction_task],
        process=Process.sequential,
        verbose=True
    )
    
    # 5. Ejecución
    print("Iniciando PayloadHunter (Cyber Threat Intelligence)...")
    result = crew.kickoff()
    
    # crew.kickoff() devuelve un objeto CrewOutput. El raw o json_dict contendrá la data.
    try:
        # Intentamos parsear la salida estructurada
        if hasattr(result, "json_dict") and result.json_dict:
            return json.dumps(result.json_dict, indent=2)
        elif hasattr(result, "raw"):
            return result.raw
        else:
            return str(result)
    except Exception as e:
        print(f"Error procesando la salida: {e}")
        return str(result)

if __name__ == "__main__":
    # Para testing directo
    if not os.environ.get("ANTHROPIC_AUTH_TOKEN"):
        print("ERROR: La variable ANTHROPIC_AUTH_TOKEN no está configurada en tu entorno.")
        exit(1)
        
    print(run_payload_hunter_crew())
