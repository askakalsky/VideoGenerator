"""
Модуль для создания субтитров с побуквенной/пословной подсветкой в стиле TikTok.
Использует Whisper (stable-ts) для транскрипции и ffmpeg для прожига субтитров.
Поддерживает GPU-ускорение (NVIDIA NVENC, Intel QSV, AMD AMF, Apple VideoToolbox).
"""

import argparse
import json
import logging
import math
import shutil
import subprocess
import sys
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Union, Any, Tuple, List, Dict

import pysubs2
from pysubs2 import SSAFile, SSAStyle, SSAEvent, Color

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
class WhisperConfig:
    """Конфигурация для Whisper транскрипции."""
    model: str = "small"
    language: Optional[str] = None
    device: Optional[str] = None
    vad: bool = True
    word_timestamps: bool = True

    # Дополнительные параметры Whisper
    temperature: float = 0.0
    best_of: int = 5
    beam_size: int = 5

    def validate(self):
        """Валидация конфигурации."""
        valid_models = {
            'tiny', 'tiny.en', 'base', 'base.en',
            'small', 'small.en', 'medium', 'medium.en',
            'large', 'large-v1', 'large-v2', 'large-v3'
        }
        if self.model not in valid_models:
            logger.warning(
                f"Модель '{self.model}' не в списке известных. "
                f"Известные: {', '.join(sorted(valid_models))}"
            )

        if self.device and self.device not in {'cpu', 'cuda'}:
            if not self.device.startswith('cuda:'):
                raise ValueError(
                    f"device должен быть 'cpu', 'cuda' или 'cuda:N', получено: {self.device}"
                )


@dataclass
class SubtitleStyle:
    """Стиль субтитров."""
    # Цвета
    highlight_color: str = "#00FF6A"  # Цвет текущего слова (зелёный)
    normal_color: str = "#FFFFFF"     # Цвет обычных слов (белый)
    outline_color: str = "#000000"    # Цвет контура (чёрный)
    shadow_color: str = "#000000"     # Цвет тени

    # Шрифт
    font_name: str = "Arial"
    font_scale: float = 0.07          # Доля от высоты видео
    bold: bool = True
    italic: bool = False

    # Отступы (доли от размеров видео)
    margin_v_ratio: float = 0.13      # Вертикальный отступ (снизу)
    margin_lr_ratio: float = 0.06     # Горизонтальные отступы

    # Контур и тень (доли от высоты видео)
    outline_ratio: float = 0.003
    shadow_ratio: float = 0.0

    # Выравнивание (1-9, как на цифровой клавиатуре)
    # 2 = внизу по центру (TikTok стиль)
    alignment: int = 2

    def validate(self):
        """Валидация стиля."""
        if not 1 <= self.alignment <= 9:
            raise ValueError(
                f"alignment должен быть 1-9, получено: {self.alignment}")

        if self.font_scale <= 0 or self.font_scale > 1:
            raise ValueError(
                f"font_scale должен быть 0-1, получено: {self.font_scale}")

        # Валидация цветов
        for color_name in ['highlight_color', 'normal_color', 'outline_color', 'shadow_color']:
            color = getattr(self, color_name)
            if not self._is_valid_color(color):
                raise ValueError(
                    f"{color_name} должен быть в формате #RRGGBB, получено: {color}")

    @staticmethod
    def _is_valid_color(color: str) -> bool:
        """Проверка корректности HEX цвета."""
        if not color.startswith('#'):
            return False
        hex_part = color[1:]
        if len(hex_part) != 6:
            return False
        try:
            int(hex_part, 16)
            return True
        except ValueError:
            return False


