"""
Монолитный скрипт для создания серии видео.

Полный процесс:
1. Генерация сюжета (Gemini API) → JSON с 3 частями
2. Озвучка каждой части (ElevenLabs API) → MP3 файлы
3. Создание видео для каждой части (Whisper + FFmpeg + GPU)

Результат: 3 готовых видео с субтитрами и музыкой
"""

import logging
import random
import sys
import subprocess
import json
import re
import os
from pathlib import Path
from typing import Optional, Union, Dict, List
from dataclasses import dataclass
from datetime import datetime

# Google Gemini
import google.generativeai as genai

# ElevenLabs
from elevenlabs import VoiceSettings
from elevenlabs.client import ElevenLabs

# Dotenv
from dotenv import load_dotenv

# MoviePy
from moviepy import AudioFileClip

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
# ЗАГРУЗКА .ENV
# ============================================================================

load_dotenv()

# ============================================================================
# КОНФИГУРАЦИЯ
# ============================================================================

# Директории
STOCK_VIDEOS_DIR = Path("assets/stock_videos")
MUSIC_DIR = Path("assets/music")
READY_VIDEOS_DIR = Path("assets/ready_videos")
GENERATED_TEXT_DIR = Path("assets/generated_text")
GENERATED_AUDIO_DIR = Path("assets/generated_audio")
PROMPTS_DIR = Path("assets/prompts")

# Создаем директории если не существуют
for directory in [READY_VIDEOS_DIR, GENERATED_TEXT_DIR, GENERATED_AUDIO_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

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

# Настройки ElevenLabs
ELEVENLABS_VOICE = "jessica"  # Голос по умолчанию
ELEVENLABS_MODEL = "v3"       # Модель по умолчанию

# Настройки Gemini
GEMINI_MODEL = "gemini-2.0-flash-exp"

# Поддерживаемые музыкальные стили
MUSIC_STYLES = {
    'relaxed',
    'sad',
    'scandal',
    'scary',
    'documentary'
}

# ============================================================================
# ГЕНЕРАЦИЯ ТЕКСТА (GEMINI)
# ============================================================================


class StoryGenerator:
    """Класс для генерации сюжетов через Gemini API."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Инициализация генератора.

        Args:
            api_key: API ключ Gemini (если None, берется из .env)
        """
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')

        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY не найден!\n"
                "Создайте .env файл и добавьте ваш API ключ."
            )

        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(GEMINI_MODEL)

    def generate(self, prompt_file: Optional[Path] = None) -> Dict:
        """
        Генерирует сюжет и сохраняет в JSON.

        Args:
            prompt_file: Путь к файлу с промптом (по умолчанию assets/prompts/prompt.md)

        Returns:
            Dict: Сгенерированный сюжет
        """
        # Читаем промпт
        if prompt_file is None:
            prompt_file = PROMPTS_DIR / 'prompt.md'

        if not prompt_file.exists():
            raise FileNotFoundError(f"Файл промпта не найден: {prompt_file}")

        with open(prompt_file, 'r', encoding='utf-8') as f:
            prompt = f.read()

        logger.info("=" * 80)
        logger.info("📝 ГЕНЕРАЦИЯ СЮЖЕТА (GEMINI API)")
        logger.info("=" * 80)
        logger.info(f"📄 Промпт: {prompt_file.name}")
        logger.info(f"🤖 Модель: {GEMINI_MODEL}")

        # Отправляем запрос
        logger.info("🔄 Отправка запроса к модели...")
        response = self.model.generate_content(prompt)
        raw_response_text = response.text

        # Очищаем JSON от markdown
        cleaned_json = self._clean_json_string(raw_response_text)

        # Парсим JSON
        try:
            story_data = json.loads(cleaned_json)

            # Валидация структуры
            self._validate_story(story_data)

            # Сохраняем в файл
            timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
            output_file = GENERATED_TEXT_DIR / f"story_{timestamp}.json"

            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(story_data, f, indent=4, ensure_ascii=False)

            logger.info(f"✅ Сюжет сохранен: {output_file.name}")
            logger.info(
                f"   ├─ Название: {story_data.get('story_title', 'N/A')}")
            logger.info(f"   ├─ Частей: {len(story_data.get('parts', []))}")
            logger.info(
                f"   └─ Размер: {output_file.stat().st_size / 1024:.1f} KB")
            logger.info("=" * 80)

            return story_data

        except json.JSONDecodeError as e:
            logger.error(f"❌ Ошибка парсинга JSON: {e}")
            logger.error(f"Ответ модели:\n{raw_response_text[:500]}...")
            raise

    @staticmethod
    def _clean_json_string(text: str) -> str:
        """Очищает JSON от markdown блоков."""
        # Убираем ```json...```
        match = re.search(r"```json\s*(\{.*\})\s*```", text, re.DOTALL)
        if match:
            return match.group(1).strip()

        # Убираем ```...```
        match = re.search(r"```\s*(\{.*\})\s*```", text, re.DOTALL)
        if match:
            return match.group(1).strip()

        return text.strip()

    @staticmethod
    def _validate_story(story_data: Dict):
        """Валидирует структуру сюжета."""
        required_keys = ['story_title', 'image_prompt', 'parts']
        for key in required_keys:
            if key not in story_data:
                raise ValueError(f"Отсутствует обязательное поле: {key}")

        if not isinstance(story_data['parts'], list):
            raise ValueError("'parts' должен быть списком")

        if len(story_data['parts']) != 3:
            raise ValueError(
                f"Ожидается 3 части, получено: {len(story_data['parts'])}")

        for i, part in enumerate(story_data['parts'], 1):
            if 'text' not in part:
                raise ValueError(f"Часть {i} не содержит 'text'")

            if 'music' not in part:
                logger.warning(
                    f"⚠️  Часть {i} не содержит 'music', будет выбрана случайная")
            else:
                music_style = part['music'].lower()
                if music_style not in MUSIC_STYLES:
                    logger.warning(
                        f"⚠️  Часть {i}: неизвестный стиль музыки '{music_style}'. "
                        f"Известные: {', '.join(MUSIC_STYLES)}"
                    )


