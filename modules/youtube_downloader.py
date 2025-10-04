#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YouTube Video Downloader - Профессиональный загрузчик видео с YouTube.

Возможности:
- Выбор качества видео (от 144p до 8K)
- Загрузка плейлистов
- Субтитры и метаданные
- Возобновление прерванных загрузок
- Пакетная обработка URL
- Ограничение скорости
- Поддержка cookies для приватных видео
- Подробное логирование и статистика
"""

import json
import logging
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable
from urllib.parse import urlparse, parse_qs

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

QUALITY_PRESETS = {
    'best': 'bestvideo+bestaudio/best',
    '4320p': 'bestvideo[height<=4320]+bestaudio/best',  # 8K
    '2160p': 'bestvideo[height<=2160]+bestaudio/best',  # 4K
    '1440p': 'bestvideo[height<=1440]+bestaudio/best',  # 2K
    '1080p': 'bestvideo[height<=1080]+bestaudio/best',  # Full HD
    '720p': 'bestvideo[height<=720]+bestaudio/best',    # HD
    '480p': 'bestvideo[height<=480]+bestaudio/best',
    '360p': 'bestvideo[height<=360]+bestaudio/best',
    '240p': 'bestvideo[height<=240]+bestaudio/best',
    '144p': 'bestvideo[height<=144]+bestaudio/best',
    'audio': 'bestaudio/best',  # Только аудио
}


# ============================================================================
# КОНФИГУРАЦИЯ
# ============================================================================

@dataclass
class DownloadConfig:
    """Конфигурация загрузки."""

    # Качество
    quality: str = '1080p'  # Может быть preset или custom format string
    format_preference: str = 'mp4'  # Предпочитаемый формат

    # Пути
    output_dir: Optional[Path] = None
    output_template: str = '%(title)s.%(ext)s'  # Шаблон имени файла

    # Субтитры и метаданные
    write_subtitles: bool = False
    write_auto_subtitles: bool = False
    subtitle_language: str = 'en,ru'  # Языки субтитров
    write_description: bool = False
    write_info_json: bool = False
    write_thumbnail: bool = False
    embed_thumbnail: bool = False
    embed_metadata: bool = True

    # Плейлисты
    download_playlist: bool = False
    playlist_start: int = 1
    playlist_end: Optional[int] = None
    playlist_items: Optional[str] = None  # Например: "1,2,5-7"

    # Производительность
    concurrent_fragments: int = 4
    rate_limit: Optional[str] = None  # Например: "1M" для 1 MB/s
    retries: int = 10
    fragment_retries: int = 10

    # Дополнительно
    cookies_file: Optional[Path] = None
    proxy: Optional[str] = None
    geo_bypass: bool = True
    age_limit: Optional[int] = None

    # Поведение
    overwrite: bool = False
    continue_download: bool = True
    keep_video: bool = True  # Сохранять видео после обработки

    def validate(self):
        """Валидация конфигурации."""
        # Проверяем качество
        if self.quality not in QUALITY_PRESETS and not self.quality.startswith('bestvideo'):
            logger.warning(
                f"Неизвестный preset качества: {self.quality}. "
                f"Доступные: {', '.join(QUALITY_PRESETS.keys())}"
            )

        # Проверяем cookies
        if self.cookies_file and not self.cookies_file.exists():
            raise FileNotFoundError(
                f"Cookies файл не найден: {self.cookies_file}")

        # Проверяем rate limit формат
        if self.rate_limit:
            if not re.match(r'^\d+[KMG]?$', self.rate_limit, re.IGNORECASE):
                raise ValueError(
                    f"Неверный формат rate_limit: {self.rate_limit}. "
                    f"Примеры: '1M', '500K', '100000'"
                )

    def get_format_string(self) -> str:
        """Получает строку формата для yt-dlp."""
        if self.quality in QUALITY_PRESETS:
            return QUALITY_PRESETS[self.quality]
        return self.quality

    def to_ydl_opts(self) -> Dict[str, Any]:
        """Преобразует конфигурацию в параметры для yt-dlp."""
        opts = {
            'format': self.get_format_string(),
            'merge_output_format': self.format_preference,
            'outtmpl': str(self.output_dir / self.output_template) if self.output_dir else self.output_template,

            # Субтитры
            'writesubtitles': self.write_subtitles,
            'writeautomaticsub': self.write_auto_subtitles,
            'subtitleslangs': self.subtitle_language.split(',') if self.subtitle_language else [],

            # Метаданные
            'writedescription': self.write_description,
            'writeinfojson': self.write_info_json,
            'writethumbnail': self.write_thumbnail,
            'embedthumbnail': self.embed_thumbnail,
            'addmetadata': self.embed_metadata,

            # Плейлисты
            'noplaylist': not self.download_playlist,
            'playliststart': self.playlist_start,
            'playlistend': self.playlist_end,
            'playlist_items': self.playlist_items,

            # Производительность
            'concurrent_fragment_downloads': self.concurrent_fragments,
            'retries': self.retries,
            'fragment_retries': self.fragment_retries,

            # Поведение
            'overwrites': self.overwrite,
            'continuedl': self.continue_download,
            'keepvideo': self.keep_video,
            'geo_bypass': self.geo_bypass,

            # Прочее
            'nocheckcertificate': False,
            'prefer_ffmpeg': True,
            'quiet': False,
            'no_warnings': False,
        }

        # Опциональные параметры
        if self.rate_limit:
            opts['ratelimit'] = self._parse_rate_limit(self.rate_limit)

        if self.cookies_file:
            opts['cookiefile'] = str(self.cookies_file)

        if self.proxy:
            opts['proxy'] = self.proxy

        if self.age_limit is not None:
            opts['age_limit'] = self.age_limit

        return opts

    @staticmethod
    def _parse_rate_limit(rate_str: str) -> int:
        """Парсит строку rate limit в байты в секунду."""
        rate_str = rate_str.upper()
        multipliers = {'K': 1024, 'M': 1024**2, 'G': 1024**3}

        match = re.match(r'^(\d+)([KMG]?)$', rate_str)
        if match:
            value, unit = match.groups()
            return int(value) * multipliers.get(unit, 1)

        return int(rate_str)


@dataclass
class VideoInfo:
    """Информация о видео."""
    id: str
    title: str
    url: str
    duration: Optional[float] = None
    uploader: Optional[str] = None
    upload_date: Optional[str] = None
    view_count: Optional[int] = None
    like_count: Optional[int] = None
    description: Optional[str] = None
    thumbnail: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    fps: Optional[float] = None
    filesize: Optional[int] = None

    @classmethod
    def from_ydl_info(cls, info: Dict[str, Any]) -> 'VideoInfo':
        """Создаёт VideoInfo из словаря yt-dlp."""
        return cls(
            id=info.get('id', ''),
            title=info.get('title', 'Unknown'),
            url=info.get('webpage_url', ''),
            duration=info.get('duration'),
            uploader=info.get('uploader'),
            upload_date=info.get('upload_date'),
            view_count=info.get('view_count'),
            like_count=info.get('like_count'),
            description=info.get('description'),
            thumbnail=info.get('thumbnail'),
            width=info.get('width'),
            height=info.get('height'),
            fps=info.get('fps'),
            filesize=info.get('filesize') or info.get('filesize_approx'),
        )

    def format_duration(self) -> str:
        """Форматирует длительность."""
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

        for unit in ['B', 'KB', 'MB', 'GB']:
            if self.filesize < 1024:
                return f"{self.filesize:.1f} {unit}"
            self.filesize /= 1024

        return f"{self.filesize:.1f} TB"

    def to_dict(self) -> dict:
        """Преобразование в словарь."""
        return {
            'id': self.id,
            'title': self.title,
            'url': self.url,
            'duration': self.duration,
            'duration_formatted': self.format_duration(),
            'uploader': self.uploader,
            'upload_date': self.upload_date,
            'view_count': self.view_count,
            'like_count': self.like_count,
            'resolution': f"{self.width}x{self.height}" if self.width and self.height else None,
            'fps': self.fps,
            'filesize': self.filesize,
            'filesize_formatted': self.format_filesize(),
        }


@dataclass
class DownloadResult:
    """Результат загрузки."""
    url: str
    success: bool
    message: str
    video_info: Optional[VideoInfo] = None
    output_path: Optional[Path] = None
    download_time: float = 0.0
    error: Optional[str] = None

    def to_dict(self) -> dict:
        """Преобразование в словарь."""
        return {
            'url': self.url,
            'success': self.success,
            'message': self.message,
            'video_info': self.video_info.to_dict() if self.video_info else None,
            'output_path': str(self.output_path) if self.output_path else None,
            'download_time': round(self.download_time, 2),
            'error': self.error,
        }


# ============================================================================
# УТИЛИТЫ
# ============================================================================

def validate_youtube_url(url: str) -> bool:
    """
    Проверяет, является ли URL ссылкой на YouTube.

    Args:
        url: URL для проверки

    Returns:
        bool: True если это YouTube URL
    """
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        # Удаляем www. если есть
        domain = domain.replace('www.', '')

        return domain in YOUTUBE_DOMAINS
    except Exception:
        return False


def extract_video_id(url: str) -> Optional[str]:
    """
    Извлекает ID видео из YouTube URL.

    Args:
        url: YouTube URL

    Returns:
        Optional[str]: ID видео или None
    """
    # Паттерны для разных форматов URL
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


def format_bytes(bytes_value: int) -> str:
    """Форматирует байты в читаемый вид."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.1f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.1f} PB"


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


