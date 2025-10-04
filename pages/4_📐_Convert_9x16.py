"""
Страница модуля конвертации в формат 9:16
"""

from modules.video_converter import BatchConverter, ConversionConfig
import streamlit as st
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent / 'modules'))


st.set_page_config(page_title="Convert to 9:16", page_icon="📐", layout="wide")


def main():
    st.title("📐 Конвертация в формат 9:16")
    st.markdown(
        "Конвертируйте видео в вертикальный формат для TikTok, Reels, Shorts")

    st.markdown("---")

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("📁 Выбор файлов")

        mode = st.radio(
            "Режим:",
            ["Одно видео", "Пакетная обработка"],
            horizontal=True
        )

        if mode == "Одно видео":
            video_source = st.radio(
                "Источник:",
                ["Загрузить файл", "Выбрать из папки"],
                horizontal=True,
                key='video_source_convert'
            )

            if video_source == "Загрузить файл":
                video_file = st.file_uploader(
                    "Выберите видео файл",
                    type=['mp4', 'mov', 'avi', 'mkv'],
                    key='video_convert'
                )
                video_files = [video_file] if video_file else []
            else:
                downloads_dir = Path('assets/downloads')
                if downloads_dir.exists():
                    available_videos = list(downloads_dir.glob(
                        '*.mp4')) + list(downloads_dir.glob('*.mov'))
                    if available_videos:
                        video_file = st.selectbox(
                            "Выберите видео:",
                            options=available_videos,
                            format_func=lambda x: x.name,
                            key='select_video_convert'
                        )
                        video_files = [video_file]
                    else:
                        st.warning("Нет видео файлов в папке")
                        video_files = []
                else:
                    st.warning("Папка не найдена")
                    video_files = []
        else:
            # Пакетная обработка
            batch_dir = st.text_input(
                "Путь к папке с видео",
                value="assets/downloads"
            )

            batch_path = Path(batch_dir)
            if batch_path.exists():
                video_files = list(batch_path.glob('*.mp4')) + \
                    list(batch_path.glob('*.mov')) + \
                    list(batch_path.glob('*.avi'))

                st.info(f"Найдено {len(video_files)} видео файлов")

                if video_files:
                    with st.expander("📋 Список файлов"):
                        for vf in video_files[:10]:
                            st.text(f"• {vf.name}")
                        if len(video_files) > 10:
                            st.text(
                                f"... и еще {len(video_files) - 10} файлов")
            else:
                st.error("Папка не найдена")
                video_files = []

    with col2:
        st.subheader("⚙️ Настройки конвертации")

        # Позиция обрезки
        crop_position = st.selectbox(
            "Позиция обрезки по вертикали",
            options=['top', 'center', 'bottom'],
            index=0,
            help="top = прижать к верху, center = центрировать, bottom = прижать к низу"
        )

        # Аудио
        remove_audio = st.checkbox(
            "Удалить аудиодорожку",
            value=True,
            help="Удаление аудио уменьшает размер файла"
        )

        if not remove_audio:
            audio_codec = st.selectbox(
                "Аудио кодек",
                options=['aac', 'mp3', 'opus'],
                index=0
            )

            audio_bitrate = st.selectbox(
                "Аудио bitrate",
                options=['128k', '192k', '256k', '320k'],
                index=1
            )
        else:
            audio_codec = None
            audio_bitrate = None

        st.markdown("---")

        # Качество видео
        st.subheader("🎬 Качество видео")

        quality_preset = st.select_slider(
            "Preset качества",
            options=['ultrafast', 'superfast', 'veryfast', 'faster',
                     'fast', 'medium', 'slow', 'slower', 'veryslow'],
            value='medium',
            help="Медленнее = лучше сжатие"
        )

        crf = st.slider(
            "CRF (качество)",
            min_value=0,
            max_value=51,
            value=18,
            help="0 = lossless, 18-23 = отличное, 23-28 = хорошее"
        )

        video_bitrate = st.text_input(
            "Video bitrate (опционально)",
            value="8000k",
            help="Оставьте пустым для автоматического"
        )

        st.markdown("---")

        # Дополнительные опции
        with st.expander("🔧 Дополнительные опции"):
            skip_vertical = st.checkbox(
                "Пропускать уже вертикальные",
                value=True,
                help="Не обрабатывать видео уже в формате 9:16"
            )

            delete_source = st.checkbox(
                "Удалить исходники после конвертации",
                value=False,
                help="⚠️ ВНИМАНИЕ: Исходные файлы будут удалены!"
            )

            min_width = st.number_input(
                "Минимальная ширина",
                min_value=360,
                max_value=3840,
                value=720,
                step=10
            )

            min_height = st.number_input(
                "Минимальная высота",
                min_value=640,
                max_value=7680,
                value=1280,
                step=10
            )

            max_workers = st.number_input(
                "Количество потоков",
                min_value=1,
                max_value=16,
                value=4,
                help="Больше = быстрее, но больше нагрузка"
            )

    st.markdown("---")

    # Кнопка обработки
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        process_button = st.button(
            f"🚀 Конвертировать ({len(video_files)} файлов)",
            type="primary",
            use_container_width=True,
            disabled=len(video_files) == 0
        )

    # Обработка
    if process_button and video_files:
        # Создаём временную папку для загруженных файлов
        temp_dir = Path('assets/temp')
        temp_dir.mkdir(parents=True, exist_ok=True)

        input_dir = temp_dir

        # Если загружен файл, сохраняем его
        if mode == "Одно видео" and video_source == "Загрузить файл":
            video_path = temp_dir / video_files[0].name
            with open(video_path, 'wb') as f:
                f.write(video_files[0].read())
            input_dir = temp_dir
        else:
            # Используем существующую папку
            if mode == "Одно видео":
                # Копируем в temp
                import shutil
                video_path = temp_dir / video_files[0].name
                shutil.copy2(video_files[0], video_path)
                input_dir = temp_dir
            else:
                input_dir = batch_path

        # Выходная папка
        output_dir = Path('assets/stock_videos')
        output_dir.mkdir(parents=True, exist_ok=True)

        # Создаём конфигурацию
        config = ConversionConfig(
            crf=crf,
            preset=quality_preset,
            crop_position=crop_position,
            remove_audio=remove_audio,
            audio_codec=audio_codec if not remove_audio else None,
            audio_bitrate=audio_bitrate if not remove_audio else None,
            video_bitrate=video_bitrate if video_bitrate else None,
            delete_source=delete_source,
            skip_if_vertical=skip_vertical,
            max_workers=max_workers,
            min_width=min_width,
            min_height=min_height
        )

        # Progress
        progress_bar = st.progress(0)
        status_text = st.empty()

        try:
            status_text.text("🎬 Начинаю конвертацию...")
            progress_bar.progress(10)

            converter = BatchConverter(config)

            # Используем заглушку для вывода
            import io
            import contextlib

            # Перехватываем stdout
            f = io.StringIO()

            with contextlib.redirect_stdout(f):
                stats = converter.process_directory(
                    input_dir=input_dir,
                    output_dir=output_dir,
                    save_report=True
                )

            progress_bar.progress(100)
            status_text.text("✅ Конвертация завершена!")

            # Показываем статистику
            st.markdown("---")
            st.subheader("📊 Результаты")

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("Всего", stats['total'])
            with col2:
                st.metric("Успешно", stats['success'], delta=None)
            with col3:
                st.metric("Ошибок", stats['failed'])
            with col4:
                st.metric("Пропущено", stats['skipped'])

            # Список результатов
            if stats['success'] > 0:
                st.subheader("✅ Конвертированные файлы")

                output_files = list(output_dir.glob('*_9x16.mp4'))
                for i, output_file in enumerate(output_files[:5]):
                    st.text(f"• {output_file.name}")

                if len(output_files) > 5:
                    st.text(f"... и еще {len(output_files) - 5} файлов")

            # Показываем ошибки если есть
            if stats['failed'] > 0:
                with st.expander("❌ Ошибки"):
                    for result in stats['results']:
                        if not result.success and not result.skipped:
                            st.error(
                                f"{result.input_path.name}: {result.error}")

            # Добавляем в историю
            from app import add_to_history
            add_to_history(
                module="Convert 9:16",
                action=f"Converted {stats['success']} videos",
                details={
                    'total': stats['total'],
                    'success': stats['success'],
                    'quality': f"CRF {crf}",
                    'position': crop_position
                }
            )

        except Exception as e:
            st.error(f"❌ Ошибка обработки: {str(e)}")
            st.exception(e)

        finally:
            # Очистка временных файлов
            if not st.session_state.get('keep_temp_files', False):
                if mode == "Одно видео" and temp_dir.exists():
                    import shutil
                    try:
                        shutil.rmtree(temp_dir)
                    except Exception as e:
                        st.warning(f"Не удалось очистить временные файлы: {e}")


if __name__ == "__main__":
    main()
