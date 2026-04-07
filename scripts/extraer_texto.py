import re
import json
import pdfplumber
from pathlib import Path
from bs4 import BeautifulSoup
import chardet


RAW_DIR       = Path("data/raw")
PROCESSED_DIR = Path("data/processed")
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

def detectar_encoding(ruta: Path) -> str:
    """Detecta el encoding real del archivo."""
    with open(ruta, "rb") as f:
        raw = f.read(10000)
    resultado = chardet.detect(raw)
    encoding = resultado.get("encoding", "utf-8") or "utf-8"
    # SUNAT usa windows-1252 o latin-1 frecuentemente
    if encoding.lower() in ["ascii", "windows-1252", "iso-8859-1", "latin-1"]:
        return "windows-1252"
    return encoding

def leer_html(ruta: Path) -> str:
    """Lee HTML probando multiples encodings."""
    # Intentar en orden de probabilidad para SUNAT
    for enc in ["windows-1252", "latin-1", "utf-8", "iso-8859-1"]:
        try:
            contenido = ruta.read_text(encoding=enc, errors="strict")
            # Verificar que no haya caracteres corruptos tipicos
            if "ï¿½" not in contenido and "Ã" not in contenido:
                return contenido
        except (UnicodeDecodeError, LookupError):
            continue
    # Ultimo recurso: leer con reemplazo de errores
    return ruta.read_text(encoding="windows-1252", errors="replace")

def limpiar_texto(texto: str) -> str:
    """Limpia el texto extraido."""
    # Eliminar caracteres de control excepto saltos de linea
    texto = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', texto)
    # Normalizar espacios multiples
    texto = re.sub(r' {3,}', ' ', texto)
    # Normalizar saltos de linea multiples
    texto = re.sub(r'\n{4,}', '\n\n\n', texto)
    # Eliminar lineas que solo tienen espacios
    lineas = [l.rstrip() for l in texto.split('\n')]
    texto = '\n'.join(lineas)
    return texto.strip()

def extraer_html(ruta: Path) -> str:
    """Extrae texto limpio de un HTML."""
    html = leer_html(ruta)
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "nav", "header",
                     "footer", "meta", "link", "noscript"]):
        tag.decompose()
    texto = soup.get_text(separator="\n")

    # Si el texto es muy corto, el contenido puede estar
    # fuera del tag </html> (HTML malformado de SUNAT)
    if len(texto.split()) < 200:
        # Buscar contenido despues de </html> o </body>
        for tag_cierre in ["</html>", "</body>", "</HTML>", "</BODY>"]:
            idx = html.lower().rfind(tag_cierre.lower())
            if idx > 0:
                resto = html[idx + len(tag_cierre):]
                if len(resto.strip()) > 100:
                    soup2 = BeautifulSoup(resto, "lxml")
                    for tag in soup2(["script", "style"]):
                        tag.decompose()
                    texto_extra = soup2.get_text(separator="\n")
                    if len(texto_extra.split()) > len(texto.split()):
                        texto = texto + "\n\n" + texto_extra

    return limpiar_texto(texto)

def extraer_pdf(ruta: Path) -> str:
    """Extrae texto de un PDF."""
    texto = ""
    with pdfplumber.open(ruta) as pdf:
        for pagina in pdf.pages:
            t = pagina.extract_text()
            if t:
                texto += t + "\n"
    return limpiar_texto(texto)

# ── Verificacion rapida de encoding ──────────────────────────
print("=" * 60)
print("EXTRACCION DE TEXTO - ADUANA-GPT")
print("=" * 60)

# Test rapido: verificar que los caracteres se lean bien
archivo_test = RAW_DIR / "gja01_ley_procedimiento_administrativo.html"
if archivo_test.exists():
    texto_test = extraer_html(archivo_test)
    # Buscar palabras con tildes o enie
    tiene_tildes = any(c in texto_test for c in "áéíóúÁÉÍÓÚñÑ")
    tiene_corruptos = "ï¿½" in texto_test or "Ã" in texto_test
    print(f"\nTest de encoding:")
    print(f"  Tildes correctas: {'SI' if tiene_tildes else 'NO'}")
    print(f"  Caracteres corruptos: {'SI - HAY PROBLEMA' if tiene_corruptos else 'NO'}")
    if tiene_tildes and not tiene_corruptos:
        print("  Resultado: OK - Encoding correcto\n")
    else:
        print("  Resultado: REVISAR\n")

archivos = list(RAW_DIR.glob("*.html")) + list(RAW_DIR.glob("*.pdf"))
resultados = []

for archivo in sorted(archivos):
    print(f"Procesando: {archivo.name[:55]}...")
    try:
        if archivo.suffix == ".html":
            texto = extraer_html(archivo)
        else:
            texto = extraer_pdf(archivo)

        destino = PROCESSED_DIR / f"{archivo.stem}.txt"
        destino.write_text(texto, encoding="utf-8")

        palabras = len(texto.split())
        # Verificar calidad
        corruptos = texto.count("ï¿½") + texto.count("Ã±")
        estado = "OK" if corruptos == 0 else f"REVISAR ({corruptos} chars corruptos)"
        print(f"   {estado} - {palabras:,} palabras")

        resultados.append({
            "archivo": archivo.name,
            "palabras": palabras,
            "chars_corruptos": corruptos,
        })
    except Exception as e:
        print(f"   ERROR: {e}")

# Resumen
total_palabras = sum(r["palabras"] for r in resultados)
con_problemas  = [r for r in resultados if r["chars_corruptos"] > 0]

print("\n" + "=" * 60)
print("RESUMEN")
print("=" * 60)
print(f"Archivos procesados: {len(resultados)}")
print(f"Total de palabras:   {total_palabras:,}")
print(f"Con problemas:       {len(con_problemas)}")

if con_problemas:
    print("\nArchivos con caracteres corruptos:")
    for r in con_problemas:
        print(f"  - {r['archivo']}: {r['chars_corruptos']} corruptos")

# Guardar resumen
(PROCESSED_DIR / "resumen_extraccion.json").write_text(
    json.dumps(resultados, ensure_ascii=False, indent=2),
    encoding="utf-8"
)

print("\nCOMPLETADO")