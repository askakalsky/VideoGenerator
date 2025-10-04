"""
Модуль для добавления аудио к случайному или заданному фрагменту видео.
Поддерживает настройку качества, fade-эффекты и сохранение исходного качества видео.
"""

import logging
import random
import sys
import argparse
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union, Tuple

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

    # Видео кодеки
    video_codec: str = 'libx264'
    video_bitrate: str = '8000k'
    crf: int = 18  # 0-51, меньше = лучше качество
    preset: str = 'medium'  # ultrafast, fast, medium, slow, veryslow

    # Аудио кодеки
    audio_codec: str = 'aac'
    audio_bitrate: str = '320k'

    # Дополнительные параметры
    pix_fmt: str = 'yuv420p'
    movflags: str = '+faststart'
    threads: int = 0  # 0 = авто
    verbose: bool = False

    def validate(self):
        """Валидация параметров."""
        if not 0 <= self.crf <= 51:
            raise ValueError(f"CRF должен быть 0-51, получено: {self.crf}")

        valid_presets = {
            'ultrafast', 'superfast', 'veryfast', 'faster',
            'fast', 'medium', 'slow', 'slower', 'veryslow'
        }
        if self.preset not in valid_presets:
            raise ValueError(
                f"preset должен быть одним из {valid_presets}, получено: {self.preset}"
            )

    def to_write_params(self) -> dict:
        """Преобразует конфиг в параметры для write_videofile."""
        return {
            'codec': self.video_codec,
            'bitrate': self.video_bitrate,
            'preset': self.preset,
            'audio_codec': self.audio_codec,
            'audio_bitrate': self.audio_bitrate,
            'ffmpeg_params': ['-crf', str(self.crf), '-pix_fmt', self.pix_fmt],
            'threads': self.threads if self.threads > 0 else None,
            'verbose': self.verbose,
            'logger': 'bar' if not self.verbose else None,
        }


@dataclass
class AudioSettings:
    """Настройки аудио обработки."""

    # Временные параметры
    min_start_time: float = 5.0  # Минимальное время начала (сек)
    max_start_time: Optional[float] = None  # Максимальное время начала
    # Конкретное время (игнорирует случайность)
    specific_start_time: Optional[float] = None

    # Громкость
    audio_volume: float = 1.0  # Громкость добавляемого аудио
    # Громкость оригинального аудио (0 = отключить)
    original_volume: float = 0.0

    # Fade эффекты
    fade_in_duration: float = 0.0  # Длительность fade-in (сек)
    fade_out_duration: float = 0.0  # Длительность fade-out (сек)

    # Случайность
    random_seed: Optional[int] = None  # Seed для воспроизводимости

    def validate(self):
        """Валидация параметров."""
        if self.min_start_time < 0:
            raise ValueError("min_start_time не может быть отрицательным")

        if self.max_start_time is not None and self.max_start_time < self.min_start_time:
            raise ValueError("max_start_time должен быть >= min_start_time")

        if self.specific_start_time is not None and self.specific_start_time < 0:
            raise ValueError("specific_start_time не может быть отрицательным")

        if not 0.0 <= self.audio_volume <= 2.0:
            raise ValueError(
                f"audio_volume должен быть 0.0-2.0, получено: {self.audio_volume}")

        if not 0.0 <= self.original_volume <= 2.0:
            raise ValueError(
                f"original_volume должен быть 0.0-2.0, получено: {self.original_volume}")

        if self.fade_in_duration < 0:
            raise ValueError("fade_in_duration не может быть отрицательным")

        if self.fade_out_duration < 0:
            raise ValueError("fade_out_duration не может быть отрицательным")


# ============================================================================
# КОНСТАНТЫ
# ============================================================================

SUPPORTED_VIDEO_FORMATS = {'.mp4', '.avi',
                           '.mov', '.mkv', '.webm', '.flv', '.wmv'}
SUPPORTED_AUDIO_FORMATS = {'.mp3', '.wav',
                           '.aac', '.m4a', '.flac', '.ogg', '.wma'}


