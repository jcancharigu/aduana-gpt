import os
import warnings
warnings.filterwarnings("ignore")
os.environ["ANONYMIZED_TELEMETRY"] = "False"

import requests
from langchain.tools import tool
from qdrant_client import QdrantClient

_JINA_KEY  = os.getenv("JINA_API_KEY")
_JINA_EMBD = "https://api.jina.ai/v1/embeddings"
_JINA_RANK = "https://api.jina.ai/v1/rerank"

_cliente = QdrantClient(
    url=os.getenv("QDRANT_URL"),
    api_key=os.getenv("QDRANT_API_KEY"),
)

def _embed(texto: str) -> list:
    resp = requests.post(
        _JINA_EMBD,
        headers={"Authorization": f"Bearer {_JINA_KEY}", "Content-Type": "application/json"},
        json={
            "model": "jina-embeddings-v3",
            "input": [texto],
            "task": "retrieval.query",
            "dimensions": 1024,
        },
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["data"][0]["embedding"]

def _rerank(consulta: str, docs: list, k_final: int) -> list:
    resp = requests.post(
        _JINA_RANK,
        headers={"Authorization": f"Bearer {_JINA_KEY}", "Content-Type": "application/json"},
        json={
            "model": "jina-reranker-v2-base-multilingual",
            "query": consulta,
            "documents": docs,
            "top_n": k_final,
        },
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()["results"]

def _buscar(coleccion: str, consulta: str, k_retrieval: int = 5, k_final: int = 3) -> str:
    try:
        emb = _embed(consulta)

        hits = _cliente.search(
            collection_name=coleccion,
            query_vector=emb,
            limit=k_retrieval,
        )

        if not hits:
            return "No se encontró información relevante."

        docs  = [h.payload.get("text", "") for h in hits]
        metas = [h.payload for h in hits]

        if len(docs) > 1:
            ranked = _rerank(consulta, docs, k_final)
            top = [(r["relevance_score"], docs[r["index"]], metas[r["index"]]) for r in ranked]
        else:
            top = [(1.0, docs[0], metas[0])]

        out = ""
        for score, doc, meta in top:
            fuente = meta.get("fuente", "desconocido")
            out += f"[Fuente: {fuente} | Relevancia: {score:.2f}]\n{doc}\n\n"
        return out.strip()

    except Exception as e:
        return f"Error al buscar en '{coleccion}': {str(e)}"


@tool
def buscar_ley_28008(consulta: str) -> str:
    """Busca en Ley 28008 - Delitos Aduaneros y Reglamento DS 121-2003-EF.
    Usar para: contrabando, defraudacion de rentas, receptacion,
    trafico ilicito, sanciones penales, agravantes, cierre de establecimientos."""
    return _buscar("ley_28008", consulta)

@tool
def buscar_ley_general_aduanas(consulta: str) -> str:
    """Busca en Ley General de Aduanas DL 1053 y Reglamento DS 010-2009-EF.
    Usar para: regimenes aduaneros, obligaciones del importador, tributos,
    plazos de despacho, abandono legal, canales de control, levante."""
    return _buscar("ley_general_aduanas", consulta)

@tool
def buscar_procedimientos_fiscalizacion(consulta: str) -> str:
    """Busca en procedimientos de fiscalizacion y control aduanero SUNAT.
    Usar para: ACEs, aforo, inmovilizacion, incautacion, precintos,
    inspeccion no intrusiva, denuncias, fiscalizacion posterior a despacho."""
    return _buscar("procedimientos_fiscalizacion", consulta)

@tool
def buscar_procedimientos_despacho(consulta: str) -> str:
    """Busca en procedimientos generales y especificos de despacho aduanero.
    Usar para: importacion, exportacion, transito, drawback, deposito,
    courier, envios postales, OEA, reconocimiento fisico, valoracion."""
    return _buscar("procedimientos_despacho", consulta)

@tool
def buscar_procedimientos_recaudacion(consulta: str) -> str:
    """Busca en procedimientos de recaudacion aduanera.
    Usar para: deuda tributaria, reclamos, devoluciones, garantias,
    fraccionamiento, cobranza coactiva, buenos contribuyentes."""
    return _buscar("procedimientos_recaudacion", consulta)

@tool
def buscar_arancel(consulta: str) -> str:
    """Busca partidas arancelarias en el Arancel de Aduanas 2022.
    Usar para: clasificacion arancelaria, derechos ad valorem,
    subpartidas nacionales, tasa de arancel por tipo de mercancia."""
    return _buscar("arancel", consulta)

@tool
def buscar_normas_asociadas(consulta: str) -> str:
    """Busca en normas asociadas vigentes: DS 182-2013-EF equipaje y menaje,
    DS 195-2013-EF declaracion dinero, DS 192-2020-EF courier,
    DS 244-2013-EF postales, DS 184-2016-EF OEA, DS 104-95-EF drawback."""
    return _buscar("normas_asociadas", consulta, k_retrieval=5, k_final=3)

@tool
def buscar_normas_generales(consulta: str) -> str:
    """Busca en normas generales: Ley 27444 Procedimiento Administrativo,
    Ley 27815 Etica Publica, normas de transparencia."""
    return _buscar("normas_generales", consulta)

@tool
def buscar_equipaje_viajeros(consulta: str) -> str:
    """Busca información ESPECÍFICA sobre equipaje de viajeros y franquicias.
    Usar cuando pregunten: cuánto puedo traer, franquicia de equipaje,
    menaje de casa, límite sin pagar impuestos, bienes de uso personal.
    Consulta DS 182-2013-EF Reglamento de Equipaje y Menaje de Casa."""
    r1 = _buscar("normas_asociadas",
                 f"equipaje viajero franquicia valor limite USD {consulta}",
                 k_retrieval=10, k_final=3)
    r2 = _buscar("procedimientos_despacho",
                 f"equipaje menaje viajero franquicia {consulta}",
                 k_retrieval=5, k_final=1)
    return f"=== DS 182-2013-EF Equipaje ===\n{r1}\n\n=== Procedimientos ===\n{r2}"

@tool
def buscar_mercancias_prohibidas_restringidas(consulta: str) -> str:
    """Busca si una mercancia es prohibida, restringida o de libre comercio.
    Consulta DESPA-PE.00.06 y Ley 28008 para determinar el régimen
    aplicable y la autoridad competente (SENASA, SERFOR, DIGEMID, etc.)."""
    r1 = _buscar("procedimientos_despacho",
                 f"mercancia prohibida restringida autorizacion {consulta}",
                 k_retrieval=8, k_final=2)
    r2 = _buscar("ley_28008",
                 f"trafico ilicito prohibido {consulta}",
                 k_retrieval=5, k_final=1)
    return f"=== Control de Mercancias ===\n{r1}\n\n=== Ley 28008 ===\n{r2}"

@tool
def buscar_sanciones_multas(consulta: str) -> str:
    """Busca sanciones e infracciones aduaneras administrativas.
    Consulta DS 418-2019-EF Tabla de Sanciones y DL 1053."""
    r1 = _buscar("ley_general_aduanas",
                 f"sancion multa infraccion {consulta}",
                 k_retrieval=8, k_final=2)
    r2 = _buscar("normas_asociadas",
                 f"tabla sanciones 418 infraccion {consulta}",
                 k_retrieval=5, k_final=1)
    return f"=== Sanciones LGA ===\n{r1}\n\n=== Tabla DS 418-2019-EF ===\n{r2}"

HERRAMIENTAS = [
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
]
