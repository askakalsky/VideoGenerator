"""
Страница загрузки видео с YouTube в максимальном качестве (до 4K).
"""

from modules.youtube_downloader import (
    YouTubeDownloader,
    DownloadConfig,
    validate_youtube_url
)
import sys
from pathlib import Path

import streamlit as st

# Добавление пути к модулям
sys.path.append(str(Path(__file__).parent.parent))


# ============================================================================
# КОНФИГУРАЦИЯ СТРАНИЦЫ
# ============================================================================

st.set_page_config(
    page_title="YouTube Downloader",
    page_icon="📥",
    layout="wide"
)


# ============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================================

def init_session_state():
    """Инициализация session state."""
    if 'download_history' not in st.session_state:
        st.session_state.download_history = []


def add_to_download_history(result):
    """Добавляет результат в историю."""
    st.session_state.download_history.insert(0, {
        'timestamp': st.session_state.get('current_time', 'Unknown'),
        'title': result.video_info.title if result.video_info else 'Unknown',
        'resolution': result.video_info.resolution_label if result.video_info else 'Unknown',
        'success': result.success,
        'filename': result.output_path.name if result.output_path else None,
    })

    # Ограничение истории
    if len(st.session_state.download_history) > 50:
        st.session_state.download_history = st.session_state.download_history[:50]


# ============================================================================
# ГЛАВНАЯ ФУНКЦИЯ
# ============================================================================

