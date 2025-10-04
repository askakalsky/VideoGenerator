#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Пакетная конвертация видео в формат 9:16 (вертикальный).

Функции:
- Обрезка видео в формат 9:16 с выравниванием по верху
- Удаление аудиодорожки (опционально)
- Сохранение высокого качества
- Параллельная обработка нескольких файлов
- Опциональное удаление исходников после конвертации
- Подробное логирование и статистика
"""

import json
import logging
import shutil
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Any

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
# КОНСТАНТЫ
# ============================================================================

VIDEO_EXTENSIONS = {
    '.mp4', '.mov', '.mkv', '.avi', '.flv',
    '.wmv', '.webm', '.mpeg', '.mpg', '.m4v',
    '.3gp', '.ts', '.mts', '.m2ts'
}

# Соотношение сторон для вертикального видео (9:16)
TARGET_ASPECT_RATIO = 9 / 16  # ширина / высота


# ============================================================================
# КОНФИГУРАЦИЯ
# ============================================================================

@dataclass
class ConversionConfig:
    """Конфигурация параметров конвертации."""

    # Параметры видео
    video_codec: str = 'libx264'
    preset: str = 'medium'  # ultrafast, fast, medium, slow, veryslow
    # 0-51, меньше = лучше качество (0=lossless, 18-23=визуально lossless)
    crf: int = 18
    pix_fmt: str = 'yuv420p'

    # Параметры обрезки
    crop_position: str = 'top'  # top, center, bottom
    ensure_even_dimensions: bool = True  # Чётные размеры для H.264

    # Параметры аудио
    remove_audio: bool = True
    audio_codec: Optional[str] = None
    audio_bitrate: Optional[str] = None

    # Дополнительные параметры
    max_workers: Optional[int] = None  # None = авто
    delete_source: bool = False
    overwrite: bool = True
    skip_if_vertical: bool = True  # Пропускать уже вертикальные видео

    # Фильтры качества
    min_width: int = 720  # Минимальная ширина для обработки
    min_height: int = 1280  # Минимальная высота для обработки

    def validate(self):
        """Валидация конфигурации."""
        if not 0 <= self.crf <= 51:
            raise ValueError(f"CRF должен быть 0-51, получено: {self.crf}")

        valid_presets = {'ultrafast', 'superfast', 'veryfast', 'faster',
                         'fast', 'medium', 'slow', 'slower', 'veryslow'}
        if self.preset not in valid_presets:
            raise ValueError(f"preset должен быть одним из {valid_presets}")

        valid_positions = {'top', 'center', 'bottom'}
        if self.crop_position not in valid_positions:
            raise ValueError(
                f"crop_position должен быть одним из {valid_positions}")

    def to_dict(self) -> dict:
        """Преобразование в словарь."""
        return asdict(self)


# ============================================================================
# ИНФОРМАЦИЯ О ВИДЕО
# ============================================================================

@dataclass
class VideoMetadata:
    """Метаданные видео файла."""
    path: Path
    width: int
    height: int
    duration: float
    fps: float
    codec: str
    bitrate: Optional[int] = None
    has_audio: bool = False

    @property
    def aspect_ratio(self) -> float:
        """Соотношение сторон (ширина / высота)."""
        return self.width / self.height if self.height > 0 else 0

    @property
    def is_vertical(self) -> bool:
        """Проверка, является ли видео вертикальным (высота > ширины)."""
        return self.height > self.width

    @property
    def is_9x16(self) -> bool:
        """Проверка, является ли видео уже 9:16."""
        target = 9 / 16
        tolerance = 0.01
        return abs(self.aspect_ratio - target) < tolerance

    def to_dict(self) -> dict:
        """Преобразование в словарь."""
        return {
            'path': str(self.path),
            'width': self.width,
            'height': self.height,
            'duration': round(self.duration, 2),
            'fps': round(self.fps, 2),
            'codec': self.codec,
            'bitrate': self.bitrate,
            'has_audio': self.has_audio,
            'aspect_ratio': round(self.aspect_ratio, 3),
            'is_vertical': self.is_vertical,
            'is_9x16': self.is_9x16,
        }


@dataclass
class ConversionResult:
    """Результат конвертации одного файла."""
    input_path: Path
    output_path: Optional[Path]
    success: bool
    message: str
    input_size: int = 0
    output_size: int = 0
    processing_time: float = 0.0
    skipped: bool = False
    error: Optional[str] = None

    def to_dict(self) -> dict:
        """Преобразование в словарь."""
        return {
            'input_path': str(self.input_path),
            'output_path': str(self.output_path) if self.output_path else None,
            'success': self.success,
            'message': self.message,
            'input_size_mb': round(self.input_size / (1024 * 1024), 2),
            'output_size_mb': round(self.output_size / (1024 * 1024), 2) if self.output_size else 0,
            'compression_ratio': round(self.output_size / self.input_size, 3) if self.input_size > 0 else 0,
            'processing_time': round(self.processing_time, 2),
            'skipped': self.skipped,
            'error': self.error,
        }


# ============================================================================
# УТИЛИТЫ
# ============================================================================

def check_ffmpeg() -> bool:
    """Проверяет наличие ffmpeg и ffprobe."""
    if shutil.which('ffmpeg') is None:
        logger.error("❌ ffmpeg не найден в PATH")
        logger.error("   Установите: https://ffmpeg.org/download.html")
        return False

    if shutil.which('ffprobe') is None:
        logger.error("❌ ffprobe не найден в PATH")
        return False

    return True


def get_video_metadata(video_path: Path) -> Optional[VideoMetadata]:
    """
    Получает метаданные видео через ffprobe.

    Args:
        video_path: Путь к видео файлу

    Returns:
        VideoMetadata или None при ошибке
    """
    cmd = [
        'ffprobe',
        '-v', 'error',
        '-select_streams', 'v:0',
        '-show_entries', 'stream=width,height,duration,r_frame_rate,codec_name,bit_rate',
        '-show_entries', 'format=duration',
        '-of', 'json',
        str(video_path)
    ]

    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
            timeout=30
        )

        data = json.loads(result.stdout)

        if not data.get('streams'):
            logger.warning(f"⚠️  Не найден видео поток: {video_path.name}")
            return None

        stream = data['streams'][0]

        # Парсинг FPS
        fps_str = stream.get('r_frame_rate', '0/1')
        if '/' in fps_str:
            num, den = fps_str.split('/')
            fps = float(num) / float(den) if float(den) > 0 else 0
        else:
            fps = float(fps_str)

        # Длительность
        duration = float(stream.get('duration', 0))
        if duration == 0 and 'format' in data:
            duration = float(data['format'].get('duration', 0))

        # Проверка наличия аудио
        cmd_audio = [
            'ffprobe',
            '-v', 'error',
            '-select_streams', 'a:0',
            '-show_entries', 'stream=codec_type',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            str(video_path)
        ]
        has_audio = False
        try:
            audio_result = subprocess.run(
                cmd_audio, capture_output=True, text=True, timeout=10)
            has_audio = 'audio' in audio_result.stdout.lower()
        except Exception:
            pass

        return VideoMetadata(
            path=video_path,
            width=int(stream.get('width', 0)),
            height=int(stream.get('height', 0)),
            duration=duration,
            fps=fps,
            codec=stream.get('codec_name', 'unknown'),
            bitrate=int(stream.get('bit_rate', 0)) if stream.get(
                'bit_rate') else None,
            has_audio=has_audio
        )

    except subprocess.TimeoutExpired:
        logger.error(f"⏱️  Таймаут при анализе {video_path.name}")
        return None
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Ошибка ffprobe для {video_path.name}: {e}")
        return None
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        logger.error(f"❌ Ошибка парсинга метаданных {video_path.name}: {e}")
        return None


def build_crop_filter(metadata: VideoMetadata, config: ConversionConfig) -> str:
    """
    Создаёт FFmpeg фильтр для обрезки в 9:16.

    Args:
        metadata: Метаданные видео
        config: Конфигурация конвертации

    Returns:
        str: FFmpeg filter string
    """
    in_w = metadata.width
    in_h = metadata.height

    # Вычисляем целевую ширину для соотношения 9:16
    target_w = in_h * 9 / 16

    # Обеспечиваем чётность (H.264 требует)
    if config.ensure_even_dimensions:
        target_w = int(target_w)
        if target_w % 2 != 0:
            target_w -= 1

    # Если целевая ширина больше исходной - видео слишком узкое
    if target_w > in_w:
        # Обрезаем по высоте вместо ширины
        target_h = int(in_w / 9 * 16)
        if config.ensure_even_dimensions and target_h % 2 != 0:
            target_h -= 1

        # Вертикальная позиция
        if config.crop_position == 'top':
            y = 0
        elif config.crop_position == 'bottom':
            y = in_h - target_h
        else:  # center
            y = (in_h - target_h) // 2

        return f"crop={in_w}:{target_h}:0:{y}"

    # Стандартный случай: обрезаем по ширине
    # Горизонтальная позиция (всегда центрируем)
    x = (in_w - target_w) // 2

    # Вертикальная позиция
    if config.crop_position == 'top':
        y = 0
    elif config.crop_position == 'bottom':
        y = in_h - in_h  # На самом деле не меняется, так как высота не обрезается
        y = 0  # Для стандартного случая всегда 0
    else:  # center
        y = 0  # Высота не меняется

    return f"crop={int(target_w)}:{in_h}:{x}:{y}"


def find_video_files(directory: Path) -> List[Path]:
    """
    Находит все видео файлы в директории.

    Args:
        directory: Директория для поиска

    Returns:
        List[Path]: Список путей к видео файлам
    """
    if not directory.exists():
        return []

    videos = [
        p for p in directory.iterdir()
        if p.is_file() and p.suffix.lower() in VIDEO_EXTENSIONS
    ]

    return sorted(videos)


# ============================================================================
# КОНВЕРТАЦИЯ
# ============================================================================

def convert_single_video(
    input_path: Path,
    output_dir: Path,
    config: ConversionConfig
) -> ConversionResult:
    """
    Конвертирует одно видео в формат 9:16.

    Args:
        input_path: Путь к исходному видео
        output_dir: Директория для сохранения
        config: Конфигурация конвертации

    Returns:
        ConversionResult: Результат конвертации
    """
    import time
    start_time = time.time()

    input_size = input_path.stat().st_size

    try:
        # Получаем метаданные
        metadata = get_video_metadata(input_path)
        if metadata is None:
            return ConversionResult(
                input_path=input_path,
                output_path=None,
                success=False,
                message="Не удалось получить метаданные",
                input_size=input_size,
                error="Metadata extraction failed"
            )

        # Проверяем минимальные требования
        if metadata.width < config.min_width or metadata.height < config.min_height:
            return ConversionResult(
                input_path=input_path,
                output_path=None,
                success=False,
                message=f"Разрешение слишком низкое: {metadata.width}x{metadata.height}",
                input_size=input_size,
                skipped=True
            )

        # Проверяем, уже ли видео 9:16
        if config.skip_if_vertical and metadata.is_9x16:
            return ConversionResult(
                input_path=input_path,
                output_path=None,
                success=True,
                message="Уже в формате 9:16, пропущено",
                input_size=input_size,
                skipped=True
            )

        # Создаём выходную директорию
        output_dir.mkdir(parents=True, exist_ok=True)

        # Формируем имя выходного файла
        output_path = output_dir / f"{input_path.stem}_9x16.mp4"

        # Проверяем перезапись
        if output_path.exists() and not config.overwrite:
            return ConversionResult(
                input_path=input_path,
                output_path=output_path,
                success=True,
                message="Файл уже существует, пропущено",
                input_size=input_size,
                skipped=True
            )

        # Строим фильтр обрезки
        crop_filter = build_crop_filter(metadata, config)

        # Строим команду ffmpeg
        cmd = [
            'ffmpeg',
            '-hide_banner',
            '-loglevel', 'error',
            '-stats',
        ]

        if config.overwrite:
            cmd.append('-y')

        cmd.extend([
            '-i', str(input_path),
            '-vf', crop_filter,
            '-c:v', config.video_codec,
            '-preset', config.preset,
            '-crf', str(config.crf),
            '-pix_fmt', config.pix_fmt,
        ])

        # Обработка аудио
        if config.remove_audio:
            cmd.append('-an')
        elif config.audio_codec:
            cmd.extend(['-c:a', config.audio_codec])
            if config.audio_bitrate:
                cmd.extend(['-b:a', config.audio_bitrate])

        cmd.extend([
            '-movflags', '+faststart',
            str(output_path)
        ])

        # Выполняем конвертацию
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True
        )

        # Проверяем результат
        if not output_path.exists():
            return ConversionResult(
                input_path=input_path,
                output_path=None,
                success=False,
                message="Выходной файл не создан",
                input_size=input_size,
                error="Output file not created",
                processing_time=time.time() - start_time
            )

        output_size = output_path.stat().st_size

        # Удаляем исходник если требуется
        if config.delete_source:
            try:
                input_path.unlink()
                deleted_msg = " (исходник удалён)"
            except Exception as e:
                deleted_msg = f" (не удалось удалить исходник: {e})"
        else:
            deleted_msg = ""

        processing_time = time.time() - start_time

        return ConversionResult(
            input_path=input_path,
            output_path=output_path,
            success=True,
            message=f"✅ {input_path.name} -> {output_path.name}{deleted_msg}",
            input_size=input_size,
            output_size=output_size,
            processing_time=processing_time
        )

    except subprocess.CalledProcessError as e:
        error_msg = e.stderr if e.stderr else str(e)
        return ConversionResult(
            input_path=input_path,
            output_path=None,
            success=False,
            message=f"❌ Ошибка FFmpeg: {input_path.name}",
            input_size=input_size,
            error=error_msg,
            processing_time=time.time() - start_time
        )

    except Exception as e:
        return ConversionResult(
            input_path=input_path,
            output_path=None,
            success=False,
            message=f"❌ Неожиданная ошибка: {input_path.name}",
            input_size=input_size,
            error=str(e),
            processing_time=time.time() - start_time
        )


# ============================================================================
# ПАКЕТНАЯ ОБРАБОТКА
# ============================================================================

class BatchConverter:
    """Класс для пакетной конвертации видео."""

    def __init__(self, config: ConversionConfig):
        self.config = config
        self.config.validate()

    def process_directory(
        self,
        input_dir: Path,
        output_dir: Path,
        save_report: bool = True
    ) -> Dict[str, Any]:
        """
        Обрабатывает все видео в директории.

        Args:
            input_dir: Входная директория
            output_dir: Выходная директория
            save_report: Сохранить отчёт в JSON

        Returns:
            Dict: Статистика обработки
        """
        logger.info("=" * 70)
        logger.info("🎬 ПАКЕТНАЯ КОНВЕРТАЦИЯ ВИДЕО В ФОРМАТ 9:16")
        logger.info("=" * 70)

        # Проверяем ffmpeg
        if not check_ffmpeg():
            raise RuntimeError("FFmpeg недоступен")

        # Находим видео файлы
        logger.info(f"📂 Входная директория: {input_dir}")
        logger.info(f"📁 Выходная директория: {output_dir}")

        video_files = find_video_files(input_dir)

        if not video_files:
            logger.warning("⚠️  Видео файлы не найдены")
            return {'total': 0, 'success': 0, 'failed': 0, 'skipped': 0}

        logger.info(f"🎥 Найдено файлов: {len(video_files)}")
        logger.info("")
        logger.info("⚙️  Параметры конвертации:")
        logger.info(f"   ├─ Кодек: {self.config.video_codec}")
        logger.info(f"   ├─ CRF: {self.config.crf}")
        logger.info(f"   ├─ Preset: {self.config.preset}")
        logger.info(f"   ├─ Позиция обрезки: {self.config.crop_position}")
        logger.info(
            f"   ├─ Удалить аудио: {'да' if self.config.remove_audio else 'нет'}")
        logger.info(
            f"   ├─ Удалить исходники: {'да' if self.config.delete_source else 'нет'}")
        logger.info(f"   └─ Потоков: {self.config.max_workers or 'авто'}")
        logger.info("")

        # Обработка
        results: List[ConversionResult] = []
        max_workers = self.config.max_workers or min(4, len(video_files))

        logger.info(f"🚀 Начинаю обработку ({max_workers} потоков)...")
        logger.info("")

        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(convert_single_video, video, output_dir, self.config): video
                for video in video_files
            }

            for future in as_completed(futures):
                result = future.result()
                results.append(result)

                # Выводим результат
                if result.skipped:
                    logger.info(f"⏭️  {result.message}")
                elif result.success:
                    logger.info(result.message)
                    if result.output_size > 0:
                        compression = (
                            result.output_size / result.input_size * 100) if result.input_size > 0 else 0
                        logger.info(f"   └─ Размер: {result.input_size / 1024 / 1024:.1f}MB -> "
                                    f"{result.output_size / 1024 / 1024:.1f}MB ({compression:.1f}%), "
                                    f"время: {result.processing_time:.1f}s")
                else:
                    logger.error(result.message)
                    if result.error:
                        logger.error(f"   └─ {result.error[:200]}")

        # Статистика
        total = len(results)
        success = sum(1 for r in results if r.success and not r.skipped)
        failed = sum(1 for r in results if not r.success)
        skipped = sum(1 for r in results if r.skipped)

        total_input_size = sum(r.input_size for r in results)
        total_output_size = sum(
            r.output_size for r in results if r.output_size > 0)
        total_time = sum(r.processing_time for r in results)

        logger.info("")
        logger.info("=" * 70)
        logger.info("📊 СТАТИСТИКА")
        logger.info("=" * 70)
        logger.info(f"Всего файлов: {total}")
        logger.info(f"✅ Успешно: {success}")
        logger.info(f"❌ Ошибок: {failed}")
        logger.info(f"⏭️  Пропущено: {skipped}")

        if total_output_size > 0:
            logger.info(
                f"📦 Входной размер: {total_input_size / 1024 / 1024:.1f} MB")
            logger.info(
                f"📦 Выходной размер: {total_output_size / 1024 / 1024:.1f} MB")
            logger.info(
                f"📉 Сжатие: {total_output_size / total_input_size * 100:.1f}%")

        logger.info(f"⏱️  Общее время: {total_time:.1f}s")
        logger.info("=" * 70)

        # Сохраняем отчёт
        if save_report and results:
            report_path = output_dir / \
                f"conversion_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            report = {
                'timestamp': datetime.now().isoformat(),
                'config': self.config.to_dict(),
                'statistics': {
                    'total': total,
                    'success': success,
                    'failed': failed,
                    'skipped': skipped,
                    'total_input_size_mb': round(total_input_size / 1024 / 1024, 2),
                    'total_output_size_mb': round(total_output_size / 1024 / 1024, 2),
                    'compression_ratio': round(total_output_size / total_input_size, 3) if total_input_size > 0 else 0,
                    'total_time_seconds': round(total_time, 2),
                },
                'results': [r.to_dict() for r in results]
            }

            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)

            logger.info(f"📄 Отчёт сохранён: {report_path}")

        return {
            'total': total,
            'success': success,
            'failed': failed,
            'skipped': skipped,
            'results': results
        }


# ============================================================================
# CLI
# ============================================================================

def main():
    """Главная функция для запуска из командной строки."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Пакетная конвертация видео в формат 9:16',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  %(prog)s
  %(prog)s -i videos -o output
  %(prog)s --crf 15 --preset slow
  %(prog)s --delete-source --position center
  %(prog)s --keep-audio --audio-bitrate 192k
        """
    )

    # Пути
    path_group = parser.add_argument_group('Пути')
    path_group.add_argument(
        '-i', '--input',
        type=Path,
        default=None,
        help='Входная директория (по умолчанию: ../assets/downloads)'
    )
    path_group.add_argument(
        '-o', '--output',
        type=Path,
        default=None,
        help='Выходная директория (по умолчанию: ../assets/stock_videos)'
    )

    # Параметры видео
    video_group = parser.add_argument_group('Параметры видео')
    video_group.add_argument(
        '--crf',
        type=int,
        default=18,
        help='CRF значение (0-51, меньше=лучше, 0=lossless, по умолчанию 18)'
    )
    video_group.add_argument(
        '--preset',
        choices=['ultrafast', 'superfast', 'veryfast', 'faster', 'fast',
                 'medium', 'slow', 'slower', 'veryslow'],
        default='medium',
        help='Preset скорости кодирования (по умолчанию medium)'
    )
    video_group.add_argument(
        '--position',
        choices=['top', 'center', 'bottom'],
        default='top',
        help='Позиция обрезки по вертикали (по умолчанию top)'
    )

    # Параметры аудио
    audio_group = parser.add_argument_group('Параметры аудио')
    audio_group.add_argument(
        '--keep-audio',
        action='store_true',
        help='Сохранить аудиодорожку'
    )
    audio_group.add_argument(
        '--audio-codec',
        default='aac',
        help='Аудио кодек (если аудио сохраняется)'
    )
    audio_group.add_argument(
        '--audio-bitrate',
        default='192k',
        help='Аудио bitrate (если аудио сохраняется)'
    )

    # Дополнительные опции
    misc_group = parser.add_argument_group('Дополнительно')
    misc_group.add_argument(
        '--delete-source',
        action='store_true',
        help='Удалить исходные файлы после успешной конвертации'
    )
    misc_group.add_argument(
        '--no-skip-vertical',
        action='store_true',
        help='Не пропускать уже вертикальные видео'
    )
    misc_group.add_argument(
        '--workers',
        type=int,
        default=None,
        help='Количество параллельных процессов (по умолчанию авто)'
    )
    misc_group.add_argument(
        '--min-width',
        type=int,
        default=720,
        help='Минимальная ширина для обработки'
    )
    misc_group.add_argument(
        '--min-height',
        type=int,
        default=1280,
        help='Минимальная высота для обработки'
    )
    misc_group.add_argument(
        '--no-report',
        action='store_true',
        help='Не сохранять JSON отчёт'
    )
    misc_group.add_argument(
        '--verbose',
        action='store_true',
        help='Подробный вывод'
    )

    args = parser.parse_args()

    # Определяем пути
    if args.input is None:
        # Относительно скрипта: ../assets/downloads
        script_dir = Path(__file__).resolve().parent
        input_dir = script_dir.parent / 'assets' / 'downloads'
    else:
        input_dir = args.input.resolve()

    if args.output is None:
        # Относительно скрипта: ../assets/stock_videos
        script_dir = Path(__file__).resolve().parent
        output_dir = script_dir.parent / 'assets' / 'stock_videos'
    else:
        output_dir = args.output.resolve()

    # Настройка логирования
    if args.verbose:
        logger.setLevel(logging.DEBUG)

    # Создание конфигурации
    config = ConversionConfig(
        crf=args.crf,
        preset=args.preset,
        crop_position=args.position,
        remove_audio=not args.keep_audio,
        audio_codec=args.audio_codec if args.keep_audio else None,
        audio_bitrate=args.audio_bitrate if args.keep_audio else None,
        delete_source=args.delete_source,
        skip_if_vertical=not args.no_skip_vertical,
        max_workers=args.workers,
        min_width=args.min_width,
        min_height=args.min_height,
    )

    try:
        # Запуск конвертации
        converter = BatchConverter(config)
        converter.process_directory(
            input_dir=input_dir,
            output_dir=output_dir,
            save_report=not args.no_report
        )

        return 0

    except KeyboardInterrupt:
        logger.warning("\n⚠️  Прервано пользователем")
        return 130

    except Exception as e:
        logger.error(f"\n❌ Ошибка: {e}", exc_info=args.verbose)
        return 1


if __name__ == '__main__':
    sys.exit(main())