# ============================================================================
# ОЗВУЧКА (ELEVENLABS) - С ПОДДЕРЖКОЙ НЕСКОЛЬКИХ API КЛЮЧЕЙ
# ============================================================================

class TextToSpeech:
    """Класс для озвучки текста через ElevenLabs API с поддержкой нескольких ключей."""

    # Доступные голоса
    VOICES = {
        "jessica": "cgSgspJ2msm6clMCkdW9",
        "adam": "pNInz6obpgDQGcFmaJgB",
    }

    # Доступные модели
    MODELS = {
        "v3": "eleven_v3",
        "turbo_v2_5": "eleven_turbo_v2_5",
        "turbo_v2": "eleven_turbo_v2",
        "multilingual_v2": "eleven_multilingual_v2",
        "monolingual_v1": "eleven_monolingual_v1",
    }

    # V3 модели (не поддерживают optimize_streaming_latency)
    V3_MODELS = {"eleven_v3"}

    def __init__(self):
        """
        Инициализация TTS с загрузкой всех доступных API ключей.
        """
        # Загружаем все доступные API ключи
        self.api_keys = []
        for i in range(1, 10):  # Проверяем до 10 ключей
            key = os.getenv(f"ELEVENLABS_API_KEY_{i}")
            if key:
                self.api_keys.append({
                    'key': key,
                    'name': f"API_KEY_{i}",
                    'client': None,
                    'active': True
                })

        if not self.api_keys:
            raise ValueError(
                "Не найдено ни одного ELEVENLABS_API_KEY_N!\n"
                "Добавьте в .env файл:\n"
                "ELEVENLABS_API_KEY_1=ваш_ключ_1\n"
                "ELEVENLABS_API_KEY_2=ваш_ключ_2\n"
                "и т.д."
            )

        self.current_key_index = 0

        logger.info(f"🔑 Загружено API ключей: {len(self.api_keys)}")
        for i, key_info in enumerate(self.api_keys):
            logger.info(
                f"   ├─ {key_info['name']}: {'✅ активен' if key_info['active'] else '❌ неактивен'}")

    def _get_current_client(self) -> ElevenLabs:
        """Возвращает клиент для текущего API ключа."""
        key_info = self.api_keys[self.current_key_index]

        # Создаем клиент если еще не создан
        if key_info['client'] is None:
            key_info['client'] = ElevenLabs(api_key=key_info['key'])

        return key_info['client']

    def _switch_to_next_key(self) -> bool:
        """
        Переключается на следующий доступный API ключ.

        Returns:
            bool: True если удалось переключиться, False если все ключи исчерпаны
        """
        # Помечаем текущий ключ как неактивный
        self.api_keys[self.current_key_index]['active'] = False

        # Ищем следующий активный ключ
        for i in range(len(self.api_keys)):
            next_index = (self.current_key_index + i + 1) % len(self.api_keys)
            if self.api_keys[next_index]['active']:
                old_key_name = self.api_keys[self.current_key_index]['name']
                new_key_name = self.api_keys[next_index]['name']

                logger.warning(
                    f"🔄 Переключение с {old_key_name} на {new_key_name}")

                self.current_key_index = next_index
                return True

        # Все ключи исчерпаны
        return False

    def generate(
        self,
        text: str,
        output_file: Path,
        voice: str = ELEVENLABS_VOICE,
        model: str = ELEVENLABS_MODEL,
        stability: float = 0.5,
        similarity_boost: float = 0.8,
        style: float = 0.0,
        use_speaker_boost: bool = True,
        max_retries: int = None  # По умолчанию пробуем все ключи
    ) -> Path:
        """
        Генерирует речь из текста с автоматическим переключением API ключей.

        Args:
            text: Текст для озвучки
            output_file: Путь к выходному файлу
            voice: Название голоса
            model: Название модели
            stability: Стабильность (0.0-1.0)
            similarity_boost: Схожесть (0.0-1.0)
            style: Стиль (0.0-1.0)
            use_speaker_boost: Усиление говорящего
            max_retries: Макс. попыток (None = все ключи)

        Returns:
            Path: Путь к сохраненному файлу

        Raises:
            RuntimeError: Если все API ключи исчерпаны
        """
        output_file = Path(output_file)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # Получаем ID
        voice_id = self.VOICES.get(voice, voice)
        model_id = self.MODELS.get(model, model)
        is_v3_model = model_id in self.V3_MODELS

        logger.info(f"🎙️  Озвучка:")
        logger.info(f"   ├─ Голос: {voice}")
        logger.info(f"   ├─ Модель: {model_id} {'🆕' if is_v3_model else ''}")
        logger.info(f"   ├─ Символов: {len(text)}")
        logger.info(f"   └─ Файл: {output_file.name}")

        # Параметры для API
        convert_params = {
            "voice_id": voice_id,
            "output_format": "mp3_44100_128",
            "text": text,
            "model_id": model_id,
            "voice_settings": VoiceSettings(
                stability=stability,
                similarity_boost=similarity_boost,
                style=style,
                use_speaker_boost=use_speaker_boost,
            ),
        }

        # Для не-v3 моделей добавляем optimize_streaming_latency
        if not is_v3_model:
            convert_params["optimize_streaming_latency"] = "0"

        # Определяем количество попыток
        if max_retries is None:
            max_retries = len(self.api_keys)

        # Пробуем генерацию с переключением ключей
        for attempt in range(max_retries):
            try:
                current_key_name = self.api_keys[self.current_key_index]['name']

                if attempt > 0:
                    logger.info(
                        f"   🔄 Попытка {attempt + 1}/{max_retries} с ключом {current_key_name}")
                else:
                    logger.info(f"   🔑 Используется ключ: {current_key_name}")

                # Получаем клиент для текущего ключа
                client = self._get_current_client()

                # Генерируем аудио
                response = client.text_to_speech.convert(**convert_params)

                # Сохраняем
                with open(output_file, "wb") as f:
                    for chunk in response:
                        if chunk:
                            f.write(chunk)

                logger.info(f"   ✅ Сохранено: {output_file}")
                return output_file

            except Exception as e:
                error_str = str(e)

                # Проверяем, является ли это ошибкой квоты
                is_quota_error = (
                    'quota_exceeded' in error_str.lower() or
                    '401' in error_str or
                    'unauthorized' in error_str.lower()
                )

                if is_quota_error:
                    logger.warning(
                        f"   ⚠️  Квота исчерпана для {current_key_name}")

                    # Пробуем переключиться на следующий ключ
                    if self._switch_to_next_key():
                        continue  # Повторяем попытку
                    else:
                        raise RuntimeError(
                            "❌ Все API ключи ElevenLabs исчерпаны!\n"
                            f"Всего ключей: {len(self.api_keys)}\n"
                            "Добавьте новые ключи или дождитесь обновления квоты."
                        ) from e
                else:
                    # Другая ошибка - пробрасываем
                    logger.error(f"   ❌ Ошибка генерации: {e}")
                    raise

        # Если все попытки исчерпаны
        raise RuntimeError(
            f"❌ Не удалось сгенерировать аудио после {max_retries} попыток"
        )

    def get_usage(self, key_index: Optional[int] = None) -> Dict:
        """
        Получает информацию об использовании API.

        Args:
            key_index: Индекс ключа (None = текущий)

        Returns:
            Dict: Информация об использовании
        """
        if key_index is None:
            key_index = self.current_key_index

        try:
            key_info = self.api_keys[key_index]

            # Создаем клиент если нужно
            if key_info['client'] is None:
                key_info['client'] = ElevenLabs(api_key=key_info['key'])

            user = key_info['client'].user.get()

            return {
                "name": key_info['name'],
                "active": key_info['active'],
                "used": user.subscription.character_count,
                "limit": user.subscription.character_limit,
                "remaining": user.subscription.character_limit - user.subscription.character_count
            }
        except Exception as e:
            logger.warning(
                f"Не удалось получить данные для {key_info['name']}: {e}")
            return {
                "name": key_info['name'],
                "active": False,
                "used": 0,
                "limit": 0,
                "remaining": 0,
                "error": str(e)
            }

    def get_all_usage(self) -> List[Dict]:
        """Получает информацию об использовании всех ключей."""
        all_usage = []
        for i in range(len(self.api_keys)):
            usage = self.get_usage(i)
            all_usage.append(usage)
        return all_usage

    def print_usage(self):
        """Выводит информацию об использовании всех API ключей."""
        logger.info("")
        logger.info("📊 Использование ElevenLabs API:")

        all_usage = self.get_all_usage()

        for usage in all_usage:
            is_current = (usage['name'] ==
                          self.api_keys[self.current_key_index]['name'])
            current_marker = " 👈 текущий" if is_current else ""

            logger.info(f"   ┌─ {usage['name']}{current_marker}")

            if 'error' in usage:
                logger.info(f"   │  └─ ❌ Ошибка: {usage['error']}")
            else:
                logger.info(
                    f"   │  ├─ Использовано: {usage['used']:,} символов")
                logger.info(f"   │  ├─ Лимит: {usage['limit']:,} символов")
                logger.info(
                    f"   │  ├─ Осталось: {usage['remaining']:,} символов")

                if usage['limit'] > 0:
                    percentage = (usage['used'] / usage['limit']) * 100
                    logger.info(f"   │  ├─ Процент: {percentage:.1f}%")

                status = "✅ активен" if usage['active'] else "❌ неактивен"
                logger.info(f"   │  └─ Статус: {status}")


