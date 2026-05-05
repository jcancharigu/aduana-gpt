# 🛃 ADUANA-GPT

**Agente de IA con RAG Multidominio para consultas sobre normativa aduanera peruana**

> Proyecto Integrador — Maestría en Ciencia de Datos · Universidad Nacional de Ingeniería · 2026-1  
> Desarrollado por: **Jaime Canchari Gutierrez** | SUNAT — División de Control Operativo IAMC  
> Docente: **Melba Torres**

![Python](https://img.shields.io/badge/Python-3.11-blue)
![LangGraph](https://img.shields.io/badge/LangGraph-1.1.6-green)
![Llama](https://img.shields.io/badge/Llama-3.3_70B-orange)
![Nodos](https://img.shields.io/badge/Nodos_LangGraph-7-purple)
![Chunks](https://img.shields.io/badge/Chunks-3%2C861-teal)
![Streaming](https://img.shields.io/badge/Streaming-token_a_token-cyan)
![Costo](https://img.shields.io/badge/Costo_total-S/._0.00-brightgreen)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## Tabla de contenidos

1. [Descripción](#-descripción)
2. [Características principales](#-características-principales)
3. [Arquitectura LangGraph](#️-arquitectura-langgraph)
4. [Los 5 dominios del negocio aduanero](#-los-5-dominios-del-negocio-aduanero)
5. [Pipeline RAG](#-pipeline-rag)
6. [Cadena de fallback LLM](#-cadena-de-fallback-llm)
7. [Memoria conversacional y caché](#-memoria-conversacional-y-caché)
8. [Observabilidad con Langfuse](#-observabilidad-con-langfuse)
9. [Interfaz Streamlit](#️-interfaz-streamlit)
10. [Stack tecnológico](#️-stack-tecnológico)
11. [Base de conocimiento](#-base-de-conocimiento)
12. [Normativa cubierta](#-normativa-cubierta)
13. [Parámetros clave](#-parámetros-clave-del-agente)
14. [Instalación](#-instalación-en-4-pasos)
15. [Variables de entorno](#-variables-de-entorno)
16. [Estructura del proyecto](#-estructura-del-proyecto)
17. [Evaluación](#-evaluación)
18. [Ejemplos de consultas](#-ejemplos-de-consultas)
19. [Despliegue en Streamlit Community Cloud](#️-despliegue-en-streamlit-community-cloud)
20. [Contexto académico](#-contexto-académico)

---

## 📋 Descripción

ADUANA-GPT es un agente de inteligencia artificial especializado en normativa aduanera peruana. Permite a **especialistas de SUNAT**, **operadores de comercio exterior** y **ciudadanos** realizar consultas en lenguaje natural sobre leyes, reglamentos, procedimientos y partidas arancelarias vigentes.

El agente responde con **cita exacta del artículo y documento fuente**, orientando sobre sanciones, multas, inmovilizaciones, incautaciones, regímenes aduaneros, drawback y cualquier materia aduanera según corresponda. Cada respuesta incluye chips de fuente con enlace directo al portal oficial de SUNAT.

**Problema que resuelve:** La normativa aduanera peruana está compuesta por más de 148 documentos (leyes, decretos supremos, procedimientos generales y específicos, instructivos y el Arancel de Aduanas 2022) dispersos en distintos portales de SUNAT. Consultarla requiere conocimiento técnico especializado, horas de búsqueda manual y acceso a asesoría jurídica costosa.

**Solución:** Un agente RAG que indexa toda esa normativa como unidades semánticas completas (por artículo), la busca en paralelo según el dominio de la consulta y sintetiza una respuesta estructurada, citando artículos exactos, en menos de 5 segundos — con un costo total de **S/. 0.00**.

---

## ✨ Características principales

| Característica | Detalle |
|---|---|
| **Streaming token a token** | La respuesta aparece en ~0.5 s en lugar de esperar 5–10 s. Implementado con `stream_mode="messages"` de LangGraph, filtrando solo los tokens del nodo síntesis. |
| **Memoria conversacional** | Historial de 5 turnos (10 mensajes) preservado por sesión usando `MemorySaver` de LangGraph. Permite preguntas de seguimiento con contexto. |
| **RAG paralelo por dominio** | Cada nodo especializado lanza 2–3 búsquedas simultáneas con `ThreadPoolExecutor`, reduciendo la latencia de recuperación en ~60%. |
| **Fallback automático de LLM** | Si el modelo principal agota su límite diario, el sistema cambia automáticamente a llama-3.1-8b-instant y luego a gemini-2.0-flash. Sin interrupciones para el usuario. |
| **Caché SQLite** | Consultas idénticas se sirven en <0.5 s sin consumir tokens. Validez de 1 mes por entrada. Hash MD5 normalizado (minúsculas + trim). |
| **Observabilidad completa** | Trazas, latencia y scores automáticos enviados a Langfuse Cloud. Feedback explícito del usuario (👍 / 👎) también registrado. |
| **Evaluación RAGAS** | Métricas automáticas de recuperación y relevancia sobre 20 casos de prueba + evaluación manual experta en 4 dimensiones. |
| **Panel de métricas en tiempo real** | Score global, relevancia, referencias normativas, estructura y fluidez calculados en cada respuesta. Gráfica de evolución de sesión con Plotly. |
| **Historial persistente SQLite** | Todas las consultas, respuestas, dominios, tiempos y feedback se almacenan en `data/historial.db`. Exportable a JSON. |
| **Chips de fuente con enlace** | Los códigos de documentos citados en la respuesta (ej. `[DS-182-2013-EF]`) se convierten en chips clicables que enlazan al portal oficial SUNAT. |
| **Costo total: S/. 0.00** | 100% servicios cloud gratuitos. Sin tarjeta de crédito requerida. |

---

## 🏗️ Arquitectura LangGraph

El agente implementa un `StateGraph` de LangGraph con **7 nodos** y **aristas condicionales** alineadas a los 5 macroprocesos del negocio aduanero peruano.

```
Consulta del usuario
         │
         ▼
┌──────────────────────────┐
│  Nodo 1 — CLASIFICADOR   │  LLM clasifica en uno de 5 dominios
│  (llama-3.3-70b +        │  Si la respuesta no es válida → DESPACHO
│   fallback automático)   │
└────────────┬─────────────┘
             │  add_conditional_edges()
     ┌───────┴────────────────────────────────────┐
     │         │          │          │            │
     ▼         ▼          ▼          ▼            ▼
  DELITOS   CONTROL   DESPACHO  RECAUDACION  ORIENTACION
  Nodo 2A   Nodo 2B   Nodo 2C    Nodo 2D      Nodo 2E
  2 RAGs    2 RAGs    3 RAGs     3 RAGs       3 RAGs
  paralelos paralelos paralelos  paralelos    paralelos
     │         │          │          │            │
     └─────────┴──────────┴──────────┴────────────┘
                           │
                           ▼
               ┌───────────────────────┐
               │  Nodo 3 — SÍNTESIS    │  Genera respuesta estructurada
               │  llama-3.3-70b +      │  Streaming token a token
               │  fallback automático  │  max_tokens: 1 200
               │  Contexto: max 3 800  │  Historial: últimos 10 msg
               └───────────┬───────────┘
                           │
                           ▼
               ┌───────────────────────┐
               │  Langfuse Cloud       │  Trazas · latencia · scores
               └───────────┬───────────┘
                           │
                          END
```

### Estado del grafo (`EstadoAgente`)

```python
class EstadoAgente(TypedDict):
    pregunta:  str   # consulta del usuario
    intencion: str   # dominio clasificado: DELITOS | CONTROL | DESPACHO | RECAUDACION | ORIENTACION
    contexto:  str   # chunks recuperados por el nodo especializado (max 3 800 chars)
    respuesta: str   # respuesta generada por el nodo síntesis
    historial: list  # últimos 10 mensajes [{"rol": "user"|"assistant", "contenido": str}]
```

### Enrutamiento condicional

```python
grafo.add_conditional_edges(
    "clasificador",
    enrutar,   # lee estado["intencion"]
    {
        "DELITOS":     "delitos",
        "CONTROL":     "control",
        "DESPACHO":    "despacho",
        "RECAUDACION": "recaudacion",
        "ORIENTACION": "orientacion",
    }
)
```

---

## 🗂️ Los 5 dominios del negocio aduanero

| Dominio | Nodo | Qué cubre | Herramientas RAG activadas |
|---|---|---|---|
| **DELITOS** | 2A | Contrabando, defraudación de rentas, receptación, tráfico ilícito, delitos penales, Ley 28008 | `buscar_ley_28008` · `buscar_sanciones_multas` |
| **CONTROL** | 2B | ACE, aforo, inmovilización, incautación, precintos, inspección no intrusiva, fiscalización posterior | `buscar_procedimientos_fiscalizacion` · `buscar_ley_general_aduanas` |
| **DESPACHO** | 2C | Importación, exportación, regímenes aduaneros, drawback, depósito, tránsito, valoración OMC, arancel, partidas, prohibidas/restringidas, abandono legal | `buscar_procedimientos_despacho` · `buscar_arancel` · `buscar_mercancias_prohibidas_restringidas` |
| **RECAUDACION** | 2D | Tributos aduaneros, deuda, garantías, reclamos, devoluciones, fraccionamiento, multas administrativas | `buscar_procedimientos_recaudacion` · `buscar_sanciones_multas` · `buscar_ley_general_aduanas` |
| **ORIENTACION** | 2E | Equipaje viajeros, franquicia arancelaria, dinero en efectivo, menaje de casa, courier, envíos postales, compras online | `buscar_equipaje_viajeros` · `buscar_normas_asociadas` · `buscar_normas_generales` |

### Clasificador de intención (Nodo 1)

El prompt del clasificador describe con detalle los límites de cada dominio para evitar ambigüedades:

```
DELITOS      → contrabando, defraudación de rentas, receptación,
               tráfico ilícito de mercancías, Ley 28008, delitos penales

CONTROL      → ACE, aforo, inmovilización, incautación, precintos,
               inspección no intrusiva, fiscalización posterior al despacho

DESPACHO     → importación, exportación, regímenes aduaneros, drawback,
               depósito, tránsito, valoración OMC, arancel, partidas,
               mercancías prohibidas y restringidas, agente de aduana,
               abandono legal, despacho anticipado

RECAUDACION  → tributos aduaneros, deuda tributaria, garantías,
               reclamos, devoluciones, fraccionamiento, multas
               administrativas, sanciones, tabla de sanciones

ORIENTACION  → equipaje de viajeros, franquicia arancelaria,
               dinero en efectivo, menaje de casa, ciudadanos,
               compras por internet, medicamentos, courier,
               envíos postales, preguntas generales
```

Si la respuesta del clasificador no coincide con ningún dominio válido, se asigna **DESPACHO** como valor por defecto.

---

## 🔍 Pipeline RAG

Cada herramienta de búsqueda ejecuta un pipeline de **3 etapas**:

```
Consulta del usuario
       │
       ▼
┌─────────────────────────────────────┐
│  1. EMBEDDING                       │
│  Jina Embeddings v3 (API cloud)     │
│  task: "retrieval.query"            │
│  1 024 dimensiones                  │
└─────────────────┬───────────────────┘
                  │ vector query
                  ▼
┌─────────────────────────────────────┐
│  2. BÚSQUEDA VECTORIAL              │
│  Qdrant Cloud — colección específica│
│  k_retrieval = 5 candidatos         │
│  búsqueda por similitud coseno      │
└─────────────────┬───────────────────┘
                  │ 5 chunks
                  ▼
┌─────────────────────────────────────┐
│  3. RERANKING                       │
│  Jina Reranker v2 multilingual      │
│  modelo: jina-reranker-v2-base      │
│  k_final = 3 chunks seleccionados   │
└─────────────────┬───────────────────┘
                  │ 3 chunks con score de relevancia
                  ▼
           Contexto normativo
```

### Colecciones Qdrant

| Colección | Herramienta | Documentos |
|---|---|---|
| `ley_28008` | `buscar_ley_28008` | Ley 28008 + DS 121-2003-EF |
| `ley_general_aduanas` | `buscar_ley_general_aduanas` | DL 1053 + DS 010-2009-EF |
| `procedimientos_fiscalizacion` | `buscar_procedimientos_fiscalizacion` | 13 procedimientos de control |
| `procedimientos_despacho` | `buscar_procedimientos_despacho` | 95 procedimientos de despacho |
| `procedimientos_recaudacion` | `buscar_procedimientos_recaudacion` | 16 procedimientos de recaudación |
| `arancel` | `buscar_arancel` | Arancel de Aduanas 2022 |
| `normas_asociadas` | `buscar_normas_asociadas` / `buscar_equipaje_viajeros` / `buscar_sanciones_multas` / `buscar_mercancias_prohibidas_restringidas` | 11 normas asociadas |
| `normas_generales` | `buscar_normas_generales` | 6 normas generales |

### Truncación proporcional de contexto

Antes del nodo síntesis, el contexto acumulado (que puede provenir de 2–3 herramientas RAG) se trunca proporcionalmente si supera `_MAX_CONTEXTO = 3 800` caracteres:

```python
def _truncar_contexto(ctx: str) -> str:
    if len(ctx) <= _MAX_CONTEXTO:
        return ctx
    partes = re.split(r'(=== .+? ===\n?)', ctx)
    resultado, budget = "", _MAX_CONTEXTO
    for p in partes:
        if len(p) <= budget:
            resultado += p; budget -= len(p)
        else:
            resultado += p[:budget] + "\n[...contexto truncado]"; break
    return resultado
```

---

## 🔁 Cadena de fallback LLM

Cuando el modelo principal agota su límite diario de tokens (TPD), el sistema cambia automáticamente al siguiente modelo de la cadena, **sin interrumpir la sesión del usuario**:

```
llama-3.3-70b-versatile  →  llama-3.1-8b-instant  →  gemini-2.0-flash
    100K tokens/día             500K tokens/día          1M tokens/día
    (Groq API)                  (Groq API)               (Google AI Studio)
```

**Total disponible:** hasta 1.6M tokens/día combinados.

La lógica está centralizada en la función `_invocar()` utilizada por **todos** los nodos (clasificador y síntesis):

```python
_CADENA_LLM = [m for m in [llm, llm_fallback, llm_fallback2] if m is not None]

def _invocar(mensajes: list) -> object:
    ultimo_error = None
    for modelo in _CADENA_LLM:
        try:
            return modelo.invoke(mensajes)
        except Exception as e:
            err = str(e)
            if "tokens per day" in err.lower():
                nombre = getattr(modelo, "model", getattr(modelo, "model_name", "modelo"))
                print(f"[LLM] límite diario en {nombre}, probando siguiente...", flush=True)
                ultimo_error = e
                continue
            elif "rate_limit" in err.lower() or "429" in err:
                time.sleep(20)
                ultimo_error = e
                continue
            raise
    raise ultimo_error or Exception("Todos los modelos LLM han alcanzado su límite diario.")
```

---

## 🧠 Memoria conversacional y caché

### Memoria de sesión (MemorySaver)

LangGraph `MemorySaver` persiste el historial conversacional entre invocaciones del mismo `thread_id`. Cada sesión de Streamlit genera un UUID único como `thread_id`:

```python
memory = MemorySaver()
agente_compilado = grafo.compile(checkpointer=memory)
```

El nodo síntesis mantiene los últimos **10 mensajes (5 turnos)** en el estado para evitar desbordamiento del contexto del LLM:

```python
historial.append({"rol": "user",      "contenido": estado["pregunta"]})
historial.append({"rol": "assistant", "contenido": respuesta[:500]})
if len(historial) > 10:
    historial = historial[-10:]
```

### Caché de respuestas (SQLite)

Las consultas idénticas (misma pregunta normalizada) se sirven desde caché local en SQLite, evitando consumir tokens y reduciendo la latencia a <0.5 s:

- **Hash**: MD5 de la pregunta en minúsculas y sin espacios al inicio/final
- **TTL**: 1 mes (`datetime('now', '-1 month')`)
- **Contador de hits**: se incrementa en cada acierto de caché
- **Tabla**: `cache_respuestas` en `data/historial.db`

---

## 📊 Observabilidad con Langfuse

ADUANA-GPT envía trazas automáticas a **Langfuse Cloud** para monitorizar cada consulta:

### Datos registrados por traza

| Dato | Descripción |
|---|---|
| `input` | Pregunta original del usuario |
| `output` | Respuesta completa generada |
| `sessionId` | `thread_id` de la sesión Streamlit |
| `metadata.intencion` | Dominio clasificado |
| `score_global` | Puntuación 0–5 calculada automáticamente |
| `relevancia` | % de términos de la pregunta en la respuesta |
| `referencias` | % de referencias normativas detectadas |
| `estructura` | 100% si tiene base legal / procedimiento |
| `fluidez` | Score basado en longitud de oraciones |
| `user_feedback` | 1.0 (👍) o 0.0 (👎) cuando el usuario califica |

### Configuración

Las claves se leen de variables de entorno:
```env
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com
```

Si no se configuran, el agente funciona igualmente sin observabilidad.

---

## 🖥️ Interfaz Streamlit

La interfaz (`app.py`) es una aplicación Streamlit de layout wide con:

### Layout principal

```
┌─────────────────────────────────────┬───────────────────┐
│           ADUANA-GPT Header         │                   │
├─────────────────────────────────────┤   Panel de        │
│  Sidebar      │    Chat principal   │   métricas        │
│  ─────────    │    ─────────────    │   ─────────       │
│  Consultas    │    Historial de     │   KPIs sesión     │
│  rápidas (8)  │    mensajes         │   Gráfica score   │
│               │    ─────────────    │   Histórico       │
│  Base de      │    Input de texto   │   persistente     │
│  conocimiento │    + streaming      │                   │
│               │                    │                   │
│  Estado       │                    │                   │
│  Langfuse     │                    │                   │
└───────────────┴────────────────────┴───────────────────┘
```

### Características de la UI

- **Streaming visual**: el texto aparece token a token con cursor `▌` animado
- **Badge de dominio**: chip de color por dominio (rojo=DELITOS, amarillo=CONTROL, verde=DESPACHO, azul=RECAUDACION, morado=ORIENTACION) con tiempo de respuesta
- **Badge de caché**: chip `⚡ caché` cuando la respuesta viene del caché SQLite
- **Chips de fuente**: cada código normativo citado (`[DS-182-2013-EF]`, `[DESPA-PG.01]`, etc.) se renderiza como chip dorado con enlace al portal SUNAT
- **Panel de métricas por respuesta**: score 0–5, barras de progreso para relevancia, referencias, estructura y fluidez
- **Feedback**: botones 👍/👎 que guardan la calificación en SQLite y la envían a Langfuse
- **Panel lateral de KPIs**: score promedio de sesión, número de consultas, tiempo promedio, relevancia media y gráfica de evolución (Plotly)
- **Historial persistente**: últimas 5 consultas desde SQLite con score, dominio y feedback

### Cálculo de métricas de respuesta

```python
def calcular_metricas(pregunta, respuesta, tiempo) -> dict:
    # relevancia: palabras de la pregunta encontradas en la respuesta
    # referencias: menciones a normas aduaneras (art., ley n°, decreto, DESPA, etc.)
    # estructura: presencia de "Base legal" / "Procedimiento" / listas numeradas
    # fluidez: ratio palabras/oraciones (óptimo: 12-25 palabras/oración)
    # score_global: ponderación 30%+30%+15%+15%+10% → escala 0-5
```

---

## 🛠️ Stack Tecnológico

| Componente | Herramienta | Versión | Límite gratuito |
|---|---|---|---|
| LLM principal | Llama 3.3 70B via Groq API | — | 100K tokens/día |
| LLM fallback 1 | Llama 3.1 8B Instant via Groq | — | 500K tokens/día |
| LLM fallback 2 | Gemini 2.0 Flash via Google AI Studio | — | 1M tokens/día |
| Framework agente | LangGraph | 1.1.6 | Gratuito (open source) |
| Cadena LLM | LangChain | 1.0.0 | Gratuito (open source) |
| Grafo | LangGraph StateGraph | 7 nodos, aristas cond. | Gratuito |
| Memoria | LangGraph MemorySaver | — | Gratuito |
| Paralelismo RAG | Python ThreadPoolExecutor | stdlib | Gratuito |
| Embeddings | Jina Embeddings v3 (API cloud) | — | 1M tokens/mes |
| Reranker | Jina Reranker v2 multilingual (API cloud) | — | 500K tokens/mes |
| Vector store | Qdrant Cloud | — | 1 cluster + 1GB |
| Observabilidad | Langfuse Cloud | 3.x | Trazas ilimitadas |
| Interfaz | Streamlit Community Cloud | 1.40.2 | Deploy público |
| Evaluación | RAGAS | 0.2.6 | Gratuito (open source) |
| Historial/Caché | SQLite (stdlib Python) | — | Gratuito |
| Gráficas | Plotly | 6.6.0 | Gratuito (open source) |

**Costo total del proyecto: S/. 0.00**

---

## 📚 Base de conocimiento

La base de conocimiento consta de **148 documentos** indexados como **3 861 chunks semánticos** en Qdrant Cloud con Jina Embeddings v3 (1 024 dimensiones).

| Colección Qdrant | Documentos | Chunks | Contenido |
|---|---|---|---|
| `ley_28008` | 2 | 102 | Ley N° 28008 + Reglamento DS 121-2003-EF |
| `ley_general_aduanas` | 3 | 452 | DL 1053 + Reglamento DS 010-2009-EF + normas complementarias |
| `procedimientos_despacho` | 95 | 1 486 | DESPA-PG.01 al PG.29 + procedimientos específicos e instructivos |
| `procedimientos_fiscalizacion` | 13 | 136 | CONTROL-PG.01/02 + CONTROL-PE.00.01 al PE.01.09 |
| `procedimientos_recaudacion` | 16 | 181 | RECA-PG.02 al PG.05 + procedimientos específicos |
| `normas_asociadas` | 11 | 203 | DS 182, DS 195, DS 192, DS 244, DS 184, DS 104, DS 418 |
| `normas_generales` | 6 | 465 | Ley 27444, Ley 27815, normas de transparencia y TUPA |
| `arancel` | 2 | 836 | Arancel de Aduanas 2022 — Secciones I-XXI + notas legales |
| **TOTAL** | **148** | **3 861** | |

### Chunking inteligente por estructura legal

El proceso de indexación respeta la estructura del texto legal:

- **Por artículo**: cada artículo se almacena como una unidad semántica completa
- **Por numeral**: los numerales largos se subdividen manteniendo el contexto del artículo padre
- **Por sección**: en procedimientos, cada sección (VI. DESCRIPCIÓN, VII. FLUJOGRAMA) se trata por separado
- **Metadatos**: cada chunk almacena `fuente` (código del documento), `articulo`, `titulo` y `texto`

---

## 📖 Normativa cubierta

### Leyes y decretos legislativos

- **Ley N° 28008** — Ley de Delitos Aduaneros
- **DS 121-2003-EF** — Reglamento de la Ley de Delitos Aduaneros
- **DL 1053** — Ley General de Aduanas
- **DS 010-2009-EF** — Reglamento de la Ley General de Aduanas

### Normas arancelarias

- **Arancel de Aduanas 2022** — Partidas, subpartidas nacionales y derechos ad valorem

### Normas asociadas clave

- **DS 418-2019-EF** — Tabla de Sanciones Aduaneras
- **DS 182-2013-EF** — Reglamento de Equipaje y Menaje de Casa
- **DS 195-2013-EF** — Declaración de Dinero en Efectivo
- **DS 192-2020-EF** — Reglamento de Envíos de Entrega Rápida (Courier)
- **DS 244-2013-EF** — Reglamento de Envíos Postales
- **DS 184-2016-EF** — Reglamento de Certificación OEA (Operador Económico Autorizado)
- **DS 104-95-EF** — Reglamento de Procedimiento de Restitución Simplificado (Drawback)

### Procedimientos de despacho (DESPA)

- **DESPA-PG.01** — Importación para el Consumo
- **DESPA-PG.02** — Exportación Definitiva
- **DESPA-PG.07** — Drawback
- **DESPA-PG.13** — Envíos Postales (Consecuencia Postal)
- **DESPA-PG.28** — Envíos de Entrega Rápida (Courier)
- **DESPA-PE.01.10a** — Valoración según Acuerdo de Valoración OMC
- **DESPA-PE.00.03** — Abandono Legal y Voluntario
- **DESPA-PE.00.06** — Mercancías Prohibidas y Restringidas
- Y 87+ procedimientos específicos e instructivos adicionales

### Procedimientos de fiscalización (CONTROL)

- **CONTROL-PG.01** — Programación de Acciones de Control Extraordinario (ACE)
- **CONTROL-PG.02** — Ejecución de Acciones de Control Extraordinario (ACE)
- **CONTROL-PE.00.01** — Inmovilización e Incautación
- **CONTROL-PE.00.08** — Precintos de Seguridad
- **CONTROL-PE.00.10** — Inspección No Intrusiva
- **CONTROL-PE.01.09** — Fiscalización Posterior al Despacho
- Y 7 procedimientos específicos adicionales

### Procedimientos de recaudación (RECA)

- **RECA-PG.03** — Deuda Tributaria Aduanera
- **RECA-PG.04** — Reclamos Tributarios Aduaneros
- **RECA-PG.05** — Devoluciones
- **RECA-PE.02.05** — Fraccionamiento y Aplazamiento de Deuda
- Y 12 procedimientos específicos adicionales

### Normas generales

- **Ley 27444** — Ley del Procedimiento Administrativo General
- **Ley 27815** — Ley del Código de Ética de la Función Pública
- Normas de transparencia y TUPAs aplicables

---

## ⚙️ Parámetros clave del agente

| Parámetro | Valor | Descripción |
|---|---|---|
| `max_tokens` | 1 200 | Longitud máxima de respuesta del LLM (síntesis) |
| `temperature` | 0.1 | Temperatura del LLM (baja para respuestas más deterministas) |
| `k_retrieval` | 5 | Candidatos por búsqueda vectorial (Jina Embeddings v3) |
| `k_final` | 3 | Chunks seleccionados tras reranking (Jina Reranker v2) |
| `_MAX_CONTEXTO` | 3 800 chars | Límite de contexto antes de síntesis (~950 tokens) |
| Historial | 5 turnos (10 msgs) | Memoria conversacional por sesión via MemorySaver |
| Caché TTL | 1 mes | Tiempo de vida de las entradas en caché SQLite |
| Streaming | `stream_mode="messages"` | Tokens del nodo síntesis enviados en tiempo real |
| Fallback sleep | 20 s | Pausa ante errores 429 de rate limiting (no TPD) |

---

## 🚀 Instalación en 4 pasos

> La base de conocimiento ya está indexada en Qdrant Cloud — no necesitas descargar ni procesar los 148 documentos localmente.

### Requisitos previos

- Python 3.11+
- Cuentas gratuitas en:
  - [Groq](https://console.groq.com) — LLM principal (Llama 3.3 70B)
  - [Jina AI](https://jina.ai) — Embeddings v3 + Reranker v2
  - [Qdrant Cloud](https://cloud.qdrant.io) — Vector store (solicitar acceso al cluster)
  - [Langfuse](https://cloud.langfuse.com) — Observabilidad (opcional)
  - [Google AI Studio](https://aistudio.google.com/apikey) — LLM fallback Gemini (opcional)

### Paso 1 — Clonar el repositorio

```bash
git clone https://github.com/jcancharigu/aduana-gpt.git
cd aduana-gpt
```

### Paso 2 — Crear entorno virtual e instalar dependencias

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux / Mac
source venv/bin/activate

pip install -r requirements.txt
```

### Paso 3 — Configurar variables de entorno

```bash
cp .env.example .env
```

Edita `.env` con tus credenciales (ver sección [Variables de entorno](#-variables-de-entorno)).

### Paso 4 — Arrancar la aplicación

```bash
streamlit run app.py
```

Abre **http://localhost:8501** en tu navegador.

---

## 🔑 Variables de entorno

```env
# ── LLM principal (Groq) ──────────────────────────────────────
# Registro gratuito: https://console.groq.com
# Límite: 100K tokens/día para llama-3.3-70b-versatile
GROQ_API_KEY=your_groq_api_key_here
LLM_MODEL=llama-3.3-70b-versatile

# ── LLM fallback 2 (Google Gemini) ────────────────────────────
# Registro gratuito: https://aistudio.google.com/apikey
# Límite: 1M tokens/día para gemini-2.0-flash
# Si no se configura, la cadena de fallback usa solo Groq
GOOGLE_API_KEY=your_google_api_key_here

# ── Jina AI (embeddings + reranker) ───────────────────────────
# Registro gratuito: https://jina.ai
# Límite: 1M tokens/mes embeddings · 500K tokens/mes reranker
JINA_API_KEY=jina_your_api_key_here

# ── Qdrant Cloud (vector store) ───────────────────────────────
# La base de conocimiento ya está indexada — solo necesitas acceso al cluster
# Registro: https://cloud.qdrant.io
QDRANT_URL=https://your-cluster-id.qdrant.io
QDRANT_API_KEY=your_qdrant_api_key_here

# ── Langfuse Cloud (observabilidad) ───────────────────────────
# Registro gratuito: https://cloud.langfuse.com
# Si no se configuran, el agente funciona sin observabilidad
LANGFUSE_PUBLIC_KEY=pk-lf-your_public_key_here
LANGFUSE_SECRET_KEY=sk-lf-your_secret_key_here
LANGFUSE_HOST=https://cloud.langfuse.com
```

**Variables mínimas requeridas** (sin observabilidad ni fallback Gemini):

```env
GROQ_API_KEY=...
JINA_API_KEY=...
QDRANT_URL=...
QDRANT_API_KEY=...
```

---

## 📁 Estructura del proyecto

```
aduana_gpt/
│
├── app.py                          # Interfaz Streamlit: chat, panel métricas, sidebar
├── requirements.txt                # Dependencias de producción (Streamlit Cloud)
├── requirements-dev.txt            # Dependencias extra para desarrollo/indexación local
├── .env.example                    # Plantilla de variables de entorno
│
├── src/
│   ├── agent/
│   │   └── agente.py              # Grafo LangGraph 7 nodos, fallback LLM, streaming
│   ├── prompts/
│   │   └── system_prompt.py       # System prompt + mapa URLS_DOCUMENTOS (29 entradas)
│   └── tools/
│       └── herramientas_rag.py    # 11 herramientas RAG: embed → Qdrant → rerank
│
├── scripts/
│   ├── descargar_todo.py          # Descarga los 148 documentos SUNAT (HTML + PDF)
│   ├── extraer_texto.py           # Extracción y limpieza de texto de HTML y PDF
│   ├── indexar_qdrant.py          # Chunking por artículo + indexación en Qdrant Cloud
│   └── evaluar_agente.py          # Evaluación RAGAS + evaluación manual experta
│
├── data/                           # Generado en tiempo de ejecución (no versionado)
│   ├── historial.db               # SQLite: consultas + caché de respuestas
│   └── evaluacion_resultados.json # Resultados de la evaluación RAGAS + manual
│
└── ADUANA_GPT_Presentacion_v2.pptx  # Presentación del proyecto (10 diapositivas)
```

### Archivos clave

**`src/agent/agente.py`** — Núcleo del sistema:
- Define `EstadoAgente` (TypedDict con 5 campos)
- Instancia los 3 LLMs (`llm`, `llm_fallback`, `llm_fallback2`) con fallback automático
- Implementa `_invocar()`: helper centralizado para todas las llamadas LLM
- Implementa `_truncar_contexto()`: recorte proporcional del contexto por sección
- Define 7 funciones de nodo + el enrutador condicional
- Compila el grafo con `MemorySaver`
- Expone `consultar()` y `consultar_stream()` para uso desde `app.py`

**`src/tools/herramientas_rag.py`** — 11 herramientas RAG:
- `_embed()`: llama a Jina Embeddings v3 API
- `_rerank()`: llama a Jina Reranker v2 API
- `_buscar()`: pipeline completo embed → Qdrant → rerank
- 11 funciones `@tool` especializadas por dominio/colección

**`src/prompts/system_prompt.py`** — Instrucciones y mapeo de URLs:
- `SYSTEM_PROMPT`: formato obligatorio de respuesta, reglas de calidad, fuentes disponibles
- `URLS_DOCUMENTOS`: diccionario de 29 códigos normativo → URL oficial SUNAT

**`app.py`** — Interfaz Streamlit (700 líneas):
- CSS personalizado (dark navy + dorado, fuentes Sora + DM Sans + DM Mono)
- Gestión de estado de sesión (`messages`, `historia`, `thread_id`)
- Caché SQLite + historial persistente
- Funciones de render: badge, chips de fuente, métricas, historial
- Integración con Langfuse REST para scores y feedback
- Loop de streaming con placeholder actualizado token a token

---

## 📊 Evaluación

El agente se evalúa con dos métodos complementarios sobre **20 casos de prueba** distribuidos en 3 perfiles de usuario:

| Perfil | Casos | Temas cubiertos |
|---|---|---|
| **Especialista SUNAT** | 7 | ACE, inmovilización, contrabando, sanciones, defraudación |
| **Operador de Comercio Exterior** | 7 | Drawback, arancel, canales de control, despacho anticipado, exportación, agente de aduana, abandono legal |
| **Ciudadano** | 6 | Equipaje, drone, no declaración, medicamentos, courier, compras online, dinero en efectivo |

### Ejecutar la evaluación

```bash
python scripts/evaluar_agente.py
```

Selecciona el modo al iniciarse:

```
¿Modo?
  1 = Solo RAGAS automático
  2 = Solo evaluación manual experto
  3 = Ambos
```

### Evaluación automática RAGAS

| Métrica | Qué mide |
|---|---|
| `context_recall` | El contexto recuperado cubre la respuesta de referencia |
| `context_precision` | El contexto recuperado es preciso y sin ruido |
| `answer_relevancy` | La respuesta responde directamente la pregunta |
| `faithfulness` | La respuesta es fiel al contexto (sin alucinaciones) |

Los scores se envían automáticamente a Langfuse. Resultados guardados en `data/evaluacion_resultados.json` como checkpoint (se guarda tras cada caso).

La evaluación incluye un **sleep de 35 s entre casos** para respetar los rate limits de Groq.

#### Nota metodológica importante

> RAGAS fue diseñado originalmente para inglés y requiere un LLM juez de alta capacidad (GPT-4 o equivalente) para funcionar correctamente. En este proyecto se usa Llama 3.1 8B como juez por ser el único disponible con suficiente cuota, lo que puede subestimar los scores reales. Los resultados RAGAS deben interpretarse como **referencia relativa**, no como medición absoluta. La evaluación manual experta complementa esta limitación.

### Evaluación manual experta

El evaluador humano puntúa cada respuesta en 4 dimensiones (escala 1–5):

| Dimensión | Criterio |
|---|---|
| `precision` | ¿La respuesta es normativamente correcta? |
| `relevancia` | ¿Responde lo que se preguntó? |
| `utilidad` | ¿Es útil para el usuario final? |
| `alucinacion` | ¿Hay alucinaciones? (0=sí hay, 5=no hay) |

---

## 💬 Ejemplos de consultas

### Especialista SUNAT — Dominio DELITOS
> *"¿Cuáles son las modalidades del contrabando según la Ley 28008?"*

**Respuesta esperada:** El agente cita el Art. 1° y concordantes de la Ley N° 28008, describe contrabando simple, agravado y la modalidad de uso de documentos falsos. Incluye sanciones penales y administrativas.

---

### Especialista SUNAT — Dominio CONTROL
> *"¿Cuál es el procedimiento para inmovilizar una mercancía durante una ACE?"*

**Respuesta esperada:** Cita CONTROL-PE.00.01 y CONTROL-PG.02, describe las etapas: detección de irregularidad → levantamiento de acta de inmovilización → plazo de 10 días hábiles → resolución de comiso o levantamiento.

---

### Operador OCE — Dominio DESPACHO
> *"¿Cuánto pago de arancel por importar laptops desde China?"*

**Respuesta esperada:** Identifica la partida 8471.30 del Arancel de Aduanas 2022, indica tasa ad valorem 0%, menciona los tributos aplicables (IGV 16% + IPM 2%).

---

### Operador OCE — Dominio DESPACHO
> *"¿Cuáles son los requisitos para acogerse al drawback?"*

**Respuesta esperada:** Cita DS 104-95-EF y DESPA-PG.07, detalla los 5 requisitos principales (tasa de restitución 3%, valor FOB mínimo, insumos importados incorporados, plazo de solicitud 180 días, documentos requeridos).

---

### Ciudadano — Dominio ORIENTACIÓN
> *"¿Cuánto equipaje puedo traer del extranjero sin pagar impuestos?"*

**Respuesta esperada:** Cita Art. 8° del DS 182-2013-EF, indica franquicia de USD 500 para mayores de 18 años, USD 300 para menores, explica que el exceso paga arancel solo sobre el monto excedente.

---

### Operador OCE — Dominio RECAUDACIÓN
> *"¿Qué es el abandono legal y en qué plazo se produce?"*

**Respuesta esperada:** Cita Art. 178° del DL 1053, indica plazo de 30 días hábiles desde la numeración de la DAM sin destinación a régimen, menciona consecuencias y DESPA-PE.00.03.

---

## ☁️ Despliegue en Streamlit Community Cloud

1. Haz fork del repositorio en GitHub
2. Ve a [share.streamlit.io](https://share.streamlit.io) → **New app** → selecciona el repo → archivo: `app.py`
3. En **Settings → Secrets**, agrega las variables de entorno en formato TOML:

```toml
GROQ_API_KEY = "gsk_..."
JINA_API_KEY = "jina_..."
QDRANT_URL = "https://tu-cluster.qdrant.io"
QDRANT_API_KEY = "..."
LANGFUSE_PUBLIC_KEY = "pk-lf-..."
LANGFUSE_SECRET_KEY = "sk-lf-..."
LANGFUSE_HOST = "https://cloud.langfuse.com"
GOOGLE_API_KEY = "..."   # opcional — habilita fallback Gemini
```

4. Click **Deploy** — la app queda disponible en una URL pública sin costo.

> **Nota:** el directorio `data/` se crea automáticamente en el contenedor de Streamlit Cloud. El historial SQLite no persiste entre redeployments (es ephemeral storage). Para persistencia real, migrar a una base de datos externa (PlanetScale, Supabase free tier).

---

## 🎓 Contexto académico

Este proyecto fue desarrollado como **Proyecto Integrador** de la Maestría en Ciencia de Datos de la Universidad Nacional de Ingeniería (UNI), promoción 2026-1, bajo la dirección de la docente **Melba Torres**.

### Objetivos demostrados

1. **Arquitectura multi-agente real**: LangGraph con nodos especializados, aristas condicionales y memoria persistente — no un chatbot simple con RAG lineal.

2. **RAG de producción**: pipeline completo embed → búsqueda vectorial → reranking, con 8 colecciones especializadas y 3 861 chunks semánticos en cloud.

3. **Resiliencia operativa**: fallback automático entre 3 LLMs (1.6M tokens/día total) + caché SQLite para consultas repetidas.

4. **Observabilidad end-to-end**: trazas en Langfuse Cloud con métricas automáticas y feedback humano registrado.

5. **Stack 100% gratuito**: demuestra que es posible construir un agente de IA de nivel profesional sin inversión económica, usando exclusivamente servicios cloud con tier gratuito.

**Costo total del proyecto: S/. 0.00**

---

## 📄 Licencia

MIT License — Ver [LICENSE](LICENSE) para más detalles.

---

*Desarrollado con dedicación para SUNAT Perú · Stack 100% gratuito y open source*  
*Maestría en Ciencia de Datos · Universidad Nacional de Ingeniería · 2026-1*
