"""
Страница модуля создания субтитров TikTok с поддержкой GPU-ускорения
"""

from modules.tiktok_subs import (
    TikTokSubtitles, WhisperConfig, SubtitleStyle, VideoConfig,
    detect_gpu_capabilities, get_recommended_hardware
)
import streamlit as st
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent / 'modules'))

st.set_page_config(page_title="TikTok Subtitles", page_icon="📝", layout="wide")

# ============================================================================
# КОНСТАНТЫ
# ============================================================================

# GPU информация (кешируется)
GPU_CAPABILITIES = None


def get_gpu_info():
    """Кеширует информацию о GPU"""
    global GPU_CAPABILITIES
    if GPU_CAPABILITIES is None:
        GPU_CAPABILITIES = {
            'available': detect_gpu_capabilities(),
            'recommended': get_recommended_hardware()
        }
    return GPU_CAPABILITIES


# Пресеты качества с GPU/CPU вариантами
QUALITY_PRESETS = {
    '🚀 GPU Ультра': {'crf': 15, 'preset': 'hq', 'bitrate': '12000k', 'hardware': True},
    '⚡ GPU Быстро': {'crf': 20, 'preset': 'fast', 'bitrate': '8000k', 'hardware': True},
    '💎 CPU Максимум': {'crf': 15, 'preset': 'slow', 'bitrate': '12000k', 'hardware': False},
    '🎯 CPU Баланс': {'crf': 18, 'preset': 'medium', 'bitrate': '8000k', 'hardware': False},
    '⏱️ CPU Быстро': {'crf': 23, 'preset': 'fast', 'bitrate': '6000k', 'hardware': False},
}

# Шрифты с поддержкой кириллицы
FONTS = [
    'Arial',
    'Arial Black',
    'Calibri',
    'Verdana',
    'Tahoma',
    'Trebuchet MS',
    'Georgia',
    'Times New Roman',
    'Impact',
    'Comic Sans MS',
    'Courier New',
    'Segoe UI',
    'Segoe UI Black',
    'Segoe UI Semibold',
    'Century Gothic',
    'Orchidea Pro Medium Italic',
    'Montserrat',
    'Roboto',
    'Open Sans',
    'Oswald',
    'PT Sans',
    'Bebas Neue'
]


# ============================================================================
# ГЛАВНАЯ ФУНКЦИЯ
# ============================================================================