# ============================================================================
# УТИЛИТЫ
# ============================================================================

def select_random_file(directory: Path, extensions: set) -> Path:
    """Выбирает случайный файл из директории."""
    if not directory.exists():
        raise FileNotFoundError(f"Директория не найдена: {directory}")

    files = [f for f in directory.iterdir() if f.is_file()
             and f.suffix.lower() in extensions]

    if not files:
        raise FileNotFoundError(
            f"Не найдено файлов в {directory} с расширениями {extensions}"
        )

    selected = random.choice(files)
    return selected


def select_music_by_style(music_style: Optional[str] = None) -> Path:
    """
    Выбирает музыкальный файл по стилю.

    Args:
        music_style: Стиль музыки (relaxed, sad, scandal, scary, documentary)
                     Если None, выбирается случайный файл

    Returns:
        Path: Путь к музыкальному файлу

    Raises:
        FileNotFoundError: Если не найдено подходящих файлов
    """
    if not MUSIC_DIR.exists():
        raise FileNotFoundError(f"Директория музыки не найдена: {MUSIC_DIR}")

    # Получаем все аудио файлы
    all_music_files = [
        f for f in MUSIC_DIR.iterdir()
        if f.is_file() and f.suffix.lower() in AUDIO_FORMATS
    ]

    if not all_music_files:
        raise FileNotFoundError(f"Не найдено музыкальных файлов в {MUSIC_DIR}")

    # Если стиль не указан - случайный файл
    if music_style is None:
        selected = random.choice(all_music_files)
        logger.debug(f"Выбрана случайная музыка: {selected.name}")
        return selected

    # Нормализуем стиль
    music_style = music_style.lower().strip()

    # Ищем файлы, начинающиеся с нужного стиля
    # Формат: {style}-{number}.mp3 (например, relaxed-1.mp3)
    matching_files = [
        f for f in all_music_files
        if f.stem.lower().startswith(f"{music_style}-")
    ]

    if matching_files:
        selected = random.choice(matching_files)
        logger.info(f"🎵 Музыка ({music_style}): {selected.name}")
        logger.debug(
            f"   └─ Найдено {len(matching_files)} файлов стиля '{music_style}'")
        return selected
    else:
        # Если файлы нужного стиля не найдены - выбираем случайный
        logger.warning(
            f"⚠️  Файлы стиля '{music_style}' не найдены в {MUSIC_DIR}. "
            f"Выбираю случайную музыку."
        )
        selected = random.choice(all_music_files)
        logger.info(f"🎵 Музыка (случайная): {selected.name}")
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
        raise ValueError("Невозможно разместить аудио в видео")

    return random.uniform(min_start, max_start)


