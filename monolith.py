# Простой запуск (случайное видео и музыка):
# python monolith.py assets/generated_audio/my_audio.mp3
#
# С указанием имени выходного файла:
# python monolith.py assets/generated_audio/my_audio.mp3 -o cool_video.mp4
#
# С конкретными видео и музыкой:
# python monolith.py assets/generated_audio/my_audio.mp3 --video assets/stock_videos/video1.mp4 --music assets/music/track1.mp3
#
# Без сохранения ASS субтитров:
# python monolith.py assets/generated_audio/my_audio.mp3 --no-keep-ass


"""
Единый скрипт для создания финального видео с субтитрами и музыкой.
Выполняет ОДИН рендеринг с использованием GPU (NVENC).

Процесс:
1. Транскрипция аудиотекста → ASS субтитры (без рендеринга)
2. Один проход FFmpeg: вырезка видео + микс аудио + прожиг субтитров + GPU кодирование
"""

import logging
import random
import sys
import subprocess
from pathlib import Path
from typing import Optional, Union
from dataclasses import dataclass

# Импорты из существующих модулей
from modules.tiktok_subs import (
    WhisperConfig,
    SubtitleStyle,
    Transcriber,
    SubtitleGenerator,
    VideoInfo,
    check_dependencies,
    validate_file_exists
)
from moviepy import AudioFileClip

# ============================================================================
# НАСТРОЙКА ЛОГИРОВАНИЯ
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# ============================================================================
# КОНФИГУРАЦИЯ
# ============================================================================

# Директории
STOCK_VIDEOS_DIR = Path("assets/stock_videos")
AUDIO_DIR = Path("assets/generated_audio")
MUSIC_DIR = Path("assets/music")
READY_VIDEOS_DIR = Path("assets/ready_videos")

# Настройки Whisper
WHISPER_CONFIG = WhisperConfig(
    model='medium',
    language='ru',
    device='cuda',
    vad=True
)

# Стиль субтитров
SUBTITLE_STYLE = SubtitleStyle(
    highlight_color="#00FF6A",
    normal_color="#FFFFFF",
    font_name='Orchidea Pro Medium Italic',
    font_scale=0.07,
    bold=True,
    alignment=2  # bottom center
)

# Настройки аудио
AUDIO_VOLUME = 1.0          # Громкость аудиотекста
MUSIC_VOLUME = 0.08         # Громкость музыки
MIN_START_TIME = 5.0        # Мин. время начала в видео
MIN_END_OFFSET = 10.0       # Мин. отступ от конца видео

# Настройки видео (GPU - RTX 5070)
VIDEO_CODEC = 'h264_nvenc'  # NVIDIA GPU кодек
PRESET = 'p7'               # Максимальное качество (p1-p7)
CRF = 15                    # Качество (0-51, меньше=лучше)
VIDEO_BITRATE = '12000k'    # Битрейт видео
AUDIO_BITRATE = '320k'      # Битрейт аудио

# Поддерживаемые форматы
VIDEO_FORMATS = {'.mp4', '.avi', '.mov', '.mkv', '.webm'}
AUDIO_FORMATS = {'.mp3', '.wav', '.aac', '.m4a', '.flac', '.ogg'}

# ============================================================================
# УТИЛИТЫ
# ============================================================================


def select_random_file(directory: Path, extensions: set) -> Path:
    """Выбирает случайный файл из директории с заданными расширениями."""
    if not directory.exists():
        raise FileNotFoundError(f"Директория не найдена: {directory}")

    files = [f for f in directory.iterdir() if f.is_file()
             and f.suffix.lower() in extensions]

    if not files:
        raise FileNotFoundError(
            f"Не найдено файлов в {directory} с расширениями {extensions}"
        )

    selected = random.choice(files)
    logger.debug(f"Выбран файл: {selected.name}")
    return selected


def calculate_start_time(video_duration: float, audio_duration: float) -> float:
    """Вычисляет случайное время начала фрагмента в видео."""
    min_required = audio_duration + MIN_START_TIME + MIN_END_OFFSET

    if video_duration < min_required:
        raise ValueError(
            f"Видео слишком короткое ({video_duration:.1f}s). "
            f"Требуется минимум {min_required:.1f}s"
        )

    min_start = MIN_START_TIME
    max_start = video_duration - MIN_END_OFFSET - audio_duration

    if min_start > max_start:
        raise ValueError(
            "Невозможно разместить аудио в видео с заданными ограничениями")

    start_time = random.uniform(min_start, max_start)
    logger.debug(
        f"Время начала: {start_time:.2f}s (диапазон: {min_start:.1f}-{max_start:.1f})")

    return start_time


