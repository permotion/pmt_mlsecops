"""
Módulo principal del Red Team Automatizado.
Orquesta los agentes: PayloadHunter y AttackSimulator.
"""
import os
import json
from pydantic import BaseModel, Field
from typing import List

from crewai import Agent, Task, Crew, Process, LLM
from crewai_tools import ScrapeWebsiteTool

# Importar la herramienta del Simulador que acabamos de crear
from src.mlsec.red_team.attack_simulator_tool import APISimulatorTool

# ---------------------------------------------------------
# Esquemas Pydantic
# ---------------------------------------------------------
class Payload(BaseModel):
    attack_type: str = Field(description="El tipo de ataque web (ej. SQLi, XSS, Path Traversal)")
    payload: str = Field(description="El payload HTTP malicioso exacto extraído de la fuente")
    source: str = Field(description="La URL o nombre de la fuente de donde se extrajo")
    target_field: str = Field(description="El campo objetivo ideal (ej. url, body, header)")

class PayloadList(BaseModel):
    payloads: List[Payload] = Field(description="Lista de payloads maliciosos encontrados")

# ---------------------------------------------------------
# Configuración del LLM
# ---------------------------------------------------------
def get_llm():
    anthropic_api_key = os.environ.get("ANTHROPIC_AUTH_TOKEN", "")
    anthropic_base_url = os.environ.get("ANTHROPIC_BASE_URL", "https://api.minimax.io/anthropic")
    anthropic_model = os.environ.get("ANTHROPIC_MODEL", "MiniMax-M2.7")
    
    if not anthropic_api_key:
        print("ADVERTENCIA: ANTHROPIC_AUTH_TOKEN no configurada.")
        
    return LLM(
        model=f"anthropic/{anthropic_model}",
        api_key=anthropic_api_key,
        api_base=anthropic_base_url,
        temperature=0.2
    )

