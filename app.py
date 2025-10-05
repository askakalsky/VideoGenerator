"""
🎬 Video Production Studio
Профессиональный инструмент для создания видео контента
"""

import streamlit as st
from pathlib import Path
import json
from datetime import datetime

# Конфигурация страницы
st.set_page_config(
    page_title="Video Production Studio",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS стили
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        padding: 2rem 0;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .module-card {
        padding: 1.5rem;
        border-radius: 10px;
        border: 2px solid #667eea;
        margin: 1rem 0;
        transition: transform 0.3s;
    }
    .module-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 20px rgba(102, 126, 234, 0.3);
    }
    .stats-box {
        padding: 1rem;
        border-radius: 8px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)


def init_session_state():
    """Инициализация session state."""
    if 'history' not in st.session_state:
        st.session_state.history = []
    if 'settings' not in st.session_state:
        st.session_state.settings = {
            'default_output_dir': str(Path('assets/output')),
            'temp_dir': str(Path('assets/temp')),
            'keep_temp_files': False,
        }


def load_history():
    """Загружает историю операций."""
    history_file = Path('assets/history.json')
    if history_file.exists():
        with open(history_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


def save_history(history):
    """Сохраняет историю операций."""
    history_file = Path('assets/history.json')
    history_file.parent.mkdir(parents=True, exist_ok=True)
    with open(history_file, 'w', encoding='utf-8') as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


def add_to_history(module, action, details):
    """Добавляет запись в историю."""
    entry = {
        'timestamp': datetime.now().isoformat(),
        'module': module,
        'action': action,
        'details': details
    }
    if 'history' not in st.session_state:
        st.session_state.history = []
    st.session_state.history.insert(0, entry)
    save_history(st.session_state.history)


def main():
    """Главная страница приложения."""
    init_session_state()

    # Заголовок
    st.markdown('<h1 class="main-header">🎬 Video Production Studio</h1>',
                unsafe_allow_html=True)
    st.markdown("---")

    # Описание
    st.markdown("""
    ### Добро пожаловать в профессиональную студию обработки видео!
    
    Выберите нужный модуль в боковой панели или используйте быстрый доступ ниже.
    """)

    st.markdown("---")

    # Модули в виде карточек
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("""
        <div class="module-card">
            <h3>🎵 Background Music</h3>
            <p>Добавление фоновой музыки к видео с настройкой громкости и микшированием</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="module-card">
            <h3>🎤 Audio Mixer</h3>
            <p>Добавление аудио к случайному фрагменту видео с fade-эффектами</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class="module-card">
            <h3>📝 TikTok Subtitles</h3>
            <p>Создание субтитров с анимированной подсветкой слов</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="module-card">
            <h3>📐 Convert to 9:16</h3>
            <p>Конвертация видео в вертикальный формат для соцсетей</p>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown("""
        <div class="module-card">
            <h3>📥 YouTube Downloader</h3>
            <p>Загрузка видео с YouTube в различных качествах</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # Статистика
    st.subheader("📊 Статистика")

    history = load_history()

    stat_col1, stat_col2, stat_col3, stat_col4 = st.columns(4)

    with stat_col1:
        st.markdown(f"""
        <div class="stats-box">
            <h2>{len(history)}</h2>
            <p>Всего операций</p>
        </div>
        """, unsafe_allow_html=True)

    with stat_col2:
        today_count = len([h for h in history if h['timestamp'].startswith(
            datetime.now().date().isoformat())])
        st.markdown(f"""
        <div class="stats-box">
            <h2>{today_count}</h2>
            <p>Операций сегодня</p>
        </div>
        """, unsafe_allow_html=True)

    with stat_col3:
        downloads_dir = Path('assets/downloads')
        video_count = len(list(downloads_dir.glob('*.*'))
                          ) if downloads_dir.exists() else 0
        st.markdown(f"""
        <div class="stats-box">
            <h2>{video_count}</h2>
            <p>Файлов в загрузках</p>
        </div>
        """, unsafe_allow_html=True)

    with stat_col4:
        output_dir = Path('assets/output')
        output_count = len(list(output_dir.glob('*.*'))
                           ) if output_dir.exists() else 0
        st.markdown(f"""
        <div class="stats-box">
            <h2>{output_count}</h2>
            <p>Готовых файлов</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # Последние операции
    if history:
        st.subheader("📜 Последние операции")

        for i, entry in enumerate(history[:5]):
            with st.expander(f"{entry['timestamp'][:19]} - {entry['module']} - {entry['action']}"):
                st.json(entry['details'])

    # Sidebar
    with st.sidebar:
        st.image("https://via.placeholder.com/300x100/667eea/ffffff?text=Video+Studio",
                 use_container_width=True)

        st.markdown("---")

        st.markdown("### 🎯 Быстрые действия")

        if st.button("🗑️ Очистить историю", use_container_width=True):
            st.session_state.history = []
            save_history([])
            st.success("История очищена!")
            st.rerun()

        if st.button("📁 Открыть папку загрузок", use_container_width=True):
            import webbrowser
            webbrowser.open(str(Path('assets/downloads').resolve()))

        if st.button("📂 Открыть папку вывода", use_container_width=True):
            import webbrowser
            webbrowser.open(str(Path('assets/output').resolve()))

        st.markdown("---")

        st.markdown("### ⚙️ Настройки")

        st.session_state.settings['keep_temp_files'] = st.checkbox(
            "Сохранять временные файлы",
            value=st.session_state.settings.get('keep_temp_files', False)
        )

        st.markdown("---")

        st.markdown("""
        ### 📚 Справка
        
        **Горячие клавиши:**
        - `Ctrl + R` - Обновить
        - `Ctrl + K` - Очистить кэш
        
        **Поддержка:**
        - [Документация](#)
        - [GitHub](#)
        - [Telegram](#)
        """)


if __name__ == "__main__":
    main()
