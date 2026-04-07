import sys
import os
import time
import json
import warnings
warnings.filterwarnings("ignore")
os.environ["ANONYMIZED_TELEMETRY"] = "False"
sys.path.append(".")

from src.agent.agente import consultar
from src.tools.herramientas_rag import _buscar

# ═══════════════════════════════════════════════════════════════
# 20 CASOS DE PRUEBA CON RESPUESTA ESPERADA (ground truth)
# ═══════════════════════════════════════════════════════════════
CASOS = [
    # ESPECIALISTA SUNAT
    {
        "id": 1, "perfil": "Especialista SUNAT", "tema": "ACE",
        "pregunta": "¿Qué es una Acción de Control Extraordinario y cuáles son sus etapas?",
        "respuesta_esperada": "Una ACE es una acción de control que se programa y ejecuta fuera del despacho aduanero normal. Sus etapas son programación, comunicación, ejecución y cierre."
    },
    {
        "id": 2, "perfil": "Especialista SUNAT", "tema": "Inmovilizacion",
        "pregunta": "¿Cuál es el procedimiento para inmovilizar una mercancía durante una ACE?",
        "respuesta_esperada": "El especialista debe levantar un acta de inmovilización, notificar al propietario, asegurar la mercancía y remitir el expediente a la autoridad competente."
    },
    {
        "id": 3, "perfil": "Especialista SUNAT", "tema": "Contrabando",
        "pregunta": "¿Cuáles son las modalidades del delito de contrabando según la Ley 28008?",
        "respuesta_esperada": "Las modalidades son: introducción de mercancías evadiendo control aduanero, extracción sin pago de tributos, y otras formas establecidas en el artículo 1 de la Ley 28008."
    },
    {
        "id": 4, "perfil": "Especialista SUNAT", "tema": "Sanciones",
        "pregunta": "¿Qué infracciones aduaneras generan sanción de comiso de mercancías?",
        "respuesta_esperada": "El comiso procede cuando se encuentran mercancías no declaradas, prohibidas, restringidas sin autorización, o vinculadas a delitos aduaneros según la Tabla de Sanciones DS 418-2019-EF."
    },
    {
        "id": 5, "perfil": "Especialista SUNAT", "tema": "Inmovilizacion vs Incautacion",
        "pregunta": "¿Cuál es la diferencia entre inmovilización e incautación de mercancías?",
        "respuesta_esperada": "La inmovilización es una medida preventiva temporal que no transfiere la posesión. La incautación implica la aprehensión física de la mercancía por la autoridad aduanera."
    },
    {
        "id": 6, "perfil": "Especialista SUNAT", "tema": "Defraudacion",
        "pregunta": "¿Qué es la defraudación de rentas de aduana y cuál es su sanción penal?",
        "respuesta_esperada": "La defraudación de rentas es el perjuicio al fisco mediante subvaluación u otros medios. La sanción es de 5 a 8 años de pena privativa de libertad según la Ley 28008."
    },

    # OPERADOR DE COMERCIO EXTERIOR
    {
        "id": 7, "perfil": "Operador OCE", "tema": "Drawback",
        "pregunta": "¿Cuáles son los requisitos para acogerse al régimen de drawback?",
        "respuesta_esperada": "El exportador debe haber importado insumos incorporados en el producto exportado, presentar solicitud dentro del plazo, y el beneficio es el 3% del valor FOB exportado."
    },
    {
        "id": 8, "perfil": "Operador OCE", "tema": "Arancel",
        "pregunta": "¿Cuánto paga de arancel quien importa laptops desde China?",
        "respuesta_esperada": "Las laptops y computadoras personales clasifican en la partida 8471 con arancel del 0% ad valorem según el Arancel de Aduanas 2022."
    },
    {
        "id": 9, "perfil": "Operador OCE", "tema": "Canales de control",
        "pregunta": "¿Cuáles son los canales de control aduanero y qué implica cada uno?",
        "respuesta_esperada": "Canal verde: sin revisión. Canal naranja: revisión documentaria. Canal rojo: reconocimiento físico de la mercancía."
    },
    {
        "id": 10, "perfil": "Operador OCE", "tema": "Despacho anticipado",
        "pregunta": "¿Cuál es el plazo para regularizar un despacho anticipado?",
        "respuesta_esperada": "El plazo es de 15 días calendario contados desde el día siguiente del término de la descarga, según DESPA-PG.01."
    },
    {
        "id": 11, "perfil": "Operador OCE", "tema": "Exportacion",
        "pregunta": "¿Qué documentos se requieren para la exportación definitiva de mercancías?",
        "respuesta_esperada": "Se requiere declaración aduanera de mercancías, factura comercial, documento de transporte, lista de empaque y autorizaciones de entidades competentes cuando corresponda."
    },
    {
        "id": 12, "perfil": "Operador OCE", "tema": "Agente de Aduana",
        "pregunta": "¿Cuáles son las obligaciones del agente de aduana en el despacho aduanero?",
        "respuesta_esperada": "El agente de aduana debe actuar como representante del importador/exportador, transmitir la declaración, presentar documentos sustentatorios y responder por la veracidad de la información."
    },
    {
        "id": 13, "perfil": "Operador OCE", "tema": "Abandono Legal",
        "pregunta": "¿Qué es el abandono legal de mercancías y en qué plazo se produce?",
        "respuesta_esperada": "El abandono legal se produce cuando las mercancías no son destinadas dentro de los 15 días calendario siguientes al término de la descarga."
    },

    # CIUDADANO
    {
        "id": 14, "perfil": "Ciudadano", "tema": "Equipaje",
        "pregunta": "¿Cuánto equipaje puedo traer del extranjero sin pagar impuestos?",
        "respuesta_esperada": "Cada viajero puede traer hasta USD 500 en bienes de uso personal sin pagar impuestos, siempre que no sean para comercio según el Reglamento de Equipaje y Menaje."
    },
    {
        "id": 15, "perfil": "Ciudadano", "tema": "Drone",
        "pregunta": "¿Puedo importar un drone desde Estados Unidos? ¿Qué impuestos pago?",
        "respuesta_esperada": "Los drones pueden importarse cumpliendo requisitos de SUCAMEC y pagando el arancel correspondiente según la partida arancelaria 8806."
    },
    {
        "id": 16, "perfil": "Ciudadano", "tema": "No declaracion",
        "pregunta": "¿Qué pasa si no declaro mercancías al ingresar al Perú?",
        "respuesta_esperada": "Las mercancías no declaradas pueden ser objeto de comiso y el viajero puede ser sancionado con multa. Si el valor supera las 4 UIT puede configurar delito de contrabando."
    },
    {
        "id": 17, "perfil": "Ciudadano", "tema": "Medicamentos",
        "pregunta": "¿Puedo traer medicamentos del extranjero? ¿Hay límites?",
        "respuesta_esperada": "Se pueden traer medicamentos para uso personal en cantidad razonable. Los medicamentos son mercancías restringidas que requieren autorización de DIGEMID para importaciones comerciales."
    },
    {
        "id": 18, "perfil": "Ciudadano", "tema": "Courier",
        "pregunta": "¿Qué es el régimen de envíos de entrega rápida o courier?",
        "respuesta_esperada": "Es un régimen especial para envíos de hasta USD 2000 transportados por empresas courier autorizadas, con proceso simplificado de despacho aduanero."
    },
    {
        "id": 19, "perfil": "Ciudadano", "tema": "Compras online",
        "pregunta": "¿Puedo comprar por internet en el extranjero y traer el paquete al Perú?",
        "respuesta_esperada": "Sí, mediante el régimen de envíos postales o courier. Envíos hasta USD 200 ingresan sin pagar arancel. Entre USD 200 y 2000 pagan arancel simplificado."
    },
    {
        "id": 20, "perfil": "Ciudadano", "tema": "Declaracion dinero",
        "pregunta": "¿Cuánto dinero en efectivo puedo llevar o traer del extranjero?",
        "respuesta_esperada": "Se puede llevar o traer cualquier cantidad de dinero, pero montos superiores a USD 10,000 deben declararse obligatoriamente según el DS 195-2013-EF."
    },
]