# ============================================================================
# PROGRESS HOOKS
# ============================================================================

class ProgressTracker:
    """Отслеживает прогресс загрузки."""

    def __init__(self, title: str = ""):
        self.title = title
        self.status = 'idle'
        self.downloaded_bytes = 0
        self.total_bytes = 0
        self.speed = 0
        self.eta = 0

    def __call__(self, d: Dict[str, Any]):
        """Hook для yt-dlp."""
        self.status = d.get('status', 'unknown')

        if self.status == 'downloading':
            self.downloaded_bytes = d.get('downloaded_bytes', 0)
            self.total_bytes = d.get('total_bytes') or d.get(
                'total_bytes_estimate', 0)
            self.speed = d.get('speed', 0)
            self.eta = d.get('eta', 0)

            # Форматируем вывод
            percent = (self.downloaded_bytes / self.total_bytes *
                       100) if self.total_bytes > 0 else 0
            downloaded = format_bytes(self.downloaded_bytes)
            total = format_bytes(
                self.total_bytes) if self.total_bytes > 0 else "Unknown"
            speed_str = f"{format_bytes(self.speed)}/s" if self.speed > 0 else "N/A"
            eta_str = format_time(self.eta) if self.eta > 0 else "N/A"

            print(
                f"\r📥 {percent:.1f}% | {downloaded}/{total} | "
                f"⚡ {speed_str} | ⏱️  ETA: {eta_str}",
                end='',
                flush=True
            )

        elif self.status == 'finished':
            print("\n✅ Загрузка завершена, обработка файла...")

        elif self.status == 'error':
            print("\n❌ Ошибка загрузки")