def format_time(seconds: float) -> str:
    """Форматирует секунды в MM:SS."""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes}:{secs:02d}"


def escape_ffmpeg_path(path: Path) -> str:
    """Экранирует путь для FFmpeg."""
    path_str = str(path.resolve())
    path_str = path_str.replace('\\', '/')
    return path_str


def run_ffmpeg_command(cmd: list, cwd: Optional[Path] = None):
    """Выполняет FFmpeg команду."""
    encoding = 'utf-8' if sys.platform == 'win32' else None

    result = subprocess.run(
        cmd,
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
        encoding=encoding,
        errors='replace'
    )
    return result


# ============================================================================
# СОЗДАНИЕ ВИДЕО
# ============================================================================

def create_video_from_audio(
    audio_path: Path,
    output_name: str,
    music_style: Optional[str] = None,
    video_path: Optional[Path] = None,
    music_path: Optional[Path] = None,
    keep_ass: bool = False
) -> Path:
    """
    Создает финальное видео из аудиофайла.

    Args:
        audio_path: Путь к аудио
        output_name: Имя выходного файла
        music_style: Стиль музыки (relaxed, sad, etc.)
        video_path: Конкретное видео (или случайное)
        music_path: Конкретная музыка (или выбор по стилю)
        keep_ass: Сохранить ASS субтитры

    Returns:
        Path: Путь к созданному видео
    """
    logger.info("")
    logger.info("=" * 80)
    logger.info("🎬 СОЗДАНИЕ ФИНАЛЬНОГО ВИДЕО")
    logger.info("=" * 80)

    # Выбор видео
    if video_path is None:
        video_path = select_random_file(STOCK_VIDEOS_DIR, VIDEO_FORMATS)
        logger.info(f"📹 Видео (случайное): {video_path.name}")
    else:
        logger.info(f"📹 Видео (указано): {video_path.name}")

    # Выбор музыки по стилю
    if music_path is None:
        music_path = select_music_by_style(music_style)
    else:
        logger.info(f"🎵 Музыка (указана): {music_path.name}")

    # Анализ
    video_info = VideoInfo(video_path)
    audio_clip = AudioFileClip(str(audio_path))
    audio_duration = audio_clip.duration
    audio_clip.close()

    logger.info(
        f"📊 Видео: {video_info.width}x{video_info.height}, {format_time(video_info.duration)}")
    logger.info(f"📊 Аудио: {format_time(audio_duration)}")

    start_time = calculate_start_time(video_info.duration, audio_duration)
    logger.info(
        f"✂️  Фрагмент: {format_time(start_time)} - {format_time(start_time + audio_duration)}")

    # Транскрипция
    logger.info("")
    logger.info("🎙️  Транскрипция...")
    transcriber = Transcriber(WHISPER_CONFIG)
    transcription_result = transcriber.transcribe(audio_path)

    # Субтитры
    logger.info("📝 Генерация субтитров...")
    output_path = READY_VIDEOS_DIR / output_name
    ass_path = output_path.with_suffix('.ass')

    generator = SubtitleGenerator(
        video_width=video_info.width,
        video_height=video_info.height,
        style=SUBTITLE_STYLE
    )
    generator.generate(transcription_result, ass_path)

    # FFmpeg рендеринг
    logger.info("")
    logger.info("🚀 Рендеринг (GPU NVENC)...")

    video_path_ffmpeg = escape_ffmpeg_path(video_path)
    audio_path_ffmpeg = escape_ffmpeg_path(audio_path)
    music_path_ffmpeg = escape_ffmpeg_path(music_path)
    output_path_ffmpeg = escape_ffmpeg_path(output_path)
    ass_name = ass_path.name

    filter_complex = (
        f"[2:a]volume={MUSIC_VOLUME},aloop=loop=-1:size=2e+09,atrim=0:{audio_duration}[music];"
        f"[1:a]volume={AUDIO_VOLUME}[voice];"
        f"[voice][music]amix=inputs=2:duration=first:dropout_transition=0[audio];"
        f"[0:v]ass={ass_name}[video]"
    )

    cmd = [
        'ffmpeg', '-y',
        '-ss', str(start_time),
        '-i', video_path_ffmpeg,
        '-t', str(audio_duration),
        '-i', audio_path_ffmpeg,
        '-stream_loop', '-1',
        '-i', music_path_ffmpeg,
        '-filter_complex', filter_complex,
        '-map', '[video]',
        '-map', '[audio]',
        '-c:v', VIDEO_CODEC,
        '-preset', PRESET,
        '-rc', 'vbr',
        '-cq', str(CRF),
        '-b:v', VIDEO_BITRATE,
        '-maxrate', VIDEO_BITRATE,
        '-bufsize', '20M',
        '-gpu', '0',
        '-c:a', 'aac',
        '-b:a', AUDIO_BITRATE,
        '-pix_fmt', 'yuv420p',
        '-movflags', '+faststart',
        output_path_ffmpeg
    ]

    run_ffmpeg_command(cmd, cwd=ass_path.parent)

    if not output_path.exists():
        raise RuntimeError("Выходной файл не был создан")

    output_size = output_path.stat().st_size / (1024 * 1024)

    logger.info("")
    logger.info("✅ ВИДЕО СОЗДАНО!")
    logger.info(f"   ├─ Файл: {output_path.name}")
    logger.info(f"   ├─ Размер: {output_size:.2f} MB")
    logger.info(f"   └─ Длительность: {format_time(audio_duration)}")

    if not keep_ass:
        ass_path.unlink(missing_ok=True)

    logger.info("=" * 80)

    return output_path