@dataclass
class VideoConfig:
    """Конфигурация обработки видео."""
    # Кодеки
    video_codec: str = 'libx264'
    audio_codec: str = 'aac'

    # Аппаратное ускорение
    use_hardware: bool = False           # Использовать GPU
    hardware_type: str = 'nvenc'         # nvenc/qsv/amf/videotoolbox

    # Качество видео
    crf: int = 18                        # 0-51, меньше = лучше
    preset: str = 'medium'               # Скорость кодирования
    video_bitrate: Optional[str] = '8000k'  # Дополнительный контроль качества
    audio_bitrate: str = '320k'

    # GPU параметры
    gpu_index: int = 0                   # Номер GPU (если несколько)

    # Дополнительные параметры
    pix_fmt: str = 'yuv420p'             # Совместимость
    movflags: str = '+faststart'         # Быстрый старт для веб
    threads: int = 0                     # 0 = авто

    def validate(self):
        """Валидация конфигурации."""
        if not 0 <= self.crf <= 51:
            raise ValueError(f"CRF должен быть 0-51, получено: {self.crf}")

        # Разные пресеты для разных кодеков
        if self.use_hardware:
            valid_presets = self._get_hardware_presets()
        else:
            valid_presets = {
                'ultrafast', 'superfast', 'veryfast', 'faster',
                'fast', 'medium', 'slow', 'slower', 'veryslow'
            }

        if self.preset not in valid_presets:
            logger.warning(
                f"preset '{self.preset}' может быть не поддержан для {self.hardware_type if self.use_hardware else 'CPU'}. "
                f"Допустимые: {', '.join(sorted(valid_presets))}"
            )

    def _get_hardware_presets(self) -> set:
        """Возвращает доступные пресеты для аппаратного кодека."""
        if self.hardware_type == 'nvenc':
            return {'slow', 'medium', 'fast', 'hp', 'hq', 'bd', 'll', 'llhq', 'llhp', 'lossless'}
        elif self.hardware_type == 'qsv':
            return {'veryslow', 'slower', 'slow', 'medium', 'fast', 'faster', 'veryfast'}
        elif self.hardware_type == 'amf':
            return {'slow', 'balanced', 'fast'}
        else:
            return {'slow', 'medium', 'fast'}

    def _get_hardware_codec(self) -> str:
        """Возвращает кодек для выбранного типа аппаратного ускорения."""
        codecs = {
            'nvenc': 'h264_nvenc',           # NVIDIA
            'qsv': 'h264_qsv',               # Intel
            'amf': 'h264_amf',               # AMD
            'videotoolbox': 'h264_videotoolbox'  # Apple
        }
        return codecs.get(self.hardware_type, 'h264_nvenc')

    def to_ffmpeg_params(self) -> List[str]:
        """Преобразует конфиг в параметры ffmpeg."""
        params = []

        # Выбор кодека
        if self.use_hardware:
            codec = self._get_hardware_codec()
            params.extend(['-c:v', codec])

            # Параметры качества для NVENC
            if self.hardware_type == 'nvenc':
                params.extend([
                    '-preset', self.preset,
                    '-rc', 'vbr',               # Variable bitrate
                    '-cq', str(self.crf),       # Quality level (0-51)
                    '-b:v', self.video_bitrate or '8000k',
                    '-maxrate', self.video_bitrate or '8000k',
                    '-bufsize', '16M',
                ])

                # Выбор GPU
                if self.gpu_index > 0:
                    params.extend(['-gpu', str(self.gpu_index)])

            # Параметры для Intel QSV
            elif self.hardware_type == 'qsv':
                params.extend([
                    '-preset', self.preset,
                    '-global_quality', str(self.crf),
                    '-b:v', self.video_bitrate or '8000k',
                ])

            # Параметры для AMD AMF
            elif self.hardware_type == 'amf':
                params.extend([
                    '-quality', self.preset,
                    '-rc', 'vbr_peak',
                    '-qp_i', str(self.crf),
                    '-b:v', self.video_bitrate or '8000k',
                ])

            # Параметры для VideoToolbox (macOS)
            elif self.hardware_type == 'videotoolbox':
                params.extend([
                    '-b:v', self.video_bitrate or '8000k',
                ])

        else:
            # Программный кодек (CPU)
            params.extend([
                '-c:v', self.video_codec,
                '-crf', str(self.crf),
                '-preset', self.preset,
            ])

            if self.video_bitrate:
                params.extend(['-b:v', self.video_bitrate])

        # Общие параметры
        params.extend([
            '-c:a', self.audio_codec,
            '-b:a', self.audio_bitrate,
            '-pix_fmt', self.pix_fmt,
            '-movflags', self.movflags,
        ])

        if self.threads > 0:
            params.extend(['-threads', str(self.threads)])

        return params


# ============================================================================
# УТИЛИТЫ
# ============================================================================

class FFmpegError(Exception):
    """Ошибка выполнения FFmpeg команды."""
    pass


class TranscriptionError(Exception):
    """Ошибка транскрипции."""
    pass


@contextmanager
def temporary_files(*paths: Union[str, Path]):
    """
    Контекстный менеджер для временных файлов.
    Удаляет их после завершения работы.
    """
    paths_list = [Path(p) for p in paths]
    try:
        yield paths_list
    finally:
        for path in paths_list:
            if path.exists():
                try:
                    path.unlink()
                    logger.debug(f"Удалён временный файл: {path}")
                except Exception as e:
                    logger.warning(f"Не удалось удалить {path}: {e}")


def run_command(
    cmd: List[str],
    cwd: Optional[Path] = None,
    timeout: Optional[int] = None,
    check: bool = True
) -> subprocess.CompletedProcess:
    """
    Выполняет команду с логированием.

    Args:
        cmd: Команда и аргументы
        cwd: Рабочая директория
        timeout: Таймаут в секундах
        check: Проверять код возврата

    Returns:
        CompletedProcess результат

    Raises:
        subprocess.CalledProcessError: Если check=True и команда упала
    """
    logger.debug(f"Запуск команды: {' '.join(str(x) for x in cmd)}")
    if cwd:
        logger.debug(f"Рабочая директория: {cwd}")

    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            check=check,
            timeout=timeout,
            capture_output=True,
            text=True
        )
        return result
    except subprocess.CalledProcessError as e:
        logger.error(f"Команда завершилась с ошибкой: {e}")
        if e.stderr:
            logger.error(f"STDERR: {e.stderr}")
        raise
    except subprocess.TimeoutExpired as e:
        logger.error(f"Команда превысила таймаут {timeout}s")
        raise


