"""Interfaz web (Streamlit).  Uso: streamlit run app.py"""
import base64
from pathlib import Path

import streamlit as st

from muertotron import Bot

NOMBRE = "Muertotron3000"
SUBTITULO = "Chatbot sobre el Día de Muertos en México"
ASSETS = Path(__file__).resolve().parent / "assets"

st.set_page_config(page_title=f"{NOMBRE} · Día de Muertos", page_icon="💀", layout="centered")


def svg_uri(name: str) -> str:
    """Imagen SVG local como data-URI (no depende de internet)."""
    data = base64.b64encode((ASSETS / f"{name}.svg").read_bytes()).decode()
    return f"data:image/svg+xml;base64,{data}"


PAPEL, FLOR, CALAVERA, BORDE = (svg_uri(n) for n in ("papel_picado", "cempasuchil", "calavera", "cempasuchil_borde"))

st.markdown(
    f"""
<style>
.stApp {{
  background: radial-gradient(ellipse at 50% 0%, #4a1a73 0%, #2b123f 45%, #12061f 100%);
}}
/* capa de flores de cempasúchil */
.stApp::before {{
  content: ""; position: fixed; inset: 0; z-index: 0; pointer-events: none;
  background-image: url("{FLOR}"); background-size: 230px; opacity: 0.13;
}}
/* papel picado en la parte superior */
.stApp::after {{
  content: ""; position: fixed; top: 0; left: 0; right: 0; height: 96px; z-index: 50; pointer-events: none;
  background: url("{PAPEL}") repeat-x top left / auto 96px;
}}
/* guirnalda de flores abajo */
.md-borde {{
  position: fixed; left: 0; right: 0; bottom: 0; height: 70px; z-index: 1; pointer-events: none;
  background: url("{BORDE}") repeat-x bottom left / auto 70px;
}}
header[data-testid="stHeader"] {{ background: transparent; }}
.block-container {{ padding-top: 7.5rem; padding-bottom: 7rem; position: relative; z-index: 2; }}
section[data-testid="stSidebar"] {{
  background: linear-gradient(180deg, #2b123f 0%, #1a0b2e 100%);
  border-right: 3px solid #ff8f00; z-index: 60;
}}
section[data-testid="stSidebar"] .md-calavera {{ display: block; margin: 0.5rem auto 1rem; width: 120px; }}
[data-testid="stChatMessage"] {{
  background: rgba(26, 11, 46, 0.82); border: 1px solid rgba(255, 143, 0, 0.55);
  border-radius: 16px; box-shadow: 0 4px 18px rgba(0, 0, 0, 0.35);
}}
[data-testid="stBottom"], [data-testid="stBottom"] > div {{ background: transparent !important; }}
[data-testid="stChatInput"] {{ border: 2px solid #ff8f00; border-radius: 14px; background: #2b123f; }}
.stButton > button {{ border: 1px solid #ff8f00; background: rgba(255, 143, 0, 0.10); color: #fff4e0; }}
.stButton > button:hover {{ background: #ff8f00; color: #1a0b2e; border-color: #ffc107; }}
.md-titulo {{ display: flex; align-items: center; gap: 1rem; margin-bottom: 0.6rem; }}
.md-titulo img {{ width: 84px; filter: drop-shadow(0 0 10px rgba(255, 143, 0, 0.6)); }}
.md-titulo h1 {{ margin: 0; padding: 0; font-size: 2.1rem; line-height: 1.1; color: #ffb300; }}
.md-titulo p {{ margin: 0.2rem 0 0; color: #fff4e0; opacity: 0.9; }}
</style>
<div class="md-borde"></div>
<div class="md-titulo">
  <img src="{CALAVERA}" alt="Calavera de azúcar">
  <div><h1>{NOMBRE}</h1><p>{SUBTITULO}</p></div>
</div>
""",
    unsafe_allow_html=True,
)

if "bot" not in st.session_state:
    st.session_state.bot = Bot()
    st.session_state.messages = []
    st.session_state.queued = None
bot: Bot = st.session_state.bot

st.caption("Pregúntame sobre el Día de Muertos en México. Sistema basado en conocimiento con fuentes citadas (sin IA generativa).")

with st.sidebar:
    st.markdown(f'<img class="md-calavera" src="{CALAVERA}" alt="Calavera">', unsafe_allow_html=True)
    st.header("Sobre este sistema")
    st.write("Cada respuesta sale de una base de conocimiento curada y trazable a fuentes (UNESCO, INAH, SEP, INPI…). "
             "Si no sé algo, lo digo.")
    debug = st.toggle("Modo transparencia (para el profesor)", value=False,
                      help="Muestra la entrada elegida, los puntajes de recuperación y las reglas activadas.")
    st.subheader("Prueba con:")
    for q in ["¿Qué es una ofrenda?", "¿Por qué se usa el cempasúchil?", "¿Cuál es el origen del Día de Muertos?",
              "¿Quién es la Catrina?", "¿Qué es Hanal Pixán?"]:
        if st.button(q, use_container_width=True):
            st.session_state.queued = q
    if st.button("🗑️ Reiniciar conversación", use_container_width=True):
        bot.reset()
        st.session_state.messages = []
        st.rerun()

if not st.session_state.messages:
    st.session_state.messages.append({"role": "assistant", "text": "¡Hola! Soy Muertotron3000. 💀🌼 ¿Qué te gustaría saber sobre el Día de Muertos?", "reply": None})


def render(msg: dict) -> None:
    with st.chat_message(msg["role"]):
        if msg["role"] == "user":
            st.text(msg["text"])  # texto plano: nunca se interpreta como HTML/Markdown
            return
        st.markdown(msg["text"])
        r = msg.get("reply")
        if r is None:
            return
        if r.sources:
            with st.expander("📚 Fuentes"):
                for s in r.sources:
                    link = f"[{s['nombre']}]({s['url']})" if s["url"] else s["nombre"]
                    st.markdown(f"- {link}  \n  <small>nivel de fuente: {s['nivel']}</small>", unsafe_allow_html=True)
        if r.suggestions:
            st.markdown("**También puedes preguntar:**\n" + "\n".join(f"- {s}" for s in r.suggestions))
        if debug:
            with st.expander("🔍 Transparencia"):
                st.json({"intent": r.intent, "entrada": r.entry_id, "confianza": r.confidence, **r.debug})


for m in st.session_state.messages:
    render(m)

prompt = st.chat_input("Escribe tu pregunta…") or st.session_state.queued
st.session_state.queued = None
if prompt:
    reply = bot.reply(prompt)
    user_msg = {"role": "user", "text": prompt}
    bot_msg = {"role": "assistant", "text": reply.text, "reply": reply}
    st.session_state.messages += [user_msg, bot_msg]
    render(user_msg)
    render(bot_msg)
