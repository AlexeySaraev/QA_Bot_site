import os
import re
import sqlite3
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

from gigachat import GigaChat
from gigachat.models import Chat, Messages

# ==================================================
# PAGE CONFIG
# ==================================================

st.set_page_config(
    page_title="AVSBOT QA Platform",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"   # ✅ FIX: было collapsed
)

# ==================================================
# CSS
# ==================================================

st.markdown("""
<style>

/* ❌ FIX: НЕ скрываем header — иначе пропадает кнопка меню */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}

/* header НЕ скрываем !!! */

/* layout */
.block-container {
    max-width: 1450px;
    padding-top: 0.5rem;
    padding-bottom: 6rem;
}

/* typography */
html, body, [class*="css"] {
    font-size: 15px;
}

/* chat */
.stChatMessage {
    border-radius: 16px;
    padding: 10px;
}

/* buttons */
.stButton button {
    width: 100%;
    border-radius: 14px;
    height: 52px;
    font-size: 15px;
    border: 1px solid #333;
}

/* inputs */
.stTextArea textarea {
    border-radius: 14px;
}

/* sidebar */
section[data-testid="stSidebar"] {
    background: #0E1117;
    border-right: 1px solid #222;
    min-width: 320px;
}

/* metrics */
[data-testid="metric-container"] {
    border-radius: 14px;
    padding: 10px;
    border: 1px solid #333;
    background: #161A23;
}

/* mobile */
@media (max-width: 768px) {

    .block-container {
        padding-left: 0.8rem;
        padding-right: 0.8rem;
    }

    h1 { font-size: 28px !important; }
    h2 { font-size: 22px !important; }
}

</style>
""", unsafe_allow_html=True)

# ==================================================
# DB
# ==================================================

DB_FILE = "qa_platform.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS analyses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT,
        role TEXT,
        prompt TEXT,
        response TEXT,
        problems INTEGER,
        questions INTEGER,
        testability INTEGER,
        uncertainty INTEGER,
        risk INTEGER
    )
    """)

    conn.commit()
    conn.close()

init_db()

# ==================================================
# ROLES
# ==================================================

ROLES = {
    "Анализ требований": {
        "prompt": "Ты — Senior QA Analyst.",
        "templates": ["Проверь API", "Найди баги", "Оцени риски"]
    },
    "Генератор тестов": {
        "prompt": "Ты — QA Engineer.",
        "templates": ["Сгенерируй тесты", "E2E сценарии", "Негативные кейсы"]
    }
}

# ==================================================
# SIDEBAR
# ==================================================

with st.sidebar:
    st.title("🚀 AVSBOT")

    selected_role = st.selectbox("Режим", list(ROLES.keys()))

    current_prompt = st.text_area(
        "System Prompt",
        value=ROLES[selected_role]["prompt"],
        height=200
    )

    temperature = st.slider("Креативность", 0.1, 1.2, 0.7)

    if st.button("🧹 Очистить чат"):
        st.session_state.messages = []
        st.rerun()

# ==================================================
# STATE
# ==================================================

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": current_prompt}
    ]

st.session_state.messages[0]["content"] = current_prompt

# ==================================================
# UI
# ==================================================

st.title("🛡️ QA AI Platform")

# ==================================================
# INPUT
# ==================================================

user_input = st.chat_input("Введите запрос...")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})

    try:
        credentials = st.secrets["GIGA_CREDENTIALS"]

        with GigaChat(credentials=credentials, verify_ssl_certs=False) as giga:

            giga_messages = [
                Messages(role=m["role"], content=m["content"])
                for m in st.session_state.messages
            ]

            response = giga.chat(Chat(messages=giga_messages, temperature=temperature))

            answer = response.choices[0].message.content

            st.session_state.messages.append(
                {"role": "assistant", "content": answer}
            )

    except Exception as e:
        st.error(f"API error: {e}")

# ==================================================
# CHAT RENDER
# ==================================================

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
