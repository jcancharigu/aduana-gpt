import re
from pathlib import Path
from sentence_transformers import SentenceTransformer
import chromadb
from tqdm import tqdm

PROCESSED_DIR = Path("data/processed")
CHROMA_DIR    = Path("data/vectorstore")
CHROMA_DIR.mkdir(parents=True, exist_ok=True)

CHUNK_SIZE    = 400
CHUNK_OVERLAP = 80

# Mapeo automatico: prefijo del archivo -> coleccion ChromaDB
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

def hacer_chunks(texto: str, tamano: int, overlap: int) -> list:
    patron = r'(?=Art[ií]culo\s+\d+|ARTICULO\s+\d+|Cap[ií]tulo\s+[IVX\d]+)'
    partes = re.split(patron, texto)
    partes = [p.strip() for p in partes if len(p.strip()) > 100]
    chunks = []
    for parte in partes:
        palabras = parte.split()
        if len(palabras) <= tamano:
            chunks.append(parte)
        else:
            i = 0
            while i < len(palabras):
                chunk = " ".join(palabras[i:i + tamano])
                chunks.append(chunk)
                i += tamano - overlap
    return chunks if chunks else [texto]

print("=" * 60)
print("INDEXACION EN CHROMADB - ADUANA-GPT")
print("=" * 60)

print("\nCargando modelo BGE-M3...")
modelo = SentenceTransformer("BAAI/bge-m3")
print("   OK")

cliente = chromadb.PersistentClient(path=str(CHROMA_DIR))

archivos = [f for f in PROCESSED_DIR.glob("*.txt")
            if f.name != "resumen_extraccion.json"]

print(f"\nArchivos a indexar: {len(archivos)}")

# Mostrar distribucion por coleccion
dist = {}
for f in archivos:
    col = asignar_coleccion(f.stem)
    dist[col] = dist.get(col, 0) + 1
print("\nDistribucion por coleccion:")
for col, count in sorted(dist.items()):
    print(f"  {col:40} -> {count} archivos")

resumen = []
total_chunks = 0

for archivo in sorted(archivos):
    nombre = archivo.stem
    coleccion_nombre = asignar_coleccion(nombre)

    print(f"\nIndexando: {archivo.name[:50]}...")
    print(f"  Coleccion: {coleccion_nombre}")

    texto = archivo.read_text(encoding="utf-8")
    chunks = hacer_chunks(texto, CHUNK_SIZE, CHUNK_OVERLAP)
    print(f"  Chunks: {len(chunks)}")

    try:
        coleccion = cliente.get_collection(coleccion_nombre)
    except Exception:
        coleccion = cliente.create_collection(
            coleccion_nombre,
            metadata={"hnsw:space": "cosine"}
        )

    LOTE = 32
    for i in tqdm(range(0, len(chunks), LOTE),
                  desc=f"  Indexando", leave=False):
        lote_chunks = chunks[i:i + LOTE]
        lote_ids    = [f"{nombre}_{i+j}" for j in range(len(lote_chunks))]
        lote_meta   = [{"fuente": nombre, "coleccion": coleccion_nombre}
                       for _ in lote_chunks]
        embeddings  = modelo.encode(
            lote_chunks,
            normalize_embeddings=True,
            show_progress_bar=False
        ).tolist()
        coleccion.add(
            documents=lote_chunks,
            embeddings=embeddings,
            metadatas=lote_meta,
            ids=lote_ids
        )

    total_chunks += len(chunks)
    resumen.append({
        "archivo": archivo.name,
        "coleccion": coleccion_nombre,
        "chunks": len(chunks)
    })
    print(f"  OK - {len(chunks)} chunks indexados")

print("\n" + "=" * 60)
print("RESUMEN FINAL")
print("=" * 60)
for r in resumen:
    print(f"  {r['archivo']:50} -> {r['chunks']:4} chunks -> '{r['coleccion']}'")

print(f"\nTOTAL chunks: {total_chunks}")
print("\nColecciones en ChromaDB:")
for col in cliente.list_collections():
    c = cliente.get_collection(col.name)
    print(f"  {col.name:40} -> {c.count()} documentos")

print("\nINDEXACION COMPLETADA")