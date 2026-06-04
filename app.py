import streamlit as st
import os
import json
from datetime import datetime
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from gigachat import GigaChat
from gigachat.models import Chat, Messages, MessagesRole
from docx import Document as DocxDocument
import time
import re
from collections import Counter
import io
import csv

# ==================== КОНФИГУРАЦИЯ ====================

st.set_page_config(
    page_title="QA Assistant Pro",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://github.com/your-repo',
        'Report a bug': 'https://github.com/your-repo/issues',
        'About': '# QA Assistant Pro v2.5\nАвтоматизация QA процессов с помощью AI'
    }
)

# ==================== ИНИЦИАЛИЗАЦИЯ SESSION STATE ====================

if 'history' not in st.session_state:
    st.session_state.history = []

if 'custom_prompts' not in st.session_state:
    st.session_state.custom_prompts = {}

if 'current_result' not in st.session_state:
    st.session_state.current_result = None

if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

if 'templates' not in st.session_state:
    st.session_state.templates = {
        'web_feature': """Как пользователь, я хочу иметь возможность сбросить пароль через email, чтобы восстановить доступ к аккаунту.

Критерии приёмки:
1. На странице логина есть ссылка "Забыли пароль?"
2. После клика открывается форма с полем для email
3. После отправки приходит письмо с ссылкой для сброса
4. Ссылка активна 24 часа
5. После перехода по ссылке можно установить новый пароль""",
        
        'mobile_feature': """Как пользователь мобильного приложения, я хочу получать push-уведомления о новых сообщениях, чтобы быть в курсе событий.

Критерии приёмки:
1. В настройках есть переключатель уведомлений
2. При получении сообщения приходит push
3. По клику на уведомление открывается чат
4. Есть группировка уведомлений (>3 сообщений)
5. Можно отключить уведомления для конкретных чатов""",
        
        'api_feature': """API эндпоинт для получения списка пользователей с фильтрацией и пагинацией.

Технические требования:
- Метод: GET /api/v1/users
- Параметры: page, limit, role, status
- Ответ: JSON с массивом пользователей + метаданные пагинации
- Авторизация: Bearer token
- Лимит: max 100 записей за запрос
- Кеширование: 5 минут"""
    }

if 'categories' not in st.session_state:
    st.session_state.categories = ['Общее', 'Web', 'Mobile', 'API', 'Backend', 'Frontend']

if 'ai_provider' not in st.session_state:
    st.session_state.ai_provider = 'gigachat'

# ==================== ПРОМПТЫ ПО УМОЛЧАНИЮ ====================

DEFAULT_PROMPTS = {
    'review': """Ты - опытный Senior QA / QA Analyst, участвующий в раннем этапе жизненного цикла разработки. Перед тобой стоит задача провести глубокий анализ и ревью требований (user story, технического задания или спецификации).

При ревью обрати внимание на следующие аспекты:
- Полнота: Все ли необходимые детали описаны? Есть ли недостающие сценарии?
- Однозначность: Нет ли двусмысленных формулировок?
- Тестируемость: Можно ли проверить каждое пункт требования? 
- Риски: Какие риски возникают при реализации этого требования?

Формат ответа:
- Краткое резюме требований
- Выявленные проблемы (с указанием строки/раздела, и комментарий к ним) + задай вопросы
- Рекомендации по улучшению
- Предварительный набор проверок (чек-лист)
- Оцени примерный срок проверки требований (ручное)
- Оцени примерный срок реализации автотестов (опиши технологии)
- Оценка рисков (низкий / средний / высокий + обоснование)

Задай как можно большее количество уточняющих вопросов""",
    
    'test_cases': """Ты — опытный Senior QA Engineer и тест-аналитик. 
Твоя задача: проанализировать предоставленный User Story и составить структурированный набор тест-кейсов.

Требования к тест-кейсам:
1. Покрытие: позитивные (Happy Path), негативные, граничные значения и edge-кейсы.
2. Формат: Представь результат в виде таблицы со следующими колонками:
   | ID | Название/Цель | Тип | Предусловия | Шаги воспроизведения | Ожидаемый результат | Приоритет |

Требования к формату:
- Шаги должны быть простыми и понятными
- Каждый шаг должен быть атомарным (одно действие)
- Ожидаемый результат должен быть конкретным и проверяемым
- НЕ используй формат Given/When/Then/Else
- Используй обычный язык без специальных конструкций

3. В конце ответа выдели блок "⚠️ Вопросы и уточнения к аналитику/заказчику" (вне таблицы).

Разработай как можно больше тест-кейсов"""
}

# ==================== СТИЛИ ====================

