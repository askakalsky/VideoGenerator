"""
Страница загрузки видео с YouTube в максимальном качестве (до 4K).
С опциональной автоматической обрезкой в формат 9:16.
"""

from modules.youtube_downloader import (
    YouTubeDownloader,
    DownloadConfig,
    validate_youtube_url
)
from modules.video_converter import (
    convert_single_video,
    ConversionConfig,
    check_nvidia_gpu
)
import sys
from pathlib import Path
from datetime import datetime

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


def add_to_download_history(result, converted_path=None):
    """Добавляет результат в историю."""
    st.session_state.download_history.insert(0, {
        'timestamp': st.session_state.get('current_time', 'Unknown'),
        'title': result.video_info.title if result.video_info else 'Unknown',
        'resolution': result.video_info.resolution_label if result.video_info else 'Unknown',
        'success': result.success,
        'filename': result.output_path.name if result.output_path else None,
        'converted': converted_path.name if converted_path else None,
    })

    # Ограничение истории
    if len(st.session_state.download_history) > 50:
        st.session_state.download_history = st.session_state.download_history[:50]


def convert_video_to_9x16(video_path: Path, config: ConversionConfig, status_container) -> tuple:
    """
    Конвертирует видео в формат 9:16.

    Args:
        video_path: Путь к скачанному видео
        config: Конфигурация конвертации
        status_container: Streamlit контейнер для статуса

    Returns:
        tuple: (success: bool, output_path: Path or None, message: str)
    """
    try:
        output_dir = Path('assets/stock_videos')
        output_dir.mkdir(parents=True, exist_ok=True)

        status_container.info(f"🎬 Обрезка в 9:16: {video_path.name}...")

        # Конвертация
        result = convert_single_video(
            input_path=video_path,
            output_dir=output_dir,
            config=config
        )

        if result.success and not result.skipped:
            status_container.success(
                f"✅ Обрезано: {result.output_resolution} за {result.processing_time:.1f}s "
                f"({'GPU' if result.used_gpu else 'CPU'})"
            )
            return True, result.output_path, result.message
        elif result.skipped:
            status_container.info(f"⏭️ {result.message}")
            return True, None, result.message
        else:
            status_container.error(f"❌ Ошибка обрезки: {result.error}")
            return False, None, result.error or "Conversion failed"

    except Exception as e:
        error_msg = f"Ошибка конвертации: {str(e)}"
        status_container.error(f"❌ {error_msg}")
        return False, None, error_msg


# ============================================================================
# ГЛАВНАЯ ФУНКЦИЯ
# ============================================================================

