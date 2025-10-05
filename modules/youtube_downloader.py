#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YouTube Video Downloader - Загрузчик видео с YouTube в МАКСИМАЛЬНОМ качестве (до 4K).

ГАРАНТИЯ максимального качества:
- Скачивание в наивысшем доступном разрешении (2160p, 1440p, 1080p и т.д.)
- Сохранение оригинального качества БЕЗ перекодирования
- Автоматическое объединение видео + аудио
- Конвертация в MP4 только при необходимости (без потери качества)
- Реальное разрешение в названии файла
"""

import json
import logging
import re
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable
from urllib.parse import urlparse

import yt_dlp
from yt_dlp.utils import DownloadError, ExtractorError

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

YOUTUBE_DOMAINS = {
    'youtube.com',
    'www.youtube.com',
    'm.youtube.com',
    'youtu.be',
    'youtube-nocookie.com',
}

# Максимальное разрешение - 4K (2160p)
MAX_RESOLUTION = 2160


# ============================================================================
# КОНФИГУРАЦИЯ
# ============================================================================

@dataclass
class DownloadConfig:
    """Конфигурация загрузки YouTube видео."""

    # Пути
    output_dir: Path

    # Плейлисты
    download_playlist: bool = False
    playlist_start: int = 1
    playlist_end: Optional[int] = None
    playlist_items: Optional[str] = None

    # Производительность
    concurrent_fragments: int = 8
    rate_limit: Optional[str] = None
    retries: int = 10

    # Дополнительно
    cookies_file: Optional[Path] = None
    proxy: Optional[str] = None

    # Поведение
    overwrite: bool = False
    continue_download: bool = True

    def __post_init__(self):
        """Валидация после инициализации."""
        self.output_dir = Path(self.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        if self.cookies_file:
            self.cookies_file = Path(self.cookies_file)
            if not self.cookies_file.exists():
                raise FileNotFoundError(
                    f"Cookies файл не найден: {self.cookies_file}")

        if self.rate_limit and not re.match(r'^\d+[KMG]?$', self.rate_limit, re.IGNORECASE):
            raise ValueError(
                f"Неверный формат rate_limit: {self.rate_limit}. "
                f"Примеры: '1M', '500K', '100000'"
            )

    def get_ydl_opts(self) -> Dict[str, Any]:
        """Создает параметры для yt-dlp с МАКСИМАЛЬНЫМ качеством."""

        # КРИТИЧНО ВАЖНО: Правильный format selector для максимального качества
        # bv* = best video (любой кодек - VP9, H.264, AV1)
        # [height<=2160] = ограничение до 4K
        # +ba = лучшее аудио
        # /b = fallback на объединенные форматы
        format_string = 'bv*[height<=2160]+ba/b[height<=2160]/bv*+ba/b'

        # Шаблон имени: добавим разрешение ПОСЛЕ загрузки через postprocessor
        output_template = str(self.output_dir / '%(title)s.%(ext)s')

        opts = {
            # ФОРМАТ: максимальное качество до 4K
            'format': format_string,

            # Выходной формат - MP4 (слияние без перекодирования где возможно)
            'merge_output_format': 'mp4',

            # Имя файла
            'outtmpl': output_template,
            'restrictfilenames': False,

            # Плейлисты
            'noplaylist': not self.download_playlist,
            'playliststart': self.playlist_start,
            'playlistend': self.playlist_end,
            'playlist_items': self.playlist_items,

            # Производительность
            'concurrent_fragment_downloads': self.concurrent_fragments,
            'retries': self.retries,
            'fragment_retries': self.retries,

            # Поведение
            'overwrites': self.overwrite,
            'continuedl': self.continue_download,
            'keepvideo': False,  # Удалять промежуточные файлы после слияния
            'geo_bypass': True,

            # Безопасность
            'nocheckcertificate': False,

            # FFmpeg - только для слияния, НЕ для перекодирования
            'prefer_ffmpeg': True,
            'postprocessors': [],  # БЕЗ постобработки которая пережимает видео

            # Вывод
            'quiet': False,
            'no_warnings': False,
            'verbose': False,
        }

        # Опциональные параметры
        if self.rate_limit:
            opts['ratelimit'] = self._parse_rate_limit(self.rate_limit)

        if self.cookies_file:
            opts['cookiefile'] = str(self.cookies_file)

        if self.proxy:
            opts['proxy'] = self.proxy

        return opts

    @staticmethod
    def _parse_rate_limit(rate_str: str) -> int:
        """Конвертирует строку rate limit в байты/сек."""
        rate_str = rate_str.upper()
        multipliers = {'K': 1024, 'M': 1024**2, 'G': 1024**3}

        match = re.match(r'^(\d+)([KMG]?)$', rate_str)
        if match:
            value, unit = match.groups()
            return int(value) * multipliers.get(unit, 1)

        return int(rate_str)


# ============================================================================
# МОДЕЛИ ДАННЫХ
# ============================================================================

@dataclass
class VideoInfo:
    """Информация о видео."""

    id: str
    title: str
    url: str
    resolution: str  # "1920x1080"
    resolution_label: str  # "1080p"
    fps: Optional[float] = None
    duration: Optional[float] = None
    uploader: Optional[str] = None
    upload_date: Optional[str] = None
    view_count: Optional[int] = None
    filesize: Optional[int] = None
    thumbnail: Optional[str] = None

    @classmethod
    def from_ydl_info(cls, info: Dict[str, Any]) -> 'VideoInfo':
        """Создает VideoInfo из данных yt-dlp."""
        width = info.get('width', 0)
        height = info.get('height', 0)

        resolution = f"{width}x{height}" if width and height else "Unknown"
        resolution_label = f"{height}p" if height else "Unknown"

        return cls(
            id=info.get('id', ''),
            title=info.get('title', 'Unknown'),
            url=info.get('webpage_url', ''),
            resolution=resolution,
            resolution_label=resolution_label,
            fps=info.get('fps'),
            duration=info.get('duration'),
            uploader=info.get('uploader'),
            upload_date=info.get('upload_date'),
            view_count=info.get('view_count'),
            filesize=info.get('filesize') or info.get('filesize_approx'),
            thumbnail=info.get('thumbnail'),
        )

    def format_duration(self) -> str:
        """Форматирует длительность в читаемый вид."""
        if self.duration is None:
            return "Unknown"

        seconds = int(self.duration)
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60

        if hours > 0:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        return f"{minutes}:{secs:02d}"

    def format_filesize(self) -> str:
        """Форматирует размер файла."""
        if self.filesize is None:
            return "Unknown"

        size = float(self.filesize)
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"


@dataclass
class DownloadResult:
    """Результат загрузки."""

    url: str
    success: bool
    message: str
    video_info: Optional[VideoInfo] = None
    output_path: Optional[Path] = None
    # Реальное разрешение скачанного видео
    actual_resolution: Optional[str] = None
    download_time: float = 0.0
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Преобразует в словарь."""
        return {
            'url': self.url,
            'success': self.success,
            'message': self.message,
            'video_info': {
                'title': self.video_info.title,
                'available_resolution': self.video_info.resolution_label,
                'downloaded_resolution': self.actual_resolution or self.video_info.resolution_label,
                'duration': self.video_info.format_duration(),
                'uploader': self.video_info.uploader,
            } if self.video_info else None,
            'output_path': str(self.output_path) if self.output_path else None,
            'download_time': round(self.download_time, 2),
            'error': self.error,
        }


