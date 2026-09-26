"""
TripSense — Interface de chat Streamlit
==========================================
Lancer : streamlit run app.py
"""

import streamlit as st
from agent import TripSenseAgent

st.set_page_config(page_title="TripSense", page_icon="✈️", layout="centered")

st.title("✈️ TripSense")
st.caption("Assistant de voyage agentique — météo, devises, distances, en temps réel")

with st.sidebar:
    st.header("À propos")
    st.markdown("""
TripSense est un agent qui combine plusieurs outils en temps réel :

- 🌍 **Géocodage** de villes
- 🌤️ **Météo** actuelle
- 💱 **Conversion** de devises
- 📏 **Distance** entre deux villes

L'agent (Claude) décide seul quels outils utiliser et dans quel ordre,
selon ta question.
    """)
    st.divider()
    if st.button("🔄 Nouvelle conversation"):
        st.session_state.clear()
        st.rerun()
    st.markdown("**Exemples de questions :**")
    st.code("Quel temps fait-il à Lisbonne ?", language=None)
    st.code("Convertis 500 euros en yens", language=None)
    st.code("Distance entre Paris et Tokyo ?", language=None)
    st.code("Je pars à New York avec 300€, "
             "quelle météo et combien de dollars ?", language=None)

# ── État de session : agent + historique affiché ─────────────────────────
if "agent" not in st.session_state:
    st.session_state.agent = TripSenseAgent()
if "history" not in st.session_state:
    st.session_state.history = []

for role, content in st.session_state.history:
    with st.chat_message(role):
        st.markdown(content)

prompt = st.chat_input("Pose ta question de voyage...")

if prompt:
    st.session_state.history.append(("user", prompt))
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("TripSense réfléchit et interroge ses outils..."):
            try:
                response = st.session_state.agent.ask(prompt, verbose=False)
            except Exception as e:
                response = f"⚠️ Erreur : {e}"
        st.markdown(response)

    st.session_state.history.append(("assistant", response))