def check_dependencies():
    """Проверяет наличие необходимых зависимостей."""
    dependencies = {
        'ffmpeg': 'FFmpeg не найден. Установите: https://ffmpeg.org/download.html',
        'ffprobe': 'FFprobe не найден. Установите вместе с FFmpeg.',
    }

    missing = []
    for cmd, msg in dependencies.items():
        if not shutil.which(cmd):
            missing.append(msg)

    if missing:
        raise RuntimeError(
            "Отсутствуют зависимости:\n" +
            "\n".join(f"  - {m}" for m in missing)
        )


def detect_gpu_capabilities() -> Dict[str, bool]:
    """
    Определяет доступные возможности аппаратного ускорения.

    Returns:
        Dict с доступными типами: {'nvenc': True, 'qsv': False, ...}
    """
    capabilities = {
        'nvenc': False,
        'qsv': False,
        'amf': False,
        'videotoolbox': False
    }

    try:
        # Проверяем доступные кодеки через ffmpeg
        result = subprocess.run(
            ['ffmpeg', '-hide_banner', '-encoders'],
            capture_output=True,
            text=True,
            timeout=5
        )

        encoders = result.stdout.lower()

        test_cmd = [
            'ffmpeg', '-y', '-f', 'lavfi', '-i', 'color=black:s=64x64:d=0.1',
            '-c:v', '{codec}', '-f', 'null', '-'
        ]

        def _test_codec(codec: str) -> bool:
            cmd = [c.replace('{codec}', codec) for c in test_cmd]
            r = subprocess.run(cmd, capture_output=True, timeout=5)
            return r.returncode == 0

        if 'h264_nvenc' in encoders and _test_codec('h264_nvenc'):
            capabilities['nvenc'] = True

        if 'h264_qsv' in encoders and _test_codec('h264_qsv'):
            capabilities['qsv'] = True

        if 'h264_amf' in encoders and _test_codec('h264_amf'):
            capabilities['amf'] = True

        if 'h264_videotoolbox' in encoders and _test_codec('h264_videotoolbox'):
            capabilities['videotoolbox'] = True

    except Exception as e:
        logger.warning(f"Не удалось определить GPU возможности: {e}")

    return capabilities


def get_recommended_hardware() -> Optional[str]:
    """
    Возвращает рекомендуемый тип аппаратного ускорения.

    Returns:
        Тип ускорения ('nvenc'/'qsv'/etc) или None если недоступно
    """
    caps = detect_gpu_capabilities()

    # Приоритет: NVENC > QSV > AMF > VideoToolbox
    for hw_type in ['nvenc', 'qsv', 'amf', 'videotoolbox']:
        if caps.get(hw_type):
            return hw_type

    return None


def validate_file_exists(path: Path, file_type: str = "Файл"):
    """Проверяет существование файла."""
    if not path.exists():
        raise FileNotFoundError(f"{file_type} не найден: {path}")
    if not path.is_file():
        raise ValueError(f"{path} не является файлом")


def hex_to_ass_bgr(hex_color: str) -> str:
    """
    Конвертирует HEX цвет (#RRGGBB) в ASS формат (BBGGRR).

    Args:
        hex_color: Цвет в формате #RRGGBB

    Returns:
        str: Цвет в формате BBGGRR для ASS
    """
    color = hex_color.strip().lstrip('#')
    if len(color) != 6:
        raise ValueError(f"Цвет должен быть #RRGGBB, получено: {hex_color}")

    r, g, b = color[0:2], color[2:4], color[4:6]
    return f"{b}{g}{r}".upper()


def escape_ass_text(text: str) -> str:
    """
    Экранирует текст для ASS формата.

    Args:
        text: Исходный текст

    Returns:
        str: Экранированный текст
    """
    return (text
            .replace('\\', r'\\')
            .replace('\n', r'\N')
            .replace('\r', ''))


def seconds_to_milliseconds(seconds: Optional[float]) -> int:
    """
    Конвертирует секунды в миллисекунды.

    Args:
        seconds: Время в секундах

    Returns:
        int: Время в миллисекундах
    """
    if seconds is None or math.isnan(seconds):
        return 0
    return int(round(seconds * 1000))


def safe_getattr(obj: Any, key: str, default: Any = None) -> Any:
    """
    Безопасное получение атрибута из объекта или словаря.

    Args:
        obj: Объект или словарь
        key: Ключ/атрибут
        default: Значение по умолчанию

    Returns:
        Значение атрибута или default
    """
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


