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
- 📊 **Observabilidad completa** — tokens, costos y latencia capturados automáticamente en Langfuse
- ✅ **Evaluación RAGAS** — 4 métricas: faithfulness, answer relevancy, context recall, context precision

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
              │  Langfuse             │  → tokens, costo, latencia
              │  CallbackHandler      │     + scores RAGAS
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

---

## 🛠️ Stack Tecnológico

| Componente | Herramienta | Versión | Costo |
|---|---|---|---|
| LLM | Llama 3.3 70B via Groq API | — | Gratuito |
| Framework agente | LangGraph + LangChain | 1.1.6 / 0.3.7 | Gratuito |
| Grafo | LangGraph StateGraph | 7 nodos, aristas condicionales | Gratuito |
| Memoria | LangGraph MemorySaver | — | Gratuito |
| Paralelismo RAG | Python ThreadPoolExecutor | stdlib | Gratuito |
| Embeddings | BGE-M3 (BAAI) | — | Gratuito |
| Reranker | BGE-Reranker-v2-m3 (BAAI) | — | Gratuito |
| Vector store | ChromaDB | 0.5.20 | Gratuito |
| Observabilidad | Langfuse self-hosted (Docker) + CallbackHandler | 2.60.0 | Gratuito |
| Interfaz | Streamlit (streaming token a token) | 1.40.2 | Gratuito |
| Evaluación | RAGAS (4 métricas) | 0.2.6 | Gratuito |

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

> Chunking inteligente por estructura legal: respeta artículos, capítulos, secciones y numerales SUNAT. Cada artículo se almacena como una unidad semántica completa.

---

## 🚀 Instalación en 5 pasos