# ═══════════════════════════════════════════════════════════════
# EVALUACION AUTOMATICA CON RAGAS
# ═══════════════════════════════════════════════════════════════
def evaluar_con_ragas(pregunta, respuesta, contextos, respuesta_esperada):
    """Evalua con RAGAS usando Groq como LLM judge."""
    try:
        from ragas import evaluate
        from ragas.metrics import faithfulness, answer_relevancy
        from datasets import Dataset
        from langchain_groq import ChatGroq
        from langchain_huggingface import HuggingFaceEmbeddings

        llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)
        embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-m3")

        data = {
            "question": [pregunta],
            "answer": [respuesta],
            "contexts": [contextos],
            "ground_truth": [respuesta_esperada],
        }
        dataset = Dataset.from_dict(data)
        result = evaluate(
            dataset,
            metrics=[faithfulness, answer_relevancy],
            llm=llm,
            embeddings=embeddings,
        )
        return {
            "faithfulness": round(float(result["faithfulness"]), 3),
            "answer_relevancy": round(float(result["answer_relevancy"]), 3),
        }
    except Exception as e:
        return {"faithfulness": None, "answer_relevancy": None, "error": str(e)[:50]}

# ═══════════════════════════════════════════════════════════════
# EVALUACION MANUAL (tu criterio como experto SUNAT)
# ═══════════════════════════════════════════════════════════════
def evaluar_manualmente(caso, respuesta):
    """Solicita evaluacion manual al usuario."""
    print("\n📋 EVALUACION MANUAL (tú como experto):")
    print(f"   Respuesta esperada: {caso['respuesta_esperada'][:100]}...")
    print()

    scores = {}
    criterios = [
        ("precision",   "¿La respuesta es normativamente correcta? (1-5)"),
        ("relevancia",  "¿Responde lo que se preguntó? (1-5)"),
        ("utilidad",    "¿Es útil para el usuario final? (1-5)"),
        ("alucinacion", "¿Hay alucinaciones o datos inventados? (0=sí hay, 5=no hay)"),
    ]

    for key, pregunta_eval in criterios:
        while True:
            try:
                val = int(input(f"   {pregunta_eval}: "))
                if 0 <= val <= 5:
                    scores[key] = val
                    break
                print("   Ingresa un número entre 0 y 5")
            except ValueError:
                print("   Número inválido")

    promedio = sum(scores.values()) / len(scores)
    scores["promedio_manual"] = round(promedio, 2)
    return scores