def main():
    """Главная функция страницы."""
    init_session_state()

    # Заголовок
    st.title("📥 YouTube Downloader + 9:16 Converter")
    st.markdown(
        "Скачивание видео с YouTube в **максимальном качестве** (до 4K) "
        "в формате **MP4** с опциональной автоматической обрезкой в **9:16**"
    )

    st.markdown("---")

    # Информационная панель
    with st.expander("ℹ️ Информация", expanded=False):
        st.markdown("""
        ### Особенности загрузки:
        
        - **Качество**: Автоматически выбирается максимальное доступное качество до 4K (2160p)
        - **Формат**: Все видео конвертируются в MP4 (H.264)
        - **Название файла**: Включает разрешение (например: `Video_1080p.mp4`)
        - **Только видео**: Аудиодорожка не сохраняется при загрузке (фокус на видео)
        - **Возобновление**: Поддержка продолжения прерванных загрузок
        
        ### Автоматическая обрезка 9:16:
        - **GPU ускорение**: NVIDIA NVENC (если доступно) - в 5-10 раз быстрее CPU
        - **Качество**: Максимальное (CQ 19, Preset p7, 50 Mbps)
        - **Битрейт**: 50 Mbps для сохранения 4K качества без потерь
        - **Обрезка**: Центрирование по ширине, сохранение полной высоты
        - **Результат**: Сохраняется в `assets/stock_videos/`
        
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

        # Основная опция: конвертация в 9:16
        convert_to_9x16 = st.checkbox(
            "📐 Автоматически обрезать в 9:16",
            value=False,
            help="После загрузки видео будет автоматически обрезано в вертикальный формат 9:16"
        )

        if convert_to_9x16:
            st.success("✅ Видео будет обрезано в 9:16 после загрузки")

            # Настройки конвертации
            with st.expander("🎬 Настройки обрезки 9:16", expanded=True):
                # GPU
                gpu_available = check_nvidia_gpu()

                if gpu_available:
                    use_gpu = st.checkbox(
                        "🚀 GPU ускорение (NVIDIA NVENC)",
                        value=True,
                        help="Использовать GPU для ускорения обрезки в 5-10 раз"
                    )

                    if use_gpu:
                        st.info("✓ NVENC доступен - обработка будет быстрой!")
                else:
                    use_gpu = False
                    st.warning(
                        "⚠️ NVIDIA GPU не обнаружен - будет использован CPU")

                # Аудио
                remove_audio_crop = st.checkbox(
                    "🔇 Удалить аудио при обрезке",
                    value=True,
                    help="Уменьшает размер файла"
                )

                # Дополнительные настройки
                skip_if_vertical = st.checkbox(
                    "⏭️ Пропускать уже вертикальные",
                    value=True,
                    help="Не обрабатывать видео уже в формате 9:16"
                )

                delete_original = st.checkbox(
                    "🗑️ Удалить оригинал после обрезки",
                    value=False,
                    help="⚠️ Удалит скачанное видео, оставит только обрезанную версию"
                )
        else:
            use_gpu = True
            remove_audio_crop = True
            skip_if_vertical = True
            delete_original = False

        st.info(
            "**Качество**: Автоматически\n\n"
            "*(макс. 4K)*\n\n"
            "**Формат**: MP4"
        )

        # Дополнительные настройки загрузки
        with st.expander("🔧 Настройки загрузки", expanded=False):
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
        if convert_to_9x16:
            st.success(
                f"✅ Готово к загрузке и обрезке: **{len(valid_urls)}** видео")
        else:
            st.success(f"✅ Готово к загрузке: **{len(valid_urls)}** видео")

    # Кнопка загрузки
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        button_text = "📥 Скачать и обрезать" if convert_to_9x16 else "📥 Скачать"
        if len(valid_urls) > 1:
            button_text += f" ({len(valid_urls)} видео)"
        else:
            button_text += " видео"

        download_button = st.button(
            button_text,
            type="primary",
            use_container_width=True,
            disabled=len(valid_urls) == 0
        )

    # Процесс загрузки
    if download_button and valid_urls:
        st.markdown("---")
        st.subheader("🚀 Загрузка" + (" и обрезка" if convert_to_9x16 else ""))

        # Сохраняем текущее время
        st.session_state.current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Создание конфигурации загрузки
        download_config = DownloadConfig(
            output_dir=Path('assets/downloads'),
            download_playlist=(mode == "📚 Плейлист"),
            playlist_start=playlist_start if mode == "📚 Плейлист" else 1,
            playlist_end=playlist_end if mode == "📚 Плейлист" else None,
            rate_limit=rate_limit.strip() if rate_limit else None,
            overwrite=overwrite,
            concurrent_fragments=concurrent_fragments,
        )

        # Создание конфигурации конвертации (если нужно)
        if convert_to_9x16:
            conversion_config = ConversionConfig(
                use_gpu=use_gpu,
                remove_audio=remove_audio_crop,
                audio_codec='copy' if not remove_audio_crop else None,
                audio_bitrate=None,
                delete_source=delete_original,
                skip_if_vertical=skip_if_vertical,
                max_workers=1,  # Обрабатываем по одному
                min_width=720,
                min_height=1280,
                # Максимальное качество для GPU
                nvenc_preset='p7',
                nvenc_cq=19,
                video_bitrate='50M',
                max_bitrate='75M',
                bufsize='100M',
                # Для CPU
                cpu_crf=18,
                cpu_preset='medium'
            )

        # Создание загрузчика
        downloader = YouTubeDownloader(download_config)

        # Progress bar
        progress_bar = st.progress(0)
        status_container = st.empty()

        # Контейнеры для результатов
        results_container = st.container()
        conversion_container = st.container()

        download_results = []
        conversion_results = []

        # Загрузка видео
        for i, url in enumerate(valid_urls):
            status_container.info(
                f"📥 Загрузка {i + 1} из {len(valid_urls)}: {url[:60]}..."
            )

            # Прогресс: первая половина - загрузка
            base_progress = i / len(valid_urls)
            if convert_to_9x16:
                progress_bar.progress(base_progress * 0.5)
            else:
                progress_bar.progress(base_progress)

            try:
                # Загрузка
                with st.spinner(f"Загрузка видео {i + 1}..."):
                    download_result = downloader.download(url)
                    download_results.append(download_result)

                # Отображение результата загрузки
                with results_container:
                    if download_result.success:
                        st.success(
                            f"✅ Загружено: **{download_result.video_info.title}** "
                            f"({download_result.video_info.resolution_label}) - "
                            f"{download_result.output_path.name if download_result.output_path else 'Unknown'}"
                        )

                        # Конвертация если включена
                        if convert_to_9x16 and download_result.output_path:
                            # Прогресс: вторая половина - конвертация
                            progress_bar.progress(base_progress * 0.5 + 0.25)

                            with conversion_container:
                                conversion_status = st.empty()

                                success, converted_path, message = convert_video_to_9x16(
                                    video_path=download_result.output_path,
                                    config=conversion_config,
                                    status_container=conversion_status
                                )

                                conversion_results.append({
                                    'success': success,
                                    'output_path': converted_path,
                                    'message': message,
                                    'original_path': download_result.output_path
                                })

                                # Добавляем в историю с информацией о конвертации
                                add_to_download_history(
                                    download_result, converted_path)
                        else:
                            # Добавляем в историю без конвертации
                            add_to_download_history(download_result)
                    else:
                        st.error(
                            f"❌ Ошибка загрузки: {download_result.message}")

            except Exception as e:
                st.error(f"❌ Ошибка при загрузке: {str(e)}")
                download_results.append(None)

        # Завершение
        progress_bar.progress(1.0)

        if convert_to_9x16:
            status_container.success("✅ Загрузка и обрезка завершены!")
        else:
            status_container.success("✅ Загрузка завершена!")

        # Статистика
        st.markdown("---")
        st.subheader("📊 Статистика")

        download_success = sum(1 for r in download_results if r and r.success)
        download_failed = len(download_results) - download_success
        total_download_time = sum(
            r.download_time for r in download_results if r)

        if convert_to_9x16 and conversion_results:
            conversion_success = sum(
                1 for r in conversion_results if r['success'])
            conversion_failed = len(conversion_results) - conversion_success
            # Все успешные использовали настройки
            gpu_used_count = sum(
                1 for r in download_results if r and r.success)

            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("📥 Загружено", download_success)
                st.metric("❌ Ошибок загрузки", download_failed)

            with col2:
                st.metric("🎬 Обрезано", conversion_success)
                st.metric("❌ Ошибок обрезки", conversion_failed)

            with col3:
                st.metric("⏱️ Время загрузки", f"{total_download_time:.1f}s")
                st.metric("🚀 Использован GPU",
                          "Да" if use_gpu and gpu_used_count > 0 else "Нет")
        else:
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("Всего", len(download_results))

            with col2:
                st.metric("Успешно", download_success)

            with col3:
                st.metric("Ошибок", download_failed)

            with col4:
                st.metric("Время", f"{total_download_time:.1f}s")

        # Список загруженных файлов
        if download_success > 0:
            st.markdown("---")

            if convert_to_9x16 and conversion_results:
                st.subheader("📁 Результаты")

                # Таблица с оригиналами и обрезанными
                for i, download_result in enumerate(download_results):
                    if download_result and download_result.success:
                        conversion_result = conversion_results[i] if i < len(
                            conversion_results) else None

                        with st.expander(f"#{i+1} {download_result.video_info.title[:50]}", expanded=False):
                            col1, col2 = st.columns(2)

                            with col1:
                                st.markdown("**📥 Оригинал:**")
                                if download_result.output_path and download_result.output_path.exists():
                                    file_size = download_result.output_path.stat().st_size / (1024 * 1024)
                                    st.text(
                                        f"📄 {download_result.output_path.name}")
                                    st.text(
                                        f"📐 {download_result.video_info.resolution_label}")
                                    st.text(f"💾 {file_size:.1f} MB")

                                    if delete_original and conversion_result and conversion_result['success']:
                                        st.text("🗑️ Удален")
                                else:
                                    st.text("❌ Файл не найден")

                            with col2:
                                st.markdown("**🎬 Обрезанное (9:16):**")
                                if conversion_result:
                                    if conversion_result['success'] and conversion_result['output_path']:
                                        file_size = conversion_result['output_path'].stat(
                                        ).st_size / (1024 * 1024)
                                        st.text(
                                            f"📄 {conversion_result['output_path'].name}")
                                        st.text(f"💾 {file_size:.1f} MB")
                                        st.text(f"✅ Готово")
                                    else:
                                        st.text(
                                            f"⏭️ {conversion_result['message']}")
                                else:
                                    st.text("❌ Не обработано")
            else:
                st.subheader("📁 Загруженные файлы")

                for download_result in download_results:
                    if download_result and download_result.success and download_result.output_path:
                        file_size = download_result.output_path.stat().st_size / (1024 * 1024)

                        col1, col2, col3 = st.columns([3, 1, 1])

                        with col1:
                            st.text(f"📄 {download_result.output_path.name}")

                        with col2:
                            st.text(
                                f"{download_result.video_info.resolution_label}")

                        with col3:
                            st.text(f"{file_size:.1f} MB")

        # Добавление в общую историю приложения
        try:
            from app import add_to_history

            if convert_to_9x16 and conversion_results:
                add_to_history(
                    "YouTube Downloader + 9:16",
                    f"Downloaded and cropped {conversion_success} video(s) to 9:16",
                    {
                        'downloaded': download_success,
                        'converted': conversion_success,
                        'mode': mode,
                        'gpu_used': use_gpu
                    }
                )
            else:
                add_to_history(
                    "YouTube Downloader",
                    f"Downloaded {download_success} video(s) in max quality (up to 4K)",
                    {'count': download_success, 'mode': mode}
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

                if item.get('converted'):
                    display_text = (
                        f"{i}. {status_icon} [{item['timestamp']}] "
                        f"{item['title']} ({item['resolution']}) - "
                        f"📥 {item['filename']} → 🎬 {item['converted']}"
                    )
                else:
                    display_text = (
                        f"{i}. {status_icon} [{item['timestamp']}] "
                        f"{item['title']} ({item['resolution']}) - {item['filename']}"
                    )

                st.text(display_text)


# ============================================================================
# ТОЧКА ВХОДА
# ============================================================================

if __name__ == "__main__":
    main()