### Requisitos previos
- Python 3.11+
- Docker Desktop
- Cuenta gratuita en [Groq](https://console.groq.com)

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

Copia el archivo de ejemplo y completa tus keys:

```bash
cp .env.example .env
```

Edita `.env` con tus credenciales:

```env
GROQ_API_KEY=tu_api_key_de_groq
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=http://localhost:3000
```

Obtén tu API key gratuita en: https://console.groq.com

Para las keys de Langfuse, primero levanta el servidor (Paso 5) y crea un proyecto en http://localhost:3000

### Paso 4 — Construir la base de conocimiento

```bash
# Descargar normativa SUNAT (148 documentos)
python scripts/descargar_todo.py

# Extraer texto de HTML y PDF
python scripts/extraer_texto.py

# Indexar en ChromaDB con BGE-M3 (chunking inteligente por artículo)
python scripts/indexar_chromadb.py
```

> ⏳ La indexación tarda ~30 minutos (descarga BGE-M3 ~1.2GB la primera vez)

### Paso 5 — Arrancar la aplicación

```bash
# Terminal 1: Langfuse (arrancar primero)
docker compose up -d

# Terminal 2: Aplicación Streamlit
streamlit run app.py
```

- Aplicación: **http://localhost:8501**
- Dashboard Langfuse: **http://localhost:3000**

---

## 📊 Evaluación

El agente se evalúa con **RAGAS** (automático) y **evaluación manual experta** en 20 casos de prueba distribuidos en 3 perfiles: Especialista SUNAT, Operador de Comercio Exterior y Ciudadano.

```bash
python scripts/evaluar_agente.py
```

Selecciona el modo:
- `1` → Solo RAGAS automático (4 métricas)
- `2` → Solo evaluación manual experto (precisión, relevancia, utilidad, alucinación)
- `3` → Ambos — evaluación completa para la bitácora

**Métricas RAGAS evaluadas:**

| Métrica | Qué mide |
|---|---|
| **faithfulness** | La respuesta está sustentada en el contexto recuperado |
| **answer_relevancy** | La respuesta responde directamente la pregunta |
| **context_recall** | El contexto cubre la respuesta de referencia |
| **context_precision** | El contexto recuperado es preciso y sin ruido |

Los scores se envían automáticamente a Langfuse para trazabilidad. Resultados guardados en `data/evaluacion_resultados.json`

> ⚠️ RAGAS usa Groq como LLM juez — requiere saldo disponible (100K tokens/día en plan gratuito). Se evalúan 5 casos representativos de los 20 totales.

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
├── docker-compose.yml              # Langfuse self-hosted
├── requirements.txt                # Dependencias
├── .env.example                    # Plantilla de variables de entorno
├── .env                            # Variables de entorno (no subir a git)
├── scripts/
│   ├── descargar_todo.py          # Descarga 148 documentos SUNAT
│   ├── extraer_texto.py           # Extracción de texto HTML/PDF
│   ├── indexar_chromadb.py        # Indexación BGE-M3 + chunking inteligente
│   └── evaluar_agente.py          # Evaluación RAGAS + manual experto
├── src/
│   ├── agent/agente.py            # Grafo LangGraph 7 nodos + aristas condicionales
│   ├── prompts/system_prompt.py   # System prompt con ejemplo de respuesta
│   └── tools/herramientas_rag.py  # 11 herramientas RAG + BGE-Reranker-v2-m3
└── data/
    ├── raw/                        # Documentos HTML/PDF (excluido del repo)
    ├── processed/                  # Texto extraído (excluido del repo)
    └── vectorstore/                # ChromaDB (excluido del repo)
```

---

## 🔧 Parámetros clave del agente

| Parámetro | Valor | Descripción |
|---|---|---|
| `max_tokens` | 1 200 | Longitud máxima de respuesta del LLM |
| `k_retrieval` | 5 | Candidatos por búsqueda vectorial (BGE-M3) |
| `k_final` | 3 | Chunks seleccionados tras reranking |
| Historial | 5 turnos (10 msgs) | Memoria conversacional por sesión |
| Caché SQLite | 1 mes | Consultas idénticas no generan nueva inferencia |
| Streaming | `stream_mode="messages"` | Tokens del nodo síntesis enviados en tiempo real |

---

## 🔧 Comandos útiles

```bash
# Arrancar Langfuse
docker compose up -d

# Arrancar aplicación
streamlit run app.py

# Re-indexar vectorstore desde cero
# Windows:
Remove-Item data\vectorstore\ -Recurse -Force
# Linux/Mac:
rm -rf data/vectorstore/
python scripts/indexar_chromadb.py

# Detener Langfuse
docker compose down
```

---

## 📖 Normativa cubierta

- **Ley N° 28008** — Ley de Delitos Aduaneros y Reglamento DS 121-2003-EF
- **DL 1053** — Ley General de Aduanas y Reglamento DS 010-2009-EF
- **DS 418-2019-EF** — Tabla de Sanciones Aduaneras
- **Arancel de Aduanas 2022** — Partidas arancelarias y derechos ad valorem
- **DS 182-2013-EF** — Reglamento de Equipaje y Menaje de Casa
- **DS 195-2013-EF** — Declaración de Dinero en Efectivo
- **DESPA-PG.01 al PG.29** — Procedimientos generales de despacho
- **CONTROL-PG.01 / PG.02** — Programación y ejecución de ACEs
- **RECA-PG.02 al PG.05** — Procedimientos de recaudación
- Y 130+ procedimientos específicos e instructivos adicionales

---

## 🎓 Contexto académico

Este proyecto fue desarrollado como Proyecto Integrador de la **Maestría en Ciencia de Datos** de la Universidad Nacional de Ingeniería (UNI), bajo la dirección de la docente **Melba Torres**.

El objetivo fue demostrar que es posible construir un agente de IA de nivel profesional usando exclusivamente herramientas gratuitas y open source, con costo total de **S/. 0.00**.

---

## 📄 Licencia

MIT License — Ver [LICENSE](LICENSE) para más detalles.

---

*Desarrollado con ❤️ para SUNAT Perú · Stack 100% gratuito y open source*
