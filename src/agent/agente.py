import os
import warnings
warnings.filterwarnings("ignore")
os.environ["ANONYMIZED_TELEMETRY"] = "False"

from dotenv import load_dotenv
load_dotenv()

from langfuse import Langfuse
langfuse = Langfuse(
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    host=os.getenv("LANGFUSE_HOST", "http://localhost:3000"),
)

def _trace(pregunta: str, intencion: str, respuesta: str):
    try:
        trace = langfuse.trace(
            name="aduana-gpt-consulta",
            input=pregunta,
            output=respuesta,
            metadata={"intencion": intencion}
        )
        trace.span(name="clasificador", input=pregunta, output=intencion)
        trace.span(name="sintesis",     input=pregunta, output=respuesta)
        langfuse.flush()
    except Exception:
        pass

from typing import TypedDict
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END
from src.prompts.system_prompt import SYSTEM_PROMPT
from src.tools.herramientas_rag import (
    buscar_ley_28008,
    buscar_ley_general_aduanas,
    buscar_procedimientos_fiscalizacion,
    buscar_procedimientos_despacho,
    buscar_procedimientos_recaudacion,
    buscar_arancel,
    buscar_normas_asociadas,
    buscar_normas_generales,
    buscar_equipaje_viajeros,
    buscar_mercancias_prohibidas_restringidas,
    buscar_sanciones_multas,
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
    pregunta:  str
    intencion: str
    contexto:  str
    respuesta: str

# ══════════════════════════════════════════════════════════
# NODO 1 — CLASIFICADOR DE INTENCIÓN
# 5 dominios del negocio aduanero peruano
# ══════════════════════════════════════════════════════════
PROMPT_CLASIFICADOR = """Clasifica la consulta aduanera en UNO de estos 5 dominios:

DELITOS      → contrabando, defraudación de rentas, receptación,
               tráfico ilícito de mercancías, Ley 28008, delitos penales

CONTROL      → ACE (Acción de Control Extraordinario), aforo,
               inmovilización, incautación, precintos, inspección
               no intrusiva, fiscalización posterior al despacho

DESPACHO     → importación, exportación, regímenes aduaneros,
               drawback, depósito, tránsito, valoración OMC,
               arancel, partidas, mercancías prohibidas y restringidas,
               agente de aduana, abandono legal, despacho anticipado

RECAUDACION  → tributos aduaneros, deuda tributaria, garantías,
               reclamos, devoluciones, fraccionamiento, multas
               administrativas, sanciones, tabla de sanciones

ORIENTACION  → equipaje de viajeros, franquicia arancelaria,
               dinero en efectivo, menaje de casa, ciudadanos,
               compras por internet, medicamentos, courier,
               envíos postales, preguntas generales

Responde SOLO con la palabra del dominio, sin explicación.

Consulta: {pregunta}"""

def nodo_clasificador(estado: EstadoAgente) -> EstadoAgente:
    resp = llm.invoke([
        SystemMessage(content="Eres un clasificador de consultas aduaneras. Responde solo con el dominio."),
        HumanMessage(content=PROMPT_CLASIFICADOR.format(pregunta=estado["pregunta"]))
    ])
    intencion = resp.content.strip().upper()
    dominios_validos = {"DELITOS", "CONTROL", "DESPACHO", "RECAUDACION", "ORIENTACION"}
    if intencion not in dominios_validos:
        intencion = "DESPACHO"
    return {**estado, "intencion": intencion}

# ── Enrutador condicional ──────────────────────────────────
def enrutar(estado: EstadoAgente) -> str:
    return estado["intencion"]

# ══════════════════════════════════════════════════════════
# NODO 2A — RECUPERACIÓN DELITOS
# Ley 28008: contrabando, defraudación, receptación
# ══════════════════════════════════════════════════════════
def nodo_delitos(estado: EstadoAgente) -> EstadoAgente:
    r1 = buscar_ley_28008.invoke(estado["pregunta"])
    r2 = buscar_sanciones_multas.invoke(estado["pregunta"])
    contexto = f"=== Ley 28008 Delitos Aduaneros ===\n{r1}\n\n=== Sanciones ===\n{r2}"
    return {**estado, "contexto": contexto}

# ══════════════════════════════════════════════════════════
# NODO 2B — RECUPERACIÓN CONTROL
# ACE, aforo, inmovilización, incautación, fiscalización
# ══════════════════════════════════════════════════════════
def nodo_control(estado: EstadoAgente) -> EstadoAgente:
    r1 = buscar_procedimientos_fiscalizacion.invoke(estado["pregunta"])
    r2 = buscar_ley_general_aduanas.invoke(estado["pregunta"])
    contexto = f"=== Procedimientos Control y Fiscalización ===\n{r1}\n\n=== Ley General de Aduanas ===\n{r2}"
    return {**estado, "contexto": contexto}

# ══════════════════════════════════════════════════════════
# NODO 2C — RECUPERACIÓN DESPACHO
# Regímenes, arancel, valoración, prohibidas, restringidas
# ══════════════════════════════════════════════════════════
def nodo_despacho(estado: EstadoAgente) -> EstadoAgente:
    r1 = buscar_procedimientos_despacho.invoke(estado["pregunta"])
    r2 = buscar_arancel.invoke(estado["pregunta"])
    r3 = buscar_mercancias_prohibidas_restringidas.invoke(estado["pregunta"])
    contexto = (f"=== Procedimientos de Despacho ===\n{r1}\n\n"
                f"=== Arancel de Aduanas 2022 ===\n{r2}\n\n"
                f"=== Mercancías Prohibidas y Restringidas ===\n{r3}")
    return {**estado, "contexto": contexto}

# ══════════════════════════════════════════════════════════
# NODO 2D — RECUPERACIÓN RECAUDACIÓN
# Tributos, deuda, garantías, sanciones administrativas
# ══════════════════════════════════════════════════════════
def nodo_recaudacion(estado: EstadoAgente) -> EstadoAgente:
    r1 = buscar_procedimientos_recaudacion.invoke(estado["pregunta"])
    r2 = buscar_sanciones_multas.invoke(estado["pregunta"])
    r3 = buscar_ley_general_aduanas.invoke(estado["pregunta"])
    contexto = (f"=== Procedimientos de Recaudación ===\n{r1}\n\n"
                f"=== Sanciones y Multas ===\n{r2}\n\n"
                f"=== Ley General de Aduanas ===\n{r3}")
    return {**estado, "contexto": contexto}

# ══════════════════════════════════════════════════════════
# NODO 2E — RECUPERACIÓN ORIENTACIÓN
# Viajeros, equipaje, ciudadanos, normas generales
# ══════════════════════════════════════════════════════════
def nodo_orientacion(estado: EstadoAgente) -> EstadoAgente:
    r1 = buscar_equipaje_viajeros.invoke(estado["pregunta"])
    r2 = buscar_normas_asociadas.invoke(estado["pregunta"])
    r3 = buscar_normas_generales.invoke(estado["pregunta"])
    contexto = (f"=== Reglamentos para Viajeros y Ciudadanos ===\n{r1}\n\n"
                f"=== Normas Asociadas ===\n{r2}\n\n"
                f"=== Normas Generales ===\n{r3}")
    return {**estado, "contexto": contexto}

# ══════════════════════════════════════════════════════════
# NODO 3 — SÍNTESIS
# Llama 3.3 70B genera respuesta estructurada
# ══════════════════════════════════════════════════════════
PROMPT_SINTESIS = """{system_prompt}

DOMINIO IDENTIFICADO: {intencion}

CONTEXTO NORMATIVO RECUPERADO:
{contexto}

CONSULTA DEL USUARIO:
{pregunta}

Genera una respuesta estructurada siguiendo el formato del system prompt.
Cita artículos exactos del contexto normativo."""

def nodo_sintesis(estado: EstadoAgente) -> EstadoAgente:
    prompt = PROMPT_SINTESIS.format(
        system_prompt=SYSTEM_PROMPT,
        intencion=estado["intencion"],
        contexto=estado["contexto"],
        pregunta=estado["pregunta"]
    )
    resp = llm.invoke([HumanMessage(content=prompt)])
    respuesta = resp.content.strip()
    return {**estado, "respuesta": respuesta}

# ══════════════════════════════════════════════════════════
# CONSTRUCCIÓN DEL GRAFO CON ARISTAS CONDICIONALES
# ══════════════════════════════════════════════════════════
grafo = StateGraph(EstadoAgente)

# Agregar nodos
grafo.add_node("clasificador",  nodo_clasificador)
grafo.add_node("delitos",       nodo_delitos)
grafo.add_node("control",       nodo_control)
grafo.add_node("despacho",      nodo_despacho)
grafo.add_node("recaudacion",   nodo_recaudacion)
grafo.add_node("orientacion",   nodo_orientacion)
grafo.add_node("sintesis",      nodo_sintesis)

# Punto de entrada
grafo.set_entry_point("clasificador")

# Aristas condicionales: clasificador → nodo especializado
grafo.add_conditional_edges(
    "clasificador",
    enrutar,
    {
        "DELITOS":     "delitos",
        "CONTROL":     "control",
        "DESPACHO":    "despacho",
        "RECAUDACION": "recaudacion",
        "ORIENTACION": "orientacion",
    }
)

# Todos los nodos especializados → síntesis → END
for nodo in ["delitos", "control", "despacho", "recaudacion", "orientacion"]:
    grafo.add_edge(nodo, "sintesis")
grafo.add_edge("sintesis", END)

agente_compilado = grafo.compile()

# ══════════════════════════════════════════════════════════
# FUNCIÓN PRINCIPAL
# ══════════════════════════════════════════════════════════
def consultar(pregunta: str) -> str:
    """Consulta al agente ADUANA-GPT con grafo LangGraph + aristas condicionales."""
    try:
        estado_inicial = {
            "pregunta":  pregunta,
            "intencion": "",
            "contexto":  "",
            "respuesta": "",
        }
        resultado = agente_compilado.invoke(estado_inicial)
        respuesta = resultado["respuesta"]
        _trace(pregunta, resultado["intencion"], respuesta)
        return respuesta

    except Exception as e:
        error = str(e)
        if "413" in error or "rate_limit" in error.lower():
            return ("⚠️ Límite de tokens de Groq alcanzado. "
                    "Por favor espera unos segundos e intenta de nuevo.")
        return f"Error al procesar la consulta: {error[:200]}"