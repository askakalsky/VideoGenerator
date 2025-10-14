import os
import uuid
from pathlib import Path
from typing import Optional, Generator

from dotenv import load_dotenv
from elevenlabs import VoiceSettings
from elevenlabs.client import ElevenLabs

load_dotenv()


class ElevenLabsV3:
    """Класс для работы с ElevenLabs API v3"""

    # Популярные голоса
    VOICES = {
        "jessica": "cgSgspJ2msm6clMCkdW9",
        "adam": "pNInz6obpgDQGcFmaJgB",
        # Добавьте другие голоса здесь
    }

    # Доступные модели
    MODELS = {
        "v3": "eleven_v3",                          # 🔥 V3 Alpha - новейшая
        "turbo_v2_5": "eleven_turbo_v2_5",
        "turbo_v2": "eleven_turbo_v2",
        "multilingual_v2": "eleven_multilingual_v2",
        "monolingual_v1": "eleven_monolingual_v1",
    }

    # Модели, которые НЕ поддерживают optimize_streaming_latency
    V3_MODELS = {"eleven_v3"}

    # Форматы вывода
    FORMATS = {
        "mp3_high": "mp3_44100_192",
        "mp3_medium": "mp3_44100_128",
        "mp3_low": "mp3_44100_64",
        "pcm_high": "pcm_44100",
        "pcm_medium": "pcm_24000",
        "pcm_low": "pcm_16000",
    }

    def __init__(self, api_key: Optional[str] = None):
        """
        Инициализация клиента.

        Args:
            api_key: API ключ (если None, берется из .env)
        """
        self.api_key = api_key or os.getenv("ELEVENLABS_API_KEY")

        if not self.api_key:
            raise ValueError(
                "ELEVENLABS_API_KEY не найден!\n"
                "Создайте .env файл и добавьте ваш API ключ."
            )

        self.client = ElevenLabs(api_key=self.api_key)
        self.output_dir = Path("output")
        self.output_dir.mkdir(exist_ok=True)

    def generate(
        self,
        text: str,
        voice: str = "jessica",
        model: str = "v3",  # 🔥 По умолчанию v3
        output_file: Optional[str] = None,
        stability: float = 0.5,
        similarity_boost: float = 0.8,
        style: float = 0.0,
        use_speaker_boost: bool = True,
        output_format: str = "mp3_medium",
        optimize_streaming_latency: Optional[str] = None  # 🔥 Опционально
    ) -> str:
        """
        Генерирует речь из текста.

        Args:
            text: Текст для озвучки
            voice: Название голоса или ID
            model: Название модели (v3, turbo_v2_5, и т.д.)
            output_file: Путь к выходному файлу (опционально)
            stability: Стабильность (0.0-1.0)
            similarity_boost: Схожесть (0.0-1.0)
            style: Стиль (0.0-1.0)
            use_speaker_boost: Усиление говорящего
            output_format: Формат вывода
            optimize_streaming_latency: Оптимизация задержки (None для v3)

        Returns:
            str: Путь к сохраненному файлу
        """
        # Получаем ID голоса
        voice_id = self.VOICES.get(voice, voice)

        # Получаем ID модели
        model_id = self.MODELS.get(model, model)

        # Получаем формат
        format_str = self.FORMATS.get(output_format, output_format)

        # 🔥 Проверяем, является ли это v3 моделью
        is_v3_model = model_id in self.V3_MODELS

        print(f"🎙️  Генерация:")
        print(f"   Голос: {voice} ({voice_id})")
        print(f"   Модель: {model_id} {'🆕 (V3 Alpha)' if is_v3_model else ''}")
        print(f"   Формат: {format_str}")

        # Подготавливаем параметры для API
        convert_params = {
            "voice_id": voice_id,
            "output_format": format_str,
            "text": text,
            "model_id": model_id,
            "voice_settings": VoiceSettings(
                stability=stability,
                similarity_boost=similarity_boost,
                style=style,
                use_speaker_boost=use_speaker_boost,
            ),
        }

        # 🔥 Добавляем optimize_streaming_latency ТОЛЬКО для не-v3 моделей
        if not is_v3_model:
            if optimize_streaming_latency is None:
                optimize_streaming_latency = "0"
            convert_params["optimize_streaming_latency"] = optimize_streaming_latency
            print(f"   Streaming latency: {optimize_streaming_latency}")
        else:
            print(f"   Streaming latency: N/A (не поддерживается в v3)")

        # Генерируем аудио
        response = self.client.text_to_speech.convert(**convert_params)

        # Определяем имя файла
        if output_file is None:
            extension = "mp3" if "mp3" in format_str else "pcm"
            output_file = self.output_dir / \
                f"{voice}_{uuid.uuid4()}.{extension}"
        else:
            output_file = Path(output_file)
            output_file.parent.mkdir(parents=True, exist_ok=True)

        # Сохраняем
        with open(output_file, "wb") as f:
            for chunk in response:
                if chunk:
                    f.write(chunk)

        print(f"✅ Сохранено: {output_file}")
        return str(output_file)

    def stream_generate(
        self,
        text: str,
        voice: str = "jessica",
        model: str = "v3",
        **kwargs
    ) -> Generator[bytes, None, None]:
        """
        Генерирует аудио потоком (для real-time воспроизведения).

        Args:
            text: Текст для озвучки
            voice: Голос
            model: Модель
            **kwargs: Дополнительные параметры

        Yields:
            bytes: Чанки аудио данных
        """
        voice_id = self.VOICES.get(voice, voice)
        model_id = self.MODELS.get(model, model)
        is_v3_model = model_id in self.V3_MODELS

        convert_params = {
            "voice_id": voice_id,
            "output_format": self.FORMATS.get(kwargs.get("output_format", "mp3_medium")),
            "text": text,
            "model_id": model_id,
            "voice_settings": VoiceSettings(
                stability=kwargs.get("stability", 0.5),
                similarity_boost=kwargs.get("similarity_boost", 0.8),
                style=kwargs.get("style", 0.0),
                use_speaker_boost=kwargs.get("use_speaker_boost", True),
            ),
        }

        # 🔥 Для не-v3 моделей добавляем optimize_streaming_latency
        if not is_v3_model:
            convert_params["optimize_streaming_latency"] = kwargs.get(
                "optimize_streaming_latency", "4"
            )

        response = self.client.text_to_speech.convert(**convert_params)

        for chunk in response:
            if chunk:
                yield chunk

    def get_voices(self):
        """Получает список доступных голосов."""
        return self.client.voices.get_all()

    def get_usage(self):
        """Получает информацию об использовании API."""
        user = self.client.user.get()
        return {
            "used": user.subscription.character_count,
            "limit": user.subscription.character_limit,
            "remaining": user.subscription.character_limit - user.subscription.character_count
        }

    def print_usage(self):
        """Выводит информацию об использовании."""
        usage = self.get_usage()
        print(f"\n📊 Использование API:")
        print(f"   Использовано: {usage['used']:,} символов")
        print(f"   Лимит: {usage['limit']:,} символов")
        print(f"   Осталось: {usage['remaining']:,} символов")
        percentage = (usage['used'] / usage['limit']) * 100
        print(f"   Процент: {percentage:.1f}%")


if __name__ == "__main__":
    # Создаем клиент
    tts = ElevenLabsV3()

    # Пример 1: V3 модель (новейшая)
    tts.generate(
        "Привет! Я Джессика, и это тест ElevenLabs API версии 3 альфа.",
        voice="jessica",
        model="v3"  # 🔥 Используем v3
    )

    # Показать использование API
    tts.print_usage()