# ---------------------------------------------------------
# Orquestador Principal
# ---------------------------------------------------------
def run_red_team_crew():
    llm = get_llm()
    
    # Herramientas
    scrape_tool = ScrapeWebsiteTool()
    api_simulator_tool = APISimulatorTool()
    
    # ==========================================
    # AGENTE 1: Payload Hunter
    # ==========================================
    payload_hunter = Agent(
        role="Cyber Threat Intelligence Analyst",
        goal="Identificar y extraer los payloads HTTP maliciosos más recientes y evasivos (SQLi, XSS, Path Traversal) desde fuentes públicas.",
        backstory="""
        Eres un cazador de amenazas de élite especializado en ataques a aplicaciones web y WAF evasion. 
        Te obsesiona estar al día con los últimos Zero-Days. Tienes una habilidad analítica superior 
        para leer repositorios técnicos y extraer exactamente la cadena de texto (el payload HTTP) 
        que el atacante envía en la URL o en el Body para vulnerar el sistema.
        """,
        verbose=True,
        allow_delegation=False,
        tools=[scrape_tool],
        llm=llm
    )
    
    # Tarea 1: Recolectar Payloads (Output estructurado en JSON)
    extraction_task = Task(
        description="""
        Investiga ÚNICAMENTE los siguientes archivos de texto plano para extraer payloads maliciosos:
        - https://raw.githubusercontent.com/swisskyrepo/PayloadsAllTheThings/master/SQL%20Injection/Intruder/Auth_Bypass.txt
        - https://raw.githubusercontent.com/swisskyrepo/PayloadsAllTheThings/master/Directory%20Traversal/Intruder/directory_traversal.txt
        - https://raw.githubusercontent.com/swisskyrepo/PayloadsAllTheThings/master/XSS%20Injection/Intruders/xss_payloads_quick.txt
        
        Lee el contenido de esas tres URLs usando tu herramienta y extrae exactamente 2 payloads de cada categoría.
        Asegúrate de copiar el payload EXACTO que se enviaría en un request HTTP.
        
        REGLA ESTRICTA: Tu respuesta FINAL (Final Answer) debe ser ÚNICA y EXCLUSIVAMENTE el diccionario JSON. 
        PROHIBIDO escribir texto introductorio. PROHIBIDO escribir 'I will analyze...'. PROHIBIDO usar formato Markdown (```json). 
        SOLO debes devolver las llaves y el contenido del JSON. Si escribes texto conversacional, romperás el pipeline.
        """,
        expected_output='''Un string JSON válido con esta estructura exacta:
        {
          "payloads": [
            {"attack_type": "...", "payload": "...", "source": "...", "target_field": "..."}
          ]
        }''',
        agent=payload_hunter
    )

    # ==========================================
    # AGENTE 2: Attack Simulator
    # ==========================================
    attack_simulator = Agent(
        role="Ethical Hacker / Penetration Tester",
        goal="Lanzar ataques contra la API local de Machine Learning utilizando payloads pre-recolectados y descubrir cuáles evaden el modelo.",
        backstory="""
        Eres un experto en simulación de adversarios (Red Teaming). Tu especialidad es automatizar
        el envío de payloads HTTP maliciosos contra sistemas de seguridad (WAFs o Modelos de ML) para 
        comprobar su resiliencia. No te asusta ensuciarte las manos haciendo requests HTTP.
        """,
        verbose=True,
        allow_delegation=False,
        tools=[api_simulator_tool],
        llm=llm
    )
    
    # Tareas del Red Team
    
    import datetime
    import os
    os.makedirs("reports", exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    report_filename = f"reports/red_team_report_{timestamp}.md"
    
    simulation_task = Task(
        description="""
        Has recibido un JSON generado por el PayloadHunter con payloads maliciosos base.
        
        REGLA DE ORO: ¡ES OBLIGATORIO QUE USES LA HERRAMIENTA 'api_simulator_tool'! No puedes simplemente inventar el resultado. DEBES llamar a la herramienta.
        
        Tu objetivo es comportarte como un GENERATOR en un esquema GAN (Macro-GAN Semántica):
        
        1. DEBES LLAMAR A LA HERRAMIENTA 'api_simulator_tool' pasando la lista de payloads exactos que recibiste. Observa los resultados devueltos por la herramienta.
        2. Analiza el resultado de la herramienta. Si el WAF los bloquea (resultado: BLOQUEADO), el modelo defensivo (Discriminator) ganó.
        3. DEBES MUTAR ITERATIVAMENTE LOS PAYLOADS BLOQUEADOS. Si fallaron, aplica técnicas de evasión 
           (URL encoding, reemplazar espacios por /**/, cambiar mayúsculas/minúsculas ej. sElEcT, agregar null bytes, etc).
        4. Construye una nueva lista de payloads con tus mutaciones y vuelve a LLAMAR A LA HERRAMIENTA 'api_simulator_tool' con la nueva lista.
        5. Repite este ciclo de Feedback (Feedback Loop) llamando a la herramienta hasta que logres que los ataques EVADAN EL MODELO 
           (Falsos Negativos) o hayas intentado al menos 3 mutaciones.
           
        IMPORTANTE: Tu Action Input para la herramienta debe ser directamente el array de payloads.
        Ejemplo: {"payloads": [{"attack_type": "...", "payload": "...", "target_field": "..."}]}
        
        Al finalizar las iteraciones con la herramienta, redacta un informe ejecutivo.
        """,
        expected_output="Un reporte en MARKDOWN detallando el Feedback Loop. ADEMÁS, DEBES incluir obligatoriamente al final una sección llamada '🚀 MINI RESUMEN EJECUTIVO' que contenga: 1) Total de Payloads Probados. 2) Total de Bloqueos (403) con 1 ejemplo. 3) Total de Mutaciones Realizadas. 4) Total de Evasiones Exitosas (200) detallando los ejemplos EXACTOS de los payloads mutados que lograron evadir el WAF.",
        agent=attack_simulator,
        context=[extraction_task], # Esto asegura que reciba el JSON del PayloadHunter
        output_file=report_filename
    )
    
    # ==========================================
    # CREW
    # ==========================================
    crew = Crew(
        agents=[payload_hunter, attack_simulator],
        tasks=[extraction_task, simulation_task],
        process=Process.sequential,
        verbose=True
    )
    
    print("Iniciando Red Team Automatizado (PayloadHunter -> AttackSimulator)...")
    result = crew.kickoff()
    
    return str(result)

if __name__ == "__main__":
    if not os.environ.get("ANTHROPIC_AUTH_TOKEN"):
        print("ERROR: La variable ANTHROPIC_AUTH_TOKEN no está configurada en tu entorno.")
        exit(1)
        
    final_report = run_red_team_crew()
    
    print("\n\n" + "="*50)
    print("INFORME FINAL DEL RED TEAM")
    print("="*50)
    print(final_report)