# ============================================================================
# РАБОТА С ВИДЕО
# ============================================================================

class VideoInfo:
    """Информация о видео файле."""

    def __init__(self, path: Union[str, Path]):
        self.path = Path(path)
        self._info: Optional[Dict] = None

    def _load_info(self):
        """Загружает информацию через ffprobe."""
        if self._info is not None:
            return

        cmd = [
            'ffprobe',
            '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=width,height,duration,r_frame_rate,bit_rate',
            '-of', 'json',
            str(self.path)
        ]

        try:
            result = run_command(cmd, check=True)
            data = json.loads(result.stdout)

            if not data.get('streams'):
                raise ValueError(f"Не найден видео поток в {self.path}")

            self._info = data['streams'][0]
        except (subprocess.CalledProcessError, json.JSONDecodeError, KeyError) as e:
            raise FFmpegError(
                f"Не удалось получить информацию о видео: {e}") from e

    @property
    def width(self) -> int:
        """Ширина видео."""
        self._load_info()
        return int(self._info['width'])

    @property
    def height(self) -> int:
        """Высота видео."""
        self._load_info()
        return int(self._info['height'])

    @property
    def size(self) -> Tuple[int, int]:
        """Размер видео (ширина, высота)."""
        return (self.width, self.height)

    @property
    def duration(self) -> Optional[float]:
        """Длительность видео в секундах."""
        self._load_info()
        duration = self._info.get('duration')
        return float(duration) if duration else None

    @property
    def fps(self) -> Optional[float]:
        """Частота кадров."""
        self._load_info()
        fps_str = self._info.get('r_frame_rate')
        if fps_str and '/' in fps_str:
            num, den = fps_str.split('/')
            return float(num) / float(den)
        return None

    def __repr__(self) -> str:
        try:
            return (f"VideoInfo(path={self.path.name}, "
                    f"size={self.width}x{self.height}, "
                    f"duration={self.duration:.2f}s, "
                    f"fps={self.fps:.2f})")
        except Exception:
            return f"VideoInfo(path={self.path})"


# ============================================================================
# ТРАНСКРИПЦИЯ
# ============================================================================

class Transcriber:
    """Класс для транскрипции аудио с помощью Whisper."""

    def __init__(self, config: WhisperConfig):
        self.config = config
        self.model = None

    def load_model(self):
        """Загружает модель Whisper."""
        if self.model is not None:
            return

        logger.info(f"📥 Загружаю модель Whisper: {self.config.model}")
        if self.config.device:
            logger.info(f"   └─ Устройство: {self.config.device}")

        try:
            import stable_whisper
            self.model = stable_whisper.load_model(
                self.config.model,
                device=self.config.device
            )
            logger.info("✅ Модель загружена")
        except Exception as e:
            raise TranscriptionError(
                f"Не удалось загрузить модель: {e}") from e

    def transcribe(self, media_path: Union[str, Path]) -> Any:
        """
        Транскрибирует медиа файл.

        Args:
            media_path: Путь к медиа файлу

        Returns:
            Результат транскрипции Whisper
        """
        self.load_model()

        media_path = Path(media_path)
        validate_file_exists(media_path, "Медиа файл")

        logger.info(f"🎙️  Начинаю транскрипцию: {media_path.name}")
        logger.info(f"   ├─ Модель: {self.config.model}")
        logger.info(f"   ├─ Язык: {self.config.language or 'авто'}")
        logger.info(
            f"   └─ VAD: {'включен' if self.config.vad else 'выключен'}")

        try:
            result = self.model.transcribe(
                str(media_path),
                word_timestamps=self.config.word_timestamps,
                vad=self.config.vad,
                language=self.config.language,
                temperature=self.config.temperature,
                best_of=self.config.best_of,
                beam_size=self.config.beam_size,
            )

            # Подсчёт статистики
            segments = safe_getattr(result, 'segments', [])
            total_words = sum(
                len(safe_getattr(seg, 'words', []))
                for seg in segments
            )

            logger.info(f"✅ Транскрипция завершена")
            logger.info(f"   ├─ Сегментов: {len(segments)}")
            logger.info(f"   └─ Слов: {total_words}")

            return result

        except Exception as e:
            raise TranscriptionError(f"Ошибка транскрипции: {e}") from e

    def __del__(self):
        """Очистка ресурсов."""
        if self.model is not None:
            del self.model


# ============================================================================
# СОЗДАНИЕ СУБТИТРОВ
# ============================================================================