# ============================================================================
# УТИЛИТЫ
# ============================================================================

def validate_youtube_url(url: str) -> bool:
    """Проверяет, является ли URL ссылкой на YouTube."""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower().replace('www.', '')
        return domain in YOUTUBE_DOMAINS
    except Exception:
        return False


def extract_video_id(url: str) -> Optional[str]:
    """Извлекает ID видео из YouTube URL."""
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
        r'(?:embed\/)([0-9A-Za-z_-]{11})',
        r'youtu\.be\/([0-9A-Za-z_-]{11})',
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    return None


def format_bytes(bytes_value: float) -> str:
    """Форматирует байты в читаемый вид."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.1f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.1f} TB"


def format_time(seconds: float) -> str:
    """Форматирует секунды в читаемый вид."""
    if seconds < 60:
        return f"{seconds:.1f}s"

    minutes = int(seconds // 60)
    secs = int(seconds % 60)

    if minutes < 60:
        return f"{minutes}m {secs}s"

    hours = minutes // 60
    minutes = minutes % 60
    return f"{hours}h {minutes}m {secs}s"


def get_video_resolution_from_file(file_path: Path) -> Optional[str]:
    """
    Извлекает РЕАЛЬНОЕ разрешение из скачанного видео файла используя FFprobe.

    Args:
        file_path: Путь к видео файлу

    Returns:
        Строка с разрешением (например, "2160p") или None
    """
    try:
        import subprocess

        cmd = [
            'ffprobe',
            '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=height',
            '-of', 'csv=p=0',
            str(file_path)
        ]

        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=10)

        if result.returncode == 0 and result.stdout.strip():
            height = int(result.stdout.strip())
            return f"{height}p"
    except Exception as e:
        logger.warning(f"Не удалось определить разрешение из файла: {e}")

    return None


# ============================================================================
# PROGRESS TRACKER
# ============================================================================

class ProgressTracker:
    """Отслеживает и отображает прогресс загрузки."""

    def __init__(self, title: str = ""):
        self.title = title
        self.status = 'idle'
        self.downloaded_bytes = 0
        self.total_bytes = 0
        self.speed = 0.0
        self.eta = 0

    def __call__(self, d: Dict[str, Any]):
        """Callback для yt-dlp."""
        self.status = d.get('status', 'unknown')

        if self.status == 'downloading':
            # Безопасное получение значений с проверкой на None
            self.downloaded_bytes = int(d.get('downloaded_bytes') or 0)

            total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
            self.total_bytes = int(total)

            speed = d.get('speed')
            self.speed = float(speed) if speed is not None else 0.0

            eta = d.get('eta')
            self.eta = int(eta) if eta is not None else 0

            # Вычисление процента
            if self.total_bytes > 0:
                percent = (self.downloaded_bytes / self.total_bytes) * 100
            else:
                # Для HLS/DASH потоков используем фрагменты
                fragment_index = d.get('fragment_index')
                fragment_count = d.get('fragment_count')

                if isinstance(fragment_index, int) and isinstance(fragment_count, int) and fragment_count > 0:
                    percent = ((fragment_index + 1) / fragment_count) * 100
                else:
                    percent = 0.0

            downloaded = format_bytes(self.downloaded_bytes)
            total_str = format_bytes(
                self.total_bytes) if self.total_bytes > 0 else "Unknown"
            speed_str = f"{format_bytes(self.speed)}/s" if self.speed > 0 else "N/A"
            eta_str = format_time(self.eta) if self.eta > 0 else "N/A"

            print(
                f"\r📥 {percent:.1f}% | {downloaded}/{total_str} | "
                f"⚡ {speed_str} | ⏱️  ETA: {eta_str}",
                end='',
                flush=True
            )

        elif self.status == 'finished':
            print("\n✅ Загрузка завершена, обработка...")

        elif self.status == 'error':
            print("\n❌ Ошибка загрузки")


# ============================================================================
# ГЛАВНЫЙ КЛАСС
# ============================================================================

class YouTubeDownloader:
    """Загрузчик видео с YouTube в МАКСИМАЛЬНОМ качестве (до 4K)."""

    def __init__(self, config: DownloadConfig):
        """
        Инициализация загрузчика.

        Args:
            config: Конфигурация загрузки
        """
        self.config = config

    def get_video_info(self, url: str) -> Optional[VideoInfo]:
        """
        Получает информацию о видео без загрузки.

        Args:
            url: URL видео

        Returns:
            VideoInfo или None в случае ошибки
        """
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if info:
                    return VideoInfo.from_ydl_info(info)
        except Exception as e:
            logger.error(f"Ошибка получения информации: {e}")

        return None

    def list_available_formats(self, url: str):
        """
        Выводит список доступных форматов для отладки.

        Args:
            url: URL видео
        """
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'listformats': True,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

                if 'formats' in info:
                    logger.info("📋 Доступные форматы:")

                    # Фильтруем только видео форматы
                    video_formats = [
                        f for f in info['formats']
                        if f.get('vcodec') != 'none' and f.get('height')
                    ]

                    # Сортируем по высоте
                    video_formats.sort(key=lambda x: x.get(
                        'height', 0), reverse=True)

                    for fmt in video_formats[:10]:  # Топ 10
                        height = fmt.get('height', 0)
                        fps = fmt.get('fps', 0)
                        vcodec = fmt.get('vcodec', 'unknown')
                        ext = fmt.get('ext', 'unknown')
                        format_id = fmt.get('format_id', 'unknown')

                        logger.info(
                            f"   [{format_id}] {height}p{fps} {vcodec} ({ext})"
                        )
        except Exception as e:
            logger.error(f"Ошибка получения форматов: {e}")

    def download(
        self,
        url: str,
        progress_callback: Optional[Callable] = None
    ) -> DownloadResult:
        """
        Загружает видео с YouTube в МАКСИМАЛЬНОМ качестве (до 4K).

        Args:
            url: URL видео
            progress_callback: Callback для отслеживания прогресса

        Returns:
            DownloadResult с результатом загрузки
        """
        start_time = time.time()

        # Валидация URL
        if not validate_youtube_url(url):
            return DownloadResult(
                url=url,
                success=False,
                message="❌ Некорректный YouTube URL",
                error="Invalid YouTube URL"
            )

        try:
            # Получение информации о видео
            logger.info(f"📹 Получение информации о видео...")
            video_info = self.get_video_info(url)

            if video_info is None:
                return DownloadResult(
                    url=url,
                    success=False,
                    message="❌ Не удалось получить информацию о видео",
                    error="Failed to extract video info"
                )

            # Вывод информации
            logger.info(f"📺 Название: {video_info.title}")
            logger.info(f"   ├─ Автор: {video_info.uploader or 'Unknown'}")
            logger.info(
                f"   ├─ Макс. разрешение: {video_info.resolution_label}")
            logger.info(f"   ├─ Длительность: {video_info.format_duration()}")
            logger.info(f"   └─ Размер: ~{video_info.format_filesize()}")

            # Показываем доступные форматы
            logger.info("")
            self.list_available_formats(url)

            # Настройка yt-dlp
            ydl_opts = self.config.get_ydl_opts()

            # Progress hook
            if progress_callback is None:
                progress_callback = ProgressTracker(video_info.title)

            ydl_opts['progress_hooks'] = [progress_callback]

            logger.info("")
            logger.info(f"⚙️  Параметры загрузки:")
            logger.info(f"   ├─ Формат: МАКСИМАЛЬНОЕ качество до 4K (2160p)")
            logger.info(f"   ├─ Выход: MP4 (без потери качества)")
            logger.info(f"   ├─ Папка: {self.config.output_dir}")
            if self.config.rate_limit:
                logger.info(
                    f"   └─ Ограничение скорости: {self.config.rate_limit}")

            logger.info("")
            logger.info("🚀 Начало загрузки в МАКСИМАЛЬНОМ качестве...")

            # Загрузка
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)

                # Определение пути к файлу
                output_path = self._find_output_file(info, ydl)

            download_time = time.time() - start_time

            if output_path and output_path.exists():
                # Определяем РЕАЛЬНОЕ разрешение из файла
                actual_resolution = get_video_resolution_from_file(output_path)

                if actual_resolution:
                    logger.info(
                        f"✓ Фактическое разрешение: {actual_resolution}")

                    # Переименовываем файл с правильным разрешением
                    new_name = f"{output_path.stem}_{actual_resolution}{output_path.suffix}"
                    new_path = output_path.parent / new_name

                    try:
                        output_path.rename(new_path)
                        output_path = new_path
                        logger.info(f"✓ Файл переименован: {new_path.name}")
                    except Exception as e:
                        logger.warning(f"Не удалось переименовать файл: {e}")
                else:
                    actual_resolution = video_info.resolution_label

                file_size = output_path.stat().st_size
                logger.info("")
                logger.info(
                    f"✅ Загрузка завершена за {format_time(download_time)}")
                logger.info(f"📁 Файл: {output_path.name}")
                logger.info(f"💾 Размер: {format_bytes(file_size)}")
                logger.info(f"🎬 Разрешение: {actual_resolution}")

                return DownloadResult(
                    url=url,
                    success=True,
                    message=f"✅ {video_info.title} ({actual_resolution})",
                    video_info=video_info,
                    output_path=output_path,
                    actual_resolution=actual_resolution,
                    download_time=download_time
                )
            else:
                raise FileNotFoundError("Загруженный файл не найден")

        except DownloadError as e:
            return DownloadResult(
                url=url,
                success=False,
                message=f"❌ Ошибка загрузки: {str(e)}",
                error=str(e),
                download_time=time.time() - start_time
            )

        except ExtractorError as e:
            return DownloadResult(
                url=url,
                success=False,
                message=f"❌ Ошибка извлечения: {str(e)}",
                error=str(e),
                download_time=time.time() - start_time
            )

        except Exception as e:
            logger.error(f"❌ Неожиданная ошибка: {e}", exc_info=True)
            return DownloadResult(
                url=url,
                success=False,
                message=f"❌ Ошибка: {str(e)}",
                error=str(e),
                download_time=time.time() - start_time
            )

    def download_multiple(
        self,
        urls: List[str],
        save_report: bool = True
    ) -> Dict[str, Any]:
        """
        Загружает несколько видео.

        Args:
            urls: Список URL
            save_report: Сохранить отчет в JSON

        Returns:
            Словарь со статистикой
        """
        logger.info("=" * 70)
        logger.info(f"🎬 ПАКЕТНАЯ ЗАГРУЗКА ({len(urls)} видео)")
        logger.info("=" * 70)
        logger.info("")

        results = []

        for i, url in enumerate(urls, 1):
            logger.info(f"[{i}/{len(urls)}] {url}")
            logger.info("-" * 70)

            result = self.download(url)
            results.append(result)

            logger.info("")

        # Статистика
        total = len(results)
        success = sum(1 for r in results if r.success)
        failed = total - success
        total_time = sum(r.download_time for r in results)

        logger.info("=" * 70)
        logger.info("📊 СТАТИСТИКА")
        logger.info("=" * 70)
        logger.info(f"Всего: {total}")
        logger.info(f"✅ Успешно: {success}")
        logger.info(f"❌ Ошибок: {failed}")
        logger.info(f"⏱️  Общее время: {format_time(total_time)}")

        # Показываем разрешения скачанных видео
        if success > 0:
            logger.info("")
            logger.info("🎬 Скачанные разрешения:")
            for r in results:
                if r.success and r.actual_resolution:
                    logger.info(
                        f"   • {r.actual_resolution} - {r.video_info.title[:50]}")

        logger.info("=" * 70)

        # Сохранение отчета
        if save_report and results:
            report_path = self.config.output_dir / \
                f"download_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

            report = {
                'timestamp': datetime.now().isoformat(),
                'total': total,
                'success': success,
                'failed': failed,
                'total_time': total_time,
                'results': [r.to_dict() for r in results]
            }

            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)

            logger.info(f"📄 Отчет сохранен: {report_path}")

        return {
            'total': total,
            'success': success,
            'failed': failed,
            'results': results
        }

    def _find_output_file(self, info: Dict[str, Any], ydl) -> Optional[Path]:
        """Находит загруженный файл."""
        # Способ 1: из requested_downloads
        if 'requested_downloads' in info and info['requested_downloads']:
            filepath = info['requested_downloads'][0].get('filepath')
            if filepath:
                path = Path(filepath)
                if path.exists():
                    return path

        # Способ 2: prepare_filename
        filename = ydl.prepare_filename(info)
        path = Path(filename)

        # Проверка с расширением .mp4
        if not path.exists() and path.suffix != '.mp4':
            path = path.with_suffix('.mp4')

        if path.exists():
            return path

        # Способ 3: поиск по паттерну (последний созданный MP4)
        title = info.get('title', '')

        if title:
            # Ищем все MP4 файлы с этим названием
            mp4_files = list(self.config.output_dir.glob("*.mp4"))

            if mp4_files:
                # Возвращаем самый свежий
                return max(mp4_files, key=lambda p: p.stat().st_mtime)

        return None


# ============================================================================
# CLI (для тестирования)
# ============================================================================

def main():
    """CLI для тестирования."""
    import argparse

    parser = argparse.ArgumentParser(
        description='YouTube Video Downloader - МАКСИМАЛЬНОЕ качество до 4K'
    )

    parser.add_argument('url', help='YouTube URL')
    parser.add_argument('-o', '--output', type=Path,
                        help='Выходная директория')
    parser.add_argument('--playlist', action='store_true',
                        help='Загрузить плейлист')
    parser.add_argument('--rate-limit', help='Ограничение скорости (1M, 500K)')
    parser.add_argument('--proxy', help='Прокси сервер')
    parser.add_argument('--cookies', type=Path, help='Файл cookies')
    parser.add_argument('--list-formats', action='store_true',
                        help='Показать доступные форматы')

    args = parser.parse_args()

    try:
        # Создание конфигурации
        output_dir = args.output or Path('assets/downloads')

        config = DownloadConfig(
            output_dir=output_dir,
            download_playlist=args.playlist,
            rate_limit=args.rate_limit,
            proxy=args.proxy,
            cookies_file=args.cookies,
        )

        # Загрузка
        downloader = YouTubeDownloader(config)

        if args.list_formats:
            downloader.list_available_formats(args.url)
            return 0

        result = downloader.download(args.url)

        return 0 if result.success else 1

    except KeyboardInterrupt:
        logger.warning("\n⚠️  Прервано пользователем")
        return 130

    except Exception as e:
        logger.error(f"\n❌ Ошибка: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