def main():
    st.title("📝 Субтитры в стиле TikTok")
    st.markdown("Создайте субтитры с анимированной подсветкой слов")

    st.markdown("---")

    # Основной layout: параметры слева, превью справа
    main_col, preview_col = st.columns([2, 1])

    with main_col:
        # ====================================================================
        # ВЫБОР ВИДЕО
        # ====================================================================
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

        # ====================================================================
        # ПАРАМЕТРЫ WHISPER И СТИЛЬ
        # ====================================================================
        param_col1, param_col2 = st.columns(2)

        with param_col1:
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

        with param_col2:
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

            font_name = st.selectbox(
                "Шрифт",
                options=FONTS,
                index=0,  # Arial по умолчанию
                help="Выберите шрифт из списка (все поддерживают кириллицу)"
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
                options=['bottom', 'center', 'top'],
                index=0,  # bottom
                format_func=lambda x: {
                    'top': 'Сверху ⬆️', 'center': 'По центру ↔️', 'bottom': 'Снизу ⬇️'}[x]
            )

        st.markdown("---")

        # ====================================================================
        # НАСТРОЙКИ КАЧЕСТВА И GPU
        # ====================================================================
        with st.expander("🎬 Настройки качества видео", expanded=True):
            # Информация о GPU
            gpu_info = get_gpu_info()
            has_gpu = any(gpu_info['available'].values())

            if has_gpu:
                gpu_name = gpu_info['recommended'].upper()
                st.success(f"✅ GPU обнаружен: {gpu_name}")

                # Информация о типах GPU
                gpu_types = []
                if gpu_info['available']['nvenc']:
                    gpu_types.append('NVIDIA NVENC')
                if gpu_info['available']['qsv']:
                    gpu_types.append('Intel QSV')
                if gpu_info['available']['amf']:
                    gpu_types.append('AMD AMF')
                if gpu_info['available']['videotoolbox']:
                    gpu_types.append('Apple VideoToolbox')

                st.info(f"💡 Доступно: {', '.join(gpu_types)}\n\n"
                        f"⚡ GPU рендеринг в **5-10 раз быстрее** CPU!")
            else:
                st.warning(
                    "⚠️ GPU не обнаружен, будет использоваться CPU (медленнее)")
                st.info("ℹ️ Для GPU-ускорения требуется:\n"
                        "- NVIDIA GPU (GTX 600+/RTX)\n"
                        "- Intel GPU (HD Graphics 2000+)\n"
                        "- AMD GPU (RX 400+)\n"
                        "- Apple M1/M2/M3")

            st.markdown("---")

            # Выбор режима кодирования
            use_hardware = st.checkbox(
                "⚡ Использовать GPU ускорение",
                value=has_gpu,
                disabled=not has_gpu,
                help="Значительно ускоряет рендеринг, но требует поддержку GPU"
            )

            # Фильтруем пресеты
            if has_gpu:
                available_presets = QUALITY_PRESETS
            else:
                # Только CPU пресеты если нет GPU
                available_presets = {
                    k: v for k, v in QUALITY_PRESETS.items()
                    if not v.get('hardware', False)
                }

            # Автовыбор пресета по умолчанию
            if use_hardware and has_gpu:
                default_preset = '🚀 GPU Ультра'
            else:
                default_preset = '🎯 CPU Баланс'

            preset_keys = list(available_presets.keys())
            default_index = preset_keys.index(
                default_preset) if default_preset in preset_keys else 0

            quality_preset = st.selectbox(
                "Пресет качества",
                options=preset_keys,
                index=default_index,
                help="GPU: быстрее, CPU: медленнее но универсальнее"
            )

            preset_config = QUALITY_PRESETS[quality_preset]
            crf_default = preset_config['crf']
            preset_default = preset_config['preset']
            bitrate_default = preset_config['bitrate']
            use_hw = preset_config.get('hardware', False)

            # Информация о настройках
            if use_hw and has_gpu:
                st.info(
                    f"📊 **GPU режим** | CRF={crf_default} | Preset={preset_default} | Bitrate={bitrate_default}")
            else:
                st.info(
                    f"📊 **CPU режим** | CRF={crf_default} | Preset={preset_default} | Bitrate={bitrate_default}")

            # ================================================================
            # РАСШИРЕННЫЕ НАСТРОЙКИ
            # ================================================================
            show_advanced = st.checkbox(
                "⚙️ Показать расширенные настройки", value=False)

            if show_advanced:
                st.markdown("---")

                if use_hardware and has_gpu:
                    # GPU параметры
                    st.markdown("**🚀 GPU Настройки**")

                    # Выбор типа GPU
                    available_hw_types = []
                    hw_type_names = {
                        'nvenc': 'NVIDIA NVENC',
                        'qsv': 'Intel QuickSync',
                        'amf': 'AMD AMF',
                        'videotoolbox': 'Apple VideoToolbox'
                    }

                    for hw_type, available in gpu_info['available'].items():
                        if available:
                            available_hw_types.append(hw_type)

                    if len(available_hw_types) > 1:
                        hardware_type = st.selectbox(
                            "Тип GPU",
                            options=available_hw_types,
                            index=available_hw_types.index(
                                gpu_info['recommended']) if gpu_info['recommended'] in available_hw_types else 0,
                            format_func=lambda x: hw_type_names.get(
                                x, x.upper()),
                            help="Выберите тип GPU-ускорения"
                        )
                    else:
                        hardware_type = available_hw_types[0] if available_hw_types else 'nvenc'
                        st.info(
                            f"Тип GPU: **{hw_type_names.get(hardware_type, hardware_type.upper())}**")

                    # Пресеты для выбранного GPU
                    if hardware_type == 'nvenc':
                        preset_options = ['slow', 'medium', 'fast',
                                          'hp', 'hq', 'bd', 'll', 'llhq', 'llhp']
                        preset_help = "**hq** = лучшее качество, **fast** = быстрее, **ll** = low latency"
                        default_preset_idx = preset_options.index(
                            preset_default) if preset_default in preset_options else 1
                    elif hardware_type == 'qsv':
                        preset_options = [
                            'veryslow', 'slower', 'slow', 'medium', 'fast', 'faster', 'veryfast']
                        preset_help = "Стандартные пресеты Intel QSV"
                        default_preset_idx = preset_options.index(
                            preset_default) if preset_default in preset_options else 3
                    elif hardware_type == 'amf':
                        preset_options = ['slow', 'balanced', 'fast']
                        preset_help = "AMD AMF пресеты качества"
                        default_preset_idx = preset_options.index(
                            preset_default) if preset_default in preset_options else 1
                    else:
                        preset_options = ['slow', 'medium', 'fast']
                        preset_help = "VideoToolbox пресеты"
                        default_preset_idx = 1

                    preset = st.selectbox(
                        "GPU Preset",
                        options=preset_options,
                        index=default_preset_idx,
                        help=preset_help
                    )
                else:
                    # CPU параметры
                    st.markdown("**🖥️ CPU Настройки**")
                    hardware_type = 'nvenc'  # Не используется, но нужно для конфига

                    preset_options = ['ultrafast', 'superfast', 'veryfast', 'faster',
                                      'fast', 'medium', 'slow', 'slower', 'veryslow']
                    preset = st.selectbox(
                        "CPU Preset",
                        options=preset_options,
                        index=preset_options.index(
                            preset_default) if preset_default in preset_options else 5,
                        help="**veryslow** = лучшее сжатие (медленно), **ultrafast** = быстро (больше размер)"
                    )

                # Общие параметры качества
                col_crf, col_bitrate = st.columns(2)

                with col_crf:
                    crf = st.slider(
                        "CRF (качество)",
                        0, 51, crf_default,
                        help="Меньше = лучше качество, больше файл\n\n"
                             "15-18 = отличное, 20-23 = хорошее, 28+ = среднее"
                    )

                with col_bitrate:
                    video_bitrate = st.text_input(
                        "Битрейт видео",
                        value=bitrate_default,
                        help="Примеры: 8000k, 10M, 15000k"
                    )

                audio_bitrate = st.select_slider(
                    "Битрейт аудио",
                    options=['128k', '192k', '256k', '320k'],
                    value='320k',
                    help="320k = максимальное качество"
                )
            else:
                # Используем значения из пресета
                crf = crf_default
                preset = preset_default
                video_bitrate = bitrate_default
                audio_bitrate = '320k'
                hardware_type = gpu_info['recommended'] if (
                    use_hardware and has_gpu) else 'nvenc'

        st.markdown("---")

        # ====================================================================
        # КНОПКА ЗАПУСКА
        # ====================================================================
        process_button = st.button(
            "🚀 Создать субтитры",
            type="primary",
            use_container_width=True,
            disabled=not video_file
        )

    # ========================================================================
    # ПРАВАЯ КОЛОНКА - ПРЕВЬЮ
    # ========================================================================
    with preview_col:
        st.subheader("📱 Превью")

        # Placeholder для превью
        preview_placeholder = st.empty()

        # CSS для фиксированной ширины видео
        st.markdown("""
        <style>
        /* Стиль для видео превью */
        [data-testid="stVideo"] {
            max-width: 280px !important;
            margin: 0 auto;
        }
        [data-testid="stVideo"] video {
            width: 100% !important;
            max-width: 280px !important;
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        }
        </style>
        """, unsafe_allow_html=True)

        # Показываем исходное видео если выбрано
        if video_file:
            with preview_placeholder.container():
                st.caption("🎬 Исходное видео:")
                try:
                    if video_source == "Загрузить файл":
                        st.video(video_file)
                    else:
                        st.video(str(video_file))
                except Exception as e:
                    st.error(f"Ошибка загрузки превью: {e}")
        else:
            with preview_placeholder.container():
                st.info("👈 Выберите видео для начала работы")

    # ========================================================================
    # ОБРАБОТКА
    # ========================================================================
    if process_button and video_file:
        # Подготовка директорий
        temp_dir = Path('assets/temp')
        output_dir = Path('assets/transcripted_videos')
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

        # ====================================================================
        # СОЗДАНИЕ КОНФИГУРАЦИЙ
        # ====================================================================
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
            use_hardware=use_hardware and has_gpu,
            hardware_type=hardware_type if (
                use_hardware and has_gpu) else 'nvenc',
            crf=crf,
            preset=preset,
            video_bitrate=video_bitrate,
            audio_bitrate=audio_bitrate if show_advanced else '320k'
        )

        # ====================================================================
        # UI ДЛЯ ПРОГРЕССА
        # ====================================================================
        with main_col:
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

            # ================================================================
            # УСПЕШНОЕ ЗАВЕРШЕНИЕ
            # ================================================================
            encoding_type = "GPU" if (use_hardware and has_gpu) else "CPU"
            st.success(
                f"✅ Видео с субтитрами создано ({encoding_type} кодирование): {output_path.name}")

            # Информация о файле
            if output_path.exists():
                output_size_mb = output_path.stat().st_size / (1024 * 1024)

                info_text = f"📊 Размер: {output_size_mb:.2f} MB | "
                info_text += f"Качество: {quality_preset} | "
                info_text += f"Кодирование: {encoding_type}"

                if use_hardware and has_gpu:
                    info_text += f" ({hardware_type.upper()})"

                st.info(info_text)

                # Кнопки скачивания
                col_dl1, col_dl2 = st.columns(2)

                with col_dl1:
                    with open(output_path, 'rb') as f:
                        st.download_button(
                            "📥 Скачать видео",
                            data=f,
                            file_name=output_path.name,
                            mime="video/mp4",
                            use_container_width=True
                        )

                with col_dl2:
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

                # Обновляем превью справа
                with preview_placeholder.container():
                    st.caption("✅ Готовое видео с субтитрами:")
                    st.video(str(output_path))

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
                        'quality': quality_preset,
                        'font': font_name,
                        'encoding': f"{encoding_type} ({hardware_type if use_hardware else 'libx264'})"
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
