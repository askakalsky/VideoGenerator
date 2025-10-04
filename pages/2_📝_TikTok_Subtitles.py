"""
Страница модуля создания субтитров TikTok
"""

from modules.tiktok_subs import TikTokSubtitles, WhisperConfig, SubtitleStyle, VideoConfig
import streamlit as st
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent / 'modules'))


st.set_page_config(page_title="TikTok Subtitles", page_icon="📝", layout="wide")


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
            downloads_dir = Path('assets/downloads')
            if downloads_dir.exists():
                video_files = list(downloads_dir.glob('*.mp4')) + \
                    list(downloads_dir.glob('*.mov'))
                if video_files:
                    video_file = st.selectbox(
                        "Выберите видео:",
                        options=video_files,
                        format_func=lambda x: x.name,
                        key='select_video_subs'
                    )
                else:
                    st.warning("Нет видео в папке")
                    video_file = None
            else:
                st.warning("Папка не найдена")
                video_file = None

        st.markdown("---")

        st.subheader("🎤 Whisper настройки")

        model = st.selectbox(
            "Модель Whisper",
            options=['tiny', 'base', 'small',
                     'medium', 'large-v2', 'large-v3'],
            index=2,
            help="small - оптимальный баланс скорости и качества"
        )

        language = st.selectbox(
            "Язык",
            options=[None, 'ru', 'en', 'es', 'fr', 'de', 'it', 'pt'],
            format_func=lambda x: 'Авто' if x is None else x,
            help="Оставьте None для автоопределения"
        )

        device = st.selectbox(
            "Устройство",
            options=[None, 'cpu', 'cuda'],
            format_func=lambda x: 'Авто' if x is None else x
        )

        vad = st.checkbox("Использовать VAD", value=True)

    with col2:
        st.subheader("🎨 Стиль субтитров")

        col_green, col_white = st.columns(2)

        with col_green:
            highlight_color = st.color_picker(
                "Цвет подсветки",
                value="#00FF6A"
            )

        with col_white:
            normal_color = st.color_picker(
                "Цвет текста",
                value="#FFFFFF"
            )

        font_name = st.text_input("Шрифт", value="Arial")

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
            index=2
        )

        st.markdown("---")

        with st.expander("🎬 Настройки видео"):
            crf = st.slider("CRF", 0, 51, 18, key='crf_subs')
            preset = st.selectbox(
                "Preset",
                ['ultrafast', 'fast', 'medium', 'slow', 'veryslow'],
                index=2,
                key='preset_subs'
            )

    st.markdown("---")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        process_button = st.button(
            "🚀 Создать субтитры",
            type="primary",
            use_container_width=True,
            disabled=not video_file
        )

    if process_button and video_file:
        temp_dir = Path('assets/temp')
        temp_dir.mkdir(parents=True, exist_ok=True)

        if video_source == "Загрузить файл":
            video_path = temp_dir / video_file.name
            with open(video_path, 'wb') as f:
                f.write(video_file.read())
        else:
            video_path = video_file

        output_dir = Path('assets/output')
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{video_path.stem}_subtitles.mp4"

        # Конфигурации
        whisper_config = WhisperConfig(
            model=model,
            language=language,
            device=device,
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
            preset=preset
        )

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

            st.success(f"Видео с субтитрами: {output_path.name}")

            with open(output_path, 'rb') as f:
                st.download_button(
                    "📥 Скачать видео",
                    data=f,
                    file_name=output_path.name,
                    mime="video/mp4"
                )

            st.video(str(output_path))

            from app import add_to_history
            add_to_history(
                "TikTok Subtitles",
                "Created subtitles",
                {'video': video_path.name, 'model': model}
            )

        except Exception as e:
            st.error(f"❌ Ошибка: {str(e)}")
            st.exception(e)


if __name__ == "__main__":
    main()
