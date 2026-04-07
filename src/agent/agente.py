import os
import warnings
warnings.filterwarnings("ignore")
os.environ["ANONYMIZED_TELEMETRY"] = "False"

from dotenv import load_dotenv
load_dotenv()

# ── Langfuse observabilidad ────────────────────────────────
from langfuse import Langfuse
langfuse = Langfuse(
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    host=os.getenv("LANGFUSE_HOST", "http://localhost:3000"),
)

def _trace(pregunta: str, intencion: str, respuesta: str):
    """Registra una traza en Langfuse v2."""
    try:
        trace = langfuse.trace(
            name="aduana-gpt-consulta",
            input=pregunta,
            output=respuesta,
            metadata={"intencion": intencion}
        )
        trace.span(
            name="clasificador",
            input=pregunta,
            output=intencion,
        )
        trace.span(
            name="sintesis",
            input=pregunta,
            output=respuesta,
        )
        langfuse.flush()
    except Exception:
        pass

from typing import TypedDict
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END
from src.prompts.system_prompt import SYSTEM_PROMPT
from src.tools.herramientas_rag import (
    HERRAMIENTAS,
    buscar_ley_28008,
    buscar_procedimientos_fiscalizacion,
    buscar_mercancias_prohibidas_restringidas,
    buscar_sanciones_multas,
    buscar_procedimientos_despacho,
    buscar_arancel,
    buscar_normas_asociadas,
    buscar_equipaje_viajeros,
    buscar_procedimientos_recaudacion,
    buscar_normas_generales,
    buscar_ley_general_aduanas,
)

# ── LLM ───────────────────────────────────────────────────
llm = ChatGroq(
    model=os.getenv("LLM_MODEL", "llama-3.3-70b-versatile"),
    api_key=os.getenv("GROQ_API_KEY"),
    temperature=0.1,
    max_tokens=1500,
)

# ── Estado del grafo ───────────────────────────────────────
class EstadoAgente(TypedDict):
    pregunta:   str
    intencion:  str
    contexto:   str
    respuesta:  str

# ── Nodo 1: Clasificador de intención ─────────────────────
PROMPT_CLASIFICADOR = """Clasifica la siguiente consulta aduanera en UNA de estas categorías:

DELITO         → contrabando, defraudación, receptación, tráfico ilícito, sanciones penales
FISCALIZACION  → ACE, aforo, inmovilización, incautación, precintos, fiscalización
DESPACHO       → importación, exportación, drawback, depósito, courier, postales, OEA, valoración
ARANCEL        → partida arancelaria, tasa, derecho ad valorem, clasificación de mercancía
PROHIBICION    → mercancía prohibida, restringida, SENASA, SERFOR, DIGEMID, PRODUCE
SANCION        → multa, infracción, comiso, suspensión, tabla de sanciones
VIAJERO        → equipaje, franquicia, menaje de casa, dinero en efectivo, turismo
RECAUDACION    → deuda tributaria, reclamo, devolución, garantía, fraccionamiento
GENERAL        → procedimiento administrativo, ética, transparencia, otros

Responde SOLO con la palabra de la categoría, sin explicación.

Consulta: {pregunta}"""

def nodo_clasificador(estado: EstadoAgente) -> EstadoAgente:
    """Clasifica la intención de la consulta."""
    resp = llm.invoke([
        SystemMessage(content="Eres un clasificador de consultas aduaneras. Responde solo con la categoría."),
        HumanMessage(content=PROMPT_CLASIFICADOR.format(pregunta=estado["pregunta"]))
    ])
    intencion = resp.content.strip().upper()
    categorias_validas = {
        "DELITO", "FISCALIZACION", "DESPACHO", "ARANCEL",
        "PROHIBICION", "SANCION", "VIAJERO", "RECAUDACION", "GENERAL"
    }
    if intencion not in categorias_validas:
        intencion = "GENERAL"
    return {**estado, "intencion": intencion}

