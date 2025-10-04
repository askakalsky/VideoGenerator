"""
Менеджер файлов - работа с файловой системой
"""

import shutil
from pathlib import Path
from typing import List, Optional, Tuple
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class FileManager:
    """Менеджер для работы с файлами приложения."""

    @staticmethod
    def get_video_files(directory: Path, recursive: bool = False) -> List[Path]:
        """
        Получает список видео файлов в директории.

        Args:
            directory: Путь к директории
            recursive: Искать рекурсивно

        Returns:
            List[Path]: Список путей к видео файлам
        """
        video_extensions = {'.mp4', '.mov', '.avi',
                            '.mkv', '.webm', '.flv', '.wmv'}

        if not directory.exists():
            return []

        if recursive:
            files = []
            for ext in video_extensions:
                files.extend(directory.rglob(f'*{ext}'))
            return sorted(files)
        else:
            files = []
            for ext in video_extensions:
                files.extend(directory.glob(f'*{ext}'))
            return sorted(files)

    @staticmethod
    def get_audio_files(directory: Path, recursive: bool = False) -> List[Path]:
        """
        Получает список аудио файлов в директории.

        Args:
            directory: Путь к директории
            recursive: Искать рекурсивно

        Returns:
            List[Path]: Список путей к аудио файлам
        """
        audio_extensions = {'.mp3', '.wav', '.aac',
                            '.m4a', '.flac', '.ogg', '.wma'}

        if not directory.exists():
            return []

        if recursive:
            files = []
            for ext in audio_extensions:
                files.extend(directory.rglob(f'*{ext}'))
            return sorted(files)
        else:
            files = []
            for ext in audio_extensions:
                files.extend(directory.glob(f'*{ext}'))
            return sorted(files)

    @staticmethod
    def get_file_info(file_path: Path) -> dict:
        """
        Получает информацию о файле.

        Args:
            file_path: Путь к файлу

        Returns:
            dict: Информация о файле
        """
        if not file_path.exists():
            return {}

        stat = file_path.stat()

        return {
            'name': file_path.name,
            'size': stat.st_size,
            'size_mb': stat.st_size / (1024 * 1024),
            'created': datetime.fromtimestamp(stat.st_ctime),
            'modified': datetime.fromtimestamp(stat.st_mtime),
            'extension': file_path.suffix,
        }

    @staticmethod
    def format_file_size(size_bytes: int) -> str:
        """
        Форматирует размер файла.

        Args:
            size_bytes: Размер в байтах

        Returns:
            str: Отформатированная строка
        """
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"

    @staticmethod
    def cleanup_old_files(directory: Path, days: int = 7, pattern: str = '*') -> int:
        """
        Удаляет старые файлы.

        Args:
            directory: Директория для очистки
            days: Файлы старше N дней будут удалены
            pattern: Паттерн файлов

        Returns:
            int: Количество удалённых файлов
        """
        if not directory.exists():
            return 0

        cutoff_date = datetime.now() - timedelta(days=days)
        deleted_count = 0

        for file_path in directory.glob(pattern):
            if file_path.is_file():
                file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                if file_time < cutoff_date:
                    try:
                        file_path.unlink()
                        deleted_count += 1
                        logger.info(f"Удалён старый файл: {file_path.name}")
                    except Exception as e:
                        logger.error(f"Ошибка удаления {file_path}: {e}")

        return deleted_count

    @staticmethod
    def get_directory_size(directory: Path) -> int:
        """
        Вычисляет размер директории.

        Args:
            directory: Путь к директории

        Returns:
            int: Размер в байтах
        """
        if not directory.exists():
            return 0

        total_size = 0
        for item in directory.rglob('*'):
            if item.is_file():
                total_size += item.stat().st_size

        return total_size

    @staticmethod
    def safe_delete(file_path: Path, backup: bool = False) -> bool:
        """
        Безопасное удаление файла.

        Args:
            file_path: Путь к файлу
            backup: Создать backup перед удалением

        Returns:
            bool: Успешность операции
        """
        if not file_path.exists():
            return False

        try:
            if backup:
                backup_dir = file_path.parent / '.backup'
                backup_dir.mkdir(exist_ok=True)
                backup_path = backup_dir / \
                    f"{file_path.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{file_path.suffix}"
                shutil.copy2(file_path, backup_path)
                logger.info(f"Создан backup: {backup_path}")

            file_path.unlink()
            logger.info(f"Удалён файл: {file_path}")
            return True

        except Exception as e:
            logger.error(f"Ошибка удаления файла {file_path}: {e}")
            return False

    @staticmethod
    def move_file(src: Path, dst: Path, overwrite: bool = False) -> Optional[Path]:
        """
        Перемещает файл.

        Args:
            src: Исходный файл
            dst: Целевой путь
            overwrite: Перезаписать если существует

        Returns:
            Optional[Path]: Путь к новому файлу или None
        """
        if not src.exists():
            logger.error(f"Файл не найден: {src}")
            return None

        dst.parent.mkdir(parents=True, exist_ok=True)

        if dst.exists() and not overwrite:
            # Добавляем счётчик к имени
            counter = 1
            while dst.exists():
                dst = dst.parent / f"{dst.stem}_{counter}{dst.suffix}"
                counter += 1

        try:
            shutil.move(str(src), str(dst))
            logger.info(f"Перемещён файл: {src.name} -> {dst}")
            return dst
        except Exception as e:
            logger.error(f"Ошибка перемещения файла: {e}")
            return None

    @staticmethod
    def copy_file(src: Path, dst: Path, overwrite: bool = False) -> Optional[Path]:
        """
        Копирует файл.

        Args:
            src: Исходный файл
            dst: Целевой путь
            overwrite: Перезаписать если существует

        Returns:
            Optional[Path]: Путь к копии или None
        """
        if not src.exists():
            logger.error(f"Файл не найден: {src}")
            return None

        dst.parent.mkdir(parents=True, exist_ok=True)

        if dst.exists() and not overwrite:
            counter = 1
            while dst.exists():
                dst = dst.parent / f"{dst.stem}_{counter}{dst.suffix}"
                counter += 1

        try:
            shutil.copy2(str(src), str(dst))
            logger.info(f"Скопирован файл: {src.name} -> {dst}")
            return dst
        except Exception as e:
            logger.error(f"Ошибка копирования файла: {e}")
            return None
