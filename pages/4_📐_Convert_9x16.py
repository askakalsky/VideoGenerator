"""
Страница модуля обрезки в формат 9:16
"""

from modules.video_converter import BatchConverter, ConversionConfig
import streamlit as st
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent / 'modules'))


st.set_page_config(page_title="Convert to 9:16", page_icon="📐", layout="wide")


def main():
    st.title("📐 Обрезка видео в формат 9:16")
    st.markdown(
        "Обрезайте видео в вертикальный формат для TikTok, Reels, Shorts")

    st.info("ℹ️ **Режим работы:** видео обрезается по центру с сохранением качества. "
            "GPU ускорение (NVIDIA NVENC) включено автоматически при наличии видеокарты.")

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
                    available_videos = list(downloads_dir.glob('*.mp4')) + \
                        list(downloads_dir.glob('*.mov')) + \
                        list(downloads_dir.glob('*.avi'))
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
                    list(batch_path.glob('*.avi')) + \
                    list(batch_path.glob('*.mkv'))

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
        st.subheader("⚙️ Настройки")

        # Аудио
        remove_audio = st.checkbox(
            "Удалить аудиодорожку",
            value=True,
            help="Удаление аудио уменьшает размер файла"
        )

        if not remove_audio:
            st.markdown("**Параметры аудио:**")
            audio_codec = st.selectbox(
                "Кодек",
                options=['copy', 'aac', 'mp3'],
                index=0,
                help="'copy' = без перекодирования (быстро)"
            )

            if audio_codec != 'copy':
                audio_bitrate = st.selectbox(
                    "Bitrate",
                    options=['128k', '192k', '256k', '320k'],
                    index=1
                )
            else:
                audio_bitrate = None
        else:
            audio_codec = None
            audio_bitrate = None

        st.markdown("---")

        # Дополнительные опции
        with st.expander("🔧 Дополнительные настройки"):

            use_gpu = st.checkbox(
                "GPU ускорение (NVIDIA)",
                value=True,
                help="Включить NVENC для ускорения обработки в 10-20 раз"
            )

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
                step=10,
                help="Видео с меньшим разрешением будут пропущены"
            )

            min_height = st.number_input(
                "Минимальная высота",
                min_value=640,
                max_value=7680,
                value=1280,
                step=10,
                help="Видео с меньшим разрешением будут пропущены"
            )

            max_workers = st.number_input(
                "Количество потоков",
                min_value=1,
                max_value=8,
                value=2 if use_gpu else 4,
                help="Для GPU рекомендуется 1-2 потока"
            )

        st.markdown("---")

        # Информация о режиме
        if use_gpu:
            st.success("""
            **🚀 GPU режим (NVENC):**
            - Энкодер: h264_nvenc (GPU)
            - Декодер: CPU (совместимость с crop)
            - Качество: CQ 19 (высокое)
            - Preset: p7 (максимальное качество)
            - Битрейт: 50 Mbps (для 4K)
            - Ускорение: ~5-10x быстрее чисто CPU
            """)
        else:
            st.info("""
            **⚙️ CPU режим:**
            - Кодек: libx264
            - CRF: 18 (высокое качество)
            - Preset: medium
            """)

    st.markdown("---")

    # Кнопка обработки
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        process_button = st.button(
            f"🚀 Обрезать ({len(video_files)} файлов)",
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
            use_gpu=use_gpu,
            remove_audio=remove_audio,
            audio_codec=audio_codec if not remove_audio else None,
            audio_bitrate=audio_bitrate if not remove_audio and audio_codec != 'copy' else None,
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
            status_text.text("🎬 Начинаю обрезку...")
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
            status_text.text("✅ Обработка завершена!")

            # Показываем статистику
            st.markdown("---")
            st.subheader("📊 Результаты")

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("Всего", stats['total'])
            with col2:
                st.metric("Успешно", stats['success'])
            with col3:
                st.metric("Ошибок", stats['failed'])
            with col4:
                st.metric("Пропущено", stats['skipped'])

            # Показываем обработанные файлы с разрешениями
            if stats['success'] > 0:
                st.subheader("✅ Обработанные файлы")

                for result in stats['results']:
                    if result.success and not result.skipped:
                        col1, col2, col3 = st.columns([2, 1, 1])

                        with col1:
                            st.text(
                                f"📹 {result.output_path.name if result.output_path else 'N/A'}")

                        with col2:
                            if result.output_resolution:
                                st.text(f"📐 {result.output_resolution}")

                        with col3:
                            if result.processing_time:
                                st.text(f"⏱️ {result.processing_time:.1f}s")

            # Показываем ошибки если есть
            if stats['failed'] > 0:
                with st.expander("❌ Ошибки"):
                    for result in stats['results']:
                        if not result.success and not result.skipped:
                            st.error(
                                f"{result.input_path.name}: {result.error}")

            # Добавляем в историю
            try:
                from app import add_to_history
                add_to_history(
                    module="Convert 9:16",
                    action=f"Cropped {stats['success']} videos",
                    details={
                        'total': stats['total'],
                        'success': stats['success'],
                        'gpu_used': use_gpu
                    }
                )
            except ImportError:
                pass

        except Exception as e:
            st.error(f"❌ Ошибка обработки: {str(e)}")
            import traceback
            with st.expander("Подробности ошибки"):
                st.code(traceback.format_exc())

        finally:
            # Очистка временных файлов
            if mode == "Одно видео" and temp_dir.exists():
                import shutil
                try:
                    shutil.rmtree(temp_dir)
                except Exception as e:
                    st.warning(f"Не удалось очистить временные файлы: {e}")


if __name__ == "__main__":
    main()
