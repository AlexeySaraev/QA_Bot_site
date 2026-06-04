
import os
import re
import sqlite3
from datetime import datetime
from io import BytesIO

import pandas as pd
import plotly.express as px
import streamlit as st

from gigachat import GigaChat
from gigachat.models import Chat, Messages, MessagesRole

# =========================
# CONFIG
# =========================

st.set_page_config(
    page_title="QA SaaS Platform",
    page_icon="🚀",
    layout="wide"
)

DB_FILE = "qa_platform.db"

DEFAULT_ANALYST_PROMPT = """
Ты — Senior QA Analyst.

Анализируй требования строго по структуре:

📌 Резюме:
❗ Проблемы:
❓ Вопросы:
✅ Чек-лист:
⏱ Оценка сроков:

В самом конце ОБЯЗАТЕЛЬНО:

МЕТРИКИ_СТАРТ
Проблем: [число]
Вопросов: [число]
Тестируемость: [0-100]
Неопределенность: [0-100]
Риск: [0-100]
МЕТРИКИ_КОНЕЦ
"""

DEFAULT_TESTER_PROMPT = """
Ты — Senior QA Engineer.

Пиши:
- тест-кейсы
- негативные сценарии
- edge-cases
- API проверки
- security проверки

Используй markdown таблицы.
"""

ROLES = {
    "Анализ требований": {
        "prompt": DEFAULT_ANALYST_PROMPT,
        "templates": [
            "Проверь требования к авторизации",
            "Найди проблемы в корзине",
            "Оцени API требования"
        ]
    },
    "Генератор тест-кейсов": {
        "prompt": DEFAULT_TESTER_PROMPT,
        "templates": [
            "Сгенерируй негативные кейсы оплаты",
            "Напиши E2E сценарий",
            "Создай smoke checklist"
        ]
    }
}

# =========================
# CSS
# =========================

st.markdown("""
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

.block-container {
    padding-top: 1.5rem;
}

.metric-card {
    background-color: #1e1e1e;
    padding: 15px;
    border-radius: 12px;
    border: 1px solid #333;
}
</style>
""", unsafe_allow_html=True)

# =========================
# DB
# =========================

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


