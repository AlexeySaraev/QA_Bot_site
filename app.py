import streamlit as st
import streamlit.components.v1 as components
import google.generativeai as genai
from gigachat import GigaChat
import requests

# --- 1. НАСТРОЙКА СТРАНИЦЫ ---
st.set_page_config(
    page_title="QA AI Assistant", 
    page_icon="🛠️", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. CSS И JS ИНЪЕКЦИЯ ---
def load_custom_assets():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        html, body, [class*="css"] { font-family: 'Inter', sans-serif; background: #f0f2f5; }
        #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
        .block-container { padding-top: 2rem; }
        .main .block-container {
            background: rgba(255, 255, 255, 0.85); backdrop-filter: blur(10px);
            border-radius: 20px; box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.15);
            border: 1px solid rgba(255, 255, 255, 0.18); padding: 3rem; margin-top: 20px;
        }
        h1 { color: #111827; font-weight: 800; font-size: 2.5rem !important; margin-bottom: 10px !important; }
        h3 { color: #4b5563; font-weight: 500; }
        .stButton>button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none;
            padding: 15px 32px; font-size: 16px; font-weight: 600; border-radius: 12px;
            transition: all 0.3s ease; box-shadow: 0 4px 15px rgba(118, 75, 162, 0.4); width: 100%;
        }
        .stButton>button:hover { transform: translateY(-3px); box-shadow: 0 8px 20px rgba(118, 75, 162, 0.6); filter: brightness(1.1); }
        .stTextInput>div>div>input, .stTextArea textarea { border: 2px solid #e5e7eb; border-radius: 12px; transition: border-color 0.3s; }
        .stTextInput>div>div>input:focus, .stTextArea textarea:focus { border-color: #667eea; box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.2); }
        section[data-testid="stSidebar"] { background-image: linear-gradient(180deg, #1e293b 0%, #0f172a 100%); color: white; }
        section[data-testid="stSidebar"] label { color: #cbd5e1 !important; }
        section[data-testid="stSidebar"] h3 { color: white !important; }
        div[data-baseweb="select"] > div { color: #1f2937 !important; background-color: white; border-radius: 8px; }
        .result-card {
            background: white; border-radius: 15px; padding: 25px; margin-top: 20px;
            border-left: 5px solid #667eea; box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1);
        }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
        .element-container { animation: fadeIn 0.6s ease-out forwards; }
        .status-ok { color: #4ade80; font-size: 0.9rem; margin-top: -10px; margin-bottom: 20px; }
        .status-error { color: #f87171; font-size: 0.9rem; margin-top: -10px; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)
    components.html("<script>window.parent.document.querySelector('header').style.display = 'none';</script>", height=0)

load_custom_assets()

# --- 3. ИНТЕРФЕЙС ---
col1, col2 = st.columns([0.05, 0.95])
with col2:
    st.title("QA AI Assistant")
    st.markdown("### Профессиональный анализ требований и генерация тестов")

# --- 4. БОКОВОЕ МЕНЮ ---
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/000000/artificial-intelligence.png", width=80)
    st.header("Настройки")
    
    model_choice = st.selectbox("🧠 Модель ИИ", ["Gemini (Google)", "GigaChat (Sber)", "Grok (xAI)"])

    # Получение ключей
    current_key = None
    try:
        if model_choice == "Gemini (Google)":
            current_key = st.secrets["GEMINI_KEY"]
        elif model_choice == "Grok (xAI)":
            current_key = st.secrets["GROK_KEY"]
        elif model_choice == "GigaChat (Sber)":
            current_key = st.secrets["GIGACHAT_KEY"]
    except KeyError:
        pass

    if current_key:
        st.markdown('<p class="status-ok">✅ API Ключ загружен</p>', unsafe_allow_html=True)
    else:
        st.markdown('<p class="status-error">❌ Ключ не настроен</p>', unsafe_allow_html=True)

    st.divider()
    task = st.selectbox("🛠️ Задача", ["Анализ требований", "Генерация тест-кейсов", "Code Review"])

# --- 5. ЛОГИКА ---
def get_system_prompt(selected_task):
    prompts = {
        "Анализ требований": "Ты опытный QA. Проведи глубокий анализ требований. Найди противоречия и пропуски. Выдай структурированный отчет.",
        "Генерация тест-кейсов": "Ты опытный QA. Сгенерируй тест-кейсы в формате таблицы (ID, Описание, Шаги, ОР).",
        "Code Review": "Ты Senior разработчик. Найди баги, проблемы с безопасностью и предложи рефакторинг."
    }
    return prompts[selected_task]

user_input = st.text_area("📄 Входные данные", height=200, placeholder="Вставьте требования или код здесь...")

if st.button("🚀 Запустить анализ"):
    if not user_input:
        st.warning("Введите данные.")
    elif not current_key:
        st.error("Ошибка: Ключ API не найден в секретах Streamlit. Добавьте их в Settings -> Secrets.")
    else:
        system_prompt = get_system_prompt(task)
        with st.spinner("Идет анализ..."):
            try:
                result = None
                
                # --- GigaChat Logic ---
                if model_choice == "GigaChat (Sber)":
                    with GigaChat(credentials=current_key, verify_ssl_certs=False) as giga:
                        resp = giga.chat(f"{system_prompt}\n\n{user_input}")
                        result = resp.choices[0].message.content
                
                # --- Gemini Logic (ОБНОВЛЕНО) ---
                elif model_choice == "Gemini (Google)":
                    try:
                        genai.configure(api_key=current_key)
                        # Используем модель gemini-1.5-flash-latest для актуальности
                        model = genai.GenerativeModel('gemini-1.5-flash-latest')
                        full_prompt = f"{system_prompt}\n\n{user_input}"
                        response = model.generate_content(full_prompt)
                        result = response.text
                    except Exception as e:
                        st.error(f"Ошибка Gemini API: {e}")

                # --- Grok Logic ---
                elif model_choice == "Grok (xAI)":
                    url = "https://api.x.ai/v1/chat/completions"
                    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {current_key}"}
                    data = {
                        "model": "grok-2-latest", 
                        "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_input}]
                    }
                    response = requests.post(url, headers=headers, json=data)
                    if response.status_code == 200:
                        result = response.json()['choices'][0]['message']['content']
                    else:
                        st.error(f"Ошибка Grok: {response.text}")
                
                if result:
                    st.success("✅ Готово!")
                    st.markdown(f'<div class="result-card">{result}</div>', unsafe_allow_html=True)
            except Exception as e:
                st.error(f"Общая ошибка: {e}")

st.markdown("<br><div style='text-align: center; color: #6b7280; font-size: 0.9em;'>Powered by AI</div>", unsafe_allow_html=True)
