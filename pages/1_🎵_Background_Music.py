"""
Страница модуля добавления фоновой музыки
"""

from modules.background_music import add_background_music, AudioSettings, VideoConfig
import streamlit as st
from pathlib import Path
import sys
import time

# Добавляем путь к модулям
sys.path.append(str(Path(__file__).parent.parent / 'modules'))


st.set_page_config(page_title="Background Music", page_icon="🎵", layout="wide")


def main():
    st.title("🎵 Добавление фоновой музыки")
    st.markdown(
        "Добавьте фоновую музыку к вашему видео с настройкой громкости и эффектами")

    st.markdown("---")

    # Два столбца: загрузка файлов и настройки
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("📁 Загрузка файлов")

        # Выбор источника видео
        video_source = st.radio(
            "Источник видео:",
            ["Загрузить файл", "Выбрать из папки"],
            horizontal=True
        )

        if video_source == "Загрузить файл":
            video_file = st.file_uploader(
                "Выберите видео файл",
                type=['mp4', 'mov', 'avi', 'mkv'],
                key='video_upload'
            )
        else:
            downloads_dir = Path('assets/transcripted_videos')
            if downloads_dir.exists():
                video_files = list(downloads_dir.glob('*.mp4')) + \
                    list(downloads_dir.glob('*.mov'))
                if video_files:
                    selected_video = st.selectbox(
                        "Выберите видео:",
                        options=video_files,
                        format_func=lambda x: x.name
                    )
                    video_file = selected_video
                else:
                    st.warning("Нет видео файлов в папке downloads")
                    video_file = None
            else:
                st.warning("Папка downloads не найдена")
                video_file = None

        # Выбор источника музыки
        audio_source = st.radio(
            "Источник музыки:",
            ["Загрузить файл", "Выбрать из папки"],
            horizontal=True
        )

        if audio_source == "Загрузить файл":
            audio_file = st.file_uploader(
                "Выберите аудио файл",
                type=['mp3', 'wav', 'aac', 'm4a', 'flac'],
                key='audio_upload'
            )
        else:
            music_dir = Path('assets/music')
            if music_dir.exists():
                audio_files = list(music_dir.glob('*.mp3')) + \
                    list(music_dir.glob('*.wav'))
                if audio_files:
                    selected_audio = st.selectbox(
                        "Выберите музыку:",
                        options=audio_files,
                        format_func=lambda x: x.name
                    )
                    audio_file = selected_audio
                else:
                    st.warning("Нет аудио файлов в папке music")
                    audio_file = None
            else:
                st.warning("Папка music не найдена")
                audio_file = None

    with col2:
        st.subheader("⚙️ Настройки")

        # Громкость
        music_volume = st.slider(
            "Громкость музыки",
            min_value=0.0,
            max_value=2.0,
            value=0.1,
            step=0.05,
            help="0.0 = беззвучно, 1.0 = оригинал, >1.0 = усиление"
        )

        voice_volume = st.slider(
            "Громкость голоса",
            min_value=0.0,
            max_value=2.0,
            value=1.0,
            step=0.05
        )

        # Дополнительные опции
        loop_music = st.checkbox("Зациклить музыку", value=True)

        fade_in = st.number_input(
            "Fade-in (сек)",
            min_value=0.0,
            max_value=10.0,
            value=0.0,
            step=0.5
        )

        fade_out = st.number_input(
            "Fade-out (сек)",
            min_value=0.0,
            max_value=10.0,
            value=0.0,
            step=0.5
        )

        st.markdown("---")

        # Качество видео
        with st.expander("🎬 Настройки качества"):
            crf = st.slider(
                "CRF (качество)",
                min_value=0,
                max_value=51,
                value=18,
                help="Меньше = лучше качество (18 рекомендуется)"
            )

            preset = st.selectbox(
                "Preset скорости",
                options=['ultrafast', 'superfast', 'veryfast', 'faster',
                         'fast', 'medium', 'slow', 'slower', 'veryslow'],
                index=5
            )

            video_bitrate = st.text_input("Video bitrate", value="8000k")
            audio_bitrate = st.text_input("Audio bitrate", value="320k")

    st.markdown("---")

    # Кнопка обработки
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        process_button = st.button(
            "🚀 Обработать видео",
            type="primary",
            use_container_width=True,
            disabled=not (video_file and audio_file)
        )

    # Обработка
    if process_button and video_file and audio_file:
        # Сохраняем загруженные файлы во временную папку
        temp_dir = Path('assets/temp')
        temp_dir.mkdir(parents=True, exist_ok=True)

        if video_source == "Загрузить файл":
            video_path = temp_dir / video_file.name
            with open(video_path, 'wb') as f:
                f.write(video_file.read())
        else:
            video_path = video_file

        if audio_source == "Загрузить файл":
            audio_path = temp_dir / audio_file.name
            with open(audio_path, 'wb') as f:
                f.write(audio_file.read())
        else:
            audio_path = audio_file

        # Путь вывода
        output_dir = Path('assets/ready_videos')
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{video_path.stem}_with_music.mp4"

        # Создаём конфигурации
        audio_settings = AudioSettings(
            music_volume=music_volume,
            voice_volume=voice_volume,
            loop_music=loop_music,
            fade_in_duration=fade_in,
            fade_out_duration=fade_out
        )

        video_config = VideoConfig(
            crf=crf,
            preset=preset,
            video_bitrate=video_bitrate,
            audio_bitrate=audio_bitrate
        )

        # Progress bar
        progress_bar = st.progress(0)
        status_text = st.empty()

        try:
            status_text.text("🎬 Начинаю обработку...")
            progress_bar.progress(10)

            # Вызываем функцию обработки
            result = add_background_music(
                video_path=str(video_path),
                music_path=str(audio_path),
                output_path=str(output_path),
                audio_settings=audio_settings,
                video_config=video_config,
                force_overwrite=True
            )

            progress_bar.progress(100)
            status_text.text("✅ Обработка завершена!")

            # Показываем результат
            st.success(f"Видео сохранено: {output_path.name}")

            # Кнопка скачивания
            with open(output_path, 'rb') as f:
                st.download_button(
                    label="📥 Скачать видео",
                    data=f,
                    file_name=output_path.name,
                    mime="video/mp4",
                    use_container_width=True
                )

            # Превью
            st.video(str(output_path))

            # Добавляем в историю
            from app import add_to_history
            add_to_history(
                module="Background Music",
                action="Added background music",
                details={
                    'video': video_path.name,
                    'audio': audio_path.name,
                    'output': output_path.name,
                    'music_volume': music_volume,
                    'voice_volume': voice_volume
                }
            )

        except Exception as e:
            st.error(f"❌ Ошибка обработки: {str(e)}")
            st.exception(e)

        finally:
            # Очистка временных файлов
            if not st.session_state.get('keep_temp_files', False):
                if video_source == "Загрузить файл" and video_path.exists():
                    video_path.unlink()
                if audio_source == "Загрузить файл" and audio_path.exists():
                    audio_path.unlink()


if __name__ == "__main__":
    main()