class SubtitleGenerator:
    """Генератор ASS субтитров с подсветкой слов."""

    def __init__(
        self,
        video_width: int,
        video_height: int,
        style: SubtitleStyle
    ):
        self.video_width = video_width
        self.video_height = video_height
        self.style = style
        self.style.validate()

    def _create_style(self) -> SSAStyle:
        """Создаёт стиль субтитров на основе конфигурации."""
        # Вычисляем абсолютные значения на основе размера видео
        font_size = max(
            12, int(round(self.video_height * self.style.font_scale)))
        margin_v = max(
            0, int(round(self.video_height * self.style.margin_v_ratio)))
        margin_l = max(
            0, int(round(self.video_width * self.style.margin_lr_ratio)))
        margin_r = margin_l
        outline = max(
            1, int(round(self.video_height * self.style.outline_ratio)))
        shadow = int(round(self.video_height * self.style.shadow_ratio))

        # Парсим цвета
        normal_bgr = hex_to_ass_bgr(self.style.normal_color)
        outline_bgr = hex_to_ass_bgr(self.style.outline_color)

        # Создаём стиль
        style = SSAStyle()
        style.fontname = self.style.font_name
        style.fontsize = font_size
        style.bold = self.style.bold
        style.italic = self.style.italic

        # Цвета в pysubs2 (RGBA, но ASS использует BGR)
        # Primary color - основной цвет текста
        style.primarycolor = Color(255, 255, 255, 0)  # Белый по умолчанию
        style.outlinecolor = Color(0, 0, 0, 0)        # Чёрный контур
        style.backcolor = Color(0, 0, 0, 128)         # Полупрозрачный фон

        # Параметры контура и тени
        style.outline = outline
        style.shadow = shadow
        style.borderstyle = 1  # Outline + shadow

        # Выравнивание и отступы
        style.alignment = self.style.alignment
        style.marginl = margin_l
        style.marginr = margin_r
        style.marginv = margin_v

        return style

    def generate(self, transcription_result: Any, output_path: Union[str, Path]):
        """
        Генерирует ASS файл с подсветкой слов.

        Args:
            transcription_result: Результат транскрипции Whisper
            output_path: Путь для сохранения ASS файла
        """
        output_path = Path(output_path)

        logger.info(f"📝 Генерирую субтитры: {output_path.name}")

        # Создаём ASS файл
        subs = SSAFile()
        subs.info['PlayResX'] = self.video_width
        subs.info['PlayResY'] = self.video_height
        subs.info['ScaledBorderAndShadow'] = 'yes'

        # Добавляем стиль
        style = self._create_style()
        subs.styles['TikTok'] = style

        # Цвета для подсветки
        highlight_bgr = hex_to_ass_bgr(self.style.highlight_color)
        normal_bgr = hex_to_ass_bgr(self.style.normal_color)

        # Обрабатываем сегменты
        segments = safe_getattr(transcription_result, 'segments', [])
        event_count = 0

        for seg_idx, segment in enumerate(segments):
            seg_start = safe_getattr(segment, 'start')
            seg_end = safe_getattr(segment, 'end')
            words = safe_getattr(segment, 'words', []) or []

            if not words:
                # Сегмент без слов - добавляем как обычный текст
                text = escape_ass_text(
                    safe_getattr(segment, 'text', '').strip())
                if text and seg_start is not None and seg_end is not None:
                    subs.events.append(SSAEvent(
                        start=seconds_to_milliseconds(seg_start),
                        end=seconds_to_milliseconds(seg_end),
                        text=text,
                        style='TikTok'
                    ))
                    event_count += 1
                continue

            # Собираем слова с корректными таймингами
            timed_words = []
            for word in words:
                w_start = safe_getattr(word, 'start')
                w_end = safe_getattr(word, 'end')
                w_text = safe_getattr(word, 'word', '').strip()

                if w_start is not None and w_end is not None and w_text:
                    timed_words.append({
                        'start': w_start,
                        'end': w_end,
                        'text': w_text,
                        'index': len(timed_words)
                    })

            if not timed_words:
                # Если не удалось извлечь тайминги слов
                full_text = escape_ass_text(
                    ' '.join(safe_getattr(w, 'word', '') for w in words if safe_getattr(w, 'word', '')).strip()
                )
                if full_text and seg_start is not None and seg_end is not None:
                    subs.events.append(SSAEvent(
                        start=seconds_to_milliseconds(seg_start),
                        end=seconds_to_milliseconds(seg_end),
                        text=full_text,
                        style='TikTok'
                    ))
                    event_count += 1
                continue

            # Создаём события с подсветкой для каждого слова
            for i, timed_word in enumerate(timed_words):
                # Время начала - начало текущего слова
                event_start = timed_word['start']

                # Время конца - начало следующего слова (избегаем перекрытий)
                if i + 1 < len(timed_words):
                    event_end = timed_words[i + 1]['start']
                else:
                    # Последнее слово - используем конец сегмента
                    event_end = max(
                        timed_word['end'],
                        seg_end if seg_end is not None else timed_word['end']
                    )

                # Защита от нулевой длительности
                if event_end <= event_start:
                    event_end = event_start + 0.1

                # Строим текст: все слова, но текущее подсвечено
                # Устанавливаем базовый цвет
                parts = [f"{{\\c&H{normal_bgr}&}}"]

                words_added = 0
                for j, word in enumerate(words):
                    word_text = safe_getattr(word, 'word', '')
                    if not word_text:
                        continue

                    if words_added > 0:
                        parts.append(" ")
                    words_added += 1

                    escaped_text = escape_ass_text(word_text)

                    # Проверяем, это текущее слово?
                    is_current = False
                    if j < len(timed_words):
                        tw = timed_words[j]
                        if tw['index'] == i:
                            is_current = True

                    if is_current:
                        # Подсвечиваем текущее слово
                        parts.append(
                            f"{{\\c&H{highlight_bgr}&}}{escaped_text}{{\\c&H{normal_bgr}&}}"
                        )
                    else:
                        parts.append(escaped_text)

                line_text = ''.join(parts)

                subs.events.append(SSAEvent(
                    start=seconds_to_milliseconds(event_start),
                    end=seconds_to_milliseconds(event_end),
                    text=line_text,
                    style='TikTok'
                ))
                event_count += 1

        # Сохраняем файл
        subs.save(str(output_path))

        logger.info(f"✅ Субтитры сохранены")
        logger.info(f"   ├─ Событий: {event_count}")
        logger.info(
            f"   ├─ Размер: {output_path.stat().st_size / 1024:.1f} KB")
        logger.info(f"   └─ Путь: {output_path}")


