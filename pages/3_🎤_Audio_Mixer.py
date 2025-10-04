"""
Страница модуля Audio Mixer - добавление аудио к фрагменту видео
"""

from modules.video_audio_mixer import VideoAudioMixer, AudioSettings, VideoConfig
import streamlit as st
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent / 'modules'))


st.set_page_config(page_title="Audio Mixer", page_icon="🎤", layout="wide")


def main():
    st.title("🎤 Audio Mixer")
    st.markdown("Добавьте аудио к случайному или заданному фрагменту видео")

    st.markdown("---")

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("📁 Загрузка файлов")

        # Видео
        video_source = st.radio(
            "Источник видео:",
            ["Загрузить файл", "Выбрать из папки"],
            horizontal=True,
            key='video_source_mixer'
        )

        if video_source == "Загрузить файл":
            video_file = st.file_uploader(
                "Выберите видео файл",
                type=['mp4', 'mov', 'avi', 'mkv'],
                key='video_mixer'
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
                        key='select_video_mixer'
                    )
                else:
                    st.warning("Нет видео файлов в папке downloads")
                    video_file = None
            else:
                st.warning("Папка downloads не найдена")
                video_file = None

        # Аудио
        audio_source = st.radio(
            "Источник аудио:",
            ["Загрузить файл", "Выбрать из папки"],
            horizontal=True,
            key='audio_source_mixer'
        )

        if audio_source == "Загрузить файл":
            audio_file = st.file_uploader(
                "Выберите аудио файл",
                type=['mp3', 'wav', 'aac', 'm4a', 'flac'],
                key='audio_mixer'
            )
        else:
            music_dir = Path('assets/music')
            if music_dir.exists():
                audio_files = list(music_dir.glob('*.mp3')) + \
                    list(music_dir.glob('*.wav'))
                if audio_files:
                    audio_file = st.selectbox(
                        "Выберите аудио:",
                        options=audio_files,
                        format_func=lambda x: x.name,
                        key='select_audio_mixer'
                    )
                else:
                    st.warning("Нет аудио файлов в папке music")
                    audio_file = None
            else:
                st.warning("Папка music не найдена")
                audio_file = None

    with col2:
        st.subheader("⚙️ Настройки времени")

        # Режим выбора времени
        time_mode = st.radio(
            "Режим выбора времени:",
            ["Случайное", "Конкретное время", "Диапазон"],
            horizontal=True
        )

        specific_start_time = None
        min_start_time = 5.0
        max_start_time = None
        random_seed = None

        if time_mode == "Случайное":
            min_start_time = st.number_input(
                "Минимальное время начала (сек)",
                min_value=0.0,
                value=5.0,
                step=1.0
            )

            use_seed = st.checkbox("Использовать seed (воспроизводимость)")
            if use_seed:
                random_seed = st.number_input(
                    "Random seed",
                    min_value=0,
                    value=42,
                    step=1
                )

        elif time_mode == "Конкретное время":
            specific_start_time = st.number_input(
                "Время начала (сек)",
                min_value=0.0,
                value=10.0,
                step=0.5
            )

        else:  # Диапазон
            col_min, col_max = st.columns(2)
            with col_min:
                min_start_time = st.number_input(
                    "Мин. время (сек)",
                    min_value=0.0,
                    value=5.0,
                    step=1.0,
                    key='min_time'
                )
            with col_max:
                max_start_time = st.number_input(
                    "Макс. время (сек)",
                    min_value=0.0,
                    value=30.0,
                    step=1.0,
                    key='max_time'
                )

        st.markdown("---")

        st.subheader("🔊 Настройки аудио")

        audio_volume = st.slider(
            "Громкость добавляемого аудио",
            min_value=0.0,
            max_value=2.0,
            value=1.0,
            step=0.05
        )

        original_volume = st.slider(
            "Громкость оригинального аудио",
            min_value=0.0,
            max_value=2.0,
            value=0.0,
            step=0.05,
            help="0.0 = отключить оригинальное аудио"
        )

        col_fade1, col_fade2 = st.columns(2)
        with col_fade1:
            fade_in = st.number_input(
                "Fade-in (сек)",
                min_value=0.0,
                max_value=10.0,
                value=0.0,
                step=0.5
            )
        with col_fade2:
            fade_out = st.number_input(
                "Fade-out (сек)",
                min_value=0.0,
                max_value=10.0,
                value=0.0,
                step=0.5
            )

        st.markdown("---")

        with st.expander("🎬 Настройки качества видео"):
            crf = st.slider(
                "CRF (качество)",
                min_value=0,
                max_value=51,
                value=18,
                key='crf_mixer'
            )

            preset = st.selectbox(
                "Preset скорости",
                options=['ultrafast', 'superfast', 'veryfast', 'faster',
                         'fast', 'medium', 'slow', 'slower', 'veryslow'],
                index=5,
                key='preset_mixer'
            )

            video_bitrate = st.text_input(
                "Video bitrate", value="8000k", key='vb_mixer')
            audio_bitrate = st.text_input(
                "Audio bitrate", value="320k", key='ab_mixer')

    st.markdown("---")

    # Кнопка обработки
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        process_button = st.button(
            "🚀 Добавить аудио к видео",
            type="primary",
            use_container_width=True,
            disabled=not (video_file and audio_file)
        )

    # Обработка
    if process_button and video_file and audio_file:
        temp_dir = Path('assets/temp')
        temp_dir.mkdir(parents=True, exist_ok=True)

        # Сохранение загруженных файлов
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
        output_dir = Path('assets/output')
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{video_path.stem}_mixed.mp4"

        # Создаём конфигурации
        audio_settings = AudioSettings(
            min_start_time=min_start_time,
            max_start_time=max_start_time,
            specific_start_time=specific_start_time,
            audio_volume=audio_volume,
            original_volume=original_volume,
            fade_in_duration=fade_in,
            fade_out_duration=fade_out,
            random_seed=random_seed
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

            mixer = VideoAudioMixer(
                audio_settings=audio_settings,
                video_config=video_config
            )

            progress_bar.progress(30)
            status_text.text("✂️ Вырезаю фрагмент и добавляю аудио...")

            result = mixer.process(
                video_path=video_path,
                audio_path=audio_path,
                output_path=output_path,
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
                module="Audio Mixer",
                action="Mixed audio with video fragment",
                details={
                    'video': video_path.name,
                    'audio': audio_path.name,
                    'output': output_path.name,
                    'time_mode': time_mode,
                    'audio_volume': audio_volume
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