st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: 800;
        background: linear-gradient(120deg, #6366f1 0%, #8b5cf6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        color: #94a3b8;
        font-size: 1.2rem;
        margin-bottom: 2rem;
    }
    .stat-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 1rem;
        color: white;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .stat-value {
        font-size: 2.5rem;
        font-weight: bold;
        margin: 0;
    }
    .stat-label {
        font-size: 0.9rem;
        opacity: 0.9;
        margin-top: 0.5rem;
    }
    .result-container {
        background: #1e1e2e;
        padding: 2rem;
        border-radius: 1rem;
        border-left: 4px solid #6366f1;
        margin: 1rem 0;
    }
    .chat-message {
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .user-message {
        background: #2d2d44;
        margin-left: 2rem;
    }
    .ai-message {
        background: #1e1e2e;
        margin-right: 2rem;
        border-left: 3px solid #6366f1;
    }
    .quality-score {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
    }
    .score-excellent { color: #10b981; }
    .score-good { color: #3b82f6; }
    .score-fair { color: #f59e0b; }
    .score-poor { color: #ef4444; }
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 2rem;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 1rem 2rem;
        background-color: #1e1e2e;
        border-radius: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

def get_prompt(mode, custom_prompts=None):
    """Получить промпт для режима"""
    if custom_prompts and mode in custom_prompts:
        return custom_prompts[mode]
    return DEFAULT_PROMPTS.get(mode, DEFAULT_PROMPTS['review'])

def extract_text_from_file(uploaded_file):
    """Извлечение текста из загруженного файла"""
    try:
        file_extension = uploaded_file.name.split('.')[-1].lower()
        
        if file_extension == 'txt':
            try:
                text = uploaded_file.read().decode('utf-8')
            except UnicodeDecodeError:
                uploaded_file.seek(0)
                text = uploaded_file.read().decode('cp1251')
            return text
        
        elif file_extension == 'docx':
            doc = DocxDocument(io.BytesIO(uploaded_file.read()))
            text = '\n'.join([paragraph.text for paragraph in doc.paragraphs])
            return text
        
        else:
            return None
    
    except Exception as e:
        raise Exception(f"Ошибка обработки файла: {str(e)}")

def extract_table_to_csv(markdown_text):
    """Извлечение таблицы из Markdown в CSV формат"""
    lines = markdown_text.split('\n')
    table_lines = [line for line in lines if '|' in line]
    
    if len(table_lines) < 2:
        return None
    
    csv_buffer = io.StringIO()
    writer = csv.writer(csv_buffer, delimiter=';', quoting=csv.QUOTE_MINIMAL)
    
    for line in table_lines:
        if '---' in line:
            continue
        row = [cell.strip() for cell in line.split('|')][1:-1]
        if row:
            writer.writerow(row)
    
    return csv_buffer.getvalue()

def analyze_with_gigachat(prompt, user_text, credentials):
    """Анализ текста с помощью GigaChat"""
    try:
        with GigaChat(credentials=credentials, verify_ssl_certs=False) as giga:
            payload = Chat(
                messages=[
                    Messages(role=MessagesRole.SYSTEM, content=prompt),
                    Messages(role=MessagesRole.USER, content=user_text)
                ],
                temperature=0.5,
                max_tokens=4000,
            )
            response = giga.chat(payload)
            return {
                'success': True,
                'result': response.choices[0].message.content,
                'error': None
            }
    except Exception as e:
        return {
            'success': False,
            'result': None,
            'error': str(e)
        }

def calculate_quality_score(text):
    """Расчет качества требований (1-10)"""
    score = 5.0
    
    if len(text) > 100:
        score += 1
    if len(text) > 500:
        score += 1
    
    if 'критери' in text.lower() or 'acceptance' in text.lower():
        score += 1
    
    if '1.' in text or '•' in text or '-' in text:
        score += 0.5
    
    questions = len(re.findall(r'\?', text))
    if questions > 3:
        score -= 1
    
    uncertainty_words = ['возможно', 'может быть', 'наверное', 'вероятно']
    for word in uncertainty_words:
        if word in text.lower():
            score -= 0.5
    
    score = max(1.0, min(10.0, score))
    return round(score, 1)

def get_score_color_class(score):
    """Цветовой класс для оценки"""
    if score >= 8:
        return 'score-excellent'
    elif score >= 6:
        return 'score-good'
    elif score >= 4:
        return 'score-fair'
    else:
        return 'score-poor'

def extract_test_case_stats(markdown_text):
    """Извлечение статистики из тест-кейсов"""
    lines = markdown_text.split('\n')
    table_lines = [line for line in lines if '|' in line and '---' not in line]
    
    if len(table_lines) < 2:
        return None
    
    stats = {
        'total': len(table_lines) - 1,
        'positive': 0,
        'negative': 0,
        'boundary': 0,
        'security': 0,
        'high_priority': 0,
        'medium_priority': 0,
        'low_priority': 0
    }
    
    for line in table_lines[1:]:
        line_lower = line.lower()
        
        if 'позитив' in line_lower or 'positive' in line_lower:
            stats['positive'] += 1
        if 'негатив' in line_lower or 'negative' in line_lower:
            stats['negative'] += 1
        if 'гранич' in line_lower or 'boundary' in line_lower:
            stats['boundary'] += 1
        if 'безопасн' in line_lower or 'security' in line_lower:
            stats['security'] += 1
        
        if 'high' in line_lower or 'высок' in line_lower:
            stats['high_priority'] += 1
        if 'medium' in line_lower or 'средн' in line_lower:
            stats['medium_priority'] += 1
        if 'low' in line_lower or 'низк' in line_lower:
            stats['low_priority'] += 1
    
    return stats

def save_to_history(title, mode, input_text, output_text, file_name=None, category='Общее', tags=None):
    """Сохранение с дополнительными метаданными"""
    analysis = {
        'id': len(st.session_state.history) + 1,
        'timestamp': datetime.now().isoformat(),
        'title': title,
        'mode': mode,
        'input': input_text,
        'output': output_text,
        'file_name': file_name,
        'input_length': len(input_text),
        'output_length': len(output_text),
        'category': category,
        'tags': tags or [],
        'quality_score': calculate_quality_score(input_text),
        'ai_provider': st.session_state.ai_provider
    }
    
    if mode == 'test_cases':
        stats = extract_test_case_stats(output_text)
        if stats:
            analysis['test_case_stats'] = stats
    
    st.session_state.history.insert(0, analysis)
    
    if len(st.session_state.history) > 100:
        st.session_state.history = st.session_state.history[:100]

def get_statistics():
    """Расширенная статистика"""
    if not st.session_state.history:
        return {
            'total': 0,
            'reviews': 0,
            'test_cases': 0,
            'files_processed': 0,
            'avg_quality': 0,
            'total_test_cases': 0
        }
    
    total = len(st.session_state.history)
    reviews = len([h for h in st.session_state.history if h['mode'] == 'review'])
    test_cases = len([h for h in st.session_state.history if h['mode'] == 'test_cases'])
    files = len([h for h in st.session_state.history if h.get('file_name')])
    
    scores = [h.get('quality_score', 0) for h in st.session_state.history]
    avg_quality = round(sum(scores) / len(scores), 1) if scores else 0
    
    total_tc = sum([
        h.get('test_case_stats', {}).get('total', 0) 
        for h in st.session_state.history 
        if h['mode'] == 'test_cases'
    ])
    
    return {
        'total': total,
        'reviews': reviews,
        'test_cases': test_cases,
        'files_processed': files,
        'avg_quality': avg_quality,
        'total_test_cases': total_tc
    }

# ==================== SIDEBAR ====================

with st.sidebar:
    st.markdown('<p class="main-header" style="font-size: 1.8rem;">🧪 QA Assistant</p>', unsafe_allow_html=True)
    st.markdown("---")
    
    page = st.radio(
        "📍 Навигация",
        [
            "🏠 Главная",
            "🔍 Анализ",
            "💬 Чат",
            "⚖️ Сравнение",
            "📦 Пакетный",
            "📚 История",
            "📝 Шаблоны",
            "📊 Аналитика",
            "⚙️ Настройки"
        ],
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    
    # API ключи
    with st.expander("🔑 API Настройки", expanded=False):
        giga_creds = st.text_input(
            "GigaChat Credentials",
            type="password",
            value=os.getenv("GIGA_CREDENTIALS", ""),
            help="Ваш токен GigaChat API"
        )
        
        if st.button("💾 Сохранить"):
            os.environ["GIGA_CREDENTIALS"] = giga_creds
            st.success("✅ Сохранено!")
    
    # Статистика в сайдбаре
    st.markdown("---")
    st.markdown("### 📊 Статистика")
    stats = get_statistics()
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Всего", stats['total'])
        st.metric("Оценка", f"{stats['avg_quality']}/10")
    with col2:
        st.metric("Ревью", stats['reviews'])
        st.metric("Кейсов", stats['test_cases'])

# ==================== ГЛАВНАЯ СТРАНИЦА ====================

if page == "🏠 Главная":
    st.markdown('<h1 class="main-header">🧪 QA Assistant Pro</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">AI-powered инструмент для анализа требований и создания тест-кейсов</p>', unsafe_allow_html=True)
    
    stats = get_statistics()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="stat-card" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">
            <p class="stat-value">{stats['total']}</p>
            <p class="stat-label">Всего анализов</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="stat-card" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);">
            <p class="stat-value">{stats['reviews']}</p>
            <p class="stat-label">Ревью требований</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="stat-card" style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);">
            <p class="stat-value">{stats['test_cases']}</p>
            <p class="stat-label">Тест-кейсов</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="stat-card" style="background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);">
            <p class="stat-value">{stats['avg_quality']}</p>
            <p class="stat-label">Средняя оценка</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    st.markdown("### ✨ Возможности")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        #### 🔍 Ревью требований
        - Анализ полноты и однозначности
        - Выявление рисков и проблем
        - Генерация уточняющих вопросов
        - Создание чек-листов для проверки
        - Оценка сроков реализации
        
        #### 📄 Работа с файлами
        - Поддержка TXT и DOCX
        - Автоматическое извлечение текста
        - Пакетная обработка (до 10 файлов)
        
        #### 💬 Чат с AI
        - Интерактивное уточнение требований
        - Диалоговый режим анализа
        - Сохранение истории чата
        """)
    
    with col2:
        st.markdown("""
        #### 🧪 Разработка тест-кейсов
        - Позитивные и негативные сценарии
        - Граничные значения и edge-кейсы
        - Формат таблицы для TMS
        - Экспорт в CSV для Jira/TestRail
        
        #### ⚙️ Кастомизация
        - Настройка AI промптов
        - Готовые шаблоны требований
        - Категории и теги
        
        #### 📊 Аналитика
        - Статистика по анализам
        - Графики покрытия
        - Оценка качества требований
        """)
    
    if st.session_state.history:
        st.markdown("---")
        st.markdown("### 📈 Активность по дням")
        
        df_history = pd.DataFrame([
            {
                'date': datetime.fromisoformat(h['timestamp']).date(),
                'mode': 'Ревью' if h['mode'] == 'review' else 'Тест-кейсы'
            }
            for h in st.session_state.history
        ])
        
        activity = df_history.groupby(['date', 'mode']).size().reset_index(name='count')
        
        fig = px.bar(
            activity,
            x='date',
            y='count',
            color='mode',
            title='Количество анализов по дням',
            color_discrete_map={'Ревью': '#667eea', 'Тест-кейсы': '#4facfe'}
        )
        
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font_color='#fafafa',
            showlegend=True
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    if st.session_state.history:
        st.markdown("---")
        st.markdown("### 🕐 Последние анализы")
        
        for analysis in st.session_state.history[:3]:
            with st.container():
                col1, col2, col3 = st.columns([3, 1, 1])
                
                with col1:
                    mode_icon = "🔍" if analysis['mode'] == 'review' else "🧪"
                    st.markdown(f"**{mode_icon} {analysis['title']}**")
                
                with col2:
                    timestamp = datetime.fromisoformat(analysis['timestamp'])
                    st.caption(timestamp.strftime("%d.%m.%Y %H:%M"))
                
                with col3:
                    if st.button("Открыть", key=f"open_{analysis['id']}"):
                        st.session_state.current_result = analysis
                        st.rerun()
                
                st.markdown("---")

# ==================== СТРАНИЦА АНАЛИЗА ====================

elif page == "🔍 Анализ":
    st.markdown('<h1 class="main-header">🔍 Анализ требований</h1>', unsafe_allow_html=True)
    
    mode = st.radio(
        "Выберите режим анализа:",
        ["🔍 Ревью требований", "🧪 Разработка тест-кейсов"],
        horizontal=True
    )
    
    mode_key = 'review' if '🔍' in mode else 'test_cases'
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        title = st.text_input(
            "📝 Название анализа",
            value=f"Анализ {datetime.now().strftime('%d.%m.%Y %H:%M')}",
            help="Дайте название для удобного поиска в истории"
        )
    
    with col2:
        category = st.selectbox(
            "📁 Категория",
            st.session_state.categories
        )
    
    tab1, tab2 = st.tabs(["✍️ Текст", "📎 Файл"])
    
    input_text = None
    file_name = None
    
    with tab1:
        # Проверка на шаблон
        if 'template_to_analyze' in st.session_state:
            input_text = st.session_state['template_to_analyze']
            del st.session_state['template_to_analyze']
        else:
            input_text = st.text_area(
                "Введите текст для анализа:",
                height=300,
                placeholder="Вставьте сюда User Story, ТЗ или спецификацию...",
                help="Минимум 50 символов"
            )
    
    with tab2:
        uploaded_file = st.file_uploader(
            "Загрузите файл",
            type=['txt', 'docx'],
            help="Поддерживаются форматы: TXT, DOCX"
        )
        
        if uploaded_file:
            try:
                with st.spinner("📄 Извлекаю текст из файла..."):
                    input_text = extract_text_from_file(uploaded_file)
                    file_name = uploaded_file.name
                
                st.success(f"✅ Текст извлечён ({len(input_text)} символов)")
                
                with st.expander("👁️ Предпросмотр"):
                    st.text(input_text[:500] + "..." if len(input_text) > 500 else input_text)
            
            except Exception as e:
                st.error(f"❌ Ошибка обработки файла: {str(e)}")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([2, 1, 2])
    
    with col2:
        analyze_button = st.button(
            "🚀 Анализировать",
            type="primary",
            use_container_width=True
        )
    
    if analyze_button:
        if not input_text or len(input_text.strip()) < 50:
            st.error("⚠️ Пожалуйста, введите текст (минимум 50 символов) или загрузите файл")
        
        elif not os.getenv("GIGA_CREDENTIALS"):
            st.error("⚠️ Пожалуйста, укажите GigaChat Credentials в настройках (боковая панель)")
        
        else:
            prompt = get_prompt(mode_key, st.session_state.custom_prompts)
            
            with st.spinner("🤖 AI анализирует требования... Это может занять до минуты."):
                result = analyze_with_gigachat(
                    prompt,
                    input_text,
                    os.getenv("GIGA_CREDENTIALS")
                )
            
            if result['success']:
                st.success("✅ Анализ завершён!")
                
                save_to_history(
                    title=title,
                    mode=mode_key,
                    input_text=input_text,
                    output_text=result['result'],
                    file_name=file_name,
                    category=category
                )
                
                st.markdown("---")
                st.markdown("### 📋 Результат анализа")
                
                # Оценка качества
                quality_score = calculate_quality_score(input_text)
                score_class = get_score_color_class(quality_score)
                
                col1, col2, col3 = st.columns([1, 3, 1])
                with col1:
                    st.markdown(f'<p class="quality-score {score_class}">{quality_score}</p>', unsafe_allow_html=True)
                    st.caption("Оценка качества")
                
                st.markdown(f'<div class="result-container">{result["result"]}</div>', unsafe_allow_html=True)
                
                st.markdown("---")
                st.markdown("### 💾 Экспорт результата")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.download_button(
                        label="📄 Скачать TXT",
                        data=result['result'],
                        file_name=f"{title}.txt",
                        mime="text/plain"
                    )
                
                with col2:
                    if mode_key == 'test_cases':
                        csv_data = extract_table_to_csv(result['result'])
                        if csv_data:
                            st.download_button(
                                label="📊 Скачать CSV",
                                data=csv_data,
                                file_name=f"{title}.csv",
                                mime="text/csv"
                            )
            
            else:
                st.error(f"❌ Ошибка анализа: {result['error']}")

# ==================== СТРАНИЦА ЧАТ ====================

elif page == "💬 Чат":
    st.markdown('<h1 class="main-header">💬 Чат с AI для уточнения требований</h1>', unsafe_allow_html=True)
    
    st.info("💡 Используйте чат для интерактивного уточнения требований. AI задаст вопросы и поможет улучшить формулировки.")
    
    initial_requirements = st.text_area(
        "📝 Введите начальные требования:",
        height=150,
        placeholder="Опишите требования или User Story..."
    )
    
    if st.button("🚀 Начать диалог") and initial_requirements:
        st.session_state.chat_history = [
            {"role": "user", "content": initial_requirements}
        ]
        
        prompt = "Ты - опытный Business Analyst. Проанализируй требования и задай 3-5 уточняющих вопросов для их улучшения."
        
        with st.spinner("AI анализирует..."):
            result = analyze_with_gigachat(prompt, initial_requirements, os.getenv("GIGA_CREDENTIALS"))
            if result['success']:
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": result['result']
                })
                st.rerun()
    
    for msg in st.session_state.chat_history:
        if msg['role'] == 'user':
            st.markdown(f'<div class="chat-message user-message">👤 Вы:<br>{msg["content"]}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="chat-message ai-message">🤖 AI:<br>{msg["content"]}</div>', unsafe_allow_html=True)
    
    if st.session_state.chat_history:
        user_response = st.text_input("💬 Ваш ответ:")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📤 Отправить", use_container_width=True) and user_response:
                st.session_state.chat_history.append({
                    "role": "user",
                    "content": user_response
                })
                
                context = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.chat_history])
                
                with st.spinner("AI обрабатывает ответ..."):
                    result = analyze_with_gigachat(
                        "Продолжай диалог, уточняя детали требований",
                        context,
                        os.getenv("GIGA_CREDENTIALS")
                    )
                    
                    if result['success']:
                        st.session_state.chat_history.append({
                            "role": "assistant",
                            "content": result['result']
                        })
                        st.rerun()
        
        with col2:
            if st.button("✅ Завершить и сохранить", use_container_width=True):
                final_requirements = "\n\n".join([m['content'] for m in st.session_state.chat_history if m['role'] == 'user'])
                
                save_to_history(
                    title=f"Диалог {datetime.now().strftime('%d.%m %H:%M')}",
                    mode='review',
                    input_text=final_requirements,
                    output_text="\n\n".join([m['content'] for m in st.session_state.chat_history]),
                    category='Диалоги'
                )
                
                st.success("✅ Диалог сохранен в историю!")
                st.session_state.chat_history = []
                st.rerun()

# ==================== СТРАНИЦА СРАВНЕНИЕ ====================

elif page == "⚖️ Сравнение":
    st.markdown('<h1 class="main-header">⚖️ Сравнение с предыдущей версией</h1>', unsafe_allow_html=True)
    
    st.info("💡 Сравните две версии требований и посмотрите, что изменилось.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 📄 Версия 1 (старая)")
        version1 = st.text_area("Введите первую версию:", height=300, key="v1")
    
    with col2:
        st.markdown("#### 📄 Версия 2 (новая)")
        version2 = st.text_area("Введите вторую версию:", height=300, key="v2")
    
    if st.button("⚖️ Сравнить версии") and version1 and version2:
        comparison_prompt = """Ты - Senior QA Analyst. Сравни две версии требований и опиши:
        1. Что было добавлено
        2. Что было удалено
        3. Что было изменено
        4. Влияние изменений на тестирование
        5. Рекомендации
        
        Версия 1:
        {version1}
        
        Версия 2:
        {version2}
        """
        
        with st.spinner("🤖 Анализирую различия..."):
            result = analyze_with_gigachat(
                comparison_prompt.format(version1=version1, version2=version2),
                "",
                os.getenv("GIGA_CREDENTIALS")
            )
            
            if result['success']:
                st.markdown("---")
                st.markdown("### 📊 Результат сравнения")
                st.markdown(f'<div class="result-container">{result["result"]}</div>', unsafe_allow_html=True)

# ==================== СТРАНИЦА ПАКЕТНАЯ ОБРАБОТКА ====================

elif page == "📦 Пакетный":
    st.markdown('<h1 class="main-header">📦 Пакетная обработка файлов</h1>', unsafe_allow_html=True)
    
    st.info("💡 Загрузите несколько файлов для одновременного анализа (до 10 файлов).")
    
    mode = st.radio(
        "Режим анализа:",
        ["🔍 Ревью требований", "🧪 Разработка тест-кейсов"],
        horizontal=True
    )
    
    mode_key = 'review' if '🔍' in mode else 'test_cases'
    
    uploaded_files = st.file_uploader(
        "📎 Загрузите файлы:",
        type=['txt', 'docx'],
        accept_multiple_files=True
    )
    
    if uploaded_files and st.button("🚀 Анализировать все"):
        if len(uploaded_files) > 10:
            st.error("⚠️ Максимум 10 файлов за раз")
        else:
            prompt = get_prompt(mode_key, st.session_state.custom_prompts)
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            results = []
            
            for i, file in enumerate(uploaded_files):
                status_text.text(f"📄 Обрабатываю {file.name}... ({i+1}/{len(uploaded_files)})")
                
                try:
                    text = extract_text_from_file(file)
                    
                    result = analyze_with_gigachat(prompt, text, os.getenv("GIGA_CREDENTIALS"))
                    
                    if result['success']:
                        results.append({
                            'file': file.name,
                            'input': text,
                            'output': result['result']
                        })
                        
                        save_to_history(
                            title=file.name,
                            mode=mode_key,
                            input_text=text,
                            output_text=result['result'],
                            file_name=file.name,
                            category='Пакетная обработка'
                        )
                
                except Exception as e:
                    st.error(f"Ошибка обработки {file.name}: {str(e)}")
                
                progress_bar.progress((i + 1) / len(uploaded_files))
                time.sleep(1)
            
            status_text.text("✅ Обработка завершена!")
            
            st.markdown("---")
            st.markdown("### 📊 Результаты пакетной обработки")
            
            for res in results:
                with st.expander(f"📄 {res['file']}", expanded=False):
                    st.markdown(f'<div class="result-container">{res["output"]}</div>', unsafe_allow_html=True)
                    
                    st.download_button(
                        "📄 Скачать",
                        data=res['output'],
                        file_name=f"{res['file']}_analysis.txt",
                        mime="text/plain",
                        key=f"download_{res['file']}"
                    )

# ==================== СТРАНИЦА ИСТОРИЯ ====================

elif page == "📚 История":
    st.markdown('<h1 class="main-header">📚 История анализов</h1>', unsafe_allow_html=True)
    
    if not st.session_state.history:
        st.info("📭 История пуста. Создайте первый анализ!")
    else:
        col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
        
        with col1:
            filter_mode = st.selectbox(
                "Режим",
                ["Все", "🔍 Ревью", "🧪 Тест-кейсы"]
            )
        
        with col2:
            filter_category = st.selectbox(
                "Категория",
                ["Все"] + st.session_state.categories
            )
        
        with col3:
            search_query = st.text_input("🔍 Поиск по названию")
        
        with col4:
            if st.button("🗑️ Очистить"):
                st.session_state.history = []
                st.rerun()
        
        filtered_history = st.session_state.history
        
        if filter_mode != "Все":
            mode_key = 'review' if '🔍' in filter_mode else 'test_cases'
            filtered_history = [h for h in filtered_history if h['mode'] == mode_key]
        
        if filter_category != "Все":
            filtered_history = [h for h in filtered_history if h.get('category') == filter_category]
        
        if search_query:
            filtered_history = [
                h for h in filtered_history 
                if search_query.lower() in h['title'].lower()
            ]
        
        st.markdown(f"*Найдено анализов: {len(filtered_history)}*")
        st.markdown("---")
        
        for analysis in filtered_history:
            with st.container():
                col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                
                with col1:
                    mode_icon = "🔍" if analysis['mode'] == 'review' else "🧪"
                    st.markdown(f"**{mode_icon} {analysis['title']}**")
                    
                    if analysis.get('file_name'):
                        st.caption(f"📎 {analysis['file_name']}")
                
                with col2:
                    timestamp = datetime.fromisoformat(analysis['timestamp'])
                    st.caption(f"🕐 {timestamp.strftime('%d.%m.%Y %H:%M')}")
                    st.caption(f"📁 {analysis.get('category', 'Общее')}")
                
                with col3:
                    st.caption(f"📊 Вход: {analysis['input_length']} симв.")
                    st.caption(f"⭐ Оценка: {analysis.get('quality_score', 'N/A')}/10")
                
                with col4:
                    if st.button("👁️", key=f"view_{analysis['id']}", help="Открыть"):
                        st.session_state.current_result = analysis
                
                st.markdown("---")
        
        if st.session_state.current_result:
            st.markdown("### 📄 Просмотр результата")
            
            analysis = st.session_state.current_result
            
            st.markdown(f"**{analysis['title']}**")
            st.caption(f"🕐 {datetime.fromisoformat(analysis['timestamp']).strftime('%d.%m.%Y %H:%M')}")
            
            with st.expander("📥 Входные данные", expanded=False):
                st.text(analysis['input'])
            
            st.markdown("#### Результат анализа:")
            st.markdown(f'<div class="result-container">{analysis["output"]}</div>', unsafe_allow_html=True)
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.download_button(
                    "📄 Скачать TXT",
                    data=analysis['output'],
                    file_name=f"{analysis['title']}.txt",
                    mime="text/plain"
                )
            
            with col2:
                if analysis['mode'] == 'test_cases':
                    csv_data = extract_table_to_csv(analysis['output'])
                    if csv_data:
                        st.download_button(
                            "📊 Скачать CSV",
                            data=csv_data,
                            file_name=f"{analysis['title']}.csv",
                            mime="text/csv"
                        )
            
            with col3:
                if st.button("❌ Закрыть"):
                    st.session_state.current_result = None
                    st.rerun()

# ==================== СТРАНИЦА ШАБЛОНЫ ====================

elif page == "📝 Шаблоны":
    st.markdown('<h1 class="main-header">📝 Шаблоны требований</h1>', unsafe_allow_html=True)
    
    st.info("💡 Используйте готовые шаблоны для быстрого старта или создайте свои.")
    
    tab1, tab2 = st.tabs(["📚 Готовые шаблоны", "➕ Мои шаблоны"])
    
    with tab1:
        for name, content in st.session_state.templates.items():
            with st.expander(f"📄 {name.replace('_', ' ').title()}", expanded=False):
                st.text_area("Содержание:", value=content, height=200, key=f"template_{name}", disabled=True)
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("📋 Копировать", key=f"copy_{name}"):
                        st.session_state['template_to_use'] = content
                        st.success("✅ Скопировано!")
                
                with col2:
                    if st.button("🔍 Анализировать", key=f"analyze_{name}"):
                        st.session_state['template_to_analyze'] = content
                        st.success("→ Перейдите на страницу 'Анализ'")
    
    with tab2:
        st.markdown("### ➕ Создать свой шаблон")
        
        new_template_name = st.text_input("Название шаблона:")
        new_template_content = st.text_area("Содержание шаблона:", height=200)
        
        if st.button("💾 Сохранить шаблон") and new_template_name and new_template_content:
            st.session_state.templates[new_template_name.lower().replace(' ', '_')] = new_template_content
            st.success(f"✅ Шаблон '{new_template_name}' сохранён!")

# ==================== СТРАНИЦА АНАЛИТИКА ====================

elif page == "📊 Аналитика":
    st.markdown('<h1 class="main-header">📊 Расширенная аналитика</h1>', unsafe_allow_html=True)
    
    if not st.session_state.history:
        st.info("📭 Нет данных для аналитики. Создайте несколько анализов.")
    else:
        stats = get_statistics()
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("📈 Всего анализов", stats['total'])
        with col2:
            st.metric("⭐ Средняя оценка", f"{stats['avg_quality']}/10")
        with col3:
            st.metric("🧪 Тест-кейсов", stats['total_test_cases'])
        with col4:
            st.metric("📁 Файлов", stats['files_processed'])
        
        st.markdown("---")
        
        df = pd.DataFrame(st.session_state.history)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 📊 Распределение по типам")
            mode_counts = df['mode'].value_counts()
            fig = px.pie(
                values=mode_counts.values,
                names=['Ревью' if m == 'review' else 'Тест-кейсы' for m in mode_counts.index],
                color_discrete_sequence=['#667eea', '#4facfe']
            )
            fig.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font_color='#fafafa'
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.markdown("#### 📊 Распределение по категориям")
            cat_counts = df['category'].value_counts()
            fig = px.bar(
                x=cat_counts.index,
                y=cat_counts.values,
                color=cat_counts.values,
                color_continuous_scale='Viridis'
            )
            fig.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font_color='#fafafa',
                showlegend=False
            )
            st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("#### 📈 Динамика оценок качества")
        
        df['date'] = pd.to_datetime(df['timestamp']).dt.date
        quality_by_date = df.groupby('date')['quality_score'].mean().reset_index()
        
        fig = px.line(
            quality_by_date,
            x='date',
            y='quality_score',
            markers=True
        )
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font_color='#fafafa',
            yaxis_title="Средняя оценка",
            xaxis_title="Дата"
        )
        st.plotly_chart(fig, use_container_width=True)
        
        tc_analyses = [h for h in st.session_state.history if h.get('test_case_stats')]
        
        if tc_analyses:
            st.markdown("---")
            st.markdown("#### 🧪 Статистика тест-кейсов")
            
            total_stats = {
                'positive': sum([a['test_case_stats']['positive'] for a in tc_analyses]),
                'negative': sum([a['test_case_stats']['negative'] for a in tc_analyses]),
                'boundary': sum([a['test_case_stats']['boundary'] for a in tc_analyses]),
                'security': sum([a['test_case_stats']['security'] for a in tc_analyses])
            }
            
            fig = go.Figure(data=[
                go.Bar(name='Позитивные', x=['Тип'], y=[total_stats['positive']], marker_color='#10b981'),
                go.Bar(name='Негативные', x=['Тип'], y=[total_stats['negative']], marker_color='#ef4444'),
                go.Bar(name='Граничные', x=['Тип'], y=[total_stats['boundary']], marker_color='#f59e0b'),
                go.Bar(name='Безопасность', x=['Тип'], y=[total_stats['security']], marker_color='#8b5cf6')
            ])
            
            fig.update_layout(
                barmode='group',
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font_color='#fafafa',
                showlegend=True
            )
            
            st.plotly_chart(fig, use_container_width=True)

# ==================== СТРАНИЦА НАСТРОЙКИ ====================

elif page == "⚙️ Настройки":
    st.markdown('<h1 class="main-header">⚙️ Настройки</h1>', unsafe_allow_html=True)
    
    st.markdown("### 📝 Кастомизация промптов")
    st.info("ℹ️ Здесь вы можете настроить системные промпты для AI под свои нужды")
    
    tab1, tab2 = st.tabs(["🔍 Ревью требований", "🧪 Тест-кейсы"])
    
    with tab1:
        st.markdown("#### Промпт для режима 'Ревью требований'")
        
        current_review_prompt = st.session_state.custom_prompts.get('review', DEFAULT_PROMPTS['review'])
        
        review_prompt = st.text_area(
            "Текст промпта:",
            value=current_review_prompt,
            height=300,
            key="review_prompt_input"
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("💾 Сохранить промпт (Ревью)", use_container_width=True):
                st.session_state.custom_prompts['review'] = review_prompt
                st.success("✅ Промпт сохранён!")
        
        with col2:
            if st.button("🔄 Сбросить к стандартному (Ревью)", use_container_width=True):
                if 'review' in st.session_state.custom_prompts:
                    del st.session_state.custom_prompts['review']
                st.success("✅ Промпт сброшен!")
                st.rerun()
    
    with tab2:
        st.markdown("#### Промпт для режима 'Тест-кейсы'")
        
        current_tc_prompt = st.session_state.custom_prompts.get('test_cases', DEFAULT_PROMPTS['test_cases'])
        
        tc_prompt = st.text_area(
            "Текст промпта:",
            value=current_tc_prompt,
            height=300,
            key="tc_prompt_input"
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("💾 Сохранить промпт (Тест-кейсы)", use_container_width=True):
                st.session_state.custom_prompts['test_cases'] = tc_prompt
                st.success("✅ Промпт сохранён!")
        
        with col2:
            if st.button("🔄 Сбросить к стандартному (Тест-кейсы)", use_container_width=True):
                if 'test_cases' in st.session_state.custom_prompts:
                    del st.session_state.custom_prompts['test_cases']
                st.success("✅ Промпт сброшен!")
                st.rerun()
    
    st.markdown("---")
    st.markdown("### 🔧 Дополнительные настройки")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 📊 Экспорт данных")
        
        if st.button("📥 Скачать всю историю (JSON)", use_container_width=True):
            history_json = json.dumps(st.session_state.history, indent=2, ensure_ascii=False)
            st.download_button(
                "💾 Сохранить историю",
                data=history_json,
                file_name=f"qa_assistant_history_{datetime.now().strftime('%Y%m%d')}.json",
                mime="application/json"
            )
    
    with col2:
        st.markdown("#### 🗑️ Управление данными")
        
        if st.button("🗑️ Очистить всю историю", use_container_width=True):
            st.session_state.history = []
            st.success("✅ История очищена")
            st.rerun()
    
    st.markdown("---")
    st.markdown("### ℹ️ Информация")
    
    st.markdown(f"""
    **Версия:** 2.5  
    **AI Provider:** GigaChat  
    **Анализов в истории:** {len(st.session_state.history)}  
    **Кастомных промптов:** {len(st.session_state.custom_prompts)}  
    **Шаблонов:** {len(st.session_state.templates)}
    """)

# ==================== FOOTER ====================

st.markdown("---")
st.markdown(
    '<div style="text-align: center; color: #94a3b8; padding: 2rem;">'
    '🧪 QA Assistant Pro v2.5 | Powered by AI | Made with ❤️'
    '</div>',
    unsafe_allow_html=True
)