# ============================================================================
# УТИЛИТЫ
# ============================================================================

class VideoProcessingError(Exception):
    """Базовая ошибка обработки видео."""
    pass


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


def validate_file_exists(path: Path, file_type: str = "Файл"):
    """Проверяет существование файла."""
    if not path.exists():
        raise FileNotFoundError(f"{file_type} не найден: {path}")
    if not path.is_file():
        raise ValueError(f"{path} не является файлом")


def validate_file_format(path: Path, supported_formats: set, file_type: str):
    """Проверяет формат файла."""
    suffix = path.suffix.lower()
    if suffix not in supported_formats:
        raise ValueError(
            f"Неподдерживаемый формат {file_type}: {suffix}. "
            f"Поддерживаются: {', '.join(sorted(supported_formats))}"
        )


def get_safe_output_path(
    input_path: Path,
    output_path: Optional[Path] = None,
    suffix: str = "_with_audio",
    force: bool = False
) -> Path:
    """
    Генерирует безопасный путь для выходного файла.

    Args:
        input_path: Путь к входному файлу
        output_path: Желаемый путь вывода
        suffix: Суффикс для автогенерации имени
        force: Разрешить перезапись

    Returns:
        Path: Безопасный путь для сохранения
    """
    if output_path is None:
        output_path = input_path.parent / \
            f"{input_path.stem}{suffix}{input_path.suffix}"
    else:
        output_path = Path(output_path)

    if output_path.exists() and not force:
        counter = 1
        original_stem = output_path.stem
        while output_path.exists():
            output_path = output_path.parent / \
                f"{original_stem}_{counter}{output_path.suffix}"
            counter += 1
        logger.warning(f"Файл существует, сохраняю как: {output_path.name}")

    return output_path