# ============================================================================
# ПРОЖИГ СУБТИТРОВ
# ============================================================================

class SubtitleBurner:
    """Класс для прожига субтитров в видео."""

    def __init__(self, config: VideoConfig):
        self.config = config
        self.config.validate()

    def burn(
        self,
        input_video: Union[str, Path],
        ass_file: Union[str, Path],
        output_video: Union[str, Path],
        fonts_dir: Optional[Union[str, Path]] = None
    ):
        """
        Прожигает субтитры в видео.

        Args:
            input_video: Путь к исходному видео
            ass_file: Путь к ASS файлу субтитров
            output_video: Путь для сохранения результата
            fonts_dir: Папка со шрифтами (опционально)
        """
        input_video = Path(input_video).resolve()
        ass_file = Path(ass_file).resolve()
        output_video = Path(output_video).resolve()

        # Валидация входных файлов
        validate_file_exists(input_video, "Входное видео")
        validate_file_exists(ass_file, "ASS файл")

        logger.info(f"🔥 Прожигаю субтитры в видео")
        logger.info(f"   ├─ Вход: {input_video.name}")
        logger.info(f"   ├─ Субтитры: {ass_file.name}")
        logger.info(f"   └─ Выход: {output_video.name}")

        # Рабочая директория - папка с ASS файлом
        work_dir = ass_file.parent
        ass_name = ass_file.name

        # Строим фильтр для субтитров
        vf = f"ass={ass_name}"

        # Добавляем путь к шрифтам если указан
        if fonts_dir:
            fonts_dir = Path(fonts_dir).resolve()
            try:
                # Пытаемся получить относительный путь
                fonts_rel = fonts_dir.relative_to(work_dir)
                fonts_path = fonts_rel.as_posix()
                vf += f":fontsdir={fonts_path}"
                logger.info(f"   ├─ Шрифты: {fonts_path}")
            except ValueError:
                # Шрифты на другом диске - используем абсолютный путь
                logger.warning(
                    f"Папка шрифтов на другом диске, используется абсолютный путь"
                )
                fonts_path = fonts_dir.as_posix().replace(':', r'\:')
                vf += f":fontsdir={fonts_path}"

        # Собираем команду ffmpeg
        cmd = [
            'ffmpeg', '-y',
            '-i', str(input_video),
            '-vf', vf,
        ]

        # Добавляем параметры кодирования
        cmd.extend(self.config.to_ffmpeg_params())

        # Выходной файл
        cmd.append(str(output_video))

        # Логирование параметров
        logger.info(f"⚙️  Параметры кодирования:")
        if self.config.use_hardware:
            logger.info(
                f"   ├─ 🚀 GPU ускорение: {self.config.hardware_type.upper()}")
            logger.info(f"   ├─ Кодек: {self.config._get_hardware_codec()}")
        else:
            logger.info(f"   ├─ 🖥️  CPU кодирование")
            logger.info(f"   ├─ Видео кодек: {self.config.video_codec}")

        logger.info(f"   ├─ CRF: {self.config.crf}")
        logger.info(f"   ├─ Preset: {self.config.preset}")
        if self.config.video_bitrate:
            logger.info(f"   ├─ Видео bitrate: {self.config.video_bitrate}")
        logger.info(f"   ├─ Аудио кодек: {self.config.audio_codec}")
        logger.info(f"   └─ Аудио bitrate: {self.config.audio_bitrate}")

        # Запускаем ffmpeg
        try:
            logger.info("🎬 Начинаю рендеринг...")
            run_command(cmd, cwd=work_dir, timeout=None)

            # Проверяем результат
            if not output_video.exists():
                raise FFmpegError("Выходной файл не был создан")

            output_size = output_video.stat().st_size / (1024 * 1024)  # MB
            logger.info(f"✅ Рендеринг завершён")
            logger.info(f"   ├─ Размер: {output_size:.2f} MB")
            logger.info(f"   └─ Путь: {output_video}")

        except subprocess.CalledProcessError as e:
            raise FFmpegError(
                f"Ошибка ffmpeg при прожиге субтитров: {e}") from e