def format_time(seconds: float) -> str:
    """Форматирует секунды в MM:SS."""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes}:{secs:02d}"


# ============================================================================
# ГЛАВНАЯ ФУНКЦИЯ
# ============================================================================

def create_final_video(
    audio_text_path: Union[str, Path],
    output_name: Optional[str] = None,
    video_path: Optional[Union[str, Path]] = None,
    music_path: Optional[Union[str, Path]] = None,
    keep_ass: bool = True
) -> Path:
    """
    Создает финальное видео из аудиотекста с субтитрами и музыкой.

    Процесс:
    1. Транскрибирует аудиотекст → создает ASS субтитры
    2. Выбирает случайное видео и музыку (если не указаны)
    3. Один FFmpeg рендеринг с GPU: вырезка + аудио микс + субтитры

    Args:
        audio_text_path: Путь к аудиотексту
        output_name: Имя выходного файла (опционально)
        video_path: Конкретное видео (опционально, иначе случайное)
        music_path: Конкретная музыка (опционально, иначе случайная)
        keep_ass: Сохранить ASS файл субтитров

    Returns:
        Path: Путь к созданному видео
    """

    audio_text_path = Path(audio_text_path).resolve()

    logger.info("=" * 80)
    logger.info("🎬 СОЗДАНИЕ ФИНАЛЬНОГО ВИДЕО (ОДИН РЕНДЕРИНГ)")
    logger.info("=" * 80)

    # ========================================================================
    # 1. ПРОВЕРКА ЗАВИСИМОСТЕЙ И ПОДГОТОВКА
    # ========================================================================

    logger.info("🔍 Проверка зависимостей...")
    check_dependencies()

    # Создание выходной директории
    READY_VIDEOS_DIR.mkdir(parents=True, exist_ok=True)

    # Валидация аудиотекста
    validate_file_exists(audio_text_path, "Аудиотекст")
    logger.info(f"✅ Аудиотекст: {audio_text_path.name}")

    # ========================================================================
    # 2. ВЫБОР ФАЙЛОВ
    # ========================================================================

    logger.info("")
    logger.info("🎲 Выбор файлов...")

    # Видео
    if video_path:
        video_path = Path(video_path).resolve()
        validate_file_exists(video_path, "Видео")
        logger.info(f"   ├─ Видео (указано): {video_path.name}")
    else:
        video_path = select_random_file(STOCK_VIDEOS_DIR, VIDEO_FORMATS)
        logger.info(f"   ├─ Видео (случайное): {video_path.name}")

    # Музыка
    if music_path:
        music_path = Path(music_path).resolve()
        validate_file_exists(music_path, "Музыка")
        logger.info(f"   └─ Музыка (указана): {music_path.name}")
    else:
        music_path = select_random_file(MUSIC_DIR, AUDIO_FORMATS)
        logger.info(f"   └─ Музыка (случайная): {music_path.name}")

    # ========================================================================
    # 3. АНАЛИЗ ФАЙЛОВ
    # ========================================================================

    logger.info("")
    logger.info("📊 Анализ файлов...")

    # Информация о видео
    video_info = VideoInfo(video_path)
    logger.info(f"   ├─ Видео: {video_info.width}x{video_info.height}")
    logger.info(f"   │  ├─ Длительность: {format_time(video_info.duration)}")
    logger.info(f"   │  └─ FPS: {video_info.fps:.2f}")

    # Длительность аудиотекста
    audio_clip = AudioFileClip(str(audio_text_path))
    audio_duration = audio_clip.duration
    audio_clip.close()
    logger.info(f"   └─ Аудиотекст: {format_time(audio_duration)}")

    # Вычисление времени начала в видео
    start_time = calculate_start_time(video_info.duration, audio_duration)
    end_time = start_time + audio_duration

    logger.info("")
    logger.info(f"✂️  Фрагмент видео:")
    logger.info(f"   ├─ Начало: {format_time(start_time)}")
    logger.info(f"   ├─ Конец: {format_time(end_time)}")
    logger.info(f"   └─ Длительность: {format_time(audio_duration)}")

    # ========================================================================
    # 4. ТРАНСКРИПЦИЯ (БЕЗ РЕНДЕРИНГА)
    # ========================================================================

    logger.info("")
    logger.info("🎙️  ЭТАП 1/2: Транскрипция аудио")
    logger.info(f"   ├─ Модель: {WHISPER_CONFIG.model}")
    logger.info(f"   ├─ Язык: {WHISPER_CONFIG.language}")
    logger.info(f"   └─ Устройство: {WHISPER_CONFIG.device}")

    transcriber = Transcriber(WHISPER_CONFIG)
    transcription_result = transcriber.transcribe(audio_text_path)

    # ========================================================================
    # 5. СОЗДАНИЕ СУБТИТРОВ (БЕЗ РЕНДЕРИНГА)
    # ========================================================================

    logger.info("")
    logger.info("📝 Генерация ASS субтитров...")

    # Определение выходных путей
    if output_name:
        if not output_name.endswith('.mp4'):
            output_name += '.mp4'
        output_path = READY_VIDEOS_DIR / output_name
    else:
        output_path = READY_VIDEOS_DIR / f"{audio_text_path.stem}_final.mp4"

    ass_path = output_path.with_suffix('.ass')

    # Генерация ASS
    generator = SubtitleGenerator(
        video_width=video_info.width,
        video_height=video_info.height,
        style=SUBTITLE_STYLE
    )
    generator.generate(transcription_result, ass_path)

    logger.info(f"   └─ Сохранено: {ass_path.name}")

    # ========================================================================
    # 6. ОДИН РЕНДЕРИНГ ЧЕРЕЗ FFMPEG (GPU)
    # ========================================================================

    logger.info("")
    logger.info("🚀 ЭТАП 2/2: Рендеринг (GPU NVENC)")
    logger.info(f"   ├─ Кодек: {VIDEO_CODEC}")
    logger.info(f"   ├─ Preset: {PRESET} (максимальное качество)")
    logger.info(f"   ├─ CRF: {CRF}")
    logger.info(f"   ├─ Битрейт видео: {VIDEO_BITRATE}")
    logger.info(f"   └─ Битрейт аудио: {AUDIO_BITRATE}")

    # Построение filter_complex для FFmpeg
    ass_name = ass_path.name

    # Фильтр: микс аудио + прожиг субтитров
    filter_complex = (
        # Зацикливаем и обрезаем музыку
        f"[2:a]volume={MUSIC_VOLUME},aloop=loop=-1:size=2e+09,atrim=0:{audio_duration}[music];"
        # Настраиваем громкость голоса
        f"[1:a]volume={AUDIO_VOLUME}[voice];"
        # Микшируем голос + музыку
        f"[voice][music]amix=inputs=2:duration=first:dropout_transition=0[audio];"
        # Прожигаем субтитры
        f"[0:v]ass={ass_name}[video]"
    )

    # Команда FFmpeg
    cmd = [
        'ffmpeg', '-y',

        # Входы
        # Начало вырезки (ПЕРЕД -i для точности)
        '-ss', str(start_time),
        '-i', str(video_path),            # Видео
        '-t', str(audio_duration),        # Длительность
        '-i', str(audio_text_path),       # Аудиотекст
        '-stream_loop', '-1',             # Зацикливание музыки
        '-i', str(music_path),            # Музыка

        # Обработка
        '-filter_complex', filter_complex,
        '-map', '[video]',                # Видео с субтитрами
        '-map', '[audio]',                # Микшированное аудио

        # Кодирование видео (NVENC GPU)
        '-c:v', VIDEO_CODEC,
        '-preset', PRESET,
        '-rc', 'vbr',                     # Variable bitrate
        '-cq', str(CRF),                  # Качество
        '-b:v', VIDEO_BITRATE,
        '-maxrate', VIDEO_BITRATE,
        '-bufsize', '20M',
        '-gpu', '0',                      # GPU индекс

        # Кодирование аудио
        '-c:a', 'aac',
        '-b:a', AUDIO_BITRATE,

        # Дополнительные параметры
        '-pix_fmt', 'yuv420p',            # Совместимость
        '-movflags', '+faststart',        # Быстрый старт для веб

        # Выход
        str(output_path)
    ]

    # Запуск FFmpeg
    logger.info("")
    logger.info("⚙️  Запуск FFmpeg...")
    logger.info(f"   └─ Рабочая директория: {ass_path.parent}")

    try:
        result = subprocess.run(
            cmd,
            cwd=ass_path.parent,  # Важно для корректной работы ASS
            check=True,
            capture_output=True,
            text=True
        )

        # Проверка результата
        if not output_path.exists():
            raise RuntimeError("Выходной файл не был создан")

        output_size = output_path.stat().st_size / (1024 * 1024)  # MB

        # ====================================================================
        # УСПЕХ
        # ====================================================================

        logger.info("")
        logger.info("=" * 80)
        logger.info("✅ ВИДЕО УСПЕШНО СОЗДАНО!")
        logger.info("=" * 80)
        logger.info(f"📁 Файл: {output_path.name}")
        logger.info(f"📂 Путь: {output_path}")
        logger.info(f"💾 Размер: {output_size:.2f} MB")
        logger.info(f"⏱️  Длительность: {format_time(audio_duration)}")
        logger.info(f"📊 Разрешение: {video_info.width}x{video_info.height}")

        if keep_ass:
            logger.info(f"📄 Субтитры: {ass_path}")
        else:
            ass_path.unlink(missing_ok=True)
            logger.info("🗑️  ASS файл удален")

        logger.info("=" * 80)

        return output_path

    except subprocess.CalledProcessError as e:
        logger.error("")
        logger.error("=" * 80)
        logger.error("❌ ОШИБКА РЕНДЕРИНГА")
        logger.error("=" * 80)
        logger.error(f"Код возврата: {e.returncode}")

        if e.stderr:
            logger.error("STDERR от FFmpeg:")
            logger.error(e.stderr[-2000:])  # Последние 2000 символов

        # Удаляем поврежденный файл
        if output_path.exists():
            try:
                output_path.unlink()
                logger.info("🗑️  Удален поврежденный выходной файл")
            except Exception:
                pass

        raise RuntimeError(f"FFmpeg завершился с ошибкой: {e.returncode}")

    except Exception as e:
        logger.error(f"❌ Неожиданная ошибка: {e}", exc_info=True)
        raise