def format_time(seconds: float) -> str:
    """
    Форматирует время в читаемый вид.

    Args:
        seconds: Время в секундах

    Returns:
        str: Отформатированная строка (MM:SS или HH:MM:SS)
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes}:{secs:02d}"


# ============================================================================
# ГЛАВНЫЙ КЛАСС
# ============================================================================

class VideoAudioMixer:
    """Класс для добавления аудио к фрагменту видео."""

    def __init__(
        self,
        audio_settings: Optional[AudioSettings] = None,
        video_config: Optional[VideoConfig] = None
    ):
        """
        Инициализация миксера.

        Args:
            audio_settings: Настройки аудио обработки
            video_config: Конфигурация видео кодирования
        """
        self.audio_settings = audio_settings or AudioSettings()
        self.video_config = video_config or VideoConfig()

        # Валидация
        self.audio_settings.validate()
        self.video_config.validate()

    def _calculate_start_time(
        self,
        video_duration: float,
        audio_duration: float
    ) -> float:
        """
        Вычисляет время начала аудио.

        Args:
            video_duration: Длительность видео
            audio_duration: Длительность аудио

        Returns:
            float: Время начала в секундах

        Raises:
            ValueError: Если невозможно вычислить корректное время
        """
        # Если указано конкретное время
        if self.audio_settings.specific_start_time is not None:
            start_time = self.audio_settings.specific_start_time
            if start_time + audio_duration > video_duration:
                raise ValueError(
                    f"Аудио ({audio_duration:.1f}s) не помещается в видео "
                    f"начиная с {start_time:.1f}s. "
                    f"Длительность видео: {video_duration:.1f}s"
                )
            return start_time

        # Проверяем, что видео достаточно длинное
        if video_duration < audio_duration:
            raise ValueError(
                f"Видео ({video_duration:.1f}s) короче аудио ({audio_duration:.1f}s)"
            )

        # Вычисляем диапазон возможных позиций
        max_possible_start = video_duration - audio_duration

        # Применяем ограничения
        min_start = self.audio_settings.min_start_time
        max_start = self.audio_settings.max_start_time

        if max_start is None:
            max_start = max_possible_start
        else:
            max_start = min(max_start, max_possible_start)

        # Проверяем валидность диапазона
        if min_start > max_start:
            raise ValueError(
                f"Невозможно разместить аудио: min_start ({min_start:.1f}s) > "
                f"max_start ({max_start:.1f}s). "
                f"Увеличьте длительность видео или уменьшите min_start."
            )

        # Устанавливаем seed если указан
        if self.audio_settings.random_seed is not None:
            random.seed(self.audio_settings.random_seed)

        # Выбираем случайное время
        start_time = random.uniform(min_start, max_start)

        logger.info(f"🎲 Случайное время начала: {format_time(start_time)}")
        logger.info(
            f"   └─ Диапазон: {format_time(min_start)} - {format_time(max_start)}")

        return start_time

    def _apply_audio_effects(
        self,
        audio: AudioFileClip,
        duration: float
    ) -> AudioFileClip:
        """
        Применяет эффекты к аудио (громкость, fade).

        Args:
            audio: Аудио клип
            duration: Длительность аудио

        Returns:
            AudioFileClip: Обработанный клип
        """
        # Применяем громкость - ИСПРАВЛЕНО для MoviePy v2
        if self.audio_settings.audio_volume != 1.0:
            logger.info(
                f"🔊 Громкость аудио: {self.audio_settings.audio_volume * 100:.0f}%")
            # MoviePy v2: используем multiply_volume вместо volumex
            audio = audio.multiply_volume(self.audio_settings.audio_volume)

        # Применяем fade-in
        if self.audio_settings.fade_in_duration > 0:
            fade_duration = min(
                self.audio_settings.fade_in_duration, duration / 2)
            logger.info(f"📈 Fade-in: {fade_duration:.1f}s")
            audio = audio.audio_fadein(fade_duration)

        # Применяем fade-out
        if self.audio_settings.fade_out_duration > 0:
            fade_duration = min(
                self.audio_settings.fade_out_duration, duration / 2)
            logger.info(f"📉 Fade-out: {fade_duration:.1f}s")
            audio = audio.audio_fadeout(fade_duration)

        return audio

    def process(
        self,
        video_path: Union[str, Path],
        audio_path: Union[str, Path],
        output_path: Optional[Union[str, Path]] = None,
        force_overwrite: bool = False
    ) -> Path:
        """
        Добавляет аудио к фрагменту видео.

        Args:
            video_path: Путь к видео файлу
            audio_path: Путь к аудио файлу
            output_path: Путь для сохранения результата
            force_overwrite: Разрешить перезапись существующих файлов

        Returns:
            Path: Путь к созданному файлу

        Raises:
            FileNotFoundError: Если входные файлы не найдены
            ValueError: Если параметры некорректны
            VideoProcessingError: Если произошла ошибка обработки
        """
        # Преобразование путей
        video_path = Path(video_path).resolve()
        audio_path = Path(audio_path).resolve()

        logger.info("=" * 70)
        logger.info("🎬 ДОБАВЛЕНИЕ АУДИО К ФРАГМЕНТУ ВИДЕО")
        logger.info("=" * 70)

        # Валидация входных файлов
        logger.info("🔍 Проверка входных файлов...")
        validate_file_exists(video_path, "Видео")
        validate_file_exists(audio_path, "Аудио")
        validate_file_format(video_path, SUPPORTED_VIDEO_FORMATS, "видео")
        validate_file_format(audio_path, SUPPORTED_AUDIO_FORMATS, "аудио")

        # Определение пути вывода
        if output_path:
            output_path = Path(output_path).resolve()
        output_path = get_safe_output_path(
            video_path, output_path, force=force_overwrite)

        # Инициализация переменных
        video = None
        audio = None
        video_clip = None
        final_clip = None

        try:
            # ================================================================
            # ЗАГРУЗКА ФАЙЛОВ
            # ================================================================

            logger.info(f"📹 Загружаю видео: {video_path.name}")
            video = VideoFileClip(str(video_path))
            video_duration = video.duration

            logger.info(f"   ├─ Длительность: {format_time(video_duration)}")
            logger.info(f"   ├─ Разрешение: {video.size[0]}x{video.size[1]}")
            logger.info(f"   ├─ FPS: {video.fps:.2f}")
            logger.info(f"   └─ Аудио: {'есть' if video.audio else 'нет'}")

            logger.info(f"🎵 Загружаю аудио: {audio_path.name}")
            audio = AudioFileClip(str(audio_path))
            audio_duration = audio.duration

            logger.info(f"   └─ Длительность: {format_time(audio_duration)}")

            # ================================================================
            # ВЫЧИСЛЕНИЕ ВРЕМЕНИ
            # ================================================================

            logger.info("")
            start_time = self._calculate_start_time(
                video_duration, audio_duration)
            end_time = start_time + audio_duration

            logger.info(f"✂️  Вырезаю фрагмент видео:")
            logger.info(f"   ├─ Начало: {format_time(start_time)}")
            logger.info(f"   ├─ Конец: {format_time(end_time)}")
            logger.info(f"   └─ Длительность: {format_time(audio_duration)}")

            # ================================================================
            # ОБРАБОТКА
            # ================================================================

            # Вырезаем фрагмент видео
            video_clip = video.subclip(start_time, end_time)

            # Применяем эффекты к аудио
            logger.info("")
            processed_audio = self._apply_audio_effects(audio, audio_duration)

            # Комбинируем аудио - ИСПРАВЛЕНО для MoviePy v2
            if video_clip.audio is not None and self.audio_settings.original_volume > 0:
                logger.info("🎚️  Микширую аудио дорожки")
                logger.info(
                    f"   ├─ Оригинальное аудио: {self.audio_settings.original_volume * 100:.0f}%"
                )
                logger.info(
                    f"   └─ Новое аудио: {self.audio_settings.audio_volume * 100:.0f}%"
                )

                # MoviePy v2: используем multiply_volume вместо volumex
                original_audio = video_clip.audio.multiply_volume(
                    self.audio_settings.original_volume
                )
                final_audio = CompositeAudioClip(
                    [original_audio, processed_audio])
            else:
                if video_clip.audio is not None:
                    logger.info("🔇 Отключаю оригинальное аудио")
                final_audio = processed_audio

            # Применяем аудио к видео
            final_clip = video_clip.set_audio(final_audio)

            # ================================================================
            # СОХРАНЕНИЕ
            # ================================================================

            logger.info("")
            logger.info(f"💾 Сохраняю результат: {output_path.name}")
            logger.info(f"⚙️  Параметры кодирования:")
            logger.info(f"   ├─ Видео кодек: {self.video_config.video_codec}")
            logger.info(
                f"   ├─ Видео bitrate: {self.video_config.video_bitrate}")
            logger.info(f"   ├─ CRF: {self.video_config.crf}")
            logger.info(f"   ├─ Preset: {self.video_config.preset}")
            logger.info(f"   ├─ Аудио кодек: {self.video_config.audio_codec}")
            logger.info(
                f"   └─ Аудио bitrate: {self.video_config.audio_bitrate}")

            write_params = self.video_config.to_write_params()
            final_clip.write_videofile(str(output_path), **write_params)

            # Статистика
            output_size = output_path.stat().st_size / (1024 * 1024)  # MB
            logger.info("")
            logger.info(f"📊 Статистика:")
            logger.info(f"   ├─ Размер файла: {output_size:.2f} MB")
            logger.info(f"   ├─ Длительность: {format_time(audio_duration)}")
            logger.info(
                f"   └─ Фрагмент: {format_time(start_time)} - {format_time(end_time)}"
            )

            logger.info("")
            logger.info("=" * 70)
            logger.info(f"✅ ГОТОВО! Файл сохранен: {output_path}")
            logger.info("=" * 70)

            return output_path

        except Exception as e:
            logger.error(f"❌ Ошибка при обработке: {e}", exc_info=True)

            # Удаляем частично созданный файл
            if output_path and output_path.exists():
                try:
                    output_path.unlink()
                    logger.info("🗑️  Удален поврежденный выходной файл")
                except Exception:
                    pass

            raise VideoProcessingError(
                f"Не удалось обработать видео: {e}") from e

        finally:
            # Освобождение ресурсов
            logger.debug("🧹 Освобождаю ресурсы...")
            for clip in [final_clip, video_clip, video, audio]:
                if clip is not None:
                    try:
                        clip.close()
                    except Exception as e:
                        logger.warning(f"Ошибка при закрытии клипа: {e}")


# ============================================================================
# CLI
# ============================================================================

def parse_arguments():
    """Парсинг аргументов командной строки."""
    parser = argparse.ArgumentParser(
        description='Добавить аудио к случайному или заданному фрагменту видео',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  %(prog)s video.mp4 audio.mp3
  %(prog)s video.mp4 audio.mp3 -o output.mp4
  %(prog)s video.mp4 audio.mp3 --min-start 10 --max-start 30
  %(prog)s video.mp4 audio.mp3 --start-at 15.5
  %(prog)s video.mp4 audio.mp3 --fade-in 1 --fade-out 2
  %(prog)s video.mp4 audio.mp3 --keep-original 0.3 --audio-volume 1.0
  %(prog)s video.mp4 audio.mp3 --crf 15 --preset slow
        """
    )

    # Обязательные аргументы
    parser.add_argument(
        'video',
        help='Путь к видео файлу'
    )
    parser.add_argument(
        'audio',
        help='Путь к аудио файлу'
    )

    # Пути и файлы
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

    # Настройки времени
    time_group = parser.add_argument_group('Настройки времени')
    time_group.add_argument(
        '--min-start',
        type=float,
        default=5.0,
        help='Минимальное время начала аудио (секунды)'
    )
    time_group.add_argument(
        '--max-start',
        type=float,
        default=None,
        help='Максимальное время начала аудио (секунды)'
    )
    time_group.add_argument(
        '--start-at',
        type=float,
        default=None,
        help='Конкретное время начала (игнорирует случайность)'
    )
    time_group.add_argument(
        '--random-seed',
        type=int,
        default=None,
        help='Seed для генератора случайных чисел (воспроизводимость)'
    )

    # Настройки аудио
    audio_group = parser.add_argument_group('Настройки аудио')
    audio_group.add_argument(
        '--audio-volume',
        type=float,
        default=1.0,
        help='Громкость добавляемого аудио (0.0-2.0)'
    )
    audio_group.add_argument(
        '--keep-original',
        type=float,
        default=0.0,
        help='Громкость оригинального аудио из видео (0.0-2.0, 0=отключить)'
    )
    audio_group.add_argument(
        '--fade-in',
        type=float,
        default=0.0,
        help='Длительность fade-in (секунды)'
    )
    audio_group.add_argument(
        '--fade-out',
        type=float,
        default=0.0,
        help='Длительность fade-out (секунды)'
    )

    # Настройки видео
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

    # Дополнительно
    misc_group = parser.add_argument_group('Дополнительно')
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

    # Настройка логирования
    if args.debug:
        logger.setLevel(logging.DEBUG)
    elif args.verbose:
        logger.setLevel(logging.INFO)

    try:
        # Создание конфигураций
        audio_settings = AudioSettings(
            min_start_time=args.min_start,
            max_start_time=args.max_start,
            specific_start_time=args.start_at,
            audio_volume=args.audio_volume,
            original_volume=args.keep_original,
            fade_in_duration=args.fade_in,
            fade_out_duration=args.fade_out,
            random_seed=args.random_seed
        )

        video_config = VideoConfig(
            video_bitrate=args.video_bitrate,
            audio_bitrate=args.audio_bitrate,
            crf=args.crf,
            preset=args.preset,
            verbose=args.verbose
        )

        # Создание процессора
        mixer = VideoAudioMixer(
            audio_settings=audio_settings,
            video_config=video_config
        )

        # Обработка
        output_path = mixer.process(
            video_path=args.video,
            audio_path=args.audio,
            output_path=args.output,
            force_overwrite=args.force
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
