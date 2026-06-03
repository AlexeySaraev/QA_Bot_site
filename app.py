import os
import streamlit as st
from gigachat import GigaChat
from gigachat.models import Chat, Messages, MessagesRole

# --- НАСТРОЙКА СТРАНИЦЫ ---
st.set_page_config(
    page_title="Senior QA Assistant",
    page_icon="🤖",
    layout="centered"
)

st.title("🤖 Senior QA Assistant")
st.write("Добро пожаловать! Я ваш ИИ-ассистент по тестированию. Помогу составить тест-кейсы, чек-листы или проанализировать требования.")

# --- СИСТЕМНЫЙ ПРОМТ (Без упоминания Сбера/GigaChat) ---
SYSTEM_PROMPT = (
    "Ты — Senior QA Assistant, высококвалифицированный эксперт в области тестирования программного обеспечения. "
    "Твоя цель — помогать пользователю проектировать тесты, писать тест-кейсы, чек-листы, "
    "искать логические ошибки в требованиях и автоматизировать рутину. "
    "Отвечай четко, структурировано, профессиональным языком тестировщиков. "
    "Не упоминай, на каких технологиях или моделях ты построен."
)

# --- ИНИЦИАЛИЗАЦИЯ ИСТОРИИ ЧАТА ---
# Streamlit перезапускает код при каждом клике, поэтому храним историю в специальном словаре session_state
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": MessagesRole.SYSTEM, "content": SYSTEM_PROMPT}
    ]

# --- ОТОБРАЖЕНИЕ ИСТОРИИ (кроме системного промта) ---
for message in st.session_state.messages:
    if message["role"] != MessagesRole.SYSTEM:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

# --- РАБОТА С ВВОДОМ ПОЛЬЗОВАТЕЛЯ ---
if user_input := st.chat_input("Например: Напиши негативные тест-кейсы для формы оплаты..."):
    
    # 1. Отображаем сообщение пользователя на экране
    with st.chat_message("user"):
        st.markdown(user_input)
    
    # 2. Сохраняем его в историю
    st.session_state.messages.append({"role": "user", "content": user_input})

    # 3. Отправляем запрос в GigaChat
    with st.chat_message("assistant"):
        with st.spinner("Анализирую..."):
            try:
                # Получаем токен из переменных окружения
                credentials = os.getenv("GIGA_CREDENTIALS")
                
                if not credentials:
                    st.error("Ошибка: Не найдена переменная окружения GIGA_CREDENTIALS!")
                    st.stop()

                # Подключаемся к GigaChat
                with GigaChat(credentials=credentials, verify_ssl_certs=False) as giga:
                    # Преобразуем нашу историю в формат, который понимает GigaChat API
                    giga_messages = [
                        Messages(role=msg["role"], content=msg["content"]) 
                        for msg in st.session_state.messages
                    ]
                    
                    # Запрос к модели
                    payload = Chat(messages=giga_messages, temperature=0.7)
                    response = giga.chat(payload)
                    bot_response = response.choices[0].message.content

                    # Отображаем ответ бота
                    st.markdown(bot_response)
                    
                    # 4. Сохраняем ответ бота в историю
                    st.session_state.messages.append({"role": "assistant", "content": bot_response})

            except Exception as e:
                st.error(f"Произошла ошибка при запросе к ИИ: {e}")
