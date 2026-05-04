import os
import sys
import time
import json
import uuid
import sqlite3
import re
import warnings
warnings.filterwarnings("ignore")
os.environ["ANONYMIZED_TELEMETRY"] = "False"
sys.path.append(".")

import streamlit as st
import plotly.graph_objects as go
from src.agent.agente import consultar, consultar_stream
from src.prompts.system_prompt import URLS_DOCUMENTOS
from langfuse import Langfuse

_lf = Langfuse(
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    host=os.getenv("LANGFUSE_HOST", "http://localhost:3000"),
)

def _lf_score(trace_id, value: float, comment: str = ""):
    if not trace_id:
        return
    try:
        _lf.score(trace_id=trace_id, name="user_feedback", value=value, comment=comment)
    except Exception:
        pass

st.set_page_config(
    page_title="ADUANA-GPT · SUNAT Perú",
    page_icon="🛃",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ══════════════════════════════════════════════════════════
# HISTORIAL PERSISTENTE — SQLite
# ══════════════════════════════════════════════════════════
DB_PATH = "data/historial.db"
os.makedirs("data", exist_ok=True)

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS consultas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT,
            pregunta TEXT,
            respuesta TEXT,
            intencion TEXT,
            tiempo_seg REAL,
            score_global REAL,
            feedback INTEGER DEFAULT NULL
        )
    """)
    conn.commit()
    conn.close()

def guardar_consulta(pregunta, respuesta, intencion, tiempo, score):
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            "INSERT INTO consultas (fecha, pregunta, respuesta, intencion, tiempo_seg, score_global) VALUES (datetime('now'), ?, ?, ?, ?, ?)",
            (pregunta, respuesta[:500], intencion, tiempo, score)
        )
        conn.commit()
        lid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.close()
        return lid
    except Exception:
        return None

def guardar_feedback(consulta_id, feedback):
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("UPDATE consultas SET feedback = ? WHERE id = ?", (feedback, consulta_id))
        conn.commit()
        conn.close()
    except Exception:
        pass

def obtener_historial_db(limit=10):
    try:
        conn = sqlite3.connect(DB_PATH)
        rows = conn.execute(
            "SELECT id, fecha, pregunta, intencion, tiempo_seg, score_global, feedback FROM consultas ORDER BY id DESC LIMIT ?",
            (limit,)
        ).fetchall()
        conn.close()
        return rows
    except Exception:
        return []

init_db()

# ══════════════════════════════════════════════════════════
# CACHÉ DE RESPUESTAS — SQLite
# ══════════════════════════════════════════════════════════
def init_cache():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS cache_respuestas (
            pregunta_hash TEXT PRIMARY KEY,
            pregunta TEXT,
            respuesta TEXT,
            intencion TEXT,
            hits INTEGER DEFAULT 1,
            fecha TEXT
        )
    """)
    conn.commit()
    conn.close()

def buscar_cache(pregunta: str):
    import hashlib
    h = hashlib.md5(pregunta.lower().strip().encode()).hexdigest()
    try:
        conn = sqlite3.connect(DB_PATH)
        row = conn.execute(
            "SELECT respuesta, intencion FROM cache_respuestas "
            "WHERE pregunta_hash = ? AND fecha > datetime('now', '-1 month')", (h,)
        ).fetchone()
        if row:
            conn.execute("UPDATE cache_respuestas SET hits = hits + 1 WHERE pregunta_hash = ?", (h,))
            conn.commit()
        conn.close()
        return row
    except Exception:
        return None

def guardar_cache(pregunta: str, respuesta: str, intencion: str):
    import hashlib
    h = hashlib.md5(pregunta.lower().strip().encode()).hexdigest()
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            "INSERT OR REPLACE INTO cache_respuestas (pregunta_hash, pregunta, respuesta, intencion, fecha) VALUES (?, ?, ?, ?, datetime('now'))",
            (h, pregunta, respuesta, intencion)
        )
        conn.commit()
        conn.close()
    except Exception:
        pass

init_cache()