# ═══════════════════════════════════════════════════════════════
# EJECUCION PRINCIPAL
# ═══════════════════════════════════════════════════════════════
print("=" * 70)
print("EVALUACION COMPLETA - ADUANA-GPT")
print("RAGAS (automatico) + Evaluacion Manual (experto)")
print("=" * 70)

modo = input("\n¿Modo de evaluacion?\n  1 = Solo RAGAS (automatico)\n  2 = Solo manual\n  3 = Ambos (completo)\nOpcion: ").strip()

resultados = []

for caso in CASOS:
    print(f"\n{'='*70}")
    print(f"CASO {caso['id']:02d}/20 | {caso['perfil']} | {caso['tema']}")
    print(f"PREGUNTA: {caso['pregunta']}")
    print(f"{'─'*70}")

    # Obtener respuesta del agente
    inicio = time.time()
    try:
        respuesta = consultar(caso["pregunta"])
        tiempo = round(time.time() - inicio, 1)
        print(f"RESPUESTA ({tiempo}s):\n{respuesta}")
        estado = "OK"
    except Exception as e:
        respuesta = f"ERROR: {str(e)[:100]}"
        tiempo = round(time.time() - inicio, 1)
        estado = "ERROR"
        print(f"ERROR: {respuesta}")

    resultado = {
        "id": caso["id"],
        "perfil": caso["perfil"],
        "tema": caso["tema"],
        "pregunta": caso["pregunta"],
        "respuesta": respuesta[:300],
        "tiempo_seg": tiempo,
        "estado": estado,
    }

    # Obtener contextos para RAGAS
    if estado == "OK" and modo in ["1", "3"]:
        try:
            col = "procedimientos_fiscalizacion" if "ACE" in caso["tema"] or "Inmo" in caso["tema"] else "procedimientos_despacho"
            contextos = [_buscar(col, caso["pregunta"], k=2)]
        except:
            contextos = [respuesta]

        print("\n🤖 Evaluando con RAGAS...")
        scores_ragas = evaluar_con_ragas(
            caso["pregunta"], respuesta,
            contextos, caso["respuesta_esperada"]
        )
        resultado.update(scores_ragas)
        print(f"   Faithfulness:      {scores_ragas.get('faithfulness', 'N/A')}")
        print(f"   Answer Relevancy:  {scores_ragas.get('answer_relevancy', 'N/A')}")

    # Evaluacion manual
    if estado == "OK" and modo in ["2", "3"]:
        scores_manual = evaluar_manualmente(caso, respuesta)
        resultado.update(scores_manual)
        print(f"   Promedio manual:   {scores_manual['promedio_manual']}/5")

    resultados.append(resultado)

    # Guardar progreso
    with open("data/evaluacion_resultados.json", "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2)

# ═══════════════════════════════════════════════════════════════
# RESUMEN FINAL
# ═══════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("RESUMEN FINAL DE EVALUACION")
print("=" * 70)

ok = [r for r in resultados if r["estado"] == "OK"]
errores = [r for r in resultados if r["estado"] == "ERROR"]

print(f"\nTotal evaluados:    {len(resultados)}/20")
print(f"Exitosos:           {len(ok)}")
print(f"Errores:            {len(errores)}")

if ok:
    tiempo_prom = sum(r["tiempo_seg"] for r in ok) / len(ok)
    print(f"Tiempo promedio:    {tiempo_prom:.1f}s")

    if "faithfulness" in ok[0] and ok[0]["faithfulness"] is not None:
        faith = [r["faithfulness"] for r in ok if r.get("faithfulness") is not None]
        relev = [r["answer_relevancy"] for r in ok if r.get("answer_relevancy") is not None]
        if faith:
            print(f"Faithfulness prom:  {sum(faith)/len(faith):.3f}")
        if relev:
            print(f"Answer Relevancy:   {sum(relev)/len(relev):.3f}")

    if "promedio_manual" in ok[0]:
        manual = [r["promedio_manual"] for r in ok if r.get("promedio_manual") is not None]
        if manual:
            print(f"Score manual prom:  {sum(manual)/len(manual):.2f}/5")

print(f"\nPor perfil:")
for perfil in ["Especialista SUNAT", "Operador OCE", "Ciudadano"]:
    casos_perfil = [r for r in resultados if r["perfil"] == perfil]
    ok_perfil = sum(1 for r in casos_perfil if r["estado"] == "OK")
    print(f"  {perfil:35} -> {ok_perfil}/{len(casos_perfil)} OK")

print(f"\nResultados guardados en: data/evaluacion_resultados.json")
print("\nEVALUACION COMPLETADA")