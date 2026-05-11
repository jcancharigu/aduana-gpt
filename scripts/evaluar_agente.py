import sys
import os
import time
import json
import asyncio
import warnings
warnings.filterwarnings("ignore")
os.environ["ANONYMIZED_TELEMETRY"] = "False"
sys.path.append(".")

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


# ── Ground score: coseno via Jina embeddings ───────────────────
def _coseno(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na  = sum(x * x for x in a) ** 0.5
    nb  = sum(x * x for x in b) ** 0.5
    return dot / (na * nb) if na and nb else 0.0

def calcular_ground(respuesta: str, respuesta_esperada: str) -> float:
    key = os.getenv("JINA_API_KEY")
    if key:
        try:
            resp = requests.post(
                "https://api.jina.ai/v1/embeddings",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={"model": "jina-embeddings-v3",
                      "input": [respuesta, respuesta_esperada],
                      "task": "retrieval.passage", "dimensions": 1024},
                timeout=20,
            )
            resp.raise_for_status()
            embs = [d["embedding"] for d in resp.json()["data"]]
            return round(_coseno(embs[0], embs[1]), 4)
        except Exception:
            pass
    # fallback: Jaccard de unigramas
    r, g = set(respuesta.lower().split()), set(respuesta_esperada.lower().split())
    return round(len(r & g) / len(r | g), 4) if r | g else 0.0


# ── Grounding léxico: BLEU-1 y ROUGE-1 ────────────────────────
import nltk
nltk.download("punkt", quiet=True)
nltk.download("punkt_tab", quiet=True)
from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
from rouge_score import rouge_scorer as rouge_lib

def evaluar_grounding(respuesta: str, respuesta_esperada: str) -> dict:
    ref = respuesta_esperada.lower().split()
    hyp = respuesta.lower().split()
    bleu1 = sentence_bleu(
        [ref], hyp,
        weights=(1, 0, 0, 0),
        smoothing_function=SmoothingFunction().method1,
    )
    scorer = rouge_lib.RougeScorer(["rouge1"], use_stemmer=False)
    rouge  = scorer.score(respuesta_esperada, respuesta)
    return {
        "bleu1":    round(bleu1, 4),
        "rouge1_f": round(rouge["rouge1"].fmeasure, 4),
    }


def veredicto(ground: float) -> str:
    if ground >= 0.80:
        return "✓ FUNDAMENTADO"
    if ground >= 0.65:
        return "~ PARCIAL"
    return "✗ NO FUNDAMENTADO"


# ═══════════════════════════════════════════════════════════════
# 20 CASOS — ground truths basados en procedimientos SUNAT reales
# Fuentes: CONTROL-PG.01/02, DESPA-PG.01/02, Ley 28008, DL 1053
# ═══════════════════════════════════════════════════════════════
# tipo: definition | procedure | scenario | comparison
CASOS = [
    # ── ESPECIALISTA SUNAT ────────────────────────────────────
    # Fuente: CONTROL-PG.01 (Res. 0206-2020/SUNAT) y CONTROL-PG.02
    {"id": "D01", "tipo": "definition", "perfil": "Especialista SUNAT", "tema": "ACE",
     "pregunta": "Que es una Accion de Control Extraordinario y cuales son sus etapas?",
     "respuesta_esperada": (
         "Una Accion de Control Extraordinario (ACE) es una intervencion aduanera sobre "
         "personas, mercancias o medios de transporte, regulada en los procedimientos "
         "CONTROL-PG.01 y CONTROL-PG.02 de SUNAT. Sus etapas son: seleccion automatizada "
         "por gestion de riesgo, programacion, comunicacion a las unidades ejecutoras, "
         "bloqueo de la mercancia en el sistema informatico, ejecucion del control y "
         "registro del acta de inspeccion que concluye la ACE.")},

    # Fuente: CONTROL-PG.02 — CONTROL-PE.00.01 para inmovilizacion
    {"id": "P02", "tipo": "procedure", "perfil": "Especialista SUNAT", "tema": "Inmovilizacion",
     "pregunta": "Cual es el procedimiento para inmovilizar una mercancia durante una ACE?",
     "respuesta_esperada": (
         "La inmovilizacion durante una ACE se regula en el procedimiento especifico "
         "CONTROL-PE.00.01. Cuando el funcionario aduanero detecta incidencias en la "
         "ejecucion, formula un Acta de Inmovilizacion que restringe el desplazamiento de "
         "la mercancia en el lugar donde se encuentra. El propietario conserva la custodia "
         "fisica pero no puede movilizarla ni disponer de ella hasta concluir la "
         "verificacion.")},

    # Fuente: Ley 28008 Arts. 1, 3, 10 (modificada por D.Leg. 1542)
    {"id": "D03", "tipo": "definition", "perfil": "Especialista SUNAT", "tema": "Contrabando",
     "pregunta": "Cuales son las modalidades del delito de contrabando segun la Ley 28008?",
     "respuesta_esperada": (
         "La Ley 28008 tipifica: contrabando simple (Art. 1) ingreso o salida de mercancias "
         "evadiendo el control aduanero, pena 5 a 8 anos y multa 365 a 730 dias; contrabando "
         "fraccionado (Art. 3) conductas sistematicas en actos fraccionados con la misma "
         "sancion; y circunstancias agravantes (Art. 10) que elevan la pena a 8-12 anos "
         "cuando intervienen funcionarios publicos, grupos organizados, armas, o los tributos "
         "evadidos superan las 5 UIT. El umbral para delito es valor superior a 4 UIT; "
         "por debajo es infraccion administrativa.")},

    # Fuente: DL 1053 Art. 197 y DS 418-2019-EF (Tabla de Sanciones)
    {"id": "D04", "tipo": "definition", "perfil": "Especialista SUNAT", "tema": "Sanciones",
     "pregunta": "Que infracciones aduaneras generan sancion de comiso de mercancias?",
     "respuesta_esperada": (
         "Conforme al DL 1053 y la Tabla de Sanciones del DS 418-2019-EF, generan comiso: "
         "no declarar mercancias, presentar documentos falsos o adulterados, transportar "
         "mercancias sin documentacion sustentatoria, y poseer mercancias prohibidas o "
         "restringidas sin autorizacion del sector competente. El comiso implica la perdida "
         "definitiva del derecho de propiedad sobre las mercancias a favor del Estado.")},

    # Fuente: DL 1053 (definiciones) y CONTROL-PE.00.01
    {"id": "C05", "tipo": "comparison", "perfil": "Especialista SUNAT", "tema": "Inmovilizacion vs Incautacion",
     "pregunta": "Cual es la diferencia entre inmovilizacion e incautacion de mercancias?",
     "respuesta_esperada": (
         "La inmovilizacion restringe el desplazamiento de la mercancia en un lugar "
         "determinado sin transferir la posesion al Estado; el propietario conserva la "
         "custodia fisica. La incautacion implica la aprehension y traslado fisico de la "
         "mercancia a custodia de la Administracion Aduanera. Ambas medidas se regulan en "
         "CONTROL-PE.00.01 y se formulan mediante actas durante la ejecucion de una ACE.")},

    # Fuente: Ley 28008 (defraudacion de rentas de aduana)
    {"id": "D06", "tipo": "definition", "perfil": "Especialista SUNAT", "tema": "Defraudacion",
     "pregunta": "Que es la defraudacion de rentas de aduana y cual es su sancion penal?",
     "respuesta_esperada": (
         "La defraudacion de rentas de aduana tipificada en la Ley 28008 consiste en "
         "utilizar documentacion falsa o mecanismos de fraude para dejar de pagar tributos "
         "aduaneros o acceder indebidamente a beneficios aduaneros. La sancion penal es "
         "pena privativa de libertad de 5 a 8 anos y multa de 365 a 730 dias. Aplica cuando "
         "el valor de los tributos evadidos supera las 4 UIT; por debajo es infraccion "
         "administrativa sancionable con multa equivalente a 2 veces los tributos no pagados.")},

    # ── OPERADOR OCE ──────────────────────────────────────────
    # Fuente: DS 104-95-EF y modificatorias (drawback)
    {"id": "P07", "tipo": "procedure", "perfil": "Operador OCE", "tema": "Drawback",
     "pregunta": "Cuales son los requisitos para acogerse al regimen de drawback?",
     "respuesta_esperada": (
         "Para acogerse al drawback (DS 104-95-EF) el exportador debe: haber importado "
         "insumos incorporados en el producto exportado pagando los derechos arancelarios, "
         "presentar la solicitud de restitucion dentro de los 180 dias de numerada la DAM "
         "de exportacion, y acreditar que los insumos importados estan contenidos en el "
         "bien exportado. La tasa de restitucion vigente es el 3% del valor FOB exportado.")},

    # Fuente: Arancel de Aduanas 2022 (subpartida 8471.30) + DESPA-PG.01
    {"id": "E08", "tipo": "scenario", "perfil": "Operador OCE", "tema": "Arancel",
     "pregunta": "Cuanto paga de arancel quien importa laptops desde China?",
     "respuesta_esperada": (
         "Las laptops se clasifican en la subpartida nacional 8471.30 del Arancel de "
         "Aduanas 2022. La tasa de derecho ad valorem es 0%. Adicionalmente se aplican "
         "IGV (16%) e IPM (2%) calculados sobre el valor CIF. No existen derechos "
         "especificos ni antidumping para esta subpartida en importaciones desde China.")},

    # Fuente: DESPA-PG.01 v8 (Res. 084-2020)
    {"id": "D09", "tipo": "definition", "perfil": "Operador OCE", "tema": "Canales de control",
     "pregunta": "Cuales son los canales de control aduanero y que implica cada uno?",
     "respuesta_esperada": (
         "Segun el procedimiento DESPA-PG.01, el sistema asigna automaticamente mediante "
         "gestion de riesgo tres canales: canal verde (sin revision documentaria ni "
         "reconocimiento fisico, levante inmediato), canal naranja (revision documentaria "
         "obligatoria por el especialista aduanero sin reconocimiento fisico) y canal rojo "
         "(reconocimiento fisico obligatorio de la mercancia, con posibilidad de toma de "
         "muestras).")},

    # Fuente: DESPA-PG.01 v8 — plazos de regularizacion
    {"id": "P10", "tipo": "procedure", "perfil": "Operador OCE", "tema": "Despacho anticipado",
     "pregunta": "Cual es el plazo para regularizar un despacho anticipado?",
     "respuesta_esperada": (
         "Conforme al procedimiento DESPA-PG.01, la regularizacion del despacho anticipado "
         "debe efectuarse dentro de los 15 dias calendario contados desde el termino de la "
         "descarga. Si el levante se otorgo despues del vencimiento de ese plazo, la "
         "regularizacion debe realizarse dentro de los 3 dias habiles siguientes al levante. "
         "El incumplimiento genera multa por autoliquidacion 0027.")},

    # Fuente: DESPA-PG.02 v6 (Res. 0137/2009)
    {"id": "P11", "tipo": "procedure", "perfil": "Operador OCE", "tema": "Exportacion",
     "pregunta": "Que documentos se requieren para la exportacion definitiva de mercancias?",
     "respuesta_esperada": (
         "Segun el procedimiento DESPA-PG.02, la exportacion definitiva requiere: documento "
         "de transporte (conocimiento de embarque, carta aerea o carta porte), factura SUNAT "
         "o boleta de venta o documento equivalente, y mandato al agente de aduana si actua "
         "un tercero. Para mercancias restringidas se exige la autorizacion del sector "
         "competente. El embarque debe realizarse dentro de los 30 dias calendario desde "
         "la numeracion de la declaracion.")},

    # Fuente: DL 1053 Art. 20 y Reglamento DS 010-2009-EF
    {"id": "D12", "tipo": "definition", "perfil": "Operador OCE", "tema": "Agente de Aduana",
     "pregunta": "Cuales son las obligaciones del agente de aduana en el despacho aduanero?",
     "respuesta_esperada": (
         "El agente de aduana, regulado en el DL 1053, es auxiliar de la funcion publica "
         "aduanera y representante del importador o exportador ante SUNAT. Sus obligaciones "
         "incluyen: transmitir la declaracion aduanera con informacion veraz y completa, "
         "responder solidariamente por los tributos dejados de pagar cuando actua con "
         "mandato, y proporcionar documentacion autentica. La Administracion Aduanera "
         "puede inhabilitarlo ante incumplimientos graves.")},

    # Fuente: DESPA-PG.01 v8 — plazos exactos del abandono legal
    {"id": "D13", "tipo": "definition", "perfil": "Operador OCE", "tema": "Abandono Legal",
     "pregunta": "Que es el abandono legal de mercancias y en que plazo se produce?",
     "respuesta_esperada": (
         "El abandono legal opera de pleno derecho en dos supuestos segun DESPA-PG.01: "
         "cuando las mercancias no son destinadas a ningun regimen aduanero dentro de los "
         "15 dias calendario posteriores al termino de la descarga, o cuando transcurren "
         "30 dias desde el vencimiento de la numeracion sin culminar el tramite. Las "
         "mercancias en situacion de abandono pasan a disposicion de SUNAT.")},

    # ── CIUDADANO ─────────────────────────────────────────────
    # Fuente: DS 182-2013-EF (Reglamento de Equipaje y Menaje de Casa)
    {"id": "E14", "tipo": "scenario", "perfil": "Ciudadano", "tema": "Equipaje",
     "pregunta": "Cuanto equipaje puedo traer del extranjero sin pagar impuestos?",
     "respuesta_esperada": (
         "Conforme al DS 182-2013-EF, los viajeros pueden ingresar su equipaje de uso "
         "personal libre de tributos. Para bienes adquiridos en el extranjero distintos al "
         "equipaje personal, existe una franquicia de hasta USD 500 por viajero mayor de "
         "edad. Los bienes deben ser de uso personal, en cantidades razonables y sin fines "
         "comerciales. El exceso sobre la franquicia tributa segun las tasas del regimen "
         "de equipaje.")},

    # Fuente: Arancel de Aduanas 2022 (partida 8806) y normativa DGAC
    {"id": "E15", "tipo": "scenario", "perfil": "Ciudadano", "tema": "Drone",
     "pregunta": "Puedo importar un drone desde Estados Unidos? Que impuestos pago?",
     "respuesta_esperada": (
         "Los drones (vehiculos aereos no tripulados, UAS) se clasifican en la partida "
         "arancelaria 8806 del Arancel de Aduanas 2022. Son mercancias restringidas que "
         "requieren autorizacion previa de la DGAC (Direccion General de Aeronautica Civil) "
         "para su importacion y operacion comercial. Tributan con derecho ad valorem de 0%, "
         "mas IGV (16%) e IPM (2%) sobre el valor CIF.")},

    # Fuente: Ley 28008 (umbral 4 UIT) y DS 418-2019-EF
    {"id": "E16", "tipo": "scenario", "perfil": "Ciudadano", "tema": "No declaracion",
     "pregunta": "Que pasa si no declaro mercancias al ingresar al Peru?",
     "respuesta_esperada": (
         "No declarar mercancias al ingreso constituye una infraccion aduanera sancionable "
         "con multa equivalente a 2 veces los tributos no pagados y/o comiso, conforme al "
         "DS 418-2019-EF. Si el valor de las mercancias no declaradas supera las 4 UIT o "
         "se trata de mercancias prohibidas, configura el delito de contrabando tipificado "
         "en la Ley 28008, sancionable con pena privativa de libertad de 5 a 8 anos.")},

    # Fuente: DL 1053 (mercancias restringidas) y normativa DIGEMID
    {"id": "E17", "tipo": "scenario", "perfil": "Ciudadano", "tema": "Medicamentos",
     "pregunta": "Puedo traer medicamentos del extranjero? Hay limites?",
     "respuesta_esperada": (
         "Los medicamentos son mercancias restringidas segun el DL 1053. Para uso personal, "
         "los viajeros pueden ingresar medicamentos en cantidades razonables sin autorizacion "
         "especial. La importacion comercial requiere registro sanitario y autorizacion de "
         "DIGEMID (Direccion General de Medicamentos, Insumos y Drogas). Los medicamentos "
         "controlados (estupefacientes, psicotropicos) requieren autorizacion previa en "
         "cualquier caso.")},

    # Fuente: DS 192-2020-EF (regimen de envios de entrega rapida)
    {"id": "D18", "tipo": "definition", "perfil": "Ciudadano", "tema": "Courier",
     "pregunta": "Que es el regimen de envios de entrega rapida o courier?",
     "respuesta_esperada": (
         "El regimen de envios de entrega rapida (courier) esta regulado en el DS 192-2020-EF "
         "y permite el despacho simplificado de envios de bajo valor transportados por "
         "empresas habilitadas por SUNAT. Los envios de hasta USD 200 estan exonerados de "
         "tributos aduaneros. Los envios entre USD 200 y USD 2,000 se despachan con tasa "
         "simplificada. Los que superan USD 2,000 siguen el despacho ordinario.")},

    # Fuente: DS 192-2020-EF (courier) y DS 244-2013-EF (envios postales)
    {"id": "E19", "tipo": "scenario", "perfil": "Ciudadano", "tema": "Compras online",
     "pregunta": "Puedo comprar por internet en el extranjero y traer el paquete al Peru?",
     "respuesta_esperada": (
         "Si. Las compras por internet del extranjero ingresan por el regimen de envios de "
         "entrega rapida (courier, DS 192-2020-EF) o por envios postales via SERPOST "
         "(DS 244-2013-EF). Mediante courier, los envios de hasta USD 200 estan libres de "
         "tributos; entre USD 200 y USD 2,000 aplica tasa simplificada. El importador debe "
         "contar con RUC activo o acreditar importacion ocasional.")},

    # Fuente: DS 195-2013-EF (declaracion jurada de transporte de dinero)
    {"id": "E20", "tipo": "scenario", "perfil": "Ciudadano", "tema": "Declaracion dinero",
     "pregunta": "Cuanto dinero en efectivo puedo llevar o traer del extranjero?",
     "respuesta_esperada": (
         "No existe limite legal para transportar dinero en efectivo al ingresar o salir "
         "del Peru. Sin embargo, los montos iguales o superiores a USD 10,000 o su "
         "equivalente en otras monedas deben declararse obligatoriamente ante SUNAT "
         "mediante la Declaracion Jurada de Transporte de Dinero en Efectivo, conforme al "
         "DS 195-2013-EF. El incumplimiento genera el comiso del monto no declarado.")},
]

_checkpoint_path = "data/evaluacion_resultados.json"

if os.path.exists(_checkpoint_path):
    os.remove(_checkpoint_path)
    print("[Info] Checkpoint anterior eliminado.")


# ── Tabla helpers ──────────────────────────────────────────────
_HDR = f"{'ID':<5} {'Tipo':<12} {'Ground':>7} {'BLEU':>7} {'ROUGE':>7}  Veredicto"
_SEP = "-" * 68

def _fila(caso_id, tipo, ground, bleu, rouge, verd):
    return (f"{caso_id:<5} {tipo:<12} {ground:>7.4f} {bleu:>7.4f} {rouge:>7.4f}  {verd}")


# ═══════════════════════════════════════════════════════════════
# EVALUACION MANUAL
# ═══════════════════════════════════════════════════════════════
def evaluar_manualmente(caso, respuesta):
    print("\nEVALUACION MANUAL (tu como experto):")
    print(f"   Respuesta del agente: {respuesta[:120]}...")
    print(f"   Esperada:             {caso['respuesta_esperada'][:120]}...")
    scores = {}
    for key, pregunta_eval in [
        ("precision",   "La respuesta es normativamente correcta? (1-5)"),
        ("relevancia",  "Responde lo que se pregunto? (1-5)"),
        ("utilidad",    "Es util para el usuario final? (1-5)"),
        ("alucinacion", "Hay alucinaciones? (0=si hay, 5=no hay)"),
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
print(f"Casos a evaluar: {len(CASOS)}")
print("=" * 70)

modo = input("\nModo?\n  1 = Solo BLEU/ROUGE/Ground\n  2 = Solo manual\n  3 = Ambos\nOpcion: ").strip()

resultados   = []
filas_tabla  = []
os.makedirs("data", exist_ok=True)

for i, caso in enumerate(CASOS):
    print(f"\n{'='*70}")
    print(f"CASO {caso['id']} | {caso['perfil']} | {caso['tema']}")
    print(f"PREGUNTA: {caso['pregunta']}")
    print(f"{'─'*70}")

    inicio   = time.time()
    trace_id = None
    try:
        respuesta, _, trace_id, _ = consultar(caso["pregunta"])
        tiempo  = round(time.time() - inicio, 1)
        estado  = "RATE_LIMIT" if "Limite de tokens" in respuesta else "OK"
        print(f"RESPUESTA ({tiempo}s):\n{respuesta[:400]}")
    except Exception as e:
        respuesta = f"ERROR: {str(e)[:100]}"
        tiempo    = round(time.time() - inicio, 1)
        estado    = "ERROR"
        print(f"ERROR: {respuesta}")

    resultado = {
        "id": caso["id"], "tipo": caso["tipo"],
        "perfil": caso["perfil"], "tema": caso["tema"],
        "pregunta": caso["pregunta"], "respuesta": respuesta[:300],
        "tiempo_seg": tiempo, "estado": estado,
    }

    ground = bleu1 = rouge1_f = 0.0

    if estado == "OK" and modo in ["1", "3"]:
        print("   Calculando Ground (Jina coseno)...")
        ground   = calcular_ground(respuesta, caso["respuesta_esperada"])
        lex      = evaluar_grounding(respuesta, caso["respuesta_esperada"])
        bleu1    = lex["bleu1"]
        rouge1_f = lex["rouge1_f"]
        verd     = veredicto(ground)

        resultado.update({"ground": ground, "bleu1": bleu1, "rouge1_f": rouge1_f, "veredicto": verd})

        fila = _fila(caso["id"], caso["tipo"], ground, bleu1, rouge1_f, verd)
        filas_tabla.append(fila)

        if len(filas_tabla) == 1:
            print(f"\n{_HDR}")
            print(_SEP)
        print(fila)

        for k, v in [("ground", ground), ("bleu1", bleu1), ("rouge1_f", rouge1_f)]:
            lf_score(trace_id, k, v)

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


# ═══════════════════════════════════════════════════════════════
# RESUMEN
# ═══════════════════════════════════════════════════════════════
print("\n\n" + "=" * 70)
print("RESUMEN FINAL — ADUANA-GPT")
print("=" * 70)

ok = [r for r in resultados if r["estado"] == "OK"]
print(f"\nEvaluados: {len(resultados)}/{len(CASOS)}  |  OK: {len(ok)}  |  Errores: {len(resultados)-len(ok)}")
if ok:
    print(f"Tiempo promedio: {sum(r['tiempo_seg'] for r in ok)/len(ok):.1f}s\n")

if filas_tabla:
    print(_HDR)
    print("=" * 68)
    for fila in filas_tabla:
        print(fila)
    print("=" * 68)

    for m, label in [("ground", "Ground (coseno)"), ("bleu1", "BLEU-1"), ("rouge1_f", "ROUGE-1 F1")]:
        vals = [r[m] for r in ok if r.get(m) is not None]
        if vals:
            print(f"  {label:<22} avg={sum(vals)/len(vals):.4f}  (n={len(vals)})")

if any(r.get("promedio_manual") for r in ok):
    vals = [r["promedio_manual"] for r in ok if r.get("promedio_manual")]
    print(f"  {'Score manual':<22} avg={sum(vals)/len(vals):.2f}/5")

print("\nPor perfil:")
for perfil in ["Especialista SUNAT", "Operador OCE", "Ciudadano"]:
    sub = [r for r in ok if r["perfil"] == perfil]
    if sub:
        g_vals = [r["ground"] for r in sub if r.get("ground") is not None]
        g_str  = f"  ground_avg={sum(g_vals)/len(g_vals):.4f}" if g_vals else ""
        print(f"  {perfil:35} {len(sub)}/{sum(1 for r in resultados if r['perfil']==perfil)} OK{g_str}")

print(f"\nGuardado en: {_checkpoint_path}")
print("EVALUACION COMPLETADA")
