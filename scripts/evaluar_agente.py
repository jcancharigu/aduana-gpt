import sys
import os
import time
import json
import asyncio
import re
import warnings
warnings.filterwarnings("ignore")
os.environ["ANONYMIZED_TELEMETRY"] = "False"
sys.path.append(".")

# Fix asyncio en Windows (evita RuntimeError: Event loop is closed entre llamadas)
if hasattr(asyncio, "WindowsSelectorEventLoopPolicy"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from dotenv import load_dotenv
load_dotenv()

import requests
from src.agent.agente import consultar

# ── Langfuse REST ──────────────────────────────────────────────
_LF_HOST = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com").rstrip("/")
_LF_AUTH = (os.getenv("LANGFUSE_PUBLIC_KEY", ""), os.getenv("LANGFUSE_SECRET_KEY", ""))

def lf_score(trace_id, name, value):
    if not (trace_id and _LF_AUTH[0] and _LF_AUTH[1]):
        return
    try:
        requests.post(
            f"{_LF_HOST}/api/public/scores",
            auth=_LF_AUTH,
            json={"traceId": trace_id, "name": name, "value": value},
            timeout=8,
        )
    except Exception:
        pass


# ── Jina embeddings para RAGAS (sin torch) ────────────────────
from langchain_core.embeddings import Embeddings

class JinaEmbeddings(Embeddings):
    def __init__(self):
        self.key = os.getenv("JINA_API_KEY")

    def _call(self, texts, task):
        resp = requests.post(
            "https://api.jina.ai/v1/embeddings",
            headers={"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"},
            json={"model": "jina-embeddings-v3", "input": texts, "task": task, "dimensions": 1024},
            timeout=30,
        )
        resp.raise_for_status()
        return [d["embedding"] for d in resp.json()["data"]]

    def embed_documents(self, texts):
        return self._call(texts, "retrieval.passage")

    def embed_query(self, text):
        return self._call([text], "retrieval.query")[0]


def limpiar_contexto(contexto: str) -> list[str]:
    """Divide el contexto en secciones y elimina los prefijos de fuente/relevancia."""
    secciones = re.split(r'=== .+? ===\n?', contexto)
    limpias = []
    for sec in secciones:
        # Quitar líneas de metadatos [Fuente: ... | Relevancia: ...]
        lineas = [l for l in sec.split('\n') if not l.startswith('[Fuente:')]
        texto = '\n'.join(lineas).strip()
        if len(texto) > 40:
            limpias.append(texto)
    return limpias if limpias else [contexto]


# ═══════════════════════════════════════════════════════════════
# 20 CASOS — ground truths realistas y derivables del RAG
# ═══════════════════════════════════════════════════════════════
CASOS = [
    # ── ESPECIALISTA SUNAT ────────────────────────────────────
    {"id": 1, "perfil": "Especialista SUNAT", "tema": "ACE",
     "pregunta": "¿Qué es una Acción de Control Extraordinario y cuáles son sus etapas?",
     "respuesta_esperada": (
         "Una Acción de Control Extraordinario (ACE) es una acción de control aduanero "
         "regulada en el procedimiento CONTROL-PG.01 de SUNAT, que se ejecuta fuera del "
         "despacho aduanero para verificar el cumplimiento de las normas aduaneras.")},

    {"id": 2, "perfil": "Especialista SUNAT", "tema": "Inmovilizacion",
     "pregunta": "¿Cuál es el procedimiento para inmovilizar una mercancía durante una ACE?",
     "respuesta_esperada": (
         "La inmovilización de mercancías se regula en el procedimiento CONTROL-PE.00.01. "
         "Es una medida cautelar temporal que restringe el movimiento de la mercancía "
         "sin transferir su posesión, adoptada cuando se detectan irregularidades aduaneras.")},

    {"id": 3, "perfil": "Especialista SUNAT", "tema": "Contrabando",
     "pregunta": "¿Cuáles son las modalidades del delito de contrabando según la Ley 28008?",
     "respuesta_esperada": (
         "Según la Ley 28008, el contrabando consiste en la introducción o extracción "
         "de mercancías del territorio nacional evadiendo el control aduanero. "
         "Se tipifica en el artículo 1° de dicha ley.")},

    {"id": 4, "perfil": "Especialista SUNAT", "tema": "Sanciones",
     "pregunta": "¿Qué infracciones aduaneras generan sanción de comiso de mercancías?",
     "respuesta_esperada": (
         "El comiso procede por infracciones como no declarar mercancías, presentar "
         "documentos falsos o tener mercancías prohibidas o restringidas sin autorización, "
         "conforme a la Ley General de Aduanas DL 1053 y el DS 418-2019-EF.")},

    {"id": 5, "perfil": "Especialista SUNAT", "tema": "Inmovilizacion vs Incautacion",
     "pregunta": "¿Cuál es la diferencia entre inmovilización e incautación de mercancías?",
     "respuesta_esperada": (
         "La inmovilización es una medida preventiva temporal que no transfiere la posesión "
         "de la mercancía. La incautación implica la aprehensión física por la autoridad "
         "aduanera, transfiriendo la custodia al Estado.")},

    {"id": 6, "perfil": "Especialista SUNAT", "tema": "Defraudacion",
     "pregunta": "¿Qué es la defraudación de rentas de aduana y cuál es su sanción penal?",
     "respuesta_esperada": (
         "La defraudación de rentas de aduana es un delito tipificado en la Ley 28008 "
         "que consiste en evadir tributos aduaneros mediante declaraciones falsas, "
         "subvaluación u otros medios fraudulentos.")},

    # ── OPERADOR OCE ──────────────────────────────────────────
    {"id": 7, "perfil": "Operador OCE", "tema": "Drawback",
     "pregunta": "¿Cuáles son los requisitos para acogerse al régimen de drawback?",
     "respuesta_esperada": (
         "El drawback es un régimen aduanero regulado en el DS 104-95-EF que permite "
         "la restitución de derechos arancelarios a exportadores que utilizaron "
         "insumos importados incorporados en el producto exportado.")},

    {"id": 8, "perfil": "Operador OCE", "tema": "Arancel",
     "pregunta": "¿Cuánto paga de arancel quien importa laptops desde China?",
     "respuesta_esperada": (
         "Las laptops y computadoras portátiles se clasifican en la partida arancelaria "
         "8471 del Arancel de Aduanas. La tasa ad valorem para esta partida es 0%.")},

    {"id": 9, "perfil": "Operador OCE", "tema": "Canales de control",
     "pregunta": "¿Cuáles son los canales de control aduanero y qué implica cada uno?",
     "respuesta_esperada": (
         "Los canales de control son tres: canal verde (levante automático sin revisión), "
         "canal naranja (revisión documentaria) y canal rojo (reconocimiento físico de "
         "la mercancía por el especialista aduanero).")},

    {"id": 10, "perfil": "Operador OCE", "tema": "Despacho anticipado",
     "pregunta": "¿Cuál es el plazo para regularizar un despacho anticipado?",
     "respuesta_esperada": (
         "El despacho anticipado permite el levante antes o durante la descarga. "
         "El importador debe regularizar la declaración en el plazo establecido "
         "en el procedimiento DESPA-PG.01 de despacho de importación.")},

    {"id": 11, "perfil": "Operador OCE", "tema": "Exportacion",
     "pregunta": "¿Qué documentos se requieren para la exportación definitiva de mercancías?",
     "respuesta_esperada": (
         "Para la exportación definitiva se requiere la Declaración Aduanera de "
         "Mercancías (DAM), factura comercial, documento de transporte y lista de empaque, "
         "conforme al procedimiento DESPA-PG.02.")},

    {"id": 12, "perfil": "Operador OCE", "tema": "Agente de Aduana",
     "pregunta": "¿Cuáles son las obligaciones del agente de aduana en el despacho aduanero?",
     "respuesta_esperada": (
         "El agente de aduana es un auxiliar de la función pública aduanera que actúa "
         "como representante del importador o exportador ante SUNAT, transmitiendo "
         "la declaración y respondiendo por la veracidad de la información.")},

    {"id": 13, "perfil": "Operador OCE", "tema": "Abandono Legal",
     "pregunta": "¿Qué es el abandono legal de mercancías y en qué plazo se produce?",
     "respuesta_esperada": (
         "El abandono legal opera cuando las mercancías no son destinadas a un régimen "
         "aduanero dentro del plazo legal establecido en el DL 1053 Ley General de Aduanas.")},

    # ── CIUDADANO ─────────────────────────────────────────────
    {"id": 14, "perfil": "Ciudadano", "tema": "Equipaje",
     "pregunta": "¿Cuánto equipaje puedo traer del extranjero sin pagar impuestos?",
     "respuesta_esperada": (
         "Los viajeros pueden ingresar bienes de uso personal sujetos a franquicia "
         "arancelaria conforme al DS 182-2013-EF Reglamento de Equipaje y Menaje de Casa. "
         "Los bienes deben ser de uso personal y no tener fines comerciales.")},

    {"id": 15, "perfil": "Ciudadano", "tema": "Drone",
     "pregunta": "¿Puedo importar un drone desde Estados Unidos? ¿Qué impuestos pago?",
     "respuesta_esperada": (
         "Los drones son mercancías de importación que deben cumplir requisitos de la "
         "autoridad competente. Tributan según la partida arancelaria correspondiente "
         "del Arancel de Aduanas 2022.")},

    {"id": 16, "perfil": "Ciudadano", "tema": "No declaracion",
     "pregunta": "¿Qué pasa si no declaro mercancías al ingresar al Perú?",
     "respuesta_esperada": (
         "No declarar mercancías constituye una infracción aduanera sancionable con "
         "multa o comiso según la Ley General de Aduanas. Si el valor supera los "
         "límites legales puede configurar el delito de contrabando según la Ley 28008.")},

    {"id": 17, "perfil": "Ciudadano", "tema": "Medicamentos",
     "pregunta": "¿Puedo traer medicamentos del extranjero? ¿Hay límites?",
     "respuesta_esperada": (
         "Los medicamentos son mercancías restringidas que requieren autorización de "
         "DIGEMID para importación comercial. Para uso personal se permiten cantidades "
         "razonables sin requerir autorización especial.")},

    {"id": 18, "perfil": "Ciudadano", "tema": "Courier",
     "pregunta": "¿Qué es el régimen de envíos de entrega rápida o courier?",
     "respuesta_esperada": (
         "El régimen de envíos de entrega rápida o courier está regulado en el "
         "DS 192-2020-EF y permite el despacho simplificado de envíos transportados "
         "por empresas courier autorizadas.")},

    {"id": 19, "perfil": "Ciudadano", "tema": "Compras online",
     "pregunta": "¿Puedo comprar por internet en el extranjero y traer el paquete al Perú?",
     "respuesta_esperada": (
         "Las compras por internet del extranjero ingresan mediante el régimen de "
         "envíos postales regulado en el DS 244-2013-EF o el régimen courier del "
         "DS 192-2020-EF, con proceso simplificado de despacho aduanero.")},

    {"id": 20, "perfil": "Ciudadano", "tema": "Declaracion dinero",
     "pregunta": "¿Cuánto dinero en efectivo puedo llevar o traer del extranjero?",
     "respuesta_esperada": (
         "Se puede transportar cualquier monto de dinero en efectivo. Los montos "
         "iguales o superiores a USD 10,000 deben declararse obligatoriamente "
         "conforme al DS 195-2013-EF sobre declaración de dinero en efectivo.")},
]

IDS_EVALUAR = set(range(1, 21))
_checkpoint_path = "data/evaluacion_resultados.json"

# Eliminar checkpoint anterior (ground truths rediseñados = resultados anteriores inválidos)
if os.path.exists(_checkpoint_path):
    os.remove(_checkpoint_path)
    print("[Info] Checkpoint anterior eliminado — ground truths rediseñados.")

CASOS_EVALUAR = [c for c in CASOS if c["id"] in IDS_EVALUAR]


# ═══════════════════════════════════════════════════════════════
# EVALUACION RAGAS
# ═══════════════════════════════════════════════════════════════
def _get_llm_ragas():
    """Devuelve el primer LLM disponible para RAGAS (mismo orden de fallback que el agente)."""
    from langchain_groq import ChatGroq
    candidatos = []
    if os.getenv("GROQ_API_KEY"):
        candidatos.append(ChatGroq(model="llama-3.3-70b-versatile", temperature=0))
        candidatos.append(ChatGroq(model="llama-3.1-8b-instant",    temperature=0))
    if os.getenv("GOOGLE_API_KEY"):
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            candidatos.append(ChatGoogleGenerativeAI(
                model="gemini-1.5-flash",
                google_api_key=os.getenv("GOOGLE_API_KEY"),
                temperature=0,
            ))
        except ImportError:
            pass
    for llm in candidatos:
        try:
            llm.invoke([{"role": "user", "content": "hi"}])
            return llm
        except Exception as e:
            err = str(e)
            if "tokens per day" in err.lower() or "rate_limit" in err.lower():
                print(f"   [RAGAS LLM] {getattr(llm, 'model', 'modelo')} no disponible, probando siguiente...")
                continue
            return llm  # otro tipo de error, devolver igual para que RAGAS lo maneje
    return candidatos[0] if candidatos else None


def evaluar_con_ragas(pregunta, respuesta, contextos, respuesta_esperada):
    try:
        from ragas import evaluate
        from ragas.metrics import faithfulness, answer_relevancy, context_recall, context_precision
        from datasets import Dataset

        llm = _get_llm_ragas()
        emb = JinaEmbeddings()

        dataset = Dataset.from_dict({
            "question":    [pregunta],
            "answer":      [respuesta],
            "contexts":    [contextos],
            "ground_truth":[respuesta_esperada],
        })

        try:
            from ragas.llms import LangchainLLMWrapper
            from ragas.embeddings import LangchainEmbeddingsWrapper
            result = evaluate(
                dataset,
                metrics=[faithfulness, answer_relevancy, context_recall, context_precision],
                llm=LangchainLLMWrapper(llm),
                embeddings=LangchainEmbeddingsWrapper(emb),
            )
        except (ImportError, TypeError):
            result = evaluate(
                dataset,
                metrics=[faithfulness, answer_relevancy, context_recall, context_precision],
                llm=llm,
                embeddings=emb,
            )

        def _v(key):
            v = result[key]
            return round(float(v[0] if isinstance(v, (list, tuple)) else v), 3)

        return {
            "faithfulness":      _v("faithfulness"),
            "answer_relevancy":  _v("answer_relevancy"),
            "context_recall":    _v("context_recall"),
            "context_precision": _v("context_precision"),
        }

    except Exception as e:
        import traceback
        print(f"   ERROR RAGAS: {e}")
        traceback.print_exc()
        return {"faithfulness": None, "answer_relevancy": None,
                "context_recall": None, "context_precision": None,
                "error": str(e)[:120]}


# ═══════════════════════════════════════════════════════════════
# EVALUACION MANUAL
# ═══════════════════════════════════════════════════════════════
def evaluar_manualmente(caso, respuesta):
    print("\n📋 EVALUACION MANUAL (tú como experto):")
    print(f"   Respuesta del agente: {respuesta[:120]}...")
    print(f"   Esperada:             {caso['respuesta_esperada'][:120]}...")
    scores = {}
    for key, pregunta_eval in [
        ("precision",   "¿La respuesta es normativamente correcta? (1-5)"),
        ("relevancia",  "¿Responde lo que se preguntó? (1-5)"),
        ("utilidad",    "¿Es útil para el usuario final? (1-5)"),
        ("alucinacion", "¿Hay alucinaciones? (0=sí hay, 5=no hay)"),
    ]:
        while True:
            try:
                val = int(input(f"   {pregunta_eval}: "))
                if 0 <= val <= 5:
                    scores[key] = val
                    break
            except ValueError:
                pass
    scores["promedio_manual"] = round(sum(scores.values()) / len(scores), 2)
    return scores


# ═══════════════════════════════════════════════════════════════
# EJECUCION
# ═══════════════════════════════════════════════════════════════
print("=" * 70)
print("EVALUACION COMPLETA — ADUANA-GPT")
print(f"Casos a evaluar: {len(CASOS_EVALUAR)}")
print("=" * 70)

modo = input("\n¿Modo?\n  1 = Solo RAGAS\n  2 = Solo manual\n  3 = Ambos\nOpcion: ").strip()

resultados = []
os.makedirs("data", exist_ok=True)

for i, caso in enumerate(CASOS_EVALUAR):
    print(f"\n{'='*70}")
    print(f"CASO {caso['id']:02d}/{len(CASOS_EVALUAR)} | {caso['perfil']} | {caso['tema']}")
    print(f"PREGUNTA: {caso['pregunta']}")
    print(f"{'─'*70}")

    inicio = time.time()
    trace_id = None
    contexto_real = ""
    try:
        respuesta, _, trace_id, contexto_real = consultar(caso["pregunta"])
        tiempo = round(time.time() - inicio, 1)
        estado = "RATE_LIMIT" if "⚠️ Límite de tokens" in respuesta else "OK"
        print(f"RESPUESTA ({tiempo}s):\n{respuesta[:400]}")
    except Exception as e:
        respuesta = f"ERROR: {str(e)[:100]}"
        tiempo = round(time.time() - inicio, 1)
        estado = "ERROR"
        print(f"ERROR: {respuesta}")

    resultado = {
        "id": caso["id"], "perfil": caso["perfil"], "tema": caso["tema"],
        "pregunta": caso["pregunta"], "respuesta": respuesta[:300],
        "tiempo_seg": tiempo, "estado": estado,
    }

    if estado == "OK" and modo in ["1", "3"]:
        # Limpiar contexto: quitar prefijos [Fuente: ... | Relevancia: ...]
        contextos = limpiar_contexto(contexto_real) if contexto_real else [respuesta]

        print(f"\n🤖 Evaluando con RAGAS ({len(contextos)} chunks de contexto)...")
        scores = evaluar_con_ragas(
            caso["pregunta"], respuesta, contextos, caso["respuesta_esperada"]
        )
        resultado.update(scores)
        for m in ["faithfulness", "answer_relevancy", "context_recall", "context_precision"]:
            print(f"   {m:<22} {scores.get(m, 'N/A')}")
            if scores.get(m) is not None:
                lf_score(trace_id, m, scores[m])

    if estado == "OK" and modo in ["2", "3"]:
        scores_m = evaluar_manualmente(caso, respuesta)
        resultado.update(scores_m)
        print(f"   Promedio manual: {scores_m['promedio_manual']}/5")
        for k in ["precision", "relevancia", "utilidad", "alucinacion"]:
            if k in scores_m:
                lf_score(trace_id, k, scores_m[k] / 5)

    resultados.append(resultado)
    with open(_checkpoint_path, "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2)

    if i < len(CASOS_EVALUAR) - 1:
        print("\n⏳ Esperando 35s para evitar rate limit de Groq...")
        time.sleep(35)

# ═══════════════════════════════════════════════════════════════
# RESUMEN
# ═══════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("RESUMEN FINAL")
print("=" * 70)

ok = [r for r in resultados if r["estado"] == "OK"]
print(f"\nEvaluados: {len(resultados)}/{len(CASOS_EVALUAR)}  |  OK: {len(ok)}  |  Errores: {len(resultados)-len(ok)}")
if ok:
    print(f"Tiempo promedio: {sum(r['tiempo_seg'] for r in ok)/len(ok):.1f}s")
    for m in ["faithfulness", "answer_relevancy", "context_recall", "context_precision"]:
        vals = [r[m] for r in ok if r.get(m) is not None]
        if vals:
            print(f"  {m:<22} {sum(vals)/len(vals):.3f}  (n={len(vals)})")
    if ok[0].get("promedio_manual"):
        vals = [r["promedio_manual"] for r in ok if r.get("promedio_manual")]
        print(f"  {'score manual':<22} {sum(vals)/len(vals):.2f}/5")

print("\nPor perfil:")
for perfil in ["Especialista SUNAT", "Operador OCE", "Ciudadano"]:
    sub = [r for r in resultados if r["perfil"] == perfil]
    print(f"  {perfil:35} {sum(1 for r in sub if r['estado']=='OK')}/{len(sub)} OK")

print(f"\nGuardado en: {_checkpoint_path}")
print("EVALUACION COMPLETADA")
