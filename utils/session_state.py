"""
Менеджер состояния сессии Streamlit
"""

import streamlit as st
from typing import Any, Optional, Dict
from datetime import datetime
import json
from pathlib import Path


class SessionStateManager:
    """Менеджер состояния сессии Streamlit."""

    @staticmethod
    def init(key: str, default: Any = None) -> Any:
        """
        Инициализирует значение в session_state если его нет.

        Args:
            key: Ключ
            default: Значение по умолчанию

        Returns:
            Значение из session_state
        """
        if key not in st.session_state:
            st.session_state[key] = default
        return st.session_state[key]

    @staticmethod
    def get(key: str, default: Any = None) -> Any:
        """
        Получает значение из session_state.

        Args:
            key: Ключ
            default: Значение по умолчанию если ключ не найден

        Returns:
            Значение
        """
        return st.session_state.get(key, default)

    @staticmethod
    def set(key: str, value: Any):
        """
        Устанавливает значение в session_state.

        Args:
            key: Ключ
            value: Значение
        """
        st.session_state[key] = value

    @staticmethod
    def delete(key: str) -> bool:
        """
        Удаляет ключ из session_state.

        Args:
            key: Ключ

        Returns:
            bool: True если ключ был удалён
        """
        if key in st.session_state:
            del st.session_state[key]
            return True
        return False

    @staticmethod
    def clear():
        """Очищает весь session_state."""
        for key in list(st.session_state.keys()):
            del st.session_state[key]

    @staticmethod
    def has(key: str) -> bool:
        """
        Проверяет наличие ключа.

        Args:
            key: Ключ

        Returns:
            bool: True если ключ существует
        """
        return key in st.session_state

    @staticmethod
    def increment(key: str, amount: int = 1, default: int = 0) -> int:
        """
        Увеличивает числовое значение.

        Args:
            key: Ключ
            amount: Величина увеличения
            default: Начальное значение

        Returns:
            int: Новое значение
        """
        current = st.session_state.get(key, default)
        new_value = current + amount
        st.session_state[key] = new_value
        return new_value

    @staticmethod
    def append(key: str, value: Any, max_size: Optional[int] = None):
        """
        Добавляет значение в список.

        Args:
            key: Ключ
            value: Значение для добавления
            max_size: Максимальный размер списка
        """
        if key not in st.session_state:
            st.session_state[key] = []

        st.session_state[key].append(value)

        if max_size and len(st.session_state[key]) > max_size:
            st.session_state[key] = st.session_state[key][-max_size:]

    @staticmethod
    def update(key: str, updates: Dict[str, Any]):
        """
        Обновляет словарь в session_state.

        Args:
            key: Ключ
            updates: Словарь с обновлениями
        """
        if key not in st.session_state:
            st.session_state[key] = {}

        if isinstance(st.session_state[key], dict):
            st.session_state[key].update(updates)

    @staticmethod
    def toggle(key: str, default: bool = False) -> bool:
        """
        Переключает булево значение.

        Args:
            key: Ключ
            default: Значение по умолчанию

        Returns:
            bool: Новое значение
        """
        current = st.session_state.get(key, default)
        new_value = not current
        st.session_state[key] = new_value
        return new_value

    @staticmethod
    def save_to_file(filepath: Path, keys: Optional[list] = None):
        """
        Сохраняет session_state в файл.

        Args:
            filepath: Путь к файлу
            keys: Список ключей для сохранения (None = все)
        """
        data = {}

        if keys is None:
            keys = st.session_state.keys()

        for key in keys:
            value = st.session_state.get(key)
            # Сохраняем только сериализуемые типы
            if isinstance(value, (str, int, float, bool, list, dict, type(None))):
                data[key] = value

        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    @staticmethod
    def load_from_file(filepath: Path, keys: Optional[list] = None):
        """
        Загружает session_state из файла.

        Args:
            filepath: Путь к файлу
            keys: Список ключей для загрузки (None = все)
        """
        if not filepath.exists():
            return

        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if keys is None:
            keys = data.keys()

        for key in keys:
            if key in data:
                st.session_state[key] = data[key]

    @staticmethod
    def get_all() -> dict:
        """
        Получает все значения из session_state.

        Returns:
            dict: Словарь всех значений
        """
        return dict(st.session_state)

    @staticmethod
    def log_state():
        """Выводит состояние session_state в лог (для отладки)."""
        import logging
        logger = logging.getLogger(__name__)

        logger.debug("Session State:")
        for key, value in st.session_state.items():
            logger.debug(
                f"  {key}: {type(value).__name__} = {str(value)[:100]}")