# ============================================================================
# ГЛАВНАЯ ФУНКЦИЯ
# ============================================================================

def process_story(
    story_json: Optional[Path] = None,
    generate_new: bool = True,
    voice: str = ELEVENLABS_VOICE,
    model: str = ELEVENLABS_MODEL,
    keep_ass: bool = False
) -> List[Path]:
    """
    Полный цикл создания видео из сюжета.

    Args:
        story_json: Путь к готовому JSON (если есть)
        generate_new: Генерировать новый сюжет
        voice: Голос для озвучки
        model: Модель ElevenLabs
        keep_ass: Сохранять ASS субтитры

    Returns:
        List[Path]: Пути к созданным видео
    """
    logger.info("")
    logger.info("╔" + "═" * 78 + "╗")
    logger.info("║" + " " * 20 +
                "🎬 МОНОЛИТ - СОЗДАНИЕ СЕРИИ ВИДЕО" + " " * 24 + "║")
    logger.info("╚" + "═" * 78 + "╝")
    logger.info("")

    # Проверка зависимостей
    check_dependencies()

    # ========================================================================
    # ЭТАП 1: ГЕНЕРАЦИЯ ИЛИ ЗАГРУЗКА СЮЖЕТА
    # ========================================================================

    if generate_new or story_json is None:
        story_generator = StoryGenerator()
        story_data = story_generator.generate()
    else:
        logger.info("=" * 80)
        logger.info("📂 ЗАГРУЗКА СУЩЕСТВУЮЩЕГО СЮЖЕТА")
        logger.info("=" * 80)
        logger.info(f"📄 Файл: {story_json}")

        with open(story_json, 'r', encoding='utf-8') as f:
            story_data = json.load(f)

        logger.info(f"✅ Загружено: {story_data.get('story_title', 'N/A')}")
        logger.info("=" * 80)

    story_title = story_data.get('story_title', 'untitled')
    parts = story_data.get('parts', [])

    if len(parts) != 3:
        raise ValueError(f"Ожидается 3 части, получено: {len(parts)}")

    # ========================================================================
    # ЭТАП 2: ОЗВУЧКА + СОЗДАНИЕ ВИДЕО ДЛЯ КАЖДОЙ ЧАСТИ
    # ========================================================================

    tts = TextToSpeech()
    created_videos = []

    timestamp = datetime.now().strftime("%Y-%m-%d")

    for part in parts:
        part_num = part.get('part_number', 0)
        text = part.get('text', '')
        music_style = part.get('music')  # Может быть None

        if not text:
            logger.warning(f"⚠️  Часть {part_num} пуста, пропускаю")
            continue

        logger.info("")
        logger.info("┌" + "─" * 78 + "┐")
        logger.info(f"│  ЧАСТЬ {part_num}/3" + " " * 68 + "│")
        if music_style:
            logger.info(
                f"│  Стиль музыки: {music_style}" + " " * (61 - len(music_style)) + "│")
        logger.info("└" + "─" * 78 + "┘")

        # Озвучка
        audio_filename = f"{timestamp}_Part {part_num}.mp3"
        audio_path = GENERATED_AUDIO_DIR / audio_filename

        logger.info("")
        logger.info(f"🔊 Озвучка части {part_num}...")

        try:
            tts.generate(
                text=text,
                output_file=audio_path,
                voice=voice,
                model=model
            )
        except Exception as e:
            logger.error(f"❌ Ошибка озвучки части {part_num}: {e}")
            continue

        # Создание видео
        video_filename = f"{timestamp}_Part {part_num}_final.mp4"

        try:
            video_path = create_video_from_audio(
                audio_path=audio_path,
                output_name=video_filename,
                music_style=music_style,  # Передаем стиль музыки
                keep_ass=keep_ass
            )
            created_videos.append(video_path)
        except Exception as e:
            logger.error(f"❌ Ошибка создания видео для части {part_num}: {e}")
            continue

    # ========================================================================
    # ФИНАЛ
    # ========================================================================

    logger.info("")
    logger.info("╔" + "═" * 78 + "╗")
    logger.info("║" + " " * 25 + "🎉 ВСЕ ВИДЕО СОЗДАНЫ!" + " " * 31 + "║")
    logger.info("╚" + "═" * 78 + "╝")
    logger.info("")
    logger.info(f"📊 Статистика:")
    logger.info(f"   ├─ Сюжет: {story_title}")
    logger.info(f"   ├─ Создано видео: {len(created_videos)}/3")
    logger.info(f"   └─ Директория: {READY_VIDEOS_DIR}")
    logger.info("")

    for i, video in enumerate(created_videos, 1):
        size = video.stat().st_size / (1024 * 1024)
        logger.info(f"   {i}. {video.name} ({size:.1f} MB)")

    # Использование ElevenLabs
    tts.print_usage()

    logger.info("")
    logger.info("═" * 80)

    return created_videos


