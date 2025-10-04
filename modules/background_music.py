"""
Модуль для добавления фоновой музыки к видео.
Поддерживает настройку громкости, зацикливание музыки и сохранение качества видео.
"""

import logging
import sys
from pathlib import Path
from typing import Optional, Union
from dataclasses import dataclass, field
from contextlib import contextmanager
import argparse

# ============================================================================
# ИМПОРТЫ MOVIEPY V2
# ============================================================================
from moviepy import VideoFileClip, AudioFileClip, CompositeAudioClip

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

@dataclass
class VideoConfig:
    """Конфигурация параметров обработки видео."""

    # Видео параметры
    video_codec: str = 'libx264'
    video_bitrate: str = '8000k'  # Высокое качество
    preset: str = 'medium'  # ultrafast, fast, medium, slow, veryslow
    crf: int = 18  # 0-51, меньше = лучше (18-23 оптимально)

    # Аудио параметры
    audio_codec: str = 'aac'
    audio_bitrate: str = '320k'

    # Дополнительные параметры
    threads: int = 4
    write_logfile: bool = False
    verbose: bool = False

    def to_write_params(self) -> dict:
        """Преобразует конфиг в параметры для write_videofile."""
        return {
            'codec': self.video_codec,
            'bitrate': self.video_bitrate,
            'preset': self.preset,
            'audio_codec': self.audio_codec,
            'audio_bitrate': self.audio_bitrate,
            'threads': self.threads,
            'write_logfile': self.write_logfile,
            'verbose': self.verbose,
            'logger': 'bar' if not self.verbose else None,
            'ffmpeg_params': ['-crf', str(self.crf)]
        }


@dataclass
class AudioSettings:
    """Настройки аудио обработки."""
    music_volume: float = 0.1
    voice_volume: float = 1.0
    loop_music: bool = True
    fade_in_duration: float = 0.0  # Секунды
    fade_out_duration: float = 0.0  # Секунды

    def __post_init__(self):
        """Валидация после инициализации."""
        self.validate()

    def validate(self):
        """Проверяет корректность параметров."""
        if not 0.0 <= self.music_volume <= 2.0:
            raise ValueError(
                f"music_volume должен быть в диапазоне 0.0-2.0, "
                f"получено: {self.music_volume}"
            )

        if not 0.0 <= self.voice_volume <= 2.0:
            raise ValueError(
                f"voice_volume должен быть в диапазоне 0.0-2.0, "
                f"получено: {self.voice_volume}"
            )

        if self.fade_in_duration < 0:
            raise ValueError(f"fade_in_duration не может быть отрицательным")

        if self.fade_out_duration < 0:
            raise ValueError(f"fade_out_duration не может быть отрицательным")


# ============================================================================
# КОНСТАНТЫ
# ============================================================================

SUPPORTED_VIDEO_FORMATS = {'.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv'}
SUPPORTED_AUDIO_FORMATS = {'.mp3', '.wav',
                           '.aac', '.m4a', '.flac', '.ogg', '.wma'}


# ============================================================================
# УТИЛИТЫ
# ============================================================================

@contextmanager
def managed_clips(*clips):
    """
    Контекстный менеджер для автоматического закрытия клипов.

    Args:
        *clips: MoviePy клипы для управления

    Yields:
        tuple: Переданные клипы
    """
    try:
        yield clips
    finally:
        for clip in clips:
            if clip is not None:
                try:
                    clip.close()
                except Exception as e:
                    logger.warning(f"Ошибка при закрытии клипа: {e}")


def validate_file_exists(file_path: Path, file_type: str = "Файл"):
    """
    Проверяет существование файла.

    Args:
        file_path: Путь к файлу
        file_type: Тип файла для сообщения об ошибке

    Raises:
        FileNotFoundError: Если файл не найден
    """
    if not file_path.exists():
        raise FileNotFoundError(f"{file_type} не найден: {file_path}")

    if not file_path.is_file():
        raise ValueError(f"{file_path} не является файлом")


def validate_file_format(file_path: Path, supported_formats: set, file_type: str):
    """
    Проверяет формат файла.

    Args:
        file_path: Путь к файлу
        supported_formats: Множество поддерживаемых расширений
        file_type: Тип файла для сообщения

    Raises:
        ValueError: Если формат не поддерживается
    """
    suffix = file_path.suffix.lower()
    if suffix not in supported_formats:
        raise ValueError(
            f"Неподдерживаемый формат {file_type}: {suffix}. "
            f"Поддерживаются: {', '.join(sorted(supported_formats))}"
        )


