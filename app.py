import os
import streamlit as st
from gigachat import GigaChat
from gigachat.models import Chat, Messages, MessagesRole

# --- НАСТРОЙКА СТРАНИЦЫ ---
st.set_page_config(
    page_title="Senior QA Ultimate Assistant",
    page_icon="🤖",
    layout="wide"  # Сделаем экран шире, чтобы панель и чат смотрелись гармонично
)

# --- БОКОВАЯ ПАНЕЛЬ (SIDEBAR) ---
with st.sidebar:
    st.header("⚙️ Настройки ассистента")
    
    # 1. Выбор роли/режима работы
    qa_role = st.selectbox(
        "Выберите специализацию ИИ:",
        [
            "Генератор тест-кейсов и чек-листов",
            "Аналитик требований (Поиск багов в ТЗ)",
            "Специалист по автоматизации (Code Review тестов)",
            "Универсальный QA Ментор"
        ]
    )
    
    # Смена системного промта в зависимости от выбора
    if qa_role == "Генератор тест-кейсов и чек-листов":
        SYSTEM_PROMPT = "Ты — Senior QA Engineer. Твоя задача — писать максимально подробные, структурированные тест-кейсы (с позитивными и негативными сценариями) и чек-листы. Используй понятные таблицы и списки."
    elif qa_role == "Аналитик требований (Поиск багов в ТЗ)":
        SYSTEM_PROMPT = "Ты — QA Системный Аналитик. Твоя задача — критически оценивать присланные требования или ТЗ, искать в них логические дыры, двусмысленности, неполноту и формулировать уточняющие вопросы к бизнесу."
    elif qa_role == "Специалист по автоматизации (Code Review тестов)":
        SYSTEM_PROMPT = "Ты — Senior QA Automation Engineer. Ты помогаешь писать автотесты, делать ревью кода (Python/JS/Java), искать баги в логике тестов и предлагать лучшие практики (Page Object, Clean Code)."
    else:
        SYSTEM_PROMPT = "Ты — Senior QA Mentor. Отвечай на любые теоретические и практические вопросы по тестированию, объясняй сложные концепции простыми словами и помогай развивать хард-скиллы."

    st.write("---")
    
    # 2. Ползунок креативности
    temperature = st.slider(
        "Креативность ответов (Temperature):",
        min_value=0.1,
        max_value=1.2,
        value=0.7,
        step=0.1,
        help="Ниже — ответы строже и точнее. Выше — более творческие."
    )
    
    st.write("---")
    
    # 3. Кнопка очистки контекста
    if st.button("🧹 Очистить историю чата"):
        st.session_state.messages = [{"role": MessagesRole.SYSTEM, "content": SYSTEM_PROMPT}]
        st.rerun()

# --- ГЛАВНЫЙ ЭКРАН ---
st.title("🤖 Senior QA Ultimate Assistant")
st.write(f"Текущий режим работы: **{qa_role}**")

# --- ИНИЦИАЛИЗАЦИЯ ИСТОРИИ ЧАТА ---
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": MessagesRole.SYSTEM, "content": SYSTEM_PROMPT}]

# Синхронизируем промт в истории при его изменении в меню
st.session_state.messages[0]["content"] = SYSTEM_PROMPT

# --- ОТОБРАЖЕНИЕ ИСТОРИИ ЧАТА ---
for idx, message in enumerate(st.session_state.messages):
    if message["role"] != MessagesRole.SYSTEM:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            
            # Если это ответ ассистента, добавляем под него кнопку скачивания
            if message["role"] == "assistant":
                st.download_button(
                    label="📥 Скачать этот ответ (.txt)",
                    data=message["content"],
                    file_name=f"qa_response_{idx}.txt",
                    mime="text/plain",
                    key=f"dl_{idx}"
                )

# --- ФУНКЦИОНАЛ ЗАГРУЗКИ ФАЙЛОВ ---
st.write("---")
uploaded_file = st.file_uploader(
    "📎 Перетащите сюда файл с ТЗ, требованиями или логами для анализа (.txt, .log, .md)", 
    type=["txt", "log", "md"]
)

file_context = ""
if uploaded_file is not None:
    # Читаем текст из файла
    file_context = uploaded_file.read().decode("utf-8")
    st.success(f"Файл '{uploaded_file.name}' успешно прикреплен к следующему запросу!")

# --- БЫСТРЫЕ ШАБЛОНЫ (КНОПКИ) ---
st.write("💡 Быстрые шаблоны:")
col1, col2, col3 = st.columns(3)
template_query = ""

with col1:
    if st.button("📝 Напиши чек-лист для авторизации"):
        template_query = "Напиши подробный чек-лист для проверки формы авторизации (логин, пароль, восстановление доступа)."
with col2:
    if st.button("🛑 Придумай негативные кейсы"):
        template_query = "Придумай 10 сложных негативных тест-кейсов для формы оплаты банковской картой."
with col3:
    if st.button("🔍 Найди баги в требованиях"):
        template_query = "Я отправлю тебе кусок ТЗ. Найди в нем логические нестыковки, противоречия и серые зоны."

# --- ОБРАБОТКА ЗАПРОСА ---
# Запрос берется либо из поля ввода, либо по клику на шаблон кнопки
user_input = st.chat_input("Задайте вопрос по тестированию...")
final_prompt = user_input if user_input else template_query

if final_prompt:
    # Если был загружен файл, склеиваем его содержимое с вопросом пользователя
    if file_context:
        final_prompt = f"Контекст из загруженного файла:\n
http://googleusercontent.com/immersive_entry_chip/0

---

### Шаг 2. Сохраняем изменения и проверяем!

1. Нажмите зеленую кнопку **`Commit changes`** на GitHub, чтобы сохранить обновленный `app.py`.
2. Перейдите в ваш личный кабинет Streamlit Cloud.
3. Поскольку код кардинально обновился, лучше один раз на всякий случай нажать на **три точки** рядом с приложением и выбрать **`Reboot app`**, чтобы обновить интерфейс.

Сайт должен полностью преобразиться: слева появится меню управления, над чатом — кнопки-помощники, а снизу — область для загрузки файлов. Попробуйте потестировать и напишите, как вам новый прокачанный инструмент!