# ============================================================================
# CLI
# ============================================================================

def main():
    """Главная функция CLI."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Монолит - создание серии видео из сюжета',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  %(prog)s                              # Генерировать новый сюжет и создать 3 видео
  %(prog)s --story story.json           # Использовать существующий сюжет
  %(prog)s --voice adam --model turbo_v2_5  # Другой голос/модель
  %(prog)s --keep-ass                   # Сохранить ASS субтитры

Процесс:
  1. Генерация сюжета (Gemini API) → JSON с 3 частями
  2. Озвучка каждой части (ElevenLabs API) → MP3
  3. Создание видео (Whisper + FFmpeg GPU) → MP4

Результат:
  3 готовых видео в assets/ready_videos/

Музыкальные стили:
  relaxed, sad, scandal, scary, documentary
  Файлы формата: {style}-{number}.mp3 (например, relaxed-1.mp3)
  Скрипт автоматически выберет случайный файл нужного стиля

Поддержка нескольких API ключей:
  В .env файле укажите:
  ELEVENLABS_API_KEY_1=ключ1
  ELEVENLABS_API_KEY_2=ключ2
  и т.д. - скрипт автоматически переключится при исчерпании квоты
        """
    )

    parser.add_argument(
        '--story',
        type=Path,
        help='Путь к JSON с сюжетом (если не указан, генерируется новый)',
        default=None
    )

    parser.add_argument(
        '--no-generate',
        action='store_true',
        help='Не генерировать новый сюжет (требует --story)'
    )

    parser.add_argument(
        '--voice',
        default=ELEVENLABS_VOICE,
        help=f'Голос для озвучки (по умолчанию: {ELEVENLABS_VOICE})'
    )

    parser.add_argument(
        '--model',
        default=ELEVENLABS_MODEL,
        help=f'Модель ElevenLabs (по умолчанию: {ELEVENLABS_MODEL})'
    )

    parser.add_argument(
        '--keep-ass',
        action='store_true',
        help='Сохранить ASS файлы субтитров'
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

    # Валидация
    if args.no_generate and args.story is None:
        logger.error("❌ --no-generate требует указания --story")
        return 1

    try:
        process_story(
            story_json=args.story,
            generate_new=not args.no_generate,
            voice=args.voice,
            model=args.model,
            keep_ass=args.keep_ass
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
