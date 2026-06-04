import os
import sqlite3
from datetime import datetime
import streamlit as st
from gigachat import GigaChat
from gigachat.models import Chat, Messages

# ==================================================
# PAGE CONFIG
# ==================================================
st.set_page_config(
    page_title="AVSBOT — Intelligent QA Platform",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================================================
# CUSTOM CSS (современный красивый дизайн)
# ==================================================
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(180deg, #0A0C14 0%, #0F1117 100%);
    }
    .main .block-container {
        padding-top: 2rem;
        max-width: 1400px;
    }
    
    /* Chat bubbles */
    .stChatMessage {
        border-radius: 18px;
        padding: 14px 18px;
        margin-bottom: 10px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    }
    .stChatMessage.user {
        background: linear-gradient(135deg, #6366F1, #8B5CF6);
        color: white;
        border-bottom-right-radius: 4px;
    }
    .stChatMessage.assistant {
        background: #1A1D2E;
        border: 1px solid #2A2F45;
        border-bottom-left-radius: 4px;
    }

    /* Buttons */
    .stButton button {
        border-radius: 12px;
        height: 48px;
        font-weight: 500;
        transition: all 0.3s ease;
    }
    .stButton button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 20px rgba(99, 102, 241, 0.3);
    }

    /* Metric cards */
    .metric-card {
        background: #161A27;
        padding: 16px;
        border-radius: 14px;
        border: 1px solid #2A2F45;
        text-align: center;
    }
    
    h1 {
        font-size: 2.8rem;
        background: linear-gradient(90deg, #C4C4F7, #A78BFA);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
</style>
""", unsafe_allow_html=True)

# ==================================================
# DATABASE
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
# ROLES & TEMPLATES
# ==================================================
ROLES = {
    "Анализ требований": {
        "prompt": "Ты — Senior QA Analyst с 10-летним опытом. Анализируй требования глубоко и критически.",
        "color": "#6366F1"
    },
    "Генератор тестов": {
        "prompt": "Ты — QA Automation Engineer. Генерируй качественные, покрывающие и реалистичные тест-кейсы.",
        "color": "#10B981"
    },
    "Поиск рисков": {
        "prompt": "Ты — Risk-Based Testing Expert. Ищи скрытые риски, неопределённости и потенциальные баги.",
        "color": "#F59E0B"
    }
}

# ==================================================
# SIDEBAR
# ==================================================
with st.sidebar:
    st.title("🚀 AVSBOT 2.0")
    st.caption("Intelligent QA Platform")
    
    selected_role = st.selectbox("Выберите режим", list(ROLES.keys()))
    
    st.divider()
    temperature = st.slider("Креативность", 0.0, 1.2, 0.7, 0.05)
    
    if st.button("🧹 Очистить чат", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# ==================================================
# SESSION STATE
# ==================================================
if "messages" not in st.session_state:
    st.session_state.messages = []

# Update system prompt
system_prompt = ROLES[selected_role]["prompt"]
if not st.session_state.messages or st.session_state.messages[0]["role"] != "system":
    st.session_state.messages.insert(0, {"role": "system", "content": system_prompt})
else:
    st.session_state.messages[0]["content"] = system_prompt

# ==================================================
# MAIN UI
# ==================================================
col1, col2 = st.columns([3, 1])
with col1:
    st.title("🛡️ AVSBOT QA Platform")

with col2:
    st.caption(f"**Режим:** {selected_role}")

# Quick Templates
st.subheader("Быстрые шаблоны")
cols = st.columns(4)
templates = [
    "Проведи полный анализ требований",
    "Сгенерируй тест-кейсы (Positive + Negative)",
    "Выяви риски и неопределённости",
    "Предложи E2E сценарии"
]

for i, template in enumerate(templates):
    if cols[i].button(template, use_container_width=True):
        st.session_state.messages.append({"role": "user", "content": template})
        st.rerun()

# Chat
for msg in st.session_state.messages[1:]:  # skip system
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Input
user_input = st.chat_input("Опишите задачу или вставьте требования...")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    with st.chat_message("user"):
        st.markdown(user_input)
    
    with st.chat_message("assistant"):
        with st.spinner("AVSBOT думает..."):
            try:
                credentials = st.secrets["GIGA_CREDENTIALS"]
                
                with GigaChat(credentials=credentials, verify_ssl_certs=False) as giga:
                    giga_messages = [
                        Messages(role=m["role"], content=m["content"])
                        for m in st.session_state.messages
                    ]
                    
                    response = giga.chat(Chat(
                        messages=giga_messages, 
                        temperature=temperature
                    ))
                    
                    answer = response.choices[0].message.content
                    st.session_state.messages.append({"role": "assistant", "content": answer})
                    st.markdown(answer)
                    
            except Exception as e:
                st.error(f"Ошибка API: {e}")

# TODO: Добавить автооценку ответа (следующий шаг)
