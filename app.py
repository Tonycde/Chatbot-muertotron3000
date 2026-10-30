"""Interfaz web (Streamlit).  Uso: streamlit run app.py"""
import streamlit as st

from muertobot import Bot

st.set_page_config(page_title="MuertoBot · Día de Muertos", page_icon="💀", layout="centered")

if "bot" not in st.session_state:
    st.session_state.bot = Bot()
    st.session_state.messages = []
    st.session_state.queued = None
bot: Bot = st.session_state.bot

st.title("💀 MuertoBot")
st.caption("Pregúntame sobre el Día de Muertos en México. Sistema basado en conocimiento con fuentes citadas (sin IA generativa).")

with st.sidebar:
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
    st.session_state.messages.append({"role": "assistant", "text": "¡Hola! Soy MuertoBot. ¿Qué te gustaría saber sobre el Día de Muertos?", "reply": None})


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
