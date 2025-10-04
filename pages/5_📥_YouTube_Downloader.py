"""
Страница модуля загрузки с YouTube
"""

from modules.youtube_downloader import YouTubeDownloader, DownloadConfig
import streamlit as st
from pathlib import Path
import sys
import re

sys.path.append(str(Path(__file__).parent.parent / 'modules'))


st.set_page_config(page_title="YouTube Downloader",
                   page_icon="📥", layout="wide")


def validate_youtube_url(url):
    """Простая валидация YouTube URL."""
    patterns = [
        r'(https?://)?(www\.)?(youtube\.com|youtu\.be)/.+',
    ]
    return any(re.match(pattern, url) for pattern in patterns)


def main():
    st.title("📥 YouTube Downloader")
    st.markdown("Скачивайте видео с YouTube в высоком качестве")

    st.markdown("---")

    # Режим работы
    mode = st.radio(
        "Режим загрузки:",
        ["Одно видео", "Плейлист", "Пакетная загрузка"],
        horizontal=True
    )

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("🔗 URL")

        if mode == "Одно видео":
            url = st.text_input(
                "YouTube URL",
                placeholder="https://www.youtube.com/watch?v=...",
                help="Вставьте ссылку на YouTube видео"
            )
            urls = [url] if url else []

        elif mode == "Плейлист":
            url = st.text_input(
                "Playlist URL",
                placeholder="https://www.youtube.com/playlist?list=...",
                help="Вставьте ссылку на плейлист"
            )

            playlist_start = st.number_input(
                "Начать с видео №", min_value=1, value=1)
            playlist_end = st.number_input(
                "Закончить на видео №", min_value=1, value=10)

            urls = [url] if url else []

        else:  # Пакетная
            urls_text = st.text_area(
                "Список URL (по одному на строку)",
                height=200,
                placeholder="https://www.youtube.com/watch?v=...\nhttps://www.youtube.com/watch?v=..."
            )
            urls = [u.strip() for u in urls_text.split('\n') if u.strip()]

    with col2:
        st.subheader("⚙️ Настройки")

        quality = st.selectbox(
            "Качество",
            options=['best', '4K', '2160p', '1440p',
                     '1080p', '720p', '480p', 'audio'],
            index=4
        )

        format_pref = st.selectbox(
            "Формат",
            options=['mp4', 'mkv', 'webm'],
            index=0
        )

        download_subtitles = st.checkbox("Скачать субтитры")

        if download_subtitles:
            subtitle_lang = st.text_input("Языки субтитров", value="en,ru")
        else:
            subtitle_lang = None

        download_thumbnail = st.checkbox("Скачать обложку")

        rate_limit = st.text_input(
            "Ограничение скорости (опционально)",
            placeholder="1M, 500K",
            help="Оставьте пустым для максимальной скорости"
        )

    st.markdown("---")

    # Валидация
    valid_urls = []
    if urls:
        for url in urls:
            if validate_youtube_url(url):
                valid_urls.append(url)
            else:
                st.warning(f"❌ Некорректный URL: {url}")

    # Кнопка загрузки
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        download_button = st.button(
            f"📥 Скачать ({len(valid_urls)} видео)",
            type="primary",
            use_container_width=True,
            disabled=len(valid_urls) == 0
        )

    if download_button and valid_urls:
        # Конфигурация
        config = DownloadConfig(
            quality=quality,
            format_preference=format_pref,
            output_dir=Path('assets/downloads'),
            write_subtitles=download_subtitles,
            subtitle_language=subtitle_lang,
            write_thumbnail=download_thumbnail,
            download_playlist=(mode == "Плейлист"),
            playlist_start=playlist_start if mode == "Плейлист" else 1,
            playlist_end=playlist_end if mode == "Плейлист" else None,
            rate_limit=rate_limit if rate_limit else None
        )

        downloader = YouTubeDownloader(config)

        # Progress
        progress_bar = st.progress(0)
        status_text = st.empty()

        results = []

        for i, url in enumerate(valid_urls):
            status_text.text(
                f"📥 Загружаю {i+1}/{len(valid_urls)}: {url[:50]}...")
            progress_bar.progress((i) / len(valid_urls))

            try:
                result = downloader.download(url)
                results.append(result)

                if result.success:
                    st.success(f"✅ {result.message}")
                else:
                    st.error(f"❌ {result.message}")

            except Exception as e:
                st.error(f"❌ Ошибка: {str(e)}")

        progress_bar.progress(1.0)
        status_text.text("✅ Загрузка завершена!")

        # Статистика
        success_count = sum(1 for r in results if r.success)

        st.markdown("---")
        st.subheader("📊 Результаты")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Всего", len(results))
        with col2:
            st.metric("Успешно", success_count)
        with col3:
            st.metric("Ошибок", len(results) - success_count)

        # Список файлов
        if success_count > 0:
            st.subheader("📁 Загруженные файлы")
            downloads_dir = Path('assets/downloads')
            for result in results:
                if result.success and result.output_path:
                    st.text(f"✅ {result.output_path.name}")

        from app import add_to_history
        add_to_history(
            "YouTube Downloader",
            f"Downloaded {success_count} videos",
            {'quality': quality, 'count': len(valid_urls)}
        )


if __name__ == "__main__":
    main()
