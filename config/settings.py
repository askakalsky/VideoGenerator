"""
Настройки приложения
"""

from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
import json


@dataclass
class AppSettings:
    """Глобальные настройки приложения."""

    # Пути
    base_dir: Path = Path(__file__).parent.parent
    downloads_dir: Path = field(
        default_factory=lambda: Path('assets/downloads'))
    output_dir: Path = field(default_factory=lambda: Path('assets/output'))
    temp_dir: Path = field(default_factory=lambda: Path('assets/temp'))
    music_dir: Path = field(default_factory=lambda: Path('assets/music'))
    stock_videos_dir: Path = field(
        default_factory=lambda: Path('assets/stock_videos'))

    # Файлы
    history_file: Path = field(
        default_factory=lambda: Path('assets/history.json'))
    settings_file: Path = field(
        default_factory=lambda: Path('config/user_settings.json'))

    # Настройки обработки
    default_crf: int = 18
    default_preset: str = 'medium'
    default_video_bitrate: str = '8000k'
    default_audio_bitrate: str = '320k'

    # Настройки UI
    theme: str = 'dark'  # dark или light
    language: str = 'ru'

    # Временные файлы
    keep_temp_files: bool = False
    auto_cleanup_days: int = 7

    # История
    max_history_items: int = 100

    # Производительность
    max_workers: int = 4

    def __post_init__(self):
        """Преобразуем относительные пути в абсолютные."""
        self.downloads_dir = self.base_dir / self.downloads_dir
        self.output_dir = self.base_dir / self.output_dir
        self.temp_dir = self.base_dir / self.temp_dir
        self.music_dir = self.base_dir / self.music_dir
        self.stock_videos_dir = self.base_dir / self.stock_videos_dir
        self.history_file = self.base_dir / self.history_file
        self.settings_file = self.base_dir / self.settings_file

    def create_directories(self):
        """Создаёт необходимые директории."""
        for dir_path in [
            self.downloads_dir,
            self.output_dir,
            self.temp_dir,
            self.music_dir,
            self.stock_videos_dir
        ]:
            dir_path.mkdir(parents=True, exist_ok=True)

    def save(self):
        """Сохраняет настройки в файл."""
        settings_dict = {
            'default_crf': self.default_crf,
            'default_preset': self.default_preset,
            'default_video_bitrate': self.default_video_bitrate,
            'default_audio_bitrate': self.default_audio_bitrate,
            'theme': self.theme,
            'language': self.language,
            'keep_temp_files': self.keep_temp_files,
            'auto_cleanup_days': self.auto_cleanup_days,
            'max_history_items': self.max_history_items,
            'max_workers': self.max_workers,
        }

        self.settings_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.settings_file, 'w', encoding='utf-8') as f:
            json.dump(settings_dict, f, indent=2, ensure_ascii=False)

    @classmethod
    def load(cls) -> 'AppSettings':
        """Загружает настройки из файла."""
        settings = cls()

        if settings.settings_file.exists():
            try:
                with open(settings.settings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                for key, value in data.items():
                    if hasattr(settings, key):
                        setattr(settings, key, value)
            except Exception as e:
                print(f"Ошибка загрузки настроек: {e}")

        return settings


# Глобальный экземпляр настроек
settings = AppSettings.load()
settings.create_directories()