# ============================================================================
# CLI
# ============================================================================

def main():
    """Главная функция для запуска из командной строки."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Создание финального видео из аудиотекста (1 рендеринг)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  %(prog)s audio.mp3
  %(prog)s audio.mp3 -o my_video.mp4
  %(prog)s audio.mp3 --video specific_video.mp4 --music specific_music.mp3
  %(prog)s audio.mp3 --no-keep-ass

Директории (по умолчанию):
  Видео:       assets/stock_videos/
  Музыка:      assets/music/
  Результат:   assets/ready_videos/
        """
    )

    # Основные параметры
    parser.add_argument(
        'audio',
        help='Путь к аудиотексту'
    )

    parser.add_argument(
        '-o', '--output',
        help='Имя выходного файла (опционально)',
        default=None
    )

    # Опциональные входы
    parser.add_argument(
        '--video',
        help='Конкретное видео (иначе случайное)',
        default=None
    )

    parser.add_argument(
        '--music',
        help='Конкретная музыка (иначе случайная)',
        default=None
    )

    # Настройки
    parser.add_argument(
        '--no-keep-ass',
        action='store_true',
        help='Не сохранять ASS файл субтитров'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Подробный вывод'
    )

    parser.add_argument(
        '--debug',
        action='store_true',
        help='Режим отладки'
    )

    args = parser.parse_args()

    # Настройка логирования
    if args.debug:
        logger.setLevel(logging.DEBUG)
    elif args.verbose:
        logger.setLevel(logging.INFO)

    try:
        create_final_video(
            audio_text_path=args.audio,
            output_name=args.output,
            video_path=args.video,
            music_path=args.music,
            keep_ass=not args.no_keep_ass
        )

        return 0

    except KeyboardInterrupt:
        logger.warning("\n⚠️  Прервано пользователем")
        return 130

    except Exception as e:
        logger.error(f"\n❌ Ошибка: {e}")
        if args.debug:
            raise
        return 1


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    sys.exit(main())
