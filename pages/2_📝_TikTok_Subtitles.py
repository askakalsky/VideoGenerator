"""
Страница модуля создания субтитров TikTok
"""

from modules.tiktok_subs import TikTokSubtitles, WhisperConfig, SubtitleStyle, VideoConfig
import streamlit as st
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent / 'modules'))


st.set_page_config(page_title="TikTok Subtitles", page_icon="📝", layout="wide")

# Константы
PRESET_OPTIONS = ['ultrafast', 'superfast', 'veryfast',
                  'faster', 'fast', 'medium', 'slow', 'slower', 'veryslow']

QUALITY_PRESETS = {
    'Максимальное': {'crf': 15, 'preset': 'veryslow', 'bitrate': '12000k'},
    'Высокое': {'crf': 18, 'preset': 'slow', 'bitrate': '10000k'},
    'Среднее': {'crf': 20, 'preset': 'medium', 'bitrate': '8000k'},
    'Быстрое': {'crf': 23, 'preset': 'fast', 'bitrate': '6000k'}
}


def main():
    st.title("📝 Субтитры в стиле TikTok")
    st.markdown("Создайте субтитры с анимированной подсветкой слов")

    st.markdown("---")

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("📁 Видео файл")

        video_source = st.radio(
            "Источник:",
            ["Загрузить файл", "Выбрать из папки"],
            horizontal=True,
            key='video_source_subs'
        )

        if video_source == "Загрузить файл":
            video_file = st.file_uploader(
                "Выберите видео",
                type=['mp4', 'mov', 'avi', 'mkv'],
                key='video_subs'
            )
        else:
            mixed_videos_dir = Path('assets/mixed_videos')
            if mixed_videos_dir.exists():
                video_files = list(mixed_videos_dir.glob('*.mp4')) + \
                    list(mixed_videos_dir.glob('*.mov'))
                if video_files:
                    video_file = st.selectbox(
                        "Выберите видео:",
                        options=video_files,
                        format_func=lambda x: x.name,
                        key='select_video_subs'
                    )
                else:
                    st.warning("⚠️ Нет видео в папке assets/mixed_videos")
                    video_file = None
            else:
                st.warning("⚠️ Папка assets/mixed_videos не найдена")
                video_file = None

        st.markdown("---")

        st.subheader("🎤 Whisper настройки")

        model = st.selectbox(
            "Модель Whisper",
            options=['tiny', 'base', 'small',
                     'medium', 'large-v2', 'large-v3'],
            index=3,  # medium
            help="medium - оптимальный баланс скорости и качества для русского языка"
        )

        language = st.selectbox(
            "Язык",
            options=['ru', 'en', 'es', 'fr', 'de', 'it', 'pt', 'auto'],
            index=0,  # ru по умолчанию
            format_func=lambda x: 'Авто' if x == 'auto' else x.upper(),
            help="Выберите язык аудио или 'Авто' для автоопределения"
        )

        device = st.selectbox(
            "Устройство",
            options=['cuda', 'cpu', 'auto'],
            index=0,  # cuda по умолчанию
            format_func=lambda x: 'Авто' if x == 'auto' else x.upper(),
            help="CUDA (GPU) - быстрее в ~10 раз, CPU - медленнее но стабильнее"
        )

        vad = st.checkbox(
            "Использовать VAD",
            value=True,
            help="Voice Activity Detection - улучшает качество транскрипции"
        )

    with col2:
        st.subheader("🎨 Стиль субтитров")

        col_green, col_white = st.columns(2)

        with col_green:
            highlight_color = st.color_picker(
                "Цвет подсветки",
                value="#00FF6A",
                help="Цвет текущего слова"
            )

        with col_white:
            normal_color = st.color_picker(
                "Цвет текста",
                value="#FFFFFF",
                help="Цвет остальных слов"
            )

        font_name = st.text_input(
            "Шрифт",
            value="Arial",
            help="Название шрифта (должен быть установлен в системе)"
        )

        font_scale = st.slider(
            "Размер шрифта (% от высоты)",
            min_value=1,
            max_value=20,
            value=7,
            help="Процент от высоты видео"
        ) / 100

        bold = st.checkbox("Жирный шрифт", value=True)

        position = st.selectbox(
            "Позиция по вертикали",
            options=['top', 'center', 'bottom'],
            index=2,  # bottom
            format_func=lambda x: {'top': 'Сверху',
                                   'center': 'По центру', 'bottom': 'Снизу'}[x]
        )

        st.markdown("---")

        with st.expander("🎬 Настройки качества видео"):
            quality_preset = st.selectbox(
                "Пресет качества",
                options=list(QUALITY_PRESETS.keys()),
                index=0,  # Максимальное по умолчанию
                help="Максимальное = медленно но отличное качество\nБыстрое = быстро но ниже качество"
            )

            # Получаем настройки из выбранного пресета
            preset_config = QUALITY_PRESETS[quality_preset]
            crf_default = preset_config['crf']
            preset_default = preset_config['preset']
            bitrate_default = preset_config['bitrate']

            st.info(
                f"📊 CRF={crf_default} | Preset={preset_default} | Bitrate={bitrate_default}")

            # Расширенные настройки
            show_advanced = st.checkbox(
                "⚙️ Показать расширенные настройки", value=False)

            if show_advanced:
                crf = st.slider(
                    "CRF (0-51, меньше=лучше)",
                    0, 51, crf_default,
                    key='crf_subs',
                    help="0=lossless, 15-18=отличное, 20-23=хорошее, 28+=среднее"
                )
                preset = st.selectbox(
                    "Preset скорости",
                    options=PRESET_OPTIONS,
                    index=PRESET_OPTIONS.index(preset_default),
                    key='preset_subs',
                    help="veryslow=лучшее качество (медленно), ultrafast=худшее (быстро)"
                )
                video_bitrate = st.text_input(
                    "Битрейт видео",
                    value=bitrate_default,
                    key='bitrate_subs',
                    help="Примеры: 8000k, 10M, 15000k"
                )
            else:
                crf = crf_default
                preset = preset_default
                video_bitrate = bitrate_default

    st.markdown("---")

    # Кнопка запуска
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        process_button = st.button(
            "🚀 Создать субтитры",
            type="primary",
            use_container_width=True,
            disabled=not video_file
        )

    if process_button and video_file:
        # Подготовка директорий
        temp_dir = Path('assets/temp')
        output_dir = Path('assets/output')
        temp_dir.mkdir(parents=True, exist_ok=True)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Обработка видео файла
        try:
            if video_source == "Загрузить файл":
                video_path = temp_dir / video_file.name
                with open(video_path, 'wb') as f:
                    f.write(video_file.read())
            else:
                video_path = video_file

            output_path = output_dir / f"{video_path.stem}_subtitles.mp4"

        except Exception as e:
            st.error(f"❌ Ошибка при обработке файла: {str(e)}")
            return

        # Конвертируем 'auto' в None для Whisper
        final_language = None if language == 'auto' else language
        final_device = None if device == 'auto' else device

        # Конфигурации
        whisper_config = WhisperConfig(
            model=model,
            language=final_language,
            device=final_device,
            vad=vad
        )

        subtitle_style = SubtitleStyle(
            highlight_color=highlight_color,
            normal_color=normal_color,
            font_name=font_name,
            font_scale=font_scale,
            bold=bold,
            alignment=2 if position == 'bottom' else (
                5 if position == 'center' else 8)
        )

        video_config = VideoConfig(
            crf=crf,
            preset=preset,
            video_bitrate=video_bitrate,
            audio_bitrate='320k'  # Максимальное качество аудио
        )

        # UI для прогресса
        progress_bar = st.progress(0)
        status_text = st.empty()

        try:
            status_text.text("🎤 Транскрипция аудио...")
            progress_bar.progress(20)

            processor = TikTokSubtitles(
                whisper_config=whisper_config,
                subtitle_style=subtitle_style,
                video_config=video_config
            )

            progress_bar.progress(50)
            status_text.text("📝 Создание субтитров...")

            result = processor.process(
                input_video=video_path,
                output_video=output_path,
                keep_ass=True
            )

            progress_bar.progress(100)
            status_text.text("✅ Готово!")

            # Успешное завершение
            st.success(f"✅ Видео с субтитрами создано: {output_path.name}")

            # Информация о файле
            if output_path.exists():
                output_size_mb = output_path.stat().st_size / (1024 * 1024)
                st.info(
                    f"📊 Размер файла: {output_size_mb:.2f} MB | Качество: {quality_preset}")

                # Кнопка скачивания видео
                with open(output_path, 'rb') as f:
                    st.download_button(
                        "📥 Скачать видео",
                        data=f,
                        file_name=output_path.name,
                        mime="video/mp4",
                        use_container_width=True
                    )

                # Превью видео
                st.video(str(output_path))

                # Скачивание ASS файла
                ass_path = output_path.with_suffix('.ass')
                if ass_path.exists():
                    with open(ass_path, 'rb') as f:
                        st.download_button(
                            "📄 Скачать субтитры (ASS)",
                            data=f,
                            file_name=ass_path.name,
                            mime="text/plain",
                            use_container_width=True
                        )

            # Добавление в историю (безопасно)
            try:
                from app import add_to_history
                add_to_history(
                    "TikTok Subtitles",
                    "Created subtitles",
                    {
                        'video': video_path.name,
                        'model': model,
                        'language': final_language or 'auto',
                        'device': final_device or 'auto',
                        'quality': quality_preset
                    }
                )
            except ImportError:
                pass  # История не критична

        except Exception as e:
            st.error(f"❌ Ошибка при обработке: {str(e)}")
            st.exception(e)
            progress_bar.progress(0)
            status_text.text("❌ Ошибка обработки")


if __name__ == "__main__":
    main()