def get_safe_output_path(
    input_path: Path,
    output_path: Optional[Path] = None,
    suffix: str = "_with_music",
    force: bool = False
) -> Path:
    """
    Генерирует безопасный путь для выходного файла.

    Args:
        input_path: Путь к входному файлу
        output_path: Желаемый путь вывода (опционально)
        suffix: Суффикс для автогенерации имени
        force: Разрешить перезапись существующих файлов

    Returns:
        Path: Безопасный путь для сохранения
    """
    if output_path is None:
        output_path = input_path.parent / \
            f"{input_path.stem}{suffix}{input_path.suffix}"
    else:
        output_path = Path(output_path)

    # Если файл существует и не разрешена перезапись
    if output_path.exists() and not force:
        counter = 1
        original_stem = output_path.stem
        while output_path.exists():
            output_path = output_path.parent / \
                f"{original_stem}_{counter}{output_path.suffix}"
            counter += 1
        logger.warning(f"Файл существует, сохраняю как: {output_path.name}")

    return output_path


def format_duration(seconds: float) -> str:
    """
    Форматирует длительность в читаемый вид.

    Args:
        seconds: Длительность в секундах

    Returns:
        str: Отформатированная строка (например, "1:23:45")
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes}:{secs:02d}"


# ============================================================================
# ОСНОВНАЯ ФУНКЦИЯ
# ============================================================================

def add_background_music(
    video_path: Union[str, Path],
    music_path: Union[str, Path],
    output_path: Optional[Union[str, Path]] = None,
    audio_settings: Optional[AudioSettings] = None,
    video_config: Optional[VideoConfig] = None,
    force_overwrite: bool = False,
) -> Path:
    """
    Добавляет фоновую музыку к видео с сохранением качества.

    Args:
        video_path: Путь к исходному видео
        music_path: Путь к файлу фоновой музыки
        output_path: Путь для сохранения результата (опционально)
        audio_settings: Настройки аудио обработки
        video_config: Конфигурация параметров видео
        force_overwrite: Разрешить перезапись существующих файлов

    Returns:
        Path: Путь к созданному файлу

    Raises:
        FileNotFoundError: Если входные файлы не найдены
        ValueError: Если параметры некорректны
        RuntimeError: Если произошла ошибка обработки

    Example:
        >>> from pathlib import Path
        >>> settings = AudioSettings(music_volume=0.2, voice_volume=1.0)
        >>> output = add_background_music(
        ...     video_path="input.mp4",
        ...     music_path="music.mp3",
        ...     audio_settings=settings
        ... )
        >>> print(f"Создан файл: {output}")
    """
    # Инициализация параметров по умолчанию
    if audio_settings is None:
        audio_settings = AudioSettings()

    if video_config is None:
        video_config = VideoConfig()

    # Преобразование путей
    video_path = Path(video_path).resolve()
    music_path = Path(music_path).resolve()

    # Валидация входных файлов
    logger.info("🔍 Проверка входных файлов...")
    validate_file_exists(video_path, "Видео")
    validate_file_exists(music_path, "Музыка")
    validate_file_format(video_path, SUPPORTED_VIDEO_FORMATS, "видео")
    validate_file_format(music_path, SUPPORTED_AUDIO_FORMATS, "аудио")

    # Определение пути вывода
    if output_path:
        output_path = Path(output_path).resolve()
    output_path = get_safe_output_path(
        video_path, output_path, force=force_overwrite)

    # Инициализация переменных для finally блока
    video = None
    music = None
    final_video = None

    try:
        # ====================================================================
        # ЗАГРУЗКА ФАЙЛОВ
        # ====================================================================
        logger.info(f"📹 Загружаю видео: {video_path.name}")
        video = VideoFileClip(str(video_path))
        video_duration = video.duration

        logger.info(f"   ├─ Длительность: {format_duration(video_duration)}")
        logger.info(f"   ├─ Разрешение: {video.size[0]}x{video.size[1]}")
        logger.info(f"   └─ FPS: {video.fps}")

        logger.info(f"🎵 Загружаю музыку: {music_path.name}")
        music = AudioFileClip(str(music_path))
        music_duration = music.duration

        logger.info(f"   └─ Длительность: {format_duration(music_duration)}")

        # ====================================================================
        # ОБРАБОТКА МУЗЫКИ
        # ====================================================================

        # Зацикливание музыки если необходимо
        if audio_settings.loop_music and music_duration < video_duration:
            loops_needed = int(video_duration / music_duration) + 1
            logger.info(f"🔁 Зацикливаю музыку (повторов: {loops_needed})")
            # В MoviePy v2 метод loop() работает так же
            music = music.loop(n=loops_needed)

        # Обрезка музыки под длительность видео
        if music.duration > video_duration:
            logger.info(
                f"✂️  Обрезаю музыку до {format_duration(video_duration)}")
            # В MoviePy v2 используем subclip вместо subclipped
            music = music.subclip(0, video_duration)

        # ====================================================================
        # ПРИМЕНЕНИЕ ЭФФЕКТОВ К МУЗЫКЕ (MoviePy v2)
        # ====================================================================

        # Настройка громкости музыки - ИСПРАВЛЕНО для v2
        if audio_settings.music_volume != 1.0:
            logger.info(
                f"🔊 Устанавливаю громкость музыки: {audio_settings.music_volume * 100:.0f}%"
            )
            # MoviePy v2: используем multiply_volume вместо volumex
            music = music.multiply_volume(audio_settings.music_volume)

        # Fade in/out для музыки
        if audio_settings.fade_in_duration > 0:
            logger.info(
                f"📈 Применяю fade-in: {audio_settings.fade_in_duration}s")
            music = music.audio_fadein(audio_settings.fade_in_duration)

        if audio_settings.fade_out_duration > 0:
            logger.info(
                f"📉 Применяю fade-out: {audio_settings.fade_out_duration}s")
            music = music.audio_fadeout(audio_settings.fade_out_duration)

        # ====================================================================
        # ОБРАБОТКА АУДИО ИЗ ВИДЕО
        # ====================================================================

        if video.audio is not None:
            logger.info("🎤 Обрабатываю оригинальное аудио из видео")
            voice = video.audio

            # Настройка громкости голоса - ИСПРАВЛЕНО для v2
            if audio_settings.voice_volume != 1.0:
                logger.info(
                    f"🔊 Устанавливаю громкость голоса: {audio_settings.voice_volume * 100:.0f}%"
                )
                # MoviePy v2: используем multiply_volume вместо volumex
                voice = voice.multiply_volume(audio_settings.voice_volume)

            # Микширование аудио
            logger.info("🎚️  Микширую голос и музыку")
            final_audio = CompositeAudioClip([voice, music])
        else:
            logger.warning(
                "⚠️  В видео отсутствует аудиодорожка, добавляю только музыку"
            )
            final_audio = music

        # ====================================================================
        # СОЗДАНИЕ ФИНАЛЬНОГО ВИДЕО
        # ====================================================================

        logger.info("🎬 Создаю финальное видео с новым аудио")
        # В MoviePy v2 метод set_audio работает так же
        final_video = video.set_audio(final_audio)

        # ====================================================================
        # СОХРАНЕНИЕ
        # ====================================================================

        logger.info(f"💾 Сохраняю результат: {output_path.name}")
        logger.info(f"   ├─ Видео кодек: {video_config.video_codec}")
        logger.info(f"   ├─ Видео bitrate: {video_config.video_bitrate}")
        logger.info(f"   ├─ CRF: {video_config.crf} (качество)")
        logger.info(f"   ├─ Preset: {video_config.preset}")
        logger.info(f"   ├─ Аудио кодек: {video_config.audio_codec}")
        logger.info(f"   └─ Аудио bitrate: {video_config.audio_bitrate}")

        write_params = video_config.to_write_params()
        final_video.write_videofile(str(output_path), **write_params)

        # Проверка размера файла
        output_size = output_path.stat().st_size / (1024 * 1024)  # MB
        logger.info(f"📊 Размер файла: {output_size:.2f} MB")

        logger.info(f"✅ Готово! Файл сохранен: {output_path}")

        return output_path

    except Exception as e:
        logger.error(f"❌ Ошибка при обработке: {e}", exc_info=True)

        # Удаляем частично созданный файл если есть
        if output_path and output_path.exists():
            try:
                output_path.unlink()
                logger.info("🗑️  Удален поврежденный выходной файл")
            except Exception:
                pass

        raise RuntimeError(f"Не удалось обработать видео: {e}") from e

    finally:
        # Гарантированное освобождение ресурсов
        logger.debug("🧹 Освобождаю ресурсы...")
        for clip in [final_video, video, music]:
            if clip is not None:
                try:
                    clip.close()
                except Exception as e:
                    logger.warning(f"Ошибка при закрытии клипа: {e}")


# ============================================================================
# CLI ИНТЕРФЕЙС
# ============================================================================

def parse_arguments():
    """Парсинг аргументов командной строки."""
    parser = argparse.ArgumentParser(
        description='Добавить фоновую музыку к видео с сохранением качества',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  %(prog)s video.mp4 music.mp3
  %(prog)s video.mp4 music.mp3 -o output.mp4
  %(prog)s video.mp4 music.mp3 -m 0.15 -v 1.2
  %(prog)s video.mp4 music.mp3 --crf 20 --preset slow
  %(prog)s video.mp4 music.mp3 --fade-in 2 --fade-out 3
        """
    )

    # Обязательные аргументы
    parser.add_argument(
        'video',
        help='Путь к видео файлу'
    )
    parser.add_argument(
        'music',
        help='Путь к файлу фоновой музыки'
    )

    # Опциональные аргументы - Пути
    path_group = parser.add_argument_group('Пути и файлы')
    path_group.add_argument(
        '-o', '--output',
        help='Путь для сохранения результата',
        default=None
    )
    path_group.add_argument(
        '--force',
        action='store_true',
        help='Перезаписать выходной файл если существует'
    )

    # Аудио настройки
    audio_group = parser.add_argument_group('Настройки аудио')
    audio_group.add_argument(
        '-m', '--music-volume',
        type=float,
        default=0.1,
        help='Громкость музыки (0.0-2.0, по умолчанию 0.1)'
    )
    audio_group.add_argument(
        '-v', '--voice-volume',
        type=float,
        default=1.0,
        help='Громкость голоса (0.0-2.0, по умолчанию 1.0)'
    )
    audio_group.add_argument(
        '--no-loop',
        action='store_true',
        help='Не зацикливать музыку'
    )
    audio_group.add_argument(
        '--fade-in',
        type=float,
        default=0.0,
        help='Длительность fade-in для музыки (секунды)'
    )
    audio_group.add_argument(
        '--fade-out',
        type=float,
        default=0.0,
        help='Длительность fade-out для музыки (секунды)'
    )

    # Видео настройки
    video_group = parser.add_argument_group('Настройки видео')
    video_group.add_argument(
        '--video-bitrate',
        default='8000k',
        help='Битрейт видео (по умолчанию 8000k)'
    )
    video_group.add_argument(
        '--audio-bitrate',
        default='320k',
        help='Битрейт аудио (по умолчанию 320k)'
    )
    video_group.add_argument(
        '--crf',
        type=int,
        default=18,
        help='CRF значение (0-51, меньше=лучше, по умолчанию 18)'
    )
    video_group.add_argument(
        '--preset',
        choices=['ultrafast', 'superfast', 'veryfast', 'faster', 'fast',
                 'medium', 'slow', 'slower', 'veryslow'],
        default='medium',
        help='Preset скорости кодирования (по умолчанию medium)'
    )

    # Дополнительные опции
    misc_group = parser.add_argument_group('Дополнительно')
    misc_group.add_argument(
        '--threads',
        type=int,
        default=4,
        help='Количество потоков для кодирования (по умолчанию 4)'
    )
    misc_group.add_argument(
        '--verbose',
        action='store_true',
        help='Подробный вывод'
    )
    misc_group.add_argument(
        '--debug',
        action='store_true',
        help='Режим отладки'
    )

    return parser.parse_args()