# ============================================================================
# ГЛАВНЫЙ КЛАСС
# ============================================================================

class TikTokSubtitles:
    """Главный класс для создания субтитров в стиле TikTok."""

    def __init__(
        self,
        whisper_config: Optional[WhisperConfig] = None,
        subtitle_style: Optional[SubtitleStyle] = None,
        video_config: Optional[VideoConfig] = None
    ):
        self.whisper_config = whisper_config or WhisperConfig()
        self.subtitle_style = subtitle_style or SubtitleStyle()
        self.video_config = video_config or VideoConfig()

        # Валидация конфигураций
        self.whisper_config.validate()
        self.subtitle_style.validate()
        self.video_config.validate()

        # Компоненты
        self.transcriber = Transcriber(self.whisper_config)

    def process(
        self,
        input_video: Union[str, Path],
        output_video: Union[str, Path],
        fonts_dir: Optional[Union[str, Path]] = None,
        keep_ass: bool = True
    ) -> Tuple[Path, Optional[Path]]:
        """
        Полный цикл: транскрипция → генерация субтитров → прожиг.

        Args:
            input_video: Путь к входному видео
            output_video: Путь для сохранения результата
            fonts_dir: Папка со шрифтами
            keep_ass: Сохранить ASS файл после обработки

        Returns:
            Tuple[Path, Optional[Path]]: Пути к выходному видео и ASS файлу
        """
        input_video = Path(input_video)
        output_video = Path(output_video)

        logger.info("=" * 70)
        logger.info("🎬 СОЗДАНИЕ СУБТИТРОВ В СТИЛЕ TIKTOK")
        logger.info("=" * 70)

        # Проверяем зависимости
        check_dependencies()

        # Получаем информацию о видео
        video_info = VideoInfo(input_video)
        logger.info(f"📹 Информация о видео:")
        logger.info(f"   ├─ Файл: {input_video.name}")
        logger.info(
            f"   ├─ Разрешение: {video_info.width}x{video_info.height}")
        if video_info.duration:
            logger.info(f"   ├─ Длительность: {video_info.duration:.1f}s")
        if video_info.fps:
            logger.info(f"   └─ FPS: {video_info.fps:.2f}")

        # Путь для ASS файла
        ass_path = output_video.with_suffix('.ass')

        try:
            # 1. Транскрипция
            logger.info("")
            transcription_result = self.transcriber.transcribe(input_video)

            # 2. Генерация субтитров
            logger.info("")
            generator = SubtitleGenerator(
                video_width=video_info.width,
                video_height=video_info.height,
                style=self.subtitle_style
            )
            generator.generate(transcription_result, ass_path)

            # 3. Прожиг субтитров
            logger.info("")
            burner = SubtitleBurner(self.video_config)
            burner.burn(input_video, ass_path, output_video, fonts_dir)

            logger.info("")
            logger.info("=" * 70)
            logger.info("🎉 УСПЕШНО ЗАВЕРШЕНО")
            logger.info(f"📁 Видео: {output_video}")
            if keep_ass:
                logger.info(f"📄 Субтитры: {ass_path}")
            logger.info("=" * 70)

            # Удаляем ASS если не нужно сохранять
            final_ass_path = ass_path if keep_ass else None
            if not keep_ass and ass_path.exists():
                ass_path.unlink()
                logger.debug(f"Удалён временный ASS файл: {ass_path}")

            return output_video, final_ass_path

        except Exception as e:
            logger.error(f"❌ Ошибка обработки: {e}", exc_info=True)

            # Очистка при ошибке
            if output_video.exists():
                try:
                    output_video.unlink()
                    logger.debug("Удалён повреждённый выходной файл")
                except Exception:
                    pass

            raise


# ============================================================================
# CLI
# ============================================================================

