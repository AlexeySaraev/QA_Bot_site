import os
import re
import json
import pandas as pd
import streamlit as st
from datetime import datetime
from gigachat import GigaChat
from gigachat.models import Chat, Messages, MessagesRole

# --- НАСТРОЙКА СТРАНИЦЫ ---
st.set_page_config(page_title="QA SaaS Platform", page_icon="🚀", layout="wide")

st.markdown("""
    <style>
    .block-container {padding-top: 1rem;}
    @media (max-width: 768px) {
        [data-testid="stHorizontalBlock"] { flex-direction: column !important; }
        div[data-testid="column"] { width: 100% !important; margin-bottom: 10px; }
    }
    .stMetric {background-color: #262730; padding: 15px; border-radius: 10px; border: 1px solid #444;}
    </style>
""", unsafe_allow_html=True)

# --- АВТОРИЗАЦИЯ ---
if "authenticated" not in st.session_state: st.session_state["authenticated"] = False
if not st.session_state["authenticated"]:
    st.markdown("## 🔒 Вход в систему")
    pwd = st.text_input("Введите пароль:", type="password")
    if st.button("Войти"):
        if pwd == "qa2026":
            st.session_state["authenticated"] = True
            st.rerun()
        else: st.error("❌ Неверный пароль")
    st.stop()

# --- КОНФИГУРАЦИЯ ---
ROLES = {
    "Анализ требований": {
        "prompt": "Ты — Senior QA Analyst. Анализируй требования. В конце ответа выведи блок: 'МЕТРИКИ: Проблем: X, Вопросов: Y, Тестируемость: Z%, Неопределенность: A%, Риск: B%'.",
        "labels": ["Тестируемость", "Неопределенность", "Риск"]
    },
    "Ревью кода / автотестов": {
        "prompt": "Ты — Senior QA Automation. Ревью кода. В конце ответа выведи блок: 'МЕТРИКИ: Замечаний: X, Вопросов: Y, Поддерживаемость: Z%, Сложность: A%, Риск: B%'.",
        "labels": ["Поддерживаемость", "Сложность", "Риск"]
    }
}

def extract_metrics(text):
    # Ищем строку МЕТРИКИ: и извлекаем из нее все числовые значения
    metric_line = re.search(r'МЕТРИКИ:(.*)', text, re.IGNORECASE)
    if metric_line:
        vals = re.findall(r'\d+', metric_line.group(1))
        if len(vals) >= 5:
            return {"p": int(vals[0]), "q": int(vals[1]), "m1": int(vals[2]), "m2": int(vals[3]), "m3": int(vals[4])}
    return None

# --- ИНТЕРФЕЙС ---
with st.sidebar:
    role = st.selectbox("Специализация:", list(ROLES.keys()))
    if st.button("🧹 Очистить сессию"): 
        st.session_state.messages = []
        st.session_state.metrics = None
        st.rerun()

st.title(f"🚀 {role}")

# Дашборд
if "metrics" not in st.session_state: st.session_state.metrics = None
if st.session_state.metrics:
    m = st.session_state.metrics
    l = ROLES[role]["labels"]
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("❗ Проблем", m['p'])
    c2.metric("❓ Вопросов", m['q'])
    c3.metric(l[0], f"{m['m1']}%")
    c4.metric(l[1], f"{m['m2']}%")
    c5.metric(l[2], f"{m['m3']}%")
    st.bar_chart(pd.DataFrame({"Значение": [m['m1'], m['m2'], m['m3']]}, index=l))

# Чат
if "messages" not in st.session_state: st.session_state.messages = []
for msg in st.session_state.messages: st.chat_message(msg["role"]).markdown(msg["content"])

if prompt := st.chat_input("Введите запрос для анализа..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.spinner("ИИ анализирует данные..."):
        try:
            # Использование GigaChat
            with GigaChat(credentials=os.getenv("GIGA_CREDENTIALS"), verify_ssl_certs=False) as giga:
                # Добавляем системный промпт текущей роли
                current_messages = [{"role": "system", "content": ROLES[role]["prompt"]}] + st.session_state.messages
                msgs = [Messages(role=m["role"], content=m["content"]) for m in current_messages]
                res = giga.chat(Chat(messages=msgs))
                ans = res.choices[0].message.content
                
                st.session_state.metrics = extract_metrics(ans)
                st.session_state.messages.append({"role": "assistant", "content": ans})
                st.rerun()
        except Exception as e: 
            st.error(f"Ошибка API: {e}")
