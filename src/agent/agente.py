import os
import warnings
warnings.filterwarnings("ignore")
os.environ["ANONYMIZED_TELEMETRY"] = "False"
from langgraph.checkpoint.memory import MemorySaver
from dotenv import load_dotenv
load_dotenv()

try:
    from langfuse.langchain import CallbackHandler as _LFHandler
    _LANGFUSE_AVAILABLE = True
except ImportError:
    _LFHandler = None
    _LANGFUSE_AVAILABLE = False

_LANGFUSE_CFG = dict(
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
)

def _get_trace_id(handler) -> str | None:
    if handler is None:
        return None
    tid = getattr(handler, "last_trace_id", None)
    if tid:
        return tid
    for attr in ("get_trace_id", "get_trace_url"):
        fn = getattr(handler, attr, None)
        if fn:
            try:
                val = fn()
                if val:
                    return val.rstrip("/").split("/")[-1]
            except Exception:
                pass
    return None

def _crear_handler(thread_id: str, user_id: str | None):
    if not _LANGFUSE_AVAILABLE:
        return None
    if not (_LANGFUSE_CFG["public_key"] and _LANGFUSE_CFG["secret_key"]):
        return None
    try:
        return _LFHandler()
    except Exception as e:
        print(f"[Langfuse] handler error: {e}", flush=True)
        return None

from concurrent.futures import ThreadPoolExecutor
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
    max_tokens=1200,
)

# ── Estado del grafo ───────────────────────────────────────
class EstadoAgente(TypedDict):
    pregunta:  str
    intencion: str
    contexto:  str
    respuesta: str
    historial: list

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
    p = estado["pregunta"]
    with ThreadPoolExecutor(max_workers=2) as ex:
        f1 = ex.submit(buscar_ley_28008.invoke, p)
        f2 = ex.submit(buscar_sanciones_multas.invoke, p)
        r1, r2 = f1.result(), f2.result()
    contexto = f"=== Ley 28008 Delitos Aduaneros ===\n{r1}\n\n=== Sanciones ===\n{r2}"
    return {**estado, "contexto": contexto}

# ══════════════════════════════════════════════════════════
# NODO 2B — RECUPERACIÓN CONTROL
# ACE, aforo, inmovilización, incautación, fiscalización
# ══════════════════════════════════════════════════════════
def nodo_control(estado: EstadoAgente) -> EstadoAgente:
    p = estado["pregunta"]
    with ThreadPoolExecutor(max_workers=2) as ex:
        f1 = ex.submit(buscar_procedimientos_fiscalizacion.invoke, p)
        f2 = ex.submit(buscar_ley_general_aduanas.invoke, p)
        r1, r2 = f1.result(), f2.result()
    contexto = f"=== Procedimientos Control y Fiscalización ===\n{r1}\n\n=== Ley General de Aduanas ===\n{r2}"
    return {**estado, "contexto": contexto}

# ══════════════════════════════════════════════════════════
# NODO 2C — RECUPERACIÓN DESPACHO
# Regímenes, arancel, valoración, prohibidas, restringidas
# ══════════════════════════════════════════════════════════
def nodo_despacho(estado: EstadoAgente) -> EstadoAgente:
    p = estado["pregunta"]
    with ThreadPoolExecutor(max_workers=3) as ex:
        f1 = ex.submit(buscar_procedimientos_despacho.invoke, p)
        f2 = ex.submit(buscar_arancel.invoke, p)
        f3 = ex.submit(buscar_mercancias_prohibidas_restringidas.invoke, p)
        r1, r2, r3 = f1.result(), f2.result(), f3.result()
    contexto = (f"=== Procedimientos de Despacho ===\n{r1}\n\n"
                f"=== Arancel de Aduanas 2022 ===\n{r2}\n\n"
                f"=== Mercancías Prohibidas y Restringidas ===\n{r3}")
    return {**estado, "contexto": contexto}

# ══════════════════════════════════════════════════════════
# NODO 2D — RECUPERACIÓN RECAUDACIÓN
# Tributos, deuda, garantías, sanciones administrativas
# ══════════════════════════════════════════════════════════
def nodo_recaudacion(estado: EstadoAgente) -> EstadoAgente:
    p = estado["pregunta"]
    with ThreadPoolExecutor(max_workers=3) as ex:
        f1 = ex.submit(buscar_procedimientos_recaudacion.invoke, p)
        f2 = ex.submit(buscar_sanciones_multas.invoke, p)
        f3 = ex.submit(buscar_ley_general_aduanas.invoke, p)
        r1, r2, r3 = f1.result(), f2.result(), f3.result()
    contexto = (f"=== Procedimientos de Recaudación ===\n{r1}\n\n"
                f"=== Sanciones y Multas ===\n{r2}\n\n"
                f"=== Ley General de Aduanas ===\n{r3}")
    return {**estado, "contexto": contexto}

# ══════════════════════════════════════════════════════════
# NODO 2E — RECUPERACIÓN ORIENTACIÓN
# Viajeros, equipaje, ciudadanos, normas generales
# ══════════════════════════════════════════════════════════
def nodo_orientacion(estado: EstadoAgente) -> EstadoAgente:
    p = estado["pregunta"]
    with ThreadPoolExecutor(max_workers=3) as ex:
        f1 = ex.submit(buscar_equipaje_viajeros.invoke, p)
        f2 = ex.submit(buscar_normas_asociadas.invoke, p)
        f3 = ex.submit(buscar_normas_generales.invoke, p)
        r1, r2, r3 = f1.result(), f2.result(), f3.result()
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

HISTORIAL DE CONVERSACION:
{historial}