def parse_arguments():
    """Парсинг аргументов командной строки."""
    parser = argparse.ArgumentParser(
        description='Создание субтитров с подсветкой слов в стиле TikTok',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  %(prog)s -i video.mp4 -o output.mp4
  %(prog)s -i video.mp4 -o output.mp4 --model medium --language ru
  %(prog)s -i video.mp4 -o output.mp4 --green "#00FF00" --font "Impact"
  %(prog)s -i video.mp4 -o output.mp4 --use-gpu --gpu-type nvenc
  %(prog)s -i video.mp4 -o output.mp4 --crf 15 --preset slow
        """
    )

    # Основные параметры
    main_group = parser.add_argument_group('Основные параметры')
    main_group.add_argument(
        '-i', '--input',
        required=True,
        help='Путь к входному видео'
    )
    main_group.add_argument(
        '-o', '--output',
        required=True,
        help='Путь для сохранения результата'
    )

    # Whisper параметры
    whisper_group = parser.add_argument_group('Параметры Whisper')
    whisper_group.add_argument(
        '--model',
        default='small',
        help='Модель Whisper (tiny/small/medium/large-v2/...)'
    )
    whisper_group.add_argument(
        '--language',
        default=None,
        help='Язык аудио (ru/en/...), None = автоопределение'
    )
    whisper_group.add_argument(
        '--device',
        default=None,
        help='Устройство вычислений (cpu/cuda)'
    )
    whisper_group.add_argument(
        '--no-vad',
        action='store_true',
        help='Отключить Voice Activity Detection'
    )

    # Стиль субтитров
    style_group = parser.add_argument_group('Стиль субтитров')
    style_group.add_argument(
        '--green',
        default='#00FF6A',
        help='Цвет подсветки текущего слова (#RRGGBB)'
    )
    style_group.add_argument(
        '--white',
        default='#FFFFFF',
        help='Цвет обычных слов (#RRGGBB)'
    )
    style_group.add_argument(
        '--font',
        default='Arial',
        help='Название шрифта'
    )
    style_group.add_argument(
        '--font-scale',
        type=float,
        default=0.07,
        help='Размер шрифта как доля от высоты видео (0.01-0.2)'
    )
    style_group.add_argument(
        '--bold',
        action='store_true',
        default=True,
        help='Жирный шрифт'
    )
    style_group.add_argument(
        '--marginv',
        type=float,
        default=0.13,
        help='Вертикальный отступ как доля от высоты'
    )
    style_group.add_argument(
        '--marginlr',
        type=float,
        default=0.06,
        help='Горизонтальные отступы как доля от ширины'
    )
    style_group.add_argument(
        '--outline',
        type=float,
        default=0.003,
        help='Толщина контура как доля от высоты'
    )
    style_group.add_argument(
        '--fontsdir',
        default=None,
        help='Папка со шрифтами для libass'
    )

    # Параметры видео
    video_group = parser.add_argument_group('Параметры видео')
    video_group.add_argument(
        '--use-gpu',
        action='store_true',
        help='Использовать GPU ускорение'
    )
    video_group.add_argument(
        '--gpu-type',
        default='nvenc',
        choices=['nvenc', 'qsv', 'amf', 'videotoolbox'],
        help='Тип GPU ускорения'
    )
    video_group.add_argument(
        '--crf',
        type=int,
        default=18,
        help='CRF значение (0-51, меньше=лучше качество)'
    )
    video_group.add_argument(
        '--preset',
        default='medium',
        help='Preset скорости кодирования'
    )
    video_group.add_argument(
        '--video-bitrate',
        default='8000k',
        help='Битрейт видео (например, 8000k, 10M)'
    )
    video_group.add_argument(
        '--audio-bitrate',
        default='320k',
        help='Битрейт аудио'
    )

    # Дополнительно
    misc_group = parser.add_argument_group('Дополнительно')
    misc_group.add_argument(
        '--no-keep-ass',
        action='store_true',
        help='Не сохранять ASS файл после обработки'
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

    # Настройка логирования
    if args.debug:
        logger.setLevel(logging.DEBUG)
    elif args.verbose:
        logger.setLevel(logging.INFO)

    try:
        # Создание конфигураций
        whisper_config = WhisperConfig(
            model=args.model,
            language=args.language,
            device=args.device,
            vad=not args.no_vad
        )

        subtitle_style = SubtitleStyle(
            highlight_color=args.green,
            normal_color=args.white,
            font_name=args.font,
            font_scale=args.font_scale,
            bold=args.bold,
            margin_v_ratio=args.marginv,
            margin_lr_ratio=args.marginlr,
            outline_ratio=args.outline
        )

        video_config = VideoConfig(
            use_hardware=args.use_gpu,
            hardware_type=args.gpu_type,
            crf=args.crf,
            preset=args.preset,
            video_bitrate=args.video_bitrate,
            audio_bitrate=args.audio_bitrate
        )

        # Создание процессора
        processor = TikTokSubtitles(
            whisper_config=whisper_config,
            subtitle_style=subtitle_style,
            video_config=video_config
        )

        # Обработка
        output_video, ass_file = processor.process(
            input_video=args.input,
            output_video=args.output,
            fonts_dir=args.fontsdir,
            keep_ass=not args.no_keep_ass
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

if __name__ == '__main__':
    sys.exit(main())
