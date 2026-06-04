import os
import re
import pandas as pd
import streamlit as st
from gigachat import GigaChat
from gigachat.models import Chat, Messages, MessagesRole

# --- 2, 5. SAAS UI & HIDE MENU ---
st.set_page_config(page_title="QA SaaS Platform", page_icon="🚀", layout="wide")

# CSS для скрытия логотипов Streamlit, ссылок на GitHub и стилизации под SaaS
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .block-container {padding-top: 2rem; padding-bottom: 0rem;}
    .stMetric {background-color: #1E1E1E; padding: 15px; border-radius: 10px; border: 1px solid #333;}
    </style>
""", unsafe_allow_html=True)

# --- 6. ПРОСТАЯ АВТОРИЗАЦИЯ (Без БД) ---
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if not st.session_state["authenticated"]:
        st.markdown("<h2 style='text-align: center;'>🔒 Доступ к платформе</h2>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            pwd = st.text_input("Введите мастер-пароль:", type="password")
            if st.button("Войти", use_container_width=True):
                if pwd == "qa2026":  # <-- ВАШ ПАРОЛЬ ЗДЕСЬ
                    st.session_state["authenticated"] = True
                    st.rerun()
                else:
                    st.error("❌ Неверный пароль")
        st.stop()

check_password()

# --- 4, 7, 8, 11, 12. НАСТРОЙКИ РОЛЕЙ И ПРОМПТОВ ---
# Мы вшиваем жесткие инструкции для нейросети, чтобы она всегда отдавала структуру и метрики
DEFAULT_ANALYST_PROMPT = """Ты — Senior QA Analyst. Анализируй требования строго по структуре:
📌 Резюме: [краткий вывод]
❗ Проблемы: [список логических дыр]
❓ Вопросы: [что спросить у бизнеса]
✅ Чек-лист: [список проверок]
⏱ Оценка сроков: [оценка в часах]

В самом конце ответа ОБЯЗАТЕЛЬНО выведи блок с метриками (только цифры):
МЕТРИКИ_СТАРТ
Проблем: [количество проблем]
Вопросов: [количество вопросов]
Тестируемость: [число от 0 до 100]
Неопределенность: [число от 0 до 100]
Риск: [число от 0 до 100]
МЕТРИКИ_КОНЕЦ"""

DEFAULT_TESTER_PROMPT = "Ты — Senior QA Engineer. Пиши только подробные тест-кейсы в виде таблиц Markdown. В конце укажи примерное время на прохождение в часах."

ROLES = {
    "Анализ требований (SaaS Score)": {
        "prompt": DEFAULT_ANALYST_PROMPT,
        "templates": ["Оцени этот кусок ТЗ на логику...", "Проверь требования к API авторизации", "Найди уязвимости в описании корзины"]
    },
    "Генератор тест-кейсов": {
        "prompt": DEFAULT_TESTER_PROMPT,
        "templates": ["Напиши негативные кейсы для оплаты", "Составь E2E сценарий покупки", "Чек-лист для мобильного приложения"]
    }
}

# --- ФУНКЦИЯ ПАРСИНГА МЕТРИК ---
def extract_metrics(text):
    metrics = {"problems": 0, "questions": 0, "testability": 0, "uncertainty": 0, "risk": 0}
    try:
        if "МЕТРИКИ_СТАРТ" in text:
            block = text.split("МЕТРИКИ_СТАРТ")[1].split("МЕТРИКИ_КОНЕЦ")[0]
            m_prob = re.search(r'Проблем[^\d]*(\d+)', block, re.IGNORECASE)
            m_ques = re.search(r'Вопросов[^\d]*(\d+)', block, re.IGNORECASE)
            m_test = re.search(r'Тестируемость[^\d]*(\d+)', block, re.IGNORECASE)
            m_uncer = re.search(r'Неопределенность[^\d]*(\d+)', block, re.IGNORECASE)
            m_risk = re.search(r'Риск[^\d]*(\d+)', block, re.IGNORECASE)
            
            if m_prob: metrics["problems"] = int(m_prob.group(1))
            if m_ques: metrics["questions"] = int(m_ques.group(1))
            if m_test: metrics["testability"] = int(m_test.group(1))
            if m_uncer: metrics["uncertainty"] = int(m_uncer.group(1))
            if m_risk: metrics["risk"] = int(m_risk.group(1))
    except Exception:
        pass
    return metrics

# --- БОКОВАЯ ПАНЕЛЬ ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2082/2082199.png", width=50) # Просто логотип для стиля
    st.header("⚙️ Конфигурация")
    
    selected_role = st.selectbox("Специализация:", list(ROLES.keys()))
    
    # 1. Редактируемый системный промпт с возвратом к дефолту
    st.write("📝 **Системный промпт**")
    if f"prompt_{selected_role}" not in st.session_state:
        st.session_state[f"prompt_{selected_role}"] = ROLES[selected_role]["prompt"]

    current_prompt = st.text_area(
        "Инструкции нейросети (можно менять):", 
        value=st.session_state[f"prompt_{selected_role}"], 
        height=200
    )
    st.session_state[f"prompt_{selected_role}"] = current_prompt

    if st.button("🔄 Вернуть по умолчанию"):
        st.session_state[f"prompt_{selected_role}"] = ROLES[selected_role]["prompt"]
        st.rerun()

    temperature = st.slider("Креативность:", 0.1, 1.2, 0.7, 0.1)
    
    if st.button("🧹 Очистить сессию", use_container_width=True):
        st.session_state.messages = []
        st.session_state.last_metrics = None
        st.rerun()

# --- ГЛАВНЫЙ ЭКРАН ---
st.title("🛡️ QA Requirements Analyzer")

# 10. АНАЛИТИКА И МЕТРИКИ (Отображается, если есть данные)
if "last_metrics" not in st.session_state:
    st.session_state.last_metrics = None

if st.session_state.last_metrics and selected_role == "Анализ требований (SaaS Score)":
    st.markdown("### 📊 Дашборд качества требований")
    m = st.session_state.last_metrics
    
    # Карточки метрик
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("❗ Проблем найдено", m['problems'], delta_color="inverse")
    c2.metric("❓ Вопросов бизнесу", m['questions'], delta_color="inverse")
    c3.metric("🧪 Тестируемость", f"{m['testability']}%")
    c4.metric("🌫 Неопределенность", f"{m['uncertainty']}%")
    c5.metric("🔥 Оценка риска", f"{m['risk']}%", delta_color="inverse")
    
    # График (Радар или столбцы)
    st.write("📉 **Анализ рисков (Визуализация)**")
    chart_data = pd.DataFrame({
        "Показатель": ["Тестируемость", "Неопределенность", "Риск"],
        "Значение (%)": [m['testability'], m['uncertainty'], m['risk']]
    }).set_index("Показатель")
    st.bar_chart(chart_data, color="#00E676", height=200)
    st.divider()

# Инициализация чата
if "messages" not in st.session_state or not st.session_state.messages:
    st.session_state.messages = [{"role": MessagesRole.SYSTEM, "content": current_prompt}]
else:
    st.session_state.messages[0]["content"] = current_prompt

# Быстрые шаблоны зависят от роли (Пункт 4)
st.write("💡 **Быстрые действия:**")
t_col1, t_col2, t_col3 = st.columns(3)
template_query = ""
templates = ROLES[selected_role]["templates"]

if t_col1.button(templates[0], use_container_width=True): template_query = templates[0]
if t_col2.button(templates[1], use_container_width=True): template_query = templates[1]
if t_col3.button(templates[2], use_container_width=True): template_query = templates[2]

# Загрузка файла
uploaded_file = st.file_uploader("📎 Загрузить ТЗ (.txt, .md)", type=["txt", "md"])
file_context = ""
if uploaded_file:
    file_context = uploaded_file.read().decode("utf-8")

# Поле ввода
user_input = st.chat_input("Вставьте текст требований сюда...")
final_prompt = user_input if user_input else template_query

if final_prompt:
    display_prompt = final_prompt
    if file_context:
        final_prompt = f"Контекст файла:\n{file_context}\n\nЗапрос: {display_prompt}"
    
    st.session_state.messages.append({"role": "user", "content": final_prompt})

    # Отправка в GigaChat
    with st.spinner("🧠 ИИ анализирует данные..."):
        try:
            credentials = os.getenv("GIGA_CREDENTIALS")
            with GigaChat(credentials=credentials, verify_ssl_certs=False) as giga:
                giga_messages = [Messages(role=m["role"], content=m["content"]) for m in st.session_state.messages]
                response = giga.chat(Chat(messages=giga_messages, temperature=temperature))
                bot_response = response.choices[0].message.content
                
                # Извлечение метрик, если мы в режиме аналитика
                if selected_role == "Анализ требований (SaaS Score)":
                    st.session_state.last_metrics = extract_metrics(bot_response)
                    # Очищаем ответ от технического блока метрик перед показом
                    bot_response = bot_response.split("МЕТРИКИ_СТАРТ")[0].strip()

                st.session_state.messages.append({"role": "assistant", "content": bot_response})
                st.rerun() # Перезагружаем страницу, чтобы отрисовать дашборд с метриками наверху
                
        except Exception as e:
            st.error(f"Ошибка API: {e}")

# Отображение истории и кнопки копирования (Пункт 9)
for idx, message in enumerate(st.session_state.messages):
    if message["role"] == "user":
        with st.chat_message("user"):
            # Показываем только суть запроса без простыни контекста файла
            st.write("Ваш запрос отправлен.") 
    elif message["role"] == "assistant":
        with st.chat_message("assistant"):
            st.markdown(message["content"])
            # 9. Кнопка копирования в буфер: В Streamlit нативный копипаст работает лучше всего через st.code
            with st.expander("📋 Показать исходный код Markdown (Кнопка копирования в правом верхнем углу)"):
                st.code(message["content"], language="markdown")
