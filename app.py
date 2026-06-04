import streamlit as st
import sqlite3
import pandas as pd
import json
from datetime import datetime
from gigachat import GigaChat
from gigachat.models import Chat, Messages
import plotly.express as px

# ==================================================
# PAGE CONFIG
# ==================================================
st.set_page_config(
    page_title="AVSBOT 2.0 — QA Intelligence",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================================================
# CUSTOM CSS
# ==================================================
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(180deg, #0a0c14 0%, #0f1117 100%);
    }
    .main-header {
        font-size: 2.8rem;
        background: linear-gradient(90deg, #6366f1, #a855f7);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    .stChatMessage {
        border-radius: 18px;
        padding: 14px 18px;
        margin-bottom: 12px;
    }
    .stButton button {
        border-radius: 12px;
        height: 48px;
        font-weight: 500;
    }
    .metric-card {
        background: #161821;
        border-radius: 16px;
        padding: 16px;
        border: 1px solid #2a2f3c;
    }
    .chip {
        display: inline-block;
        background: #1f2333;
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 0.9rem;
        margin: 4px;
    }
</style>
""", unsafe_allow_html=True)

# ==================================================
# DATABASE
# ==================================================
DB_FILE = "avsbot.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT,
            session_id TEXT,
            role TEXT,
            user_prompt TEXT,
            response TEXT,
            problems INTEGER,
            questions INTEGER,
            testability INTEGER,
            uncertainty INTEGER,
            risk INTEGER,
            overall_score REAL
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def save_analysis(data: dict):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        INSERT INTO analyses 
        (created_at, session_id, role, user_prompt, response, problems, questions, 
         testability, uncertainty, risk, overall_score)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        datetime.now().isoformat(),
        data['session_id'],
        data['role'],
        data['user_prompt'],
        data['response'],
        data['problems'],
        data['questions'],
        data['testability'],
        data['uncertainty'],
        data['risk'],
        data['overall_score']
    ))
    conn.commit()
    conn.close()

# ==================================================
# ROLES & TEMPLATES
# ==================================================
ROLES = {
    "Senior QA Analyst": {
        "prompt": "Ты — Senior QA Analyst с 10+ летним опытом. Анализируй требования глубоко, находи неоднозначности, риски и пробелы.",
        "color": "#6366f1"
    },
    "Test Architect": {
        "prompt": "Ты — Test Architect. Генерируй стратегию тестирования, тест-кейсы, E2E сценарии и чек-листы.",
        "color": "#a855f7"
    },
    "QA Automation Engineer": {
        "prompt": "Ты — QA Automation Engineer. Пиши автотесты, думай о стабильности, Page Object, data-driven.",
        "color": "#22c55e"
    }
}

TEMPLATES = {
    "Полный анализ требований": "Проведи полный анализ требований: найди неоднозначности, противоречия, пропущенные сценарии и риски.",
    "Генерация тест-кейсов": "Сгенерируй полный набор тест-кейсов (позитивные, негативные, граничные).",
    "Поиск рисков": "Выдели все потенциальные риски проекта и предложи mitigation plan.",
    "Негативное тестирование": "Сгенерируй мощные негативные сценарии и edge cases."
}

# ==================================================
# SIDEBAR
# ==================================================
with st.sidebar:
    st.title("🛡️ AVSBOT 2.0")
    st.caption("Intelligent QA Platform")
    
    selected_role_name = st.selectbox("Роль", list(ROLES.keys()))
    selected_role = ROLES[selected_role_name]
    
    temperature = st.slider("Температура", 0.1, 1.2, 0.65, 0.05)
    
    st.divider()
    st.subheader("Быстрые шаблоны")
    for name, prompt in TEMPLATES.items():
        if st.button(name, use_container_width=True):
            st.session_state.quick_prompt = prompt

# ==================================================
# TABS
# ==================================================
tab_chat, tab_analytics, tab_history, tab_settings = st.tabs([
    "💬 Чат", "📊 Аналитика", "📜 История", "⚙️ Настройки"
])

# ==================================================
# SESSION STATE
# ==================================================
if "messages" not in st.session_state:
    st.session_state.messages = []
if "quick_prompt" not in st.session_state:
    st.session_state.quick_prompt = ""

# ==================================================
# CHAT TAB
# ==================================================
with tab_chat:
    st.markdown(f'<h1 class="main-header">Чат с {selected_role_name}</h1>', unsafe_allow_html=True)
    
    # File uploader
    uploaded_file = st.file_uploader("Прикрепить документ (TXT, PDF, DOCX)", 
                                   type=["txt", "pdf", "docx"])
    
    # Display chat
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Input
    user_input = st.chat_input("Опишите задачу...")
    
    if user_input or st.session_state.quick_prompt:
        if st.session_state.quick_prompt:
            user_input = st.session_state.quick_prompt
            st.session_state.quick_prompt = ""
        
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        with st.chat_message("user"):
            st.markdown(user_input)
        
        with st.spinner("AVSBOT думает..."):
            try:
                credentials = st.secrets["GIGA_CREDENTIALS"]
                
                system_prompt = selected_role["prompt"]
                
                messages = [{"role": "system", "content": system_prompt}] + st.session_state.messages
                
                with GigaChat(credentials=credentials, verify_ssl_certs=False) as giga:
                    giga_messages = [Messages(role=m["role"], content=m["content"]) for m in messages]
                    response = giga.chat(Chat(messages=giga_messages, temperature=temperature))
                    answer = response.choices[0].message.content
                
                st.session_state.messages.append({"role": "assistant", "content": answer})
                
                with st.chat_message("assistant"):
                    st.markdown(answer)
                
                # Auto Evaluation
                eval_prompt = f"""
                Оцени предыдущий ответ по шкале 1-10. Верни только JSON:
                {{"problems": X, "questions": X, "testability": X, "uncertainty": X, "risk": X, "overall_score": X}}
                """
                
                # Здесь можно сделать отдельный вызов для оценки (рекомендуется)
                # Для экономии токенов сейчас пропустим или сделаем в одном промпте
                
            except Exception as e:
                st.error(f"Ошибка API: {e}")

# ==================================================
# ANALYTICS TAB
# ==================================================
with tab_analytics:
    st.header("📊 Аналитика QA")
    
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql("SELECT * FROM analyses ORDER BY created_at DESC", conn)
    conn.close()
    
    if not df.empty:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Всего анализов", len(df))
        with col2:
            st.metric("Средний Risk", round(df['risk'].mean(), 1))
        with col3:
            st.metric("Средняя Testability", round(df['testability'].mean(), 1))
        with col4:
            st.metric("Средний Score", round(df['overall_score'].mean(), 1))
        
        st.plotly_chart(px.histogram(df, x="overall_score", nbins=10, title="Распределение качества ответов"), use_container_width=True)
    else:
        st.info("Пока нет данных. Начните анализировать требования в чате.")

# ==================================================
# HISTORY TAB
# ==================================================
with tab_history:
    st.header("📜 История анализов")
    
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql("SELECT id, created_at, role, user_prompt, overall_score FROM analyses ORDER BY created_at DESC", conn)
    conn.close()
    
    if not df.empty:
        for _, row in df.iterrows():
            with st.expander(f"#{row['id']} — {row['created_at'][:16]} | {row['role']} | Score: {row['overall_score']}"):
                st.write("**Запрос:**", row['user_prompt'][:300] + "...")
                if st.button("Загрузить в чат", key=f"load_{row['id']}"):
                    st.warning("Функция загрузки в чат будет добавлена в следующей итерации")
    else:
        st.info("История пока пуста.")

# ==================================================
# SETTINGS TAB
# ==================================================
with tab_settings:
    st.header("⚙️ Настройки")
    st.write("Здесь можно будет добавить модели, API-ключи, кастомные роли и т.д.")

st.caption("AVSBOT 2.0 — Built with ❤️ for QA Engineers")