def main():
    """Главная функция CLI."""
    args = parse_arguments()

    # Настройка уровня логирования
    if args.debug:
        logger.setLevel(logging.DEBUG)
    elif args.verbose:
        logger.setLevel(logging.INFO)
    else:
        logger.setLevel(logging.INFO)

    try:
        # Создание конфигураций
        audio_settings = AudioSettings(
            music_volume=args.music_volume,
            voice_volume=args.voice_volume,
            loop_music=not args.no_loop,
            fade_in_duration=args.fade_in,
            fade_out_duration=args.fade_out
        )

        video_config = VideoConfig(
            video_bitrate=args.video_bitrate,
            audio_bitrate=args.audio_bitrate,
            crf=args.crf,
            preset=args.preset,
            threads=args.threads,
            verbose=args.verbose
        )

        # Запуск обработки
        logger.info("=" * 60)
        logger.info("🎬 ДОБАВЛЕНИЕ ФОНОВОЙ МУЗЫКИ К ВИДЕО")
        logger.info("=" * 60)

        output_path = add_background_music(
            video_path=args.video,
            music_path=args.music,
            output_path=args.output,
            audio_settings=audio_settings,
            video_config=video_config,
            force_overwrite=args.force
        )

        logger.info("=" * 60)
        logger.info(f"🎉 УСПЕШНО ЗАВЕРШЕНО")
        logger.info(f"📁 Результат: {output_path}")
        logger.info("=" * 60)

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
