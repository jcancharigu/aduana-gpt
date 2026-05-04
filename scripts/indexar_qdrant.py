"""
Indexa los documentos procesados en Qdrant Cloud usando Jina AI para embeddings.
Ejecutar una sola vez (o cuando se actualice la normativa).

Características:
- IDs determinísticos (re-run no duplica datos)
- Checkpoint: retoma desde donde se quedó si falla
- Retry automático para Jina (429) y Qdrant (timeout)

Requiere en .env:
    JINA_API_KEY
    QDRANT_URL
    QDRANT_API_KEY
"""

import os
import re
import time
import json
import uuid
import requests
from pathlib import Path
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from tqdm import tqdm

load_dotenv()

JINA_KEY      = os.getenv("JINA_API_KEY")
QDRANT_URL    = os.getenv("QDRANT_URL")
QDRANT_APIKEY = os.getenv("QDRANT_API_KEY")

PROCESSED_DIR    = Path("data/processed")
CHECKPOINT_FILE  = Path("data/indexacion_checkpoint.json")
VECTOR_DIM       = 1024
JINA_BATCH       = 20    # chunks por llamada a Jina
QDRANT_BATCH     = 5     # puntos por llamada a Qdrant
SLEEP_JINA       = 2.0   # segundos entre lotes Jina
CHUNK_SIZE       = 400
CHUNK_OVERLAP    = 80

COLECCIONES = [
    "ley_28008",
    "ley_general_aduanas",
    "procedimientos_fiscalizacion",
    "procedimientos_despacho",
    "procedimientos_recaudacion",
    "normas_asociadas",
    "normas_generales",
    "arancel",
]


# ── Checkpoint ────────────────────────────────────────────────
def cargar_checkpoint() -> set:
    if CHECKPOINT_FILE.exists():
        return set(json.loads(CHECKPOINT_FILE.read_text()))
    return set()

def guardar_checkpoint(indexados: set):
    CHECKPOINT_FILE.parent.mkdir(exist_ok=True)
    CHECKPOINT_FILE.write_text(json.dumps(list(indexados)))


# ── Mapeo colecciones ─────────────────────────────────────────
def asignar_coleccion(nombre: str) -> str:
    if nombre.startswith("arancel") or nombre.startswith("ds_163"):
        return "arancel"
    elif nombre.startswith("gja05") or nombre.startswith("gja_00_09"):
        return "ley_28008"
    elif nombre.startswith("gja03") or nombre.startswith("gja_00_04") or nombre.startswith("gja_00_05"):
        return "ley_general_aduanas"
    elif nombre.startswith("gja01") or nombre.startswith("gja_00_01") or \
         nombre.startswith("gja_00_02") or nombre.startswith("gja_00_03") or \
         nombre.startswith("gja_00_13") or nombre.startswith("gja_00_20"):
        return "normas_generales"
    elif nombre.startswith("gja_00"):
        return "normas_asociadas"
    elif nombre.startswith("control"):
        return "procedimientos_fiscalizacion"
    elif nombre.startswith("despa") or nombre.startswith("esp_despa"):
        return "procedimientos_despacho"
    elif nombre.startswith("reca"):
        return "procedimientos_recaudacion"
    else:
        return "procedimientos_despacho"


# ── Chunking ──────────────────────────────────────────────────
def hacer_chunks(texto: str) -> list:
    patron = (
        r'(?='
        r'Art[ií]culo\s+\d+|'
        r'ARTICULO\s+\d+|'
        r'Art\.\s*\d+[°º]?|'
        r'Cap[ií]tulo\s+[IVXivx\d]+|'
        r'CAPITULO\s+[IVXivx\d]+|'
        r'SECCION\s+[IVXivx\d]+|'
        r'Secci[oó]n\s+[IVXivx\d]+|'
        r'TITULO\s+[IVXivx\d]+|'
        r'T[ií]tulo\s+[IVXivx\d]+|'
        r'DISPOSICION\s+|'
        r'Literal\s+[A-Z]\.|'
        r'LITERAL\s+[A-Z]\.|'
        r'Numeral\s+\d+\.|'
        r'NUMERAL\s+\d+\.'
        r')'
    )
    partes = re.split(patron, texto)
    partes = [p.strip() for p in partes if len(p.strip()) > 80]
    chunks = []
    for parte in partes:
        palabras = parte.split()
        if len(palabras) <= CHUNK_SIZE:
            chunks.append(parte)
        else:
            i = 0
            while i < len(palabras):
                chunks.append(" ".join(palabras[i:i + CHUNK_SIZE]))
                i += CHUNK_SIZE - CHUNK_OVERLAP
    return chunks if chunks else [texto]