# ── Nodo 2: Recuperación especializada ────────────────────
HERRAMIENTAS_POR_INTENCION = {
    "DELITO":       [buscar_ley_28008,                    buscar_sanciones_multas],
    "FISCALIZACION":[buscar_procedimientos_fiscalizacion, buscar_ley_general_aduanas],
    "DESPACHO":     [buscar_procedimientos_despacho,      buscar_ley_general_aduanas],
    "ARANCEL":      [buscar_arancel,                      buscar_procedimientos_despacho],
    "PROHIBICION":  [buscar_mercancias_prohibidas_restringidas, buscar_ley_28008],
    "SANCION":      [buscar_sanciones_multas,             buscar_ley_general_aduanas],
    "VIAJERO":      [buscar_equipaje_viajeros,            buscar_normas_asociadas],
    "RECAUDACION":  [buscar_procedimientos_recaudacion,   buscar_ley_general_aduanas],
    "GENERAL":      [buscar_normas_generales,             buscar_procedimientos_despacho],
}

def nodo_recuperacion(estado: EstadoAgente) -> EstadoAgente:
    """Ejecuta las herramientas RAG especializadas según la intención."""
    herramientas = HERRAMIENTAS_POR_INTENCION.get(
        estado["intencion"],
        [buscar_procedimientos_despacho]
    )
    contexto = ""
    for herramienta in herramientas:
        resultado = herramienta.invoke(estado["pregunta"])
        nombre = herramienta.name
        contexto += f"\n=== {nombre} ===\n{resultado}\n"
    return {**estado, "contexto": contexto}

# ── Nodo 3: Síntesis y generación ─────────────────────────
PROMPT_SINTESIS = """{system_prompt}

CONTEXTO NORMATIVO RECUPERADO:
{contexto}

CONSULTA DEL USUARIO:
{pregunta}

Genera una respuesta estructurada siguiendo el formato del system prompt.
Usa la información del contexto normativo para citar artículos exactos."""

def nodo_sintesis(estado: EstadoAgente) -> EstadoAgente:
    """Sintetiza el contexto y genera la respuesta final."""
    prompt = PROMPT_SINTESIS.format(
        system_prompt=SYSTEM_PROMPT,
        contexto=estado["contexto"],
        pregunta=estado["pregunta"]
    )
    resp = llm.invoke([HumanMessage(content=prompt)])
    respuesta = resp.content.strip()
    if "[INSTRUCCIÓN" in respuesta:
        respuesta = respuesta[:respuesta.find("[INSTRUCCIÓN")].strip()
    return {**estado, "respuesta": respuesta}

# ── Construcción del grafo ─────────────────────────────────
grafo = StateGraph(EstadoAgente)
grafo.add_node("clasificador", nodo_clasificador)
grafo.add_node("recuperacion", nodo_recuperacion)
grafo.add_node("sintesis",     nodo_sintesis)

grafo.set_entry_point("clasificador")
grafo.add_edge("clasificador", "recuperacion")
grafo.add_edge("recuperacion", "sintesis")
grafo.add_edge("sintesis",     END)

agente_compilado = grafo.compile()

# ── Función principal ──────────────────────────────────────
def consultar(pregunta: str) -> str:
    """Consulta al agente ADUANA-GPT con grafo LangGraph + Langfuse."""
    try:
        estado_inicial = {
            "pregunta":  pregunta,
            "intencion": "",
            "contexto":  "",
            "respuesta": "",
        }
        resultado = agente_compilado.invoke(estado_inicial)
        respuesta = resultado["respuesta"]

        # Registrar en Langfuse
        _trace(pregunta, resultado["intencion"], respuesta)

        return respuesta

    except Exception as e:
        error = str(e)
        if "413" in error or "rate_limit" in error.lower():
            return ("⚠️ Límite de tokens de Groq alcanzado. "
                    "Por favor espera unos segundos e intenta de nuevo.")
        return f"Error al procesar la consulta: {error[:200]}"