def save_analysis(role, prompt, response, metrics):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute("""
    INSERT INTO analyses (
        created_at,
        role,
        prompt,
        response,
        problems,
        questions,
        testability,
        uncertainty,
        risk
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        role,
        prompt,
        response,
        metrics["problems"],
        metrics["questions"],
        metrics["testability"],
        metrics["uncertainty"],
        metrics["risk"]
    ))

    conn.commit()
    conn.close()


def load_history():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query(
        "SELECT * FROM analyses ORDER BY id DESC",
        conn
    )
    conn.close()
    return df


init_db()

# =========================
# AUTH
# =========================

def check_auth():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        st.title("🔒 QA SaaS Platform")

        password = st.text_input(
            "Введите пароль",
            type="password"
        )

        login_password = os.getenv("APP_PASSWORD", "qa2026")

        if st.button("Войти"):
            if password == login_password:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Неверный пароль")

        st.stop()


check_auth()

# =========================
# METRICS
# =========================

def extract_metrics(text):
    metrics = {
        "problems": 0,
        "questions": 0,
        "testability": 0,
        "uncertainty": 0,
        "risk": 0
    }

    try:
        if "МЕТРИКИ_СТАРТ" in text:
            block = text.split("МЕТРИКИ_СТАРТ")[1].split("МЕТРИКИ_КОНЕЦ")[0]

            patterns = {
                "problems": r'Проблем[^\d]*(\d+)',
                "questions": r'Вопросов[^\d]*(\d+)',
                "testability": r'Тестируемость[^\d]*(\d+)',
                "uncertainty": r'Неопределенность[^\d]*(\d+)',
                "risk": r'Риск[^\d]*(\d+)'
            }

            for key, pattern in patterns.items():
                match = re.search(pattern, block, re.IGNORECASE)
                if match:
                    metrics[key] = int(match.group(1))

    except Exception:
        pass

    return metrics


# =========================
# FILE READER
# =========================

def read_uploaded_file(uploaded_file):
    ext = uploaded_file.name.split(".")[-1].lower()

    if ext in ["txt", "md"]:
        return uploaded_file.read().decode("utf-8")

    elif ext == "docx":
        from docx import Document

        doc = Document(uploaded_file)
        return "\n".join([p.text for p in doc.paragraphs])

    elif ext == "pdf":
        import fitz

        pdf = fitz.open(stream=uploaded_file.read(), filetype="pdf")

        text = ""

        for page in pdf:
            text += page.get_text()

        return text

    return ""


# =========================
# SIDEBAR
# =========================

with st.sidebar:
    st.header("⚙️ Конфигурация")

    selected_role = st.selectbox(
        "Режим",
        list(ROLES.keys())
    )

    if f"prompt_{selected_role}" not in st.session_state:
        st.session_state[f"prompt_{selected_role}"] = ROLES[selected_role]["prompt"]

    current_prompt = st.text_area(
        "System Prompt",
        value=st.session_state[f"prompt_{selected_role}"],
        height=220
    )

    st.session_state[f"prompt_{selected_role}"] = current_prompt

    temperature = st.slider(
        "Креативность",
        0.1,
        1.2,
        0.7,
        0.1
    )

    if st.button("🧹 Очистить чат"):
        st.session_state.messages = []
        st.rerun()

    st.divider()

    st.subheader("📚 История")

    history_df = load_history()

    st.metric("Всего анализов", len(history_df))

# =========================
# MAIN
# =========================

st.title("🛡️ QA Requirements Analyzer")

# =========================
# DASHBOARD
# =========================

if "last_metrics" not in st.session_state:
    st.session_state.last_metrics = None

if st.session_state.last_metrics:
    st.subheader("📊 QA Quality Dashboard")

    m = st.session_state.last_metrics

    c1, c2, c3, c4, c5 = st.columns(5)

    c1.metric("❗ Проблемы", m["problems"])
    c2.metric("❓ Вопросы", m["questions"])
    c3.metric("🧪 Тестируемость", f'{m["testability"]}%')
    c4.metric("🌫 Неопределенность", f'{m["uncertainty"]}%')
    c5.metric("🔥 Риск", f'{m["risk"]}%')

    chart_df = pd.DataFrame({
        "Metric": [
            "Testability",
            "Uncertainty",
            "Risk"
        ],
        "Value": [
            m["testability"],
            m["uncertainty"],
            m["risk"]
        ]
    })

    fig = px.bar(
        chart_df,
        x="Metric",
        y="Value",
        title="Risk Analysis"
    )

    st.plotly_chart(fig, use_container_width=True)

# =========================
# CHAT
# =========================

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": MessagesRole.SYSTEM,
            "content": current_prompt
        }
    ]

st.session_state.messages[0]["content"] = current_prompt

# =========================
# QUICK ACTIONS
# =========================

st.write("### 💡 Быстрые действия")

templates = ROLES[selected_role]["templates"]

cols = st.columns(3)

template_prompt = ""

for i, template in enumerate(templates):
    if cols[i].button(template, use_container_width=True):
        template_prompt = template

# =========================
# FILE UPLOAD
# =========================

uploaded_file = st.file_uploader(
    "📎 Загрузить файл",
    type=["txt", "md", "docx", "pdf"]
)

file_context = ""

if uploaded_file:
    file_context = read_uploaded_file(uploaded_file)

# =========================
# INPUT
# =========================

user_input = st.chat_input("Введите требования...")

final_prompt = user_input if user_input else template_prompt

# =========================
# AI REQUEST
# =========================

if final_prompt:
    if file_context:
        final_prompt = f"""
Контекст документа:
{file_context}

Запрос:
{final_prompt}
"""

    st.session_state.messages.append({
        "role": "user",
        "content": final_prompt
    })

    with st.spinner("🧠 AI анализирует требования..."):

        try:
            credentials = os.getenv("GIGA_CREDENTIALS")

            with GigaChat(
                credentials=credentials
            ) as giga:

                giga_messages = [
                    Messages(
                        role=m["role"],
                        content=m["content"]
                    )
                    for m in st.session_state.messages
                ]

                response = giga.chat(
                    Chat(
                        messages=giga_messages,
                        temperature=temperature
                    )
                )

                bot_response = response.choices[0].message.content

                metrics = extract_metrics(bot_response)

                st.session_state.last_metrics = metrics

                cleaned_response = bot_response.split(
                    "МЕТРИКИ_СТАРТ"
                )[0].strip()

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": cleaned_response
                })

                save_analysis(
                    selected_role,
                    final_prompt,
                    cleaned_response,
                    metrics
                )

                st.rerun()

        except Exception as e:
            st.error(f"Ошибка API: {e}")

# =========================
# HISTORY
# =========================

for message in st.session_state.messages:

    if message["role"] == "user":
        with st.chat_message("user"):
            st.write("Запрос отправлен")

    elif message["role"] == "assistant":
        with st.chat_message("assistant"):
            st.markdown(message["content"])

            st.download_button(
                "📥 Скачать markdown",
                data=message["content"],
                file_name="qa_analysis.md",
                mime="text/markdown"
            )

            with st.expander("📋 Исходный Markdown"):
                st.code(
                    message["content"],
                    language="markdown"
                )

# =========================
# ANALYTICS
# =========================

st.divider()

st.subheader("📈 История анализов")

history_df = load_history()

if not history_df.empty:
    st.dataframe(
        history_df[
            [
                "created_at",
                "role",
                "problems",
                "questions",
                "testability",
                "risk"
            ]
        ],
        use_container_width=True
    )

    trend_fig = px.line(
        history_df,
        x="created_at",
        y="risk",
        title="Risk Trend"
    )

    st.plotly_chart(trend_fig, use_container_width=True)