# ── Jina con retry ────────────────────────────────────────────
def embed_batch(textos: list, reintentos: int = 6) -> list:
    for intento in range(reintentos):
        try:
            resp = requests.post(
                "https://api.jina.ai/v1/embeddings",
                headers={"Authorization": f"Bearer {JINA_KEY}", "Content-Type": "application/json"},
                json={
                    "model": "jina-embeddings-v3",
                    "input": textos,
                    "task": "retrieval.passage",
                    "dimensions": VECTOR_DIM,
                },
                timeout=60,
            )
            if resp.status_code == 429:
                espera = 2 ** (intento + 1)
                print(f"\n  Rate limit Jina — esperando {espera}s...")
                time.sleep(espera)
                continue
            resp.raise_for_status()
            return [item["embedding"] for item in resp.json()["data"]]
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            espera = 2 ** (intento + 1)
            print(f"\n  Error red Jina ({type(e).__name__}) — reintentando en {espera}s...")
            time.sleep(espera)
    raise RuntimeError("Jina API: demasiados reintentos")


# ── Qdrant upsert con retry ───────────────────────────────────
def upsert_con_retry(cliente, coleccion: str, puntos: list, reintentos: int = 6):
    for intento in range(reintentos):
        try:
            cliente.upsert(collection_name=coleccion, points=puntos)
            time.sleep(0.3)  # pausa breve tras cada escritura
            return
        except Exception as e:
            if intento < reintentos - 1:
                espera = 2 ** (intento + 1)
                print(f"\n  Error Qdrant ({type(e).__name__}) — reintentando en {espera}s...")
                time.sleep(espera)
            else:
                raise


# ── Main ──────────────────────────────────────────────────────
print("=" * 60)
print("INDEXACION EN QDRANT CLOUD — ADUANA-GPT")
print("=" * 60)

cliente = QdrantClient(url=QDRANT_URL, api_key=QDRANT_APIKEY, timeout=60)

hay_checkpoint = CHECKPOINT_FILE.exists()

print("\nPreparando colecciones...")
for col in COLECCIONES:
    if not hay_checkpoint:
        # Primera ejecución limpia: borrar para evitar duplicados de intentos anteriores
        if cliente.collection_exists(col):
            cliente.delete_collection(col)
        cliente.create_collection(
            collection_name=col,
            vectors_config=VectorParams(size=VECTOR_DIM, distance=Distance.COSINE),
        )
        print(f"  Recreada: {col}")
    else:
        if not cliente.collection_exists(col):
            cliente.create_collection(
                collection_name=col,
                vectors_config=VectorParams(size=VECTOR_DIM, distance=Distance.COSINE),
            )
            print(f"  Creada: {col}")
        else:
            print(f"  OK: {col}")

archivos = sorted(f for f in PROCESSED_DIR.glob("*.txt")
                  if f.name != "resumen_extraccion.json")

indexados   = cargar_checkpoint()
pendientes  = [f for f in archivos if f.stem not in indexados]
total_files = len(archivos)

print(f"\nArchivos totales : {total_files}")
print(f"Ya indexados     : {len(indexados)}")
print(f"Pendientes       : {len(pendientes)}")

total_chunks = 0

for archivo in pendientes:
    nombre    = archivo.stem
    coleccion = asignar_coleccion(nombre)
    texto     = archivo.read_text(encoding="utf-8")
    chunks    = hacer_chunks(texto)

    print(f"\n{archivo.name[:55]}  →  {coleccion}  ({len(chunks)} chunks)")

    # Embeddings en lotes
    for i in tqdm(range(0, len(chunks), JINA_BATCH), desc="  Embeddings", leave=False):
        lote_chunks = chunks[i:i + JINA_BATCH]
        embeddings  = embed_batch(lote_chunks)

        # Construir puntos con ID determinístico (UUID5) y embedding listo
        lote_puntos = [
            PointStruct(
                id=str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{nombre}_{i + j}")),
                vector=emb,
                payload={"text": chunk, "fuente": nombre, "coleccion": coleccion},
            )
            for j, (chunk, emb) in enumerate(zip(lote_chunks, embeddings))
        ]

        # Sub-lotes para Qdrant
        for k in range(0, len(lote_puntos), QDRANT_BATCH):
            upsert_con_retry(cliente, coleccion, lote_puntos[k:k + QDRANT_BATCH])

        time.sleep(SLEEP_JINA)

    total_chunks += len(chunks)
    indexados.add(nombre)
    guardar_checkpoint(indexados)
    print(f"  ✓ guardado en checkpoint")

# ── Resumen ───────────────────────────────────────────────────
print("\n" + "=" * 60)
print("RESUMEN FINAL")
print("=" * 60)
print(f"\nTotal chunks indexados esta sesión: {total_chunks}")
print("\nColecciones en Qdrant Cloud:")
for col in COLECCIONES:
    info = cliente.get_collection(col)
    print(f"  {col:40} → {info.points_count} vectores")

print("\nINDEXACION COMPLETADA")