# ============================================================================
# ГЛАВНЫЙ КЛАСС
# ============================================================================

class YouTubeDownloader:
    """Профессиональный загрузчик YouTube видео."""

    def __init__(self, config: Optional[DownloadConfig] = None):
        """
        Инициализация загрузчика.

        Args:
            config: Конфигурация загрузки
        """
        self.config = config or DownloadConfig()
        self.config.validate()

        # Устанавливаем output_dir по умолчанию
        if self.config.output_dir is None:
            script_dir = Path(__file__).resolve().parent
            self.config.output_dir = script_dir.parent / 'assets' / 'downloads'

        self.config.output_dir.mkdir(parents=True, exist_ok=True)

    def get_video_info(self, url: str) -> Optional[VideoInfo]:
        """
        Получает информацию о видео без загрузки.

        Args:
            url: URL видео

        Returns:
            Optional[VideoInfo]: Информация о видео или None
        """
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return VideoInfo.from_ydl_info(info)
        except Exception as e:
            logger.error(f"Не удалось получить информацию о видео: {e}")
            return None

    def download(
        self,
        url: str,
        progress_callback: Optional[Callable] = None
    ) -> DownloadResult:
        """
        Загружает видео с YouTube.

        Args:
            url: URL видео
            progress_callback: Callback для отслеживания прогресса

        Returns:
            DownloadResult: Результат загрузки
        """
        import time
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
            # Получаем информацию о видео
            logger.info(f"📹 Получаю информацию о видео...")
            video_info = self.get_video_info(url)

            if video_info is None:
                return DownloadResult(
                    url=url,
                    success=False,
                    message="❌ Не удалось получить информацию о видео",
                    error="Failed to extract video info"
                )

            logger.info(f"📺 Название: {video_info.title}")
            logger.info(f"   ├─ Автор: {video_info.uploader or 'Unknown'}")
            logger.info(f"   ├─ Длительность: {video_info.format_duration()}")
            if video_info.width and video_info.height:
                logger.info(
                    f"   ├─ Разрешение: {video_info.width}x{video_info.height}")
            if video_info.view_count:
                logger.info(f"   ├─ Просмотров: {video_info.view_count:,}")
            logger.info(f"   └─ Размер: ~{video_info.format_filesize()}")

            # Настройка yt-dlp
            ydl_opts = self.config.to_ydl_opts()

            # Добавляем progress hook
            if progress_callback is None:
                progress_callback = ProgressTracker(video_info.title)

            ydl_opts['progress_hooks'] = [progress_callback]

            # Логирование параметров
            logger.info("")
            logger.info(f"⚙️  Параметры загрузки:")
            logger.info(f"   ├─ Качество: {self.config.quality}")
            logger.info(f"   ├─ Формат: {self.config.format_preference}")
            logger.info(f"   ├─ Папка: {self.config.output_dir}")
            if self.config.write_subtitles or self.config.write_auto_subtitles:
                logger.info(
                    f"   ├─ Субтитры: да ({self.config.subtitle_language})")
            if self.config.rate_limit:
                logger.info(
                    f"   ├─ Ограничение скорости: {self.config.rate_limit}")
            logger.info(
                f"   └─ Продолжить при обрыве: {'да' if self.config.continue_download else 'нет'}")

            logger.info("")
            logger.info("🚀 Начинаю загрузку...")

            # Загрузка
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)

                # Определяем путь к загруженному файлу
                if 'requested_downloads' in info and info['requested_downloads']:
                    output_path = Path(
                        info['requested_downloads'][0]['filepath'])
                else:
                    # Пытаемся предсказать путь
                    filename = ydl.prepare_filename(info)
                    output_path = Path(filename)

                if not output_path.exists():
                    # Ищем файл по паттерну
                    pattern = f"{video_info.title}.*"
                    matches = list(self.config.output_dir.glob(pattern))
                    if matches:
                        output_path = matches[0]

            download_time = time.time() - start_time

            logger.info("")
            logger.info(
                f"✅ Загрузка завершена за {format_time(download_time)}")
            logger.info(f"📁 Файл: {output_path}")

            if output_path.exists():
                file_size = output_path.stat().st_size
                logger.info(f"💾 Размер: {format_bytes(file_size)}")

            return DownloadResult(
                url=url,
                success=True,
                message=f"✅ {video_info.title}",
                video_info=video_info,
                output_path=output_path,
                download_time=download_time
            )

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
                message=f"❌ Ошибка извлечения данных: {str(e)}",
                error=str(e),
                download_time=time.time() - start_time
            )

        except Exception as e:
            logger.error(f"❌ Неожиданная ошибка: {e}", exc_info=True)
            return DownloadResult(
                url=url,
                success=False,
                message=f"❌ Неожиданная ошибка: {str(e)}",
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
            urls: Список URL для загрузки
            save_report: Сохранить отчёт в JSON

        Returns:
            Dict: Статистика загрузок
        """
        logger.info("=" * 70)
        logger.info(f"🎬 ПАКЕТНАЯ ЗАГРУЗКА ВИДЕО ({len(urls)} шт.)")
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
        logger.info("=" * 70)

        # Сохраняем отчёт
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

            logger.info(f"📄 Отчёт сохранён: {report_path}")

        return {
            'total': total,
            'success': success,
            'failed': failed,
            'results': results
        }


# ============================================================================
# CLI
# ============================================================================

def main():
    """Главная функция для CLI."""
    import argparse

    parser = argparse.ArgumentParser(
        description='YouTube Video Downloader - Профессиональный загрузчик',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  %(prog)s "https://www.youtube.com/watch?v=..."
  %(prog)s URL -q 4K -o ~/Videos
  %(prog)s URL --quality audio -f m4a
  %(prog)s URL --subtitles --subtitle-lang "en,ru"
  %(prog)s URL --playlist --playlist-items "1-5,8,10"
  %(prog)s -f urls.txt --batch
        """
    )

    # URL
    parser.add_argument(
        'url',
        nargs='?',
        help='YouTube URL (или -f для пакетной загрузки)'
    )

    # Основные параметры
    main_group = parser.add_argument_group('Основные параметры')
    main_group.add_argument(
        '-q', '--quality',
        default='1080p',
        help=f'Качество видео ({", ".join(QUALITY_PRESETS.keys())})'
    )
    main_group.add_argument(
        '-f', '--format',
        default='mp4',
        help='Формат файла (mp4, mkv, webm, ...)'
    )
    main_group.add_argument(
        '-o', '--output',
        type=Path,
        help='Выходная директория'
    )

    # Субтитры и метаданные
    meta_group = parser.add_argument_group('Субтитры и метаданные')
    meta_group.add_argument(
        '--subtitles',
        action='store_true',
        help='Скачать субтитры'
    )
    meta_group.add_argument(
        '--auto-subtitles',
        action='store_true',
        help='Скачать автоматические субтитры'
    )
    meta_group.add_argument(
        '--subtitle-lang',
        default='en,ru',
        help='Языки субтитров (через запятую)'
    )
    meta_group.add_argument(
        '--thumbnail',
        action='store_true',
        help='Скачать миниатюру'
    )
    meta_group.add_argument(
        '--description',
        action='store_true',
        help='Сохранить описание'
    )
    meta_group.add_argument(
        '--info-json',
        action='store_true',
        help='Сохранить JSON с метаданными'
    )

    # Плейлисты
    playlist_group = parser.add_argument_group('Плейлисты')
    playlist_group.add_argument(
        '--playlist',
        action='store_true',
        help='Загрузить весь плейлист'
    )
    playlist_group.add_argument(
        '--playlist-start',
        type=int,
        default=1,
        help='Начать с видео N'
    )
    playlist_group.add_argument(
        '--playlist-end',
        type=int,
        help='Закончить на видео N'
    )
    playlist_group.add_argument(
        '--playlist-items',
        help='Номера видео (например: "1,2,5-7")'
    )

    # Производительность
    perf_group = parser.add_argument_group('Производительность')
    perf_group.add_argument(
        '--rate-limit',
        help='Ограничение скорости (например: 1M, 500K)'
    )
    perf_group.add_argument(
        '--concurrent-fragments',
        type=int,
        default=4,
        help='Количество одновременно загружаемых фрагментов'
    )

    # Дополнительно
    misc_group = parser.add_argument_group('Дополнительно')
    misc_group.add_argument(
        '--cookies',
        type=Path,
        help='Файл cookies для авторизации'
    )
    misc_group.add_argument(
        '--proxy',
        help='Прокси сервер'
    )
    misc_group.add_argument(
        '--batch',
        type=Path,
        help='Файл со списком URL (по одному на строку)'
    )
    misc_group.add_argument(
        '--info-only',
        action='store_true',
        help='Только получить информацию, не загружать'
    )
    misc_group.add_argument(
        '--verbose',
        action='store_true',
        help='Подробный вывод'
    )

    args = parser.parse_args()

    # Настройка логирования
    if args.verbose:
        logger.setLevel(logging.DEBUG)

    # Проверка URL
    if not args.url and not args.batch:
        # Интерактивный режим
        print("=" * 70)
        print("YouTube Video Downloader")
        print("=" * 70)
        print()
        url = input("Введите YouTube URL: ").strip()
        if not url:
            print("❌ URL не может быть пустым")
            return 1
    elif args.batch:
        # Пакетная загрузка из файла
        if not args.batch.exists():
            print(f"❌ Файл не найден: {args.batch}")
            return 1

        urls = []
        with open(args.batch, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    urls.append(line)

        if not urls:
            print("❌ В файле нет URL")
            return 1
    else:
        url = args.url
        urls = None

    try:
        # Создание конфигурации
        config = DownloadConfig(
            quality=args.quality,
            format_preference=args.format,
            output_dir=args.output,
            write_subtitles=args.subtitles,
            write_auto_subtitles=args.auto_subtitles,
            subtitle_language=args.subtitle_lang,
            write_description=args.description,
            write_info_json=args.info_json,
            write_thumbnail=args.thumbnail,
            download_playlist=args.playlist,
            playlist_start=args.playlist_start,
            playlist_end=args.playlist_end,
            playlist_items=args.playlist_items,
            concurrent_fragments=args.concurrent_fragments,
            rate_limit=args.rate_limit,
            cookies_file=args.cookies,
            proxy=args.proxy,
        )

        # Создание загрузчика
        downloader = YouTubeDownloader(config)

        # Режим только информации
        if args.info_only:
            video_info = downloader.get_video_info(
                url if not urls else urls[0])
            if video_info:
                print(json.dumps(video_info.to_dict(),
                      indent=2, ensure_ascii=False))
            return 0

        # Загрузка
        if urls:
            # Пакетная загрузка
            downloader.download_multiple(urls)
        else:
            # Одиночная загрузка
            downloader.download(url)

        return 0

    except KeyboardInterrupt:
        logger.warning("\n⚠️  Прервано пользователем")
        return 130

    except Exception as e:
        logger.error(f"\n❌ Ошибка: {e}", exc_info=args.verbose if hasattr(
            args, 'verbose') else False)
        return 1


if __name__ == "__main__":
    sys.exit(main())