# ══════════════════════════════════════════════════════════
# CSS
# ══════════════════════════════════════════════════════════
def limpiar_respuesta(texto: str) -> str:
    return texto.replace("$", "&#36;").replace(r"\$", "&#36;")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@300;400;600;700&family=DM+Sans:wght@300;400;500&family=DM+Mono:wght@400;500&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
.stApp { background: #07091A; }
.aduana-header { position: relative; padding: 28px 32px 24px; border-radius: 16px; margin-bottom: 20px; overflow: hidden; background: #0D1230; border: 1px solid rgba(212,175,55,0.2); }
.aduana-header::after { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px; background: linear-gradient(90deg, transparent, #D4AF37 30%, #F0C842 60%, transparent); }
.header-eyebrow { font-family: 'DM Mono', monospace; font-size: 10px; letter-spacing: 3px; text-transform: uppercase; color: #D4AF37; margin: 0 0 10px 0; opacity: 0.8; }
.header-title { font-family: 'Sora', sans-serif; font-size: 2.4em; font-weight: 700; color: #F0F4FF; margin: 0 0 6px 0; letter-spacing: -1px; line-height: 1.1; }
.header-title span { color: #D4AF37; }
.header-desc { color: #6B7A99; font-size: 0.88em; margin: 0 0 14px 0; font-weight: 300; }
.header-badges { display: flex; gap: 8px; flex-wrap: wrap; }
.hbadge { background: rgba(240,244,255,0.06); border: 1px solid rgba(240,244,255,0.1); color: #A0AECF; padding: 4px 12px; border-radius: 20px; font-size: 0.72em; font-family: 'DM Mono', monospace; }
.hbadge.gold { background: rgba(212,175,55,0.12); border-color: rgba(212,175,55,0.25); color: #D4AF37; }
.panel-title { font-family: 'DM Mono', monospace; font-size: 10px; letter-spacing: 3px; text-transform: uppercase; color: #38BDF8; margin: 0 0 14px 0; }
.kpi-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 16px; }
.kpi-card { background: #0D1230; border: 1px solid rgba(255,255,255,0.06); border-radius: 12px; padding: 14px; }
.kpi-label { font-size: 10px; color: #4A5568; text-transform: uppercase; letter-spacing: 1.5px; font-family: 'DM Mono', monospace; margin-bottom: 4px; }
.kpi-val { font-family: 'Sora', sans-serif; font-size: 1.7em; font-weight: 700; line-height: 1; }
.kpi-val.good { color: #10B981; } .kpi-val.mid { color: #F59E0B; } .kpi-val.bad { color: #EF4444; } .kpi-val.info { color: #38BDF8; }
.kpi-unit { font-size: 0.4em; color: #4A5568; font-weight: 400; }
.prog-wrap { margin-bottom: 11px; }
.prog-label { display: flex; justify-content: space-between; font-size: 11px; color: #6B7A99; margin-bottom: 4px; }
.prog-label span:last-child { font-family: 'DM Mono', monospace; color: #A0AECF; font-weight: 500; }
.prog-track { height: 4px; background: rgba(255,255,255,0.06); border-radius: 99px; overflow: hidden; }
.prog-fill { height: 100%; border-radius: 99px; }
.resp-metrics { background: #0D1230; border: 1px solid rgba(212,175,55,0.15); border-radius: 12px; padding: 16px 18px; margin-top: 14px; }
.resp-metrics-title { font-family: 'DM Mono', monospace; font-size: 10px; letter-spacing: 2.5px; text-transform: uppercase; color: #D4AF37; margin-bottom: 14px; opacity: 0.85; }
.hist-item { background: #0D1230; border: 1px solid rgba(255,255,255,0.05); border-radius: 10px; padding: 11px 14px; margin-bottom: 8px; }
.hist-q { font-size: 12px; color: #A0AECF; margin-bottom: 7px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.hist-stats { display: flex; gap: 8px; flex-wrap: wrap; }
.hist-pill { font-family: 'DM Mono', monospace; font-size: 10px; padding: 2px 8px; border-radius: 4px; background: rgba(255,255,255,0.05); color: #6B7A99; }
.hist-pill.g { background: rgba(16,185,129,0.1); color: #10B981; }
.hist-pill.y { background: rgba(245,158,11,0.1); color: #F59E0B; }
.hist-pill.r { background: rgba(239,68,68,0.1); color: #EF4444; }
.source-chip { display: inline-flex; align-items: center; gap: 4px; background: rgba(212,175,55,0.08); border: 1px solid rgba(212,175,55,0.2); color: #D4AF37; padding: 3px 10px; border-radius: 6px; font-size: 11px; font-family: 'DM Mono', monospace; text-decoration: none; margin: 3px 3px 3px 0; }
.source-chip:hover { background: rgba(212,175,55,0.15); }
.source-unknown { background: rgba(255,255,255,0.04); border-color: rgba(255,255,255,0.08); color: #6B7A99; }
.feedback-box { display: flex; align-items: center; gap: 8px; margin-top: 12px; padding: 8px 12px; background: rgba(255,255,255,0.02); border-radius: 8px; font-size: 12px; color: #4A5568; }
.cache-badge { display: inline-flex; align-items: center; gap: 4px; background: rgba(56,189,248,0.1); border: 1px solid rgba(56,189,248,0.2); color: #38BDF8; padding: 2px 8px; border-radius: 4px; font-size: 10px; font-family: 'DM Mono', monospace; margin-left: 8px; }
section[data-testid="stSidebar"] { background: #07091A !important; border-right: 1px solid rgba(255,255,255,0.05) !important; }
.sidebar-section-title { font-family: 'DM Mono', monospace; font-size: 9px; letter-spacing: 2.5px; text-transform: uppercase; color: #4A5568; margin: 0 0 10px 0; padding-bottom: 6px; border-bottom: 1px solid rgba(255,255,255,0.05); }
.kb-item { display: flex; align-items: center; gap: 8px; padding: 6px 0; font-size: 12px; color: #6B7A99; border-bottom: 1px solid rgba(255,255,255,0.03); }
.kb-dot { width: 6px; height: 6px; border-radius: 50%; background: #10B981; flex-shrink: 0; }
.kb-num { margin-left: auto; font-family: 'DM Mono', monospace; font-size: 11px; color: #38BDF8; }
.stButton > button { background: rgba(255,255,255,0.03) !important; border: 1px solid rgba(255,255,255,0.07) !important; color: #8896B3 !important; font-size: 12px !important; border-radius: 8px !important; text-align: left !important; font-family: 'DM Sans', sans-serif !important; }
.stButton > button:hover { background: rgba(212,175,55,0.07) !important; border-color: rgba(212,175,55,0.2) !important; color: #D4AF37 !important; }
[data-testid="stChatMessageContent"] { color: #CBD5E1 !important; font-size: 14px !important; line-height: 1.7 !important; }
.welcome-card { background: #0D1230; border: 1px solid rgba(56,189,248,0.12); border-radius: 14px; padding: 20px 22px; margin-bottom: 8px; }
.welcome-title { font-family: 'Sora', sans-serif; font-size: 1.05em; font-weight: 600; color: #F0F4FF; margin-bottom: 12px; }
.wl { font-size: 13px; color: #6B7A99; padding: 3px 0; display: flex; gap: 8px; }
.wl::before { content: '→'; color: #38BDF8; flex-shrink: 0; }
hr { border-color: rgba(255,255,255,0.05) !important; }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════
# CONSTANTES
# ══════════════════════════════════════════════════════════
COLORES_DOMINIO = {
    "DELITOS":     ("#EF4444", "⚖️"),
    "CONTROL":     ("#F59E0B", "🔍"),
    "DESPACHO":    ("#10B981", "📦"),
    "RECAUDACION": ("#3B82F6", "💰"),
    "ORIENTACION": ("#8B5CF6", "👤"),
    "ERROR":       ("#6B7A99", "⚠️"),
}

# ══════════════════════════════════════════════════════════
# FUNCIONES DE RENDER
# ══════════════════════════════════════════════════════════
def render_badge(intencion: str, tiempo: float, desde_cache: bool = False):
    color, icono = COLORES_DOMINIO.get(intencion, ("#6B7A99", "📋"))
    cache_html = '<span class="cache-badge">⚡ caché</span>' if desde_cache else ""
    st.markdown(f"""
<div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;flex-wrap:wrap">
  <span style="background:{color}22;border:1px solid {color}44;color:{color};
               padding:3px 10px;border-radius:20px;font-family:'DM Mono',monospace;
               font-size:11px;font-weight:600;letter-spacing:1px">
    {icono} {intencion}
  </span>
  <span style="color:#4A5568;font-family:'DM Mono',monospace;font-size:11px">
    ⏱ {tiempo:.1f}s
  </span>
  {cache_html}
</div>""", unsafe_allow_html=True)

def extraer_fuentes(respuesta: str) -> list:
    """Extrae los códigos de documentos de la sección Fuentes."""
    patron = r'\[([A-Z0-9\.\-]+)\]'
    fuentes_raw = re.findall(patron, respuesta)
    return list(dict.fromkeys(fuentes_raw))  # deduplicar manteniendo orden

def render_fuentes(fuentes: list):
    if not fuentes:
        return
    chips = ""
    for codigo in fuentes:
        url = URLS_DOCUMENTOS.get(codigo)
        if url:
            chips += f'<a href="{url}" target="_blank" class="source-chip">📄 {codigo} ↗</a>'
        else:
            chips += f'<span class="source-chip source-unknown">📄 {codigo}</span>'
    st.markdown(f'<div style="margin-top:12px">{chips}</div>', unsafe_allow_html=True)

def limpiar_fuentes_del_texto(respuesta: str) -> str:
    """Remueve la sección **Fuentes:** del texto antes de mostrarlo."""
    lineas = respuesta.split('\n')
    resultado = []
    skip = False
    for linea in lineas:
        if linea.strip().startswith("**Fuentes:**"):
            skip = True
        if not skip:
            resultado.append(linea)
    return '\n'.join(resultado).strip()

def calcular_metricas(pregunta: str, respuesta: str, tiempo: float) -> dict:
    palabras = len(respuesta.split())
    rl = respuesta.lower()
    oraciones = max(respuesta.count(".") + respuesta.count("?") + respuesta.count("!"), 1)
    if 80 <= palabras <= 300:
        sl = 1.0
    elif palabras < 80:
        sl = palabras / 80
    else:
        sl = max(0.6, 1.0 - (palabras - 300) / 300)
    refs_fuertes = ["art.", "artículo", "ley n°", "ley n", "decreto", "ds n°", "dl n°", "resolución", "reglamento de"]
    refs_medias  = ["sunat", "despa", "control-", "reca-", "arancel", "procedimiento", "norma", "ley 28008", "dl 1053"]
    sf1 = min(1.0, sum(1 for r in refs_fuertes if r in rl) / 3)
    sm1 = min(1.0, sum(1 for r in refs_medias  if r in rl) / 4)
    sr = sf1 * 0.6 + sm1 * 0.4
    stopwords = {"cuál","cuáles","cómo","qué","para","desde","cuando","puede","puedo","sobre","tiene","tienen","hacer","debo"}
    pq = set(w.lower().strip("¿?.,") for w in pregunta.split() if len(w) > 4 and w.lower() not in stopwords)
    srel = min(1.0, sum(1 for w in pq if w in rl) / max(len(pq), 1))
    tiene_estructura = (respuesta.count("**") >= 2 or any(f"{i}." in respuesta for i in range(1, 5)) or "Base legal" in respuesta or "Procedimiento" in respuesta)
    se = 1.0 if tiene_estructura else 0.6
    ppo = palabras / oraciones
    sf2 = 1.0 if 12 <= ppo <= 25 else max(0.5, 1.0 - abs(ppo - 18) / 18)
    sg = srel * 0.30 + sr * 0.30 + sl * 0.15 + se * 0.15 + sf2 * 0.10
    return {
        "score_global": round(sg * 5, 2),
        "relevancia":   round(srel * 100, 1),
        "referencias":  round(sr * 100, 1),
        "estructura":   round(se * 100, 1),
        "fluidez":      round(sf2 * 100, 1),
        "palabras":     palabras,
        "tiempo_seg":   round(tiempo, 1),
        "pregunta":     pregunta,
    }

def sc(v, mx=5):
    r = v / mx
    return "good" if r >= 0.7 else ("mid" if r >= 0.45 else "bad")

def bc(v, mx=100):
    r = v / mx
    return "#10B981" if r >= 0.7 else ("#F59E0B" if r >= 0.45 else "#EF4444")

def prog_bar(label, val, unit="%", mx=100):
    color = bc(val, mx)
    pct = min(100, val / mx * 100) if mx != 100 else val
    return f"""<div class="prog-wrap">
  <div class="prog-label"><span>{label}</span><span>{val}{unit}</span></div>
  <div class="prog-track"><div class="prog-fill" style="width:{pct}%;background:{color}"></div></div>
</div>"""

def render_metrics(m):
    sg = m["score_global"]
    cls = sc(sg)
    c = {"good":"#10B981","mid":"#F59E0B","bad":"#EF4444"}[cls]
    pc = {"good":"g","mid":"y","bad":"r"}[cls]
    bars = (prog_bar("Relevancia", m["relevancia"]) +
            prog_bar("Refs. normativas", m["referencias"]) +
            prog_bar("Estructura", m.get("estructura", 100)) +
            prog_bar("Fluidez", m["fluidez"]))
    st.markdown(f"""
<div class="resp-metrics">
  <div class="resp-metrics-title">Métricas de respuesta</div>
  <div style="display:flex;align-items:center;gap:20px;margin-bottom:14px">
    <div style="text-align:center;flex-shrink:0">
      <div style="font-family:'Sora',sans-serif;font-size:2.4em;font-weight:700;color:{c};line-height:1">{sg}</div>
      <div style="font-size:10px;color:#4A5568;font-family:'DM Mono',monospace">/ 5.00</div>
    </div>
    <div style="flex:1">{bars}</div>
  </div>
  <div style="display:flex;gap:8px;flex-wrap:wrap">
    <span class="hist-pill {pc}">score {sg}/5</span>
    <span class="hist-pill">⏱ {m['tiempo_seg']}s</span>
    <span class="hist-pill">{m['palabras']} palabras</span>
  </div>
</div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════
# ESTADO DE SESIÓN
# ══════════════════════════════════════════════════════════
for k, v in [("messages", []), ("historia", []), ("pregunta_rapida", None), ("thread_id", str(uuid.uuid4()))]:
    if k not in st.session_state:
        st.session_state[k] = v

# ══════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════
st.markdown("""
<div class="aduana-header">
  <p class="header-eyebrow">Sistema de Consulta Normativa · SUNAT Perú</p>
  <h1 class="header-title">ADUANA<span>-GPT</span></h1>
  <p class="header-desc">Asistente inteligente de normativa aduanera peruana con RAG multidominio</p>
  <div class="header-badges">
    <span class="hbadge gold">Llama 3.3 70B</span>
    <span class="hbadge">148 documentos</span>
    <span class="hbadge">3,861 chunks</span>
    <span class="hbadge">7 nodos LangGraph</span>
    <span class="hbadge">Jina AI + Reranker</span>
    <span class="hbadge">Memoria conversacional</span>
  </div>
</div>""", unsafe_allow_html=True)

col_chat, col_panel = st.columns([3, 1], gap="large")

# ══════════════════════════════════════════════════════════
# PANEL DE MÉTRICAS
# ══════════════════════════════════════════════════════════
with col_panel:
    hist = st.session_state.historia
    if hist:
        n = len(hist)
        avg_sg  = sum(m["score_global"] for m in hist) / n
        avg_t   = sum(m["tiempo_seg"]   for m in hist) / n
        avg_rel = sum(m["relevancia"]   for m in hist) / n
        cls_sg = sc(avg_sg)
        st.markdown(f"""
<div class="kpi-grid">
  <div class="kpi-card"><div class="kpi-label">Score prom.</div><div class="kpi-val {cls_sg}">{avg_sg:.2f}<span class="kpi-unit">/5</span></div></div>
  <div class="kpi-card"><div class="kpi-label">Consultas</div><div class="kpi-val info">{n}</div></div>
  <div class="kpi-card"><div class="kpi-label">T. promedio</div><div class="kpi-val info">{avg_t:.1f}<span class="kpi-unit">s</span></div></div>
  <div class="kpi-card"><div class="kpi-label">Relevancia</div><div class="kpi-val {sc(avg_rel,100)}">{avg_rel:.0f}<span class="kpi-unit">%</span></div></div>
</div>""", unsafe_allow_html=True)

        scores = [m["score_global"] for m in hist]
        if len(scores) > 1:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                y=scores, mode="lines+markers",
                line=dict(color="#D4AF37", width=2),
                marker=dict(color="#D4AF37", size=6),
                fill="tozeroy", fillcolor="rgba(212,175,55,0.07)",
                hovertemplate="Consulta %{x+1}<br>Score: %{y:.2f}<extra></extra>"
            ))
            fig.update_layout(
                height=110, margin=dict(l=0, r=0, t=4, b=0),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
                yaxis=dict(showgrid=False, showticklabels=False, zeroline=False, range=[0, 5.3]),
                showlegend=False,
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        st.markdown('<div class="panel-title">Histórico de sesión</div>', unsafe_allow_html=True)
        for m in reversed(hist):
            cls = {"good":"g","mid":"y","bad":"r"}[sc(m["score_global"])]
            dom = m.get("intencion", "")
            color_d, icono_d = COLORES_DOMINIO.get(dom, ("#6B7A99", "📋"))
            st.markdown(f"""
<div class="hist-item">
  <div class="hist-q">{m['pregunta'][:55]}...</div>
  <div class="hist-stats">
    <span class="hist-pill" style="background:{color_d}22;color:{color_d}">{icono_d} {dom}</span>
    <span class="hist-pill {cls}">★ {m['score_global']}</span>
    <span class="hist-pill">⏱ {m['tiempo_seg']}s</span>
  </div>
</div>""", unsafe_allow_html=True)

        if st.button("↓ Exportar métricas JSON", use_container_width=True):
            st.download_button(
                "Descargar",
                data=json.dumps(hist, ensure_ascii=False, indent=2),
                file_name="metricas_aduana_gpt.json",
                mime="application/json",
                use_container_width=True
            )

        # Historial persistente
        st.markdown("---")
        st.markdown('<div class="panel-title">Historial persistente</div>', unsafe_allow_html=True)
        rows = obtener_historial_db(5)
        for row in rows:
            rid, fecha, preg, intent, tiem, score, fb = row
            fb_icon = "👍" if fb == 1 else ("👎" if fb == 0 else "—")
            color_d, icono_d = COLORES_DOMINIO.get(intent, ("#6B7A99", "📋"))
            st.markdown(f"""
<div class="hist-item">
  <div class="hist-q">{preg[:50]}...</div>
  <div class="hist-stats">
    <span class="hist-pill" style="background:{color_d}22;color:{color_d}">{icono_d} {intent}</span>
    <span class="hist-pill">★ {score:.2f}</span>
    <span class="hist-pill">{fb_icon}</span>
  </div>
</div>""", unsafe_allow_html=True)
    else:
        st.markdown('<div class="panel-title">Panel de métricas</div>', unsafe_allow_html=True)
        st.markdown("""
<div class="kpi-grid">
  <div class="kpi-card"><div class="kpi-label">Score prom.</div><div class="kpi-val info">—</div></div>
  <div class="kpi-card"><div class="kpi-label">Consultas</div><div class="kpi-val info">0</div></div>
  <div class="kpi-card"><div class="kpi-label">T. promedio</div><div class="kpi-val info">—</div></div>
  <div class="kpi-card"><div class="kpi-label">Relevancia</div><div class="kpi-val info">—</div></div>
</div>
<div style="font-size:12px;color:#2D3748;text-align:center;margin-top:20px;font-family:'DM Mono',monospace;line-height:1.8">
  Las métricas aparecerán<br>con tu primera consulta
</div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════
# CHAT
# ══════════════════════════════════════════════════════════
with col_chat:
    with st.sidebar:
        st.markdown('<div class="sidebar-section-title">Consultas rápidas</div>', unsafe_allow_html=True)
        for ej in [
            "¿Qué es el contrabando según la Ley 28008?",
            "¿Cuánto pago de arancel por importar laptops?",
            "¿Cuáles son los canales de control aduanero?",
            "¿Qué documentos necesito para exportar?",
            "¿Cuánto equipaje puedo traer sin pagar impuestos?",
            "¿Qué es el drawback y cómo se solicita?",
            "¿Cuánto dinero puedo traer del extranjero?",
            "¿Qué pasa si no declaro mercancía en aduana?",
        ]:
            if st.button(ej[:46] + "...", use_container_width=True, key=ej):
                st.session_state.pregunta_rapida = ej

        st.markdown("---")
        st.markdown('<div class="sidebar-section-title">Base de conocimiento</div>', unsafe_allow_html=True)
        for nombre, num in [
            ("Ley 28008 + Reglamento", "2"),
            ("Ley General de Aduanas", "3"),
            ("Proced. de despacho", "95"),
            ("Proced. fiscalización", "13"),
            ("Proced. recaudación", "16"),
            ("Normas asociadas", "11"),
            ("Arancel de Aduanas 2022", "2"),
        ]:
            st.markdown(f"""
<div class="kb-item">
  <div class="kb-dot"></div>
  <span>{nombre}</span>
  <span class="kb-num">{num}</span>
</div>""", unsafe_allow_html=True)

        st.markdown("---")
        if st.button("🗑 Limpiar conversación", use_container_width=True):
            st.session_state.messages = []
            st.session_state.historia = []
            st.session_state.pregunta_rapida = None
            st.session_state.thread_id = str(uuid.uuid4())
            st.rerun()
        st.markdown("---")
        st.markdown("""
<div style="font-size:11px;color:#2D3748;font-family:'DM Mono',monospace;line-height:1.8">
  LangGraph 7 nodos · aristas condicionales<br>
  Llama 3.3 70B · Groq API<br>
  Jina AI + Reranker · Qdrant Cloud<br>
  Memoria conversacional · Caché SQLite<br>
  <span style="color:#10B981">Costo total: S/. 0.00</span>
</div>""", unsafe_allow_html=True)

    # Historial de mensajes
    for i, msg in enumerate(st.session_state.messages):
        with st.chat_message(msg["role"], avatar="🛃" if msg["role"] == "assistant" else "👤"):
            if msg["role"] == "assistant" and "intencion" in msg:
                render_badge(msg["intencion"], msg.get("tiempo", 0), msg.get("desde_cache", False))
            st.markdown(limpiar_respuesta(msg["content"]), unsafe_allow_html=True)
            if msg["role"] == "assistant":
                if "fuentes" in msg and msg["fuentes"]:
                    render_fuentes(msg["fuentes"])
                if "metricas" in msg:
                    render_metrics(msg["metricas"])
                # Feedback
                if "db_id" in msg:
                    fb_actual = msg.get("feedback")
                    col1, col2, col3 = st.columns([1, 1, 8])
                    with col1:
                        if st.button("👍", key=f"fb_pos_{i}", help="Respuesta útil"):
                            guardar_feedback(msg["db_id"], 1)
                            _lf_score(msg.get("trace_id"), 1.0, comment="👍")
                            st.session_state.messages[i]["feedback"] = 1
                            st.rerun()
                    with col2:
                        if st.button("👎", key=f"fb_neg_{i}", help="Respuesta incorrecta"):
                            guardar_feedback(msg["db_id"], 0)
                            _lf_score(msg.get("trace_id"), 0.0, comment="👎")
                            st.session_state.messages[i]["feedback"] = 0
                            st.rerun()
                    with col3:
                        if fb_actual == 1:
                            st.markdown('<span style="color:#10B981;font-size:12px">✓ Marcado como útil</span>', unsafe_allow_html=True)
                        elif fb_actual == 0:
                            st.markdown('<span style="color:#EF4444;font-size:12px">✗ Marcado como incorrecto</span>', unsafe_allow_html=True)

    # Bienvenida
    if not st.session_state.messages:
        with st.chat_message("assistant", avatar="🛃"):
            st.markdown("""
<div class="welcome-card">
<div class="welcome-title">Bienvenido a ADUANA-GPT</div>
<div class="wl">Delitos aduaneros — tipificación según Ley 28008</div>
<div class="wl">Procedimientos de despacho y ACE</div>
<div class="wl">Partidas arancelarias y derechos ad valorem</div>
<div class="wl">Mercancías prohibidas y restringidas</div>
<div class="wl">Sanciones, multas y garantías aduaneras</div>
</div>
Escribe tu consulta o usa los ejemplos del panel izquierdo.
""", unsafe_allow_html=True)

    # Input
    pregunta = st.chat_input("Consulta la normativa aduanera peruana...")
    if st.session_state.pregunta_rapida:
        pregunta = st.session_state.pregunta_rapida
        st.session_state.pregunta_rapida = None

    if pregunta:
        with st.chat_message("user", avatar="👤"):
            st.markdown(pregunta)
        st.session_state.messages.append({"role": "user", "content": pregunta})

        with st.chat_message("assistant", avatar="🛃"):
            # Verificar caché
            cached = buscar_cache(pregunta)
            desde_cache = False

            if cached:
                respuesta, intencion = cached
                tiempo = 0.1
                desde_cache = True
                trace_id = None
                usar_placeholder = False
            else:
                t0 = time.time()
                texto_acumulado = ""
                intencion  = "DESPACHO"
                trace_id   = None
                respuesta  = ""
                ph = st.empty()
                ph.markdown("*⚙️ Clasificando y recuperando normativa...*")

                for chunk in consultar_stream(pregunta, thread_id=st.session_state.thread_id):
                    if chunk["type"] == "token":
                        texto_acumulado += chunk["content"]
                        ph.markdown(
                            limpiar_respuesta(limpiar_fuentes_del_texto(texto_acumulado)) + " ▌",
                            unsafe_allow_html=True,
                        )
                    elif chunk["type"] == "done":
                        ph.markdown(
                            limpiar_respuesta(limpiar_fuentes_del_texto(texto_acumulado)),
                            unsafe_allow_html=True,
                        )
                        intencion = chunk["intencion"]
                        trace_id  = chunk["trace_id"]
                        respuesta = chunk["respuesta"] or texto_acumulado

                tiempo = time.time() - t0
                guardar_cache(pregunta, respuesta, intencion)
                desde_cache      = False
                usar_placeholder = True

            # Extraer fuentes y limpiar texto
            fuentes = extraer_fuentes(respuesta)
            respuesta_limpia_texto = limpiar_fuentes_del_texto(respuesta)
            respuesta_display = limpiar_respuesta(respuesta_limpia_texto)

            render_badge(intencion, tiempo, desde_cache)
            if not usar_placeholder:
                st.markdown(respuesta_display, unsafe_allow_html=True)

            if fuentes:
                render_fuentes(fuentes)

            m = calcular_metricas(pregunta, respuesta, tiempo)
            m["intencion"] = intencion
            render_metrics(m)

            # Guardar en DB y obtener ID
            db_id = guardar_consulta(pregunta, respuesta, intencion, tiempo, m["score_global"])

            # Feedback
            col1, col2, col3 = st.columns([1, 1, 8])
            with col1:
                if st.button("👍", key=f"fb_pos_new", help="Respuesta útil"):
                    guardar_feedback(db_id, 1)
                    _lf_score(trace_id, 1.0, comment="👍")
            with col2:
                if st.button("👎", key=f"fb_neg_new", help="Respuesta incorrecta"):
                    guardar_feedback(db_id, 0)
                    _lf_score(trace_id, 0.0, comment="👎")

        st.session_state.messages.append({
            "role":        "assistant",
            "content":     respuesta_display,
            "metricas":    m,
            "intencion":   intencion,
            "tiempo":      tiempo,
            "fuentes":     fuentes,
            "db_id":       db_id,
            "feedback":    None,
            "desde_cache": desde_cache,
            "trace_id":    trace_id,
        })
        st.session_state.historia.append(m)
        st.rerun()