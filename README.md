# 🛃 ADUANA-GPT

**Agente de IA con RAG Multidominio para consultas sobre normativa aduanera peruana**

> Proyecto Integrador — Maestría en Ciencia de Datos · Universidad Nacional de Ingeniería · 2026-1  
> Desarrollado por: Jaime Canchari Gutierrez | SUNAT — División de Control Operativo IAMC

![Python](https://img.shields.io/badge/Python-3.11-blue)
![LangGraph](https://img.shields.io/badge/LangGraph-1.1.6-green)
![Llama](https://img.shields.io/badge/Llama-3.3_70B-orange)
![Costo](https://img.shields.io/badge/Costo_total-S/._0.00-brightgreen)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## 📋 Descripción

ADUANA-GPT es un agente de IA especializado en normativa aduanera peruana que permite a especialistas de aduanas, operadores de comercio exterior y ciudadanos realizar consultas en lenguaje natural sobre leyes, reglamentos y procedimientos aduaneros vigentes.

El agente responde con cita exacta del artículo y documento fuente, orientando sobre sanciones, multas, inmovilizaciones e incautaciones según corresponda.

**Stack 100% gratuito y open source — Costo total: S/. 0.00**

---

## 🏗️ Arquitectura

```
Consulta usuario
      │
      ▼
┌─────────────────────────────────────┐
│  Nodo 1 — Clasificador de intención │  → 9 categorías: DELITO, FISCALIZACION,
│          LangGraph                  │    DESPACHO, ARANCEL, PROHIBICION,
└──────────────────┬──────────────────┘    SANCION, VIAJERO, RECAUDACION, GENERAL
                   │
                   ▼
┌─────────────────────────────────────┐
│  Nodo 2 — Recuperación especializada│  → BGE-M3 embeddings (k=10 candidatos)
│  RAG + BGE-Reranker-v2-m3           │  → Reranker selecciona k=3 mejores
│  11 herramientas · 9 colecciones    │  → Herramientas asignadas por intención
└──────────────────┬──────────────────┘
                   │
                   ▼
┌─────────────────────────────────────┐
│  Nodo 3 — Síntesis                  │  → Llama 3.3 70B via Groq API
│          Llama 3.3 70B              │  → Respuesta estructurada con artículos
└──────────────────┬──────────────────┘
                   │
                   ▼
┌─────────────────────────────────────┐
│  Langfuse self-hosted               │  → Trazabilidad completa (Docker)
│  Observabilidad                     │  → Dashboard: http://localhost:3000
└─────────────────────────────────────┘
```

---

## 🛠️ Stack Tecnológico

| Componente | Herramienta | Versión | Costo |
|---|---|---|---|
| LLM | Llama 3.3 70B via Groq API | — | Gratuito |
| Framework agente | LangGraph + LangChain | 1.1.6 / 0.3.7 | Gratuito |
| Clasificador intención | LangGraph StateGraph | 9 nodos | Gratuito |
| Embeddings | BGE-M3 (BAAI) | — | Gratuito |
| Reranker | BGE-Reranker-v2-m3 (BAAI) | — | Gratuito |
| Vector store | ChromaDB | 0.5.20 | Gratuito |
| Observabilidad | Langfuse self-hosted (Docker) | 2.x | Gratuito |
| Interfaz | Streamlit | 1.40.2 | Gratuito |
| Evaluación | RAGAS | 0.2.6 | Gratuito |

---

## 📚 Base de Conocimiento

| Colección | Documentos | Chunks |
|---|---|---|
| Ley 28008 + Reglamento | 2 | 100 |
| Ley General de Aduanas (DL 1053) | 3 | 347 |
| Procedimientos de despacho | 95 | 1,464 |
| Procedimientos de fiscalización | 13 | 128 |
| Procedimientos de recaudación | 16 | 176 |
| Normas asociadas | 11 | 202 |
| Normas generales | 6 | 461 |
| Arancel de Aduanas 2022 | 2 | 769 |
| **TOTAL** | **148** | **3,647** |

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

Crea un archivo `.env` en la raíz del proyecto:

```env
GROQ_API_KEY=tu_api_key_de_groq
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=http://localhost:3000
```

Obtén tu API key gratuita en: https://console.groq.com

Para obtener las keys de Langfuse, primero levanta el servidor (Paso 5) y crea un proyecto en http://localhost:3000

### Paso 4 — Construir la base de conocimiento

```bash
# Descargar normativa SUNAT (148 documentos)
python scripts/descargar_todo.py

# Extraer texto de HTML y PDF
python scripts/extraer_texto.py

# Indexar en ChromaDB con BGE-M3
python scripts/indexar_chromadb.py
```

> ⏳ La indexación tarda ~30 minutos (descarga BGE-M3 ~1.2GB la primera vez)

### Paso 5 — Arrancar la aplicación

```bash
# Terminal 1: Langfuse (observabilidad) — arrancar primero
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
- `1` → Solo RAGAS automático (faithfulness + answer relevancy)
- `2` → Solo evaluación manual experto (precisión, relevancia, utilidad, alucinación)
- `3` → Ambos — evaluación completa para la bitácora

Resultados guardados en `data/evaluacion_resultados.json`

> ⚠️ RAGAS usa Groq como LLM juez — requiere saldo disponible (100K tokens/día en plan gratuito).

---

## 💬 Ejemplos de consultas

**Especialista de Aduanas:**
> *"¿Cuál es el procedimiento para inmovilizar una mercancía durante una ACE?"*

**Operador de Comercio Exterior:**
> *"¿Cuánto pago de arancel por importar laptops desde China?"*

**Ciudadano:**
> *"¿Cuánto equipaje puedo traer del extranjero sin pagar impuestos?"*

---

## 📁 Estructura del proyecto

```
aduana_gpt/
├── app.py                          # Interfaz Streamlit con panel de métricas
├── docker-compose.yml              # Langfuse self-hosted
├── requirements.txt                # Dependencias
├── .env                            # Variables de entorno (no subir a git)
├── scripts/
│   ├── descargar_todo.py          # Descarga 148 documentos SUNAT
│   ├── extraer_texto.py           # Extracción de texto HTML/PDF
│   ├── indexar_chromadb.py        # Indexación con BGE-M3
│   └── evaluar_agente.py          # Evaluación RAGAS + manual experto
├── src/
│   ├── agent/agente.py            # Grafo LangGraph (3 nodos)
│   ├── prompts/system_prompt.py   # System prompt con ejemplo de respuesta
│   └── tools/herramientas_rag.py  # 11 herramientas RAG con reranker
└── data/
    ├── raw/                        # Documentos HTML/PDF (excluido del repo)
    ├── processed/                  # Texto extraído (excluido del repo)
    └── vectorstore/                # ChromaDB (excluido del repo)
```

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