CONTEXTO NORMATIVO RECUPERADO:
{contexto}

CONSULTA ACTUAL:
{pregunta}

Genera una respuesta estructurada. Si el historial tiene contexto relevante, 
úsalo para dar una respuesta más precisa y coherente."""

_MAX_CONTEXTO = 3800   # chars — ~950 tokens, deja margen para prompt+respuesta
_MAX_REINTENTOS = 2

def _truncar_contexto(ctx: str) -> str:
    if len(ctx) <= _MAX_CONTEXTO:
        return ctx
    # Recortar cada sección proporcionalmente en vez de cortar a mitad
    import re as _re
    partes = _re.split(r'(=== .+? ===\n?)', ctx)
    resultado, budget = "", _MAX_CONTEXTO
    for p in partes:
        if len(p) <= budget:
            resultado += p
            budget -= len(p)
        else:
            resultado += p[:budget] + "\n[...contexto truncado]"
            break
    return resultado

def nodo_sintesis(estado: EstadoAgente) -> EstadoAgente:
    historial_texto = ""
    for msg in estado.get("historial", []):
        rol = "Usuario" if msg["rol"] == "user" else "Agente"
        historial_texto += f"{rol}: {msg['contenido']}\n"

    contexto_seguro = _truncar_contexto(estado["contexto"])

    prompt = PROMPT_SINTESIS.format(
        system_prompt=SYSTEM_PROMPT,
        intencion=estado["intencion"],
        historial=historial_texto if historial_texto else "Sin historial previo.",
        contexto=contexto_seguro,
        pregunta=estado["pregunta"]
    )

    import time as _time
    ultimo_error = None
    for intento in range(_MAX_REINTENTOS + 1):
        try:
            resp = llm.invoke([HumanMessage(content=prompt)])
            break
        except Exception as e:
            ultimo_error = e
            err = str(e)
            if "rate_limit" in err.lower() or "429" in err:
                espera = 20 * (intento + 1)
                print(f"[Groq] rate limit, esperando {espera}s...", flush=True)
                _time.sleep(espera)
            else:
                raise
    else:
        raise ultimo_error

    respuesta = resp.content.strip()

    # Actualizar historial — cap de 10 mensajes (5 turnos) para evitar overflow
    historial = list(estado.get("historial", []))
    historial.append({"rol": "user",      "contenido": estado["pregunta"]})
    historial.append({"rol": "assistant", "contenido": respuesta[:500]})
    if len(historial) > 10:
        historial = historial[-10:]

    return {**estado, "respuesta": respuesta, "historial": historial}

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

memory = MemorySaver()
agente_compilado = grafo.compile(checkpointer=memory)

# ══════════════════════════════════════════════════════════
# FUNCIÓN PRINCIPAL
# ══════════════════════════════════════════════════════════
def consultar(
    pregunta: str,
    thread_id: str = "default",
    user_id: str | None = None,
) -> tuple[str, str]:
    """Consulta al agente ADUANA-GPT con memoria conversacional."""
    try:
        handler = _crear_handler(thread_id, user_id)
        estado_inicial = {
            "pregunta":  pregunta,
            "intencion": "",
            "contexto":  "",
            "respuesta": "",
            # historial se omite: MemorySaver preserva el valor del checkpoint
        }
        config = {
            "configurable": {"thread_id": thread_id},
            "callbacks": [handler] if handler else [],
        }
        resultado = agente_compilado.invoke(estado_inicial, config=config)
        respuesta = resultado["respuesta"]
        trace_id = _get_trace_id(handler)
        if handler and hasattr(handler, "flush"):
            handler.flush()
        return respuesta, resultado["intencion"], trace_id, resultado.get("contexto", "")

    except Exception as e:
        error = str(e)
        if "413" in error or "rate_limit" in error.lower():
            return "⚠️ Límite de tokens...", "ERROR", None, ""
        return f"Error al procesar: {error[:300]}", "ERROR", None, ""


def consultar_stream(
    pregunta: str,
    thread_id: str = "default",
    user_id: str | None = None,
):
    """Versión streaming: yield {'type':'token','content':str} por cada chunk
    del nodo síntesis, y {'type':'done', intencion, trace_id, contexto, respuesta}
    al finalizar. Usado por app.py para mostrar texto token a token."""
    try:
        handler = _crear_handler(thread_id, user_id)
        estado_inicial = {
            "pregunta":  pregunta,
            "intencion": "",
            "contexto":  "",
            "respuesta": "",
        }
        config = {
            "configurable": {"thread_id": thread_id},
            "callbacks": [handler] if handler else [],
        }

        for msg, metadata in agente_compilado.stream(
            estado_inicial,
            config=config,
            stream_mode="messages",
        ):
            if (metadata.get("langgraph_node") == "sintesis"
                    and hasattr(msg, "content")
                    and msg.content):
                yield {"type": "token", "content": msg.content}

        state    = agente_compilado.get_state(config)
        trace_id = _get_trace_id(handler)
        if handler and hasattr(handler, "flush"):
            handler.flush()
        vals = state.values
        yield {
            "type":      "done",
            "intencion": vals.get("intencion", "DESPACHO"),
            "trace_id":  trace_id,
            "contexto":  vals.get("contexto", ""),
            "respuesta": vals.get("respuesta", ""),
        }

    except Exception as e:
        error = str(e)
        if "413" in error or "rate_limit" in error.lower():
            msg = "⚠️ Límite de tokens alcanzado. Intenta con una pregunta más corta."
        else:
            msg = f"Error al procesar: {error[:300]}"
        yield {"type": "done", "intencion": "ERROR",
               "trace_id": None, "contexto": "", "respuesta": msg}