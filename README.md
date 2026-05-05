# 🛃 ADUANA-GPT

**Agente de IA con RAG Multidominio para consultas sobre normativa aduanera peruana**

> Proyecto Integrador — Maestría en Ciencia de Datos · Universidad Nacional de Ingeniería · 2026-1  
> Desarrollado por: Jaime Canchari Gutierrez | SUNAT — División de Control Operativo IAMC

![Python](https://img.shields.io/badge/Python-3.11-blue)
![LangGraph](https://img.shields.io/badge/LangGraph-1.1.6-green)
![Llama](https://img.shields.io/badge/Llama-3.3_70B-orange)
![Nodos](https://img.shields.io/badge/Nodos_LangGraph-7-purple)
![Chunks](https://img.shields.io/badge/Chunks-3%2C861-teal)
![Streaming](https://img.shields.io/badge/Streaming-token_a_token-cyan)
![Costo](https://img.shields.io/badge/Costo_total-S/._0.00-brightgreen)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## 📋 Descripción

ADUANA-GPT es un agente de IA especializado en normativa aduanera peruana que permite a especialistas de aduanas, operadores de comercio exterior y ciudadanos realizar consultas en lenguaje natural sobre leyes, reglamentos y procedimientos aduaneros vigentes.

El agente responde con cita exacta del artículo y documento fuente, orientando sobre sanciones, multas, inmovilizaciones e incautaciones según corresponda.

**Características principales:**
- 🔴 **Streaming token a token** — la respuesta aparece en ~0.5s en lugar de esperar 5–10s
- 🧠 **Memoria conversacional** — historial de 5 turnos preservado por sesión (MemorySaver)
- 🔍 **RAG paralelo** — búsquedas simultáneas con `ThreadPoolExecutor` por dominio
- 🔁 **Fallback automático de LLM** — 70B → 8B → Gemini si se agota el límite diario
- 📊 **Observabilidad completa** — trazas, latencia y scores en Langfuse Cloud
- ✅ **Evaluación RAGAS** — métricas automáticas + evaluación manual experta (20 casos)
- ⚡ **Caché SQLite** — consultas repetidas se sirven en <0.5s sin consumir tokens

**Stack 100% gratuito y open source — Costo total: S/. 0.00**

---

## 🏗️ Arquitectura

El agente implementa un grafo LangGraph con **7 nodos** y **aristas condicionales** alineadas a los 5 macroprocesos del negocio aduanero peruano:

```
Consulta del usuario
         │
         ▼
┌─────────────────────┐
│  Nodo 1             │
│  CLASIFICADOR       │  → identifica el dominio aduanero
└──────────┬──────────┘
           │  aristas condicionales
     ┌─────┴──────────────────────────────────┐
     │         │          │         │         │
     ▼         ▼          ▼         ▼         ▼
  DELITOS   CONTROL   DESPACHO  RECAUDAC. ORIENTAC.
  Nodo 2A   Nodo 2B   Nodo 2C   Nodo 2D   Nodo 2E
  (2 RAGs)  (2 RAGs)  (3 RAGs)  (3 RAGs)  (3 RAGs)
 paralelos  paralelos paralelos paralelos paralelos
     │         │          │         │         │
     └─────────┴──────────┴─────────┴─────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │  Nodo 3 — SÍNTESIS    │  → streaming token a token
              │  Llama 3.3 70B        │     (max_tokens: 1200)
              └───────────┬───────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │  Langfuse Cloud       │  → trazas, latencia, scores
              └───────────┬───────────┘
                          │
                         END
```

### Los 5 dominios del negocio aduanero

| Dominio | Nodo | Herramientas RAG activadas |
|---|---|---|
| **Delitos** | 2A | buscar_ley_28008 · buscar_sanciones_multas |
| **Control** | 2B | buscar_procedimientos_fiscalizacion · buscar_ley_general_aduanas |
| **Despacho** | 2C | buscar_procedimientos_despacho · buscar_arancel · buscar_mercancias_prohibidas |
| **Recaudación** | 2D | buscar_procedimientos_recaudacion · buscar_sanciones_multas · buscar_ley_general_aduanas |
| **Orientación** | 2E | buscar_equipaje_viajeros · buscar_normas_asociadas · buscar_normas_generales |

### Cadena de fallback LLM

Cuando el modelo principal agota su límite diario, el sistema cambia automáticamente:

```
llama-3.3-70b-versatile  →  llama-3.1-8b-instant  →  gemini-2.0-flash
     (100K tokens/día)          (500K tokens/día)        (1M tokens/día)
```

---

## 🛠️ Stack Tecnológico

| Componente | Herramienta | Versión | Costo |
|---|---|---|---|
| LLM principal | Llama 3.3 70B via Groq API | — | Gratuito |
| LLM fallback 1 | Llama 3.1 8B Instant via Groq | — | Gratuito |
| LLM fallback 2 | Gemini 2.0 Flash via Google AI Studio | — | Gratuito |
| Framework agente | LangGraph + LangChain | 1.1.6 / 1.0.0 | Gratuito |
| Grafo | LangGraph StateGraph | 7 nodos, aristas condicionales | Gratuito |
| Memoria | LangGraph MemorySaver | — | Gratuito |
| Paralelismo RAG | Python ThreadPoolExecutor | stdlib | Gratuito |
| Embeddings | Jina Embeddings v3 (API cloud) | — | Gratuito |
| Reranker | Jina Reranker v2 multilingual (API cloud) | — | Gratuito |
| Vector store | Qdrant Cloud | — | Gratuito |
| Observabilidad | Langfuse Cloud | 3.x | Gratuito |
| Interfaz | Streamlit Community Cloud | 1.40.2 | Gratuito |
| Evaluación | RAGAS + evaluación manual | 0.2.6 | Gratuito |

---

## 📚 Base de Conocimiento

| Colección | Documentos | Chunks |
|---|---|---|
| Ley 28008 + Reglamento | 2 | 102 |
| Ley General de Aduanas (DL 1053) | 3 | 452 |
| Procedimientos de despacho | 95 | 1,486 |
| Procedimientos de fiscalización | 13 | 136 |
| Procedimientos de recaudación | 16 | 181 |
| Normas asociadas | 11 | 203 |
| Normas generales | 6 | 465 |
| Arancel de Aduanas 2022 | 2 | 836 |
| **TOTAL** | **148** | **3,861** |

> Chunking inteligente por estructura legal: respeta artículos, capítulos, secciones y numerales SUNAT. Cada artículo se almacena como una unidad semántica completa. Indexado en Qdrant Cloud con Jina Embeddings v3 (1024 dimensiones).

---

## 🚀 Instalación en 4 pasos

> La base de conocimiento ya está indexada en Qdrant Cloud — no necesitas descargar ni procesar documentos.

### Requisitos previos
- Python 3.11+
- Cuentas gratuitas en: [Groq](https://console.groq.com) · [Jina AI](https://jina.ai) · [Qdrant Cloud](https://cloud.qdrant.io) · [Langfuse](https://cloud.langfuse.com)
- Opcional: [Google AI Studio](https://aistudio.google.com/apikey) para fallback Gemini

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

# Linux/Mac
source venv/bin/activate

pip install -r requirements.txt
```

### Paso 3 — Configurar variables de entorno

```bash
cp .env.example .env
```

Edita `.env` con tus credenciales:

```env
# LLM principal
GROQ_API_KEY=tu_api_key_de_groq
LLM_MODEL=llama-3.3-70b-versatile

# LLM fallback 2 (opcional)
GOOGLE_API_KEY=tu_api_key_de_google

# Embeddings + Reranker
JINA_API_KEY=tu_api_key_de_jina

# Vector store
QDRANT_URL=https://tu-cluster.qdrant.io
QDRANT_API_KEY=tu_qdrant_api_key

# Observabilidad (opcional)
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com
```

### Paso 4 — Arrancar la aplicación

```bash
streamlit run app.py
```

- Aplicación: **http://localhost:8501**

---

## ☁️ Despliegue en Streamlit Community Cloud

1. Haz fork del repositorio en GitHub
2. Ve a [share.streamlit.io](https://share.streamlit.io) → **New app** → selecciona el repo
3. En **Settings → Secrets**, agrega las mismas variables del `.env`:

```toml
GROQ_API_KEY = "..."
JINA_API_KEY = "..."
QDRANT_URL = "..."
QDRANT_API_KEY = "..."
LANGFUSE_PUBLIC_KEY = "..."
LANGFUSE_SECRET_KEY = "..."
GOOGLE_API_KEY = "..."   # opcional
```

4. Click **Deploy** — la app queda disponible en una URL pública sin costo.

---

## 📊 Evaluación

El agente se evalúa con **RAGAS** (automático) y **evaluación manual experta** en 20 casos de prueba distribuidos en 3 perfiles: Especialista SUNAT, Operador de Comercio Exterior y Ciudadano.

```bash
python scripts/evaluar_agente.py
```

Selecciona el modo:
- `1` → Solo RAGAS automático
- `2` → Solo evaluación manual experto (precisión, relevancia, utilidad, alucinación)
- `3` → Ambos

**Métricas RAGAS evaluadas:**

| Métrica | Qué mide |
|---|---|
| **context_recall** | El contexto recuperado cubre la respuesta de referencia |
| **context_precision** | El contexto recuperado es preciso y sin ruido |
| **answer_relevancy** | La respuesta responde directamente la pregunta |

> **Nota metodológica:** RAGAS fue diseñado para inglés y requiere un LLM juez de alta capacidad (GPT-4 o equivalente). En este proyecto se usa Llama 3.1 8B como juez, lo que puede subestimar los scores reales. Los resultados RAGAS deben interpretarse como referencia relativa, no como medición absoluta. La evaluación manual experta complementa esta limitación.

Los scores se envían automáticamente a Langfuse para trazabilidad. Resultados guardados en `data/evaluacion_resultados.json`.

---

## 💬 Ejemplos de consultas

**Especialista de Aduanas (dominio CONTROL):**
> *"¿Cuál es el procedimiento para inmovilizar una mercancía durante una ACE?"*

**Operador de Comercio Exterior (dominio DESPACHO):**
> *"¿Cuánto pago de arancel por importar laptops desde China?"*

**Ciudadano (dominio ORIENTACIÓN):**
> *"¿Cuánto equipaje puedo traer del extranjero sin pagar impuestos?"*

**Especialista SUNAT (dominio DELITOS):**
> *"¿Cuáles son las modalidades del contrabando según la Ley 28008?"*

**Operador OCE (dominio RECAUDACIÓN):**
> *"¿Qué es el abandono legal y en qué plazo se produce?"*

---

## 📁 Estructura del proyecto

```
aduana_gpt/
├── app.py                          # Interfaz Streamlit con panel de métricas
├── requirements.txt                # Dependencias de producción
├── requirements-dev.txt            # Dependencias de desarrollo (indexación local)
├── .env.example                    # Plantilla de variables de entorno
├── scripts/
│   ├── descargar_todo.py          # Descarga 148 documentos SUNAT
│   ├── extraer_texto.py           # Extracción de texto HTML/PDF
│   ├── indexar_qdrant.py          # Indexación en Qdrant Cloud con Jina Embeddings
│   └── evaluar_agente.py          # Evaluación RAGAS + manual experto
└── src/
    ├── agent/agente.py            # Grafo LangGraph 7 nodos + fallback LLM
    ├── prompts/system_prompt.py   # System prompt + mapa de URLs normativas
    └── tools/herramientas_rag.py  # 11 herramientas RAG + Jina Reranker
```

---

## 🔧 Parámetros clave del agente

| Parámetro | Valor | Descripción |
|---|---|---|
| `max_tokens` | 1 200 | Longitud máxima de respuesta del LLM |
| `k_retrieval` | 5 | Candidatos por búsqueda vectorial (Jina Embeddings v3) |
| `k_final` | 3 | Chunks seleccionados tras reranking (Jina Reranker v2) |
| Contexto máximo | 3 800 chars | Truncación automática antes de síntesis |
| Historial | 5 turnos (10 msgs) | Memoria conversacional por sesión |
| Caché SQLite | 1 mes | Consultas idénticas no generan nueva inferencia |
| Streaming | `stream_mode="messages"` | Tokens del nodo síntesis enviados en tiempo real |

---

## 📖 Normativa cubierta

- **Ley N° 28008** — Ley de Delitos Aduaneros y Reglamento DS 121-2003-EF
- **DL 1053** — Ley General de Aduanas y Reglamento DS 010-2009-EF
- **DS 418-2019-EF** — Tabla de Sanciones Aduaneras
- **Arancel de Aduanas 2022** — Partidas arancelarias y derechos ad valorem
- **DS 182-2013-EF** — Reglamento de Equipaje y Menaje de Casa
- **DS 195-2013-EF** — Declaración de Dinero en Efectivo
- **DS 192-2020-EF** — Reglamento de Envíos de Entrega Rápida (Courier)
- **DS 244-2013-EF** — Reglamento de Envíos Postales
- **DS 184-2016-EF** — Reglamento de Certificación OEA
- **DS 104-95-EF** — Reglamento de Drawback
- **DESPA-PG.01 al PG.29** — Procedimientos generales de despacho
- **CONTROL-PG.01 / PG.02** — Programación y ejecución de ACEs
- **RECA-PG.02 al PG.05** — Procedimientos de recaudación
- Y 130+ procedimientos específicos e instructivos adicionales

---

## 🎓 Contexto académico

Este proyecto fue desarrollado como Proyecto Integrador de la **Maestría en Ciencia de Datos** de la Universidad Nacional de Ingeniería (UNI), bajo la dirección de la docente **Melba Torres**.

El objetivo fue demostrar que es posible construir un agente de IA de nivel profesional usando exclusivamente herramientas gratuitas y servicios cloud, con costo total de **S/. 0.00**.

---

## 📄 Licencia

MIT License — Ver [LICENSE](LICENSE) para más detalles.

---

*Desarrollado con ❤️ para SUNAT Perú · Stack 100% gratuito y open source*