def main():
    """Главная функция страницы."""
    init_session_state()

    # Заголовок
    st.title("📥 YouTube Downloader")
    st.markdown(
        "Скачивание видео с YouTube в **максимальном качестве** (до 4K) "
        "в формате **MP4**"
    )

    st.markdown("---")

    # Информационная панель
    with st.expander("ℹ️ Информация", expanded=False):
        st.markdown("""
        ### Особенности загрузки:
        
        - **Качество**: Автоматически выбирается максимальное доступное качество до 4K (2160p)
        - **Формат**: Все видео конвертируются в MP4 (H.264)
        - **Название файла**: Включает разрешение (например: `Video_1080p.mp4`)
        - **Только видео**: Аудиодорожка не сохраняется (фокус на видео)
        - **Возобновление**: Поддержка продолжения прерванных загрузок
        
        ### Поддерживаемые URL:
        - Одиночные видео: `https://www.youtube.com/watch?v=...`
        - Короткие ссылки: `https://youtu.be/...`
        - Плейлисты: `https://www.youtube.com/playlist?list=...`
        """)

    st.markdown("---")

    # Режим работы
    mode = st.radio(
        "**Режим загрузки**",
        options=["📹 Одно видео", "📚 Плейлист", "📋 Пакетная загрузка"],
        horizontal=True,
        help="Выберите режим работы"
    )

    st.markdown("##")

    # Основная форма
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("🔗 URL адрес")

        if mode == "📹 Одно видео":
            url = st.text_input(
                "YouTube URL",
                placeholder="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                help="Вставьте ссылку на YouTube видео",
                label_visibility="collapsed"
            )
            urls = [url] if url else []

        elif mode == "📚 Плейлист":
            url = st.text_input(
                "Playlist URL",
                placeholder="https://www.youtube.com/playlist?list=...",
                help="Вставьте ссылку на плейлист YouTube",
                label_visibility="collapsed"
            )

            col_start, col_end = st.columns(2)

            with col_start:
                playlist_start = st.number_input(
                    "Начать с видео №",
                    min_value=1,
                    value=1,
                    help="Номер первого видео для загрузки"
                )

            with col_end:
                playlist_end = st.number_input(
                    "Закончить на видео №",
                    min_value=1,
                    value=10,
                    help="Номер последнего видео (0 = все)"
                )

            playlist_end = playlist_end if playlist_end > 0 else None
            urls = [url] if url else []

        else:  # Пакетная загрузка
            urls_text = st.text_area(
                "Список URL (по одному на строку)",
                height=200,
                placeholder="https://www.youtube.com/watch?v=...\nhttps://www.youtube.com/watch?v=...",
                help="Вставьте несколько ссылок, каждая с новой строки",
                label_visibility="collapsed"
            )
            urls = [u.strip() for u in urls_text.split('\n') if u.strip()]

    with col2:
        st.subheader("⚙️ Настройки")

        st.info(
            "**Качество**: Автоматически\n\n"
            "*(макс. 4K)*\n\n"
            "**Формат**: MP4"
        )

        # Дополнительные настройки
        with st.expander("Дополнительно", expanded=False):
            rate_limit = st.text_input(
                "Ограничение скорости",
                placeholder="1M, 500K",
                help="Оставьте пустым для максимальной скорости"
            )

            overwrite = st.checkbox(
                "Перезаписывать существующие файлы",
                value=False,
                help="Если файл уже существует, он будет перезаписан"
            )

            concurrent_fragments = st.slider(
                "Параллельные загрузки фрагментов",
                min_value=1,
                max_value=16,
                value=8,
                help="Количество одновременно загружаемых фрагментов"
            )

    st.markdown("---")

    # Валидация URL
    valid_urls = []
    invalid_urls = []

    for url in urls:
        if validate_youtube_url(url):
            valid_urls.append(url)
        else:
            invalid_urls.append(url)

    # Показываем ошибки валидации
    if invalid_urls:
        st.error(f"❌ Некорректные URL ({len(invalid_urls)}):")
        for invalid_url in invalid_urls[:5]:  # Показываем первые 5
            st.code(invalid_url, language=None)
        if len(invalid_urls) > 5:
            st.caption(f"...и еще {len(invalid_urls) - 5}")

    # Информация о валидных URL
    if valid_urls:
        st.success(f"✅ Готово к загрузке: **{len(valid_urls)}** видео")

    # Кнопка загрузки
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        download_button = st.button(
            f"📥 Скачать ({len(valid_urls)} видео)" if len(valid_urls) != 1
            else "📥 Скачать видео",
            type="primary",
            use_container_width=True,
            disabled=len(valid_urls) == 0
        )

    # Процесс загрузки
    if download_button and valid_urls:
        st.markdown("---")
        st.subheader("🚀 Загрузка")

        # Сохраняем текущее время
        from datetime import datetime
        st.session_state.current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Создание конфигурации
        config = DownloadConfig(
            output_dir=Path('assets/downloads'),
            download_playlist=(mode == "📚 Плейлист"),
            playlist_start=playlist_start if mode == "📚 Плейлист" else 1,
            playlist_end=playlist_end if mode == "📚 Плейлист" else None,
            rate_limit=rate_limit.strip() if rate_limit else None,
            overwrite=overwrite,
            concurrent_fragments=concurrent_fragments,
        )

        # Создание загрузчика
        downloader = YouTubeDownloader(config)

        # Progress bar
        progress_bar = st.progress(0)
        status_container = st.empty()

        # Контейнер для результатов
        results_container = st.container()

        results = []

        # Загрузка видео
        for i, url in enumerate(valid_urls):
            status_container.info(
                f"📥 Загрузка {i + 1} из {len(valid_urls)}: {url[:60]}..."
            )
            progress_bar.progress(i / len(valid_urls))

            try:
                # Загрузка с захватом вывода
                with st.spinner(f"Загрузка видео {i + 1}..."):
                    result = downloader.download(url)
                    results.append(result)

                # Отображение результата
                with results_container:
                    if result.success:
                        st.success(
                            f"✅ **{result.video_info.title}** "
                            f"({result.video_info.resolution_label}) - "
                            f"{result.output_path.name if result.output_path else 'Unknown'}"
                        )

                        # Добавляем в историю
                        add_to_download_history(result)
                    else:
                        st.error(f"❌ {result.message}")

            except Exception as e:
                st.error(f"❌ Ошибка при загрузке: {str(e)}")
                results.append(None)

        # Завершение
        progress_bar.progress(1.0)
        status_container.success("✅ Загрузка завершена!")

        # Статистика
        st.markdown("---")
        st.subheader("📊 Статистика")

        success_count = sum(1 for r in results if r and r.success)
        failed_count = len(results) - success_count
        total_time = sum(r.download_time for r in results if r)

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Всего", len(results))

        with col2:
            st.metric("Успешно", success_count, delta=None)

        with col3:
            st.metric("Ошибок", failed_count, delta=None)

        with col4:
            st.metric("Время", f"{total_time:.1f}s")

        # Список загруженных файлов
        if success_count > 0:
            st.markdown("---")
            st.subheader("📁 Загруженные файлы")

            for result in results:
                if result and result.success and result.output_path:
                    file_size = result.output_path.stat().st_size / (1024 * 1024)  # MB

                    col1, col2, col3 = st.columns([3, 1, 1])

                    with col1:
                        st.text(f"📄 {result.output_path.name}")

                    with col2:
                        st.text(f"{result.video_info.resolution_label}")

                    with col3:
                        st.text(f"{file_size:.1f} MB")

        # Добавление в общую историю приложения
        try:
            from app import add_to_history
            add_to_history(
                "YouTube Downloader",
                f"Downloaded {success_count} video(s) in max quality (up to 4K)",
                {'count': success_count, 'mode': mode}
            )
        except ImportError:
            pass

    # История загрузок
    if st.session_state.download_history:
        st.markdown("---")
        st.subheader("📜 История загрузок")

        with st.expander("Показать историю", expanded=False):
            for i, item in enumerate(st.session_state.download_history[:10], 1):
                status_icon = "✅" if item['success'] else "❌"
                st.text(
                    f"{i}. {status_icon} [{item['timestamp']}] "
                    f"{item['title']} ({item['resolution']}) - {item['filename']}"
                )


# ============================================================================
# ТОЧКА ВХОДА
# ============================================================================

if __name__ == "__main__":
    main()
