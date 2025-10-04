# 🎬 Video Production Studio

<div align="center">

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)
![MoviePy](https://img.shields.io/badge/MoviePy-2.0%2B-green.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)

**Профессиональный набор инструментов для обработки видео с веб-интерфейсом на Streamlit**

Комплексное решение для автоматизации видеопроизводства: от загрузки с YouTube до готового вертикального видео с субтитрами и музыкой.

[Возможности](#-основные-возможности) • [Установка](#-установка) • [Быстрый старт](#-быстрый-старт) • [Документация](#-модули) • [FAQ](#-faq) • [Roadmap](#-backlog-улучшений)

</div>

---

## 📋 Содержание

- [О проекте](#-о-проекте)
- [Основные возможности](#-основные-возможности)
- [Архитектура](#-архитектура-проекта)
- [Требования](#-требования)
- [Установка](#-установка)
  - [Быстрая установка](#быстрая-установка-5-минут)
  - [Windows](#windows)
  - [macOS](#macos)
  - [Linux](#linux)
  - [Docker](#docker)
- [Быстрый старт](#-быстрый-старт)
- [Модули](#-модули)
  - [Background Music](#1️⃣-background-music)
  - [TikTok Subtitles](#2️⃣-tiktok-subtitles)
  - [Audio Mixer](#3️⃣-audio-mixer)
  - [Convert to 9:16](#4️⃣-convert-to-916)
  - [YouTube Downloader](#5️⃣-youtube-downloader)
- [Веб-интерфейс](#-веб-интерфейс-streamlit)
- [Конфигурация](#️-конфигурация)
- [Примеры использования](#-примеры-использования)
- [Производительность](#-оптимизация-производительности)
- [Troubleshooting](#-troubleshooting)
- [FAQ](#-faq)
- [Backlog улучшений](#-backlog-улучшений)
- [Contributing](#-contributing)
- [Лицензия](#-лицензия)

---

## 🎯 О проекте

**Video Production Studio** — это модульная система для профессиональной обработки видео, разработанная специально для контент-криейторов, видеомонтажёров и SMM-специалистов.

### 🎪 Для кого этот проект?

| Роль | Применение |
|------|------------|
| **📱 TikTok/Reels криейторы** | Автоматическое создание вертикальных видео с субтитрами |
| **🎥 YouTube-блогеры** | Загрузка, обработка и добавление музыки к видео |
| **✂️ Видеомонтажёры** | Пакетная обработка больших объёмов видео |
| **🎓 Преподаватели** | Создание образовательного контента с субтитрами |
| **📺 SMM-менеджеры** | Адаптация видео для разных соцсетей |
| **🎬 Продакшн-студии** | Автоматизация рутинных задач монтажа |

### 🌟 Ключевые особенности

- ✅ **Модульная архитектура** — каждый модуль работает независимо (CLI + Web UI)
- ✅ **MoviePy 2.0** — современная библиотека обработки видео
- ✅ **AI-транскрипция** — OpenAI Whisper для субтитров на 90+ языках
- ✅ **Высокое качество** — сохранение исходного качества видео (CRF 18)
- ✅ **Пакетная обработка** — параллельная обработка множества файлов
- ✅ **Docker-ready** — готовые образы для быстрого развёртывания
- ✅ **Open Source** — MIT лицензия, полный доступ к коду

---

## ✨ Основные возможности

### 🎵 Background Music
**Добавление фоновой музыки с профессиональным микшированием**

- Автоматическое зацикливание музыки под длительность видео
- Раздельная регулировка громкости голоса (0-200%) и музыки (0-200%)
- Fade-in/Fade-out эффекты с настройкой длительности
- Сохранение качества: CRF 18, bitrate 8000k, AAC 320k
- Поддержка форматов: MP4, AVI, MOV, MKV → MP3, WAV, AAC, FLAC

**Пример использования:**
```bash
python modules/background_music.py video.mp4 music.mp3 -m 0.1 -v 1.0 --fade-in 2
```

---

### 📝 TikTok Subtitles
**AI-субтитры с анимированной подсветкой слов (как в TikTok)**

- **Whisper AI** транскрипция на 90+ языках
- Пословная анимация с точными временными метками
- Настройка цветов, шрифтов, размеров и позиции
- Экспорт ASS субтитров для дальнейшего редактирования
- Автоопределение языка или ручной выбор
- Модели: tiny/base/small/medium/large (компромисс скорость/точность)

**Технологии:**
- OpenAI Whisper (stable-ts) — транскрипция
- pysubs2 — генерация ASS субтитров
- FFmpeg libass — прожиг субтитров в видео

**Пример:**
```bash
python modules/tiktok_subs.py -i video.mp4 -o output.mp4 --model small --language ru
```

---

### 🎤 Audio Mixer
**Добавление аудио к случайному или заданному фрагменту видео**

- Случайный выбор времени начала (с диапазоном)
- Точное указание времени начала (секунды)
- Микширование с оригинальным аудио (настройка пропорций)
- Fade-in/Fade-out для плавных переходов
- Random seed для воспроизводимых результатов

**Сценарии:**
- Добавление озвучки к конкретному фрагменту
- Создание превью с музыкой
- Тестирование разных аудио на видео

**Пример:**
```bash
# Случайное время 10-30 сек
python modules/video_audio_mixer.py video.mp4 audio.mp3 --min-start 10 --max-start 30

# Конкретное время 15.5 сек
python modules/video_audio_mixer.py video.mp4 audio.mp3 --start-at 15.5
```

---

### 📐 Convert to 9:16
**Пакетная конвертация в вертикальный формат для социальных сетей**

- Автоматическая обрезка в соотношение 9:16 (1080x1920)
- Выбор позиции обрезки: **top** (сверху), **center** (центр), **bottom** (снизу)
- Параллельная обработка (многопоточность)
- Опциональное удаление аудио для уменьшения размера
- Пропуск уже вертикальных видео (экономия времени)
- JSON-отчёты с детальной статистикой

**Возможности:**
- Обработка сотен видео за раз
- Настройка минимального разрешения (фильтрация низкого качества)
- Удаление исходников после успешной конвертации
- Отчёты о размере файлов, времени обработки, ошибках

**Пример:**
```bash
# Одно видео
python modules/video_converter.py -i video.mp4 -o output/

# Пакетная обработка
python modules/video_converter.py -i videos/ -o output/ --workers 8 --position top
```

---

### 📥 YouTube Downloader
**Профессиональный загрузчик видео с YouTube**

- Выбор качества: 144p, 240p, 360p, 480p, 720p, 1080p, 1440p, 4K, 8K
- Загрузка плейлистов (с выбором диапазона видео)
- Скачивание субтитров (любые языки)
- Поддержка cookies для приватных видео
- Возобновление прерванных загрузок
- Ограничение скорости (не перегружать канал)
- Пакетная загрузка из списка URL

**На основе yt-dlp** — самого мощного загрузчика YouTube

**Пример:**
```bash
# Базовая загрузка
python modules/youtube_downloader.py "https://youtube.com/watch?v=..."

# 4K с субтитрами
python modules/youtube_downloader.py "URL" -q 4K --subtitles --subtitle-lang "en,ru"

# Плейлист (первые 5 видео)
python modules/youtube_downloader.py "PLAYLIST_URL" --playlist --playlist-items "1-5"
```

---

## 🏗 Архитектура проекта

### Структура файлов

```
video-production-studio/
│
├── 📄 app.py                          # Главная страница Streamlit (статистика, история)
├── 📄 requirements.txt                # Python зависимости
├── 📄 Dockerfile                      # Docker образ для контейнеризации
├── 📄 docker-compose.yml              # Оркестрация Docker
├── 📄 .gitignore                      # Git ignore правила
│
├── 📂 config/                         # Конфигурация
│   ├── __init__.py
│   └── settings.py                    # Централизованные настройки приложения
│
├── 📂 modules/                        # Ядро: модули обработки (CLI-ready)
│   ├── __init__.py
│   ├── background_music.py           # ♫ Добавление фоновой музыки
│   ├── tiktok_subs.py                # 📝 AI-субтитры с подсветкой
│   ├── video_audio_mixer.py          # 🎤 Микширование аудио с фрагментом
│   ├── video_converter.py            # 📐 Конвертация в 9:16
│   └── youtube_downloader.py         # 📥 Загрузка с YouTube
│
├── 📂 pages/                          # Streamlit UI страницы
│   ├── 1_🎵_Background_Music.py      # Web UI для модуля 1
│   ├── 2_📝_TikTok_Subtitles.py      # Web UI для модуля 2
│   ├── 3_🎤_Audio_Mixer.py           # Web UI для модуля 3
│   ├── 4_📐_Convert_9x16.py          # Web UI для модуля 4
│   └── 5_📥_YouTube_Downloader.py    # Web UI для модуля 5
│
├── 📂 utils/                          # Вспомогательные утилиты
│   ├── __init__.py
│   ├── file_manager.py               # Управление файлами
│   └── session_state.py              # Streamlit session state
│
├── 📂 assets/                         # Рабочие директории (создаются автоматически)
│   ├── downloads/                     # YouTube загрузки
│   ├── output/                        # Результаты обработки
│   ├── temp/                          # Временные файлы (автоочистка)
│   ├── music/                         # Библиотека музыки пользователя
│   ├── stock_videos/                  # Готовые 9:16 видео
│   └── history.json                   # История всех операций
│
└── 📂 .streamlit/                     # Streamlit конфигурация
    └── config.toml                    # Настройки темы и UI
```

### Технологический стек

| Компонент | Технология | Версия | Назначение |
|-----------|------------|--------|------------|
| **Backend** | Python | 3.10+ | Язык программирования |
| **Web Framework** | Streamlit | 1.32+ | Веб-интерфейс |
| **Video Processing** | MoviePy | 2.0+ | Обработка видео (важно: v2!) |
| **Video Encoding** | FFmpeg | 4.4+ | Кодирование/декодирование |
| **AI Transcription** | OpenAI Whisper | latest | Транскрипция речи |
| **Whisper Enhancement** | stable-ts | 2.0+ | Улучшенные timestamp'ы |
| **Subtitles** | pysubs2 | 1.6+ | Работа с ASS/SRT |
| **YouTube** | yt-dlp | 2024+ | Загрузка видео |
| **Containerization** | Docker | 20.10+ | Контейнеризация |

### Принципы архитектуры

1. **Модульность** — каждый модуль независим, имеет CLI и может использоваться отдельно
2. **Separation of Concerns** — бизнес-логика в `modules/`, UI в `pages/`
3. **Configuration as Code** — все настройки в `config/settings.py`
4. **Stateless** — модули не хранят состояние между запусками
5. **Fail-Safe** — обработка ошибок, логирование, откат изменений

---

## 💻 Требования

### Минимальные требования

| Компонент | Минимум | Рекомендуется |
|-----------|---------|---------------|
| **OS** | Windows 10 / macOS 10.14 / Ubuntu 18.04 | Windows 11 / macOS 13+ / Ubuntu 22.04 |
| **CPU** | 2 ядра, 2.0 GHz | 4+ ядра, 3.0+ GHz |
| **RAM** | 4 GB | 8 GB (16 GB для Whisper large) |
| **GPU** | Не требуется | NVIDIA с CUDA 11.8+ (ускорение Whisper) |
| **Диск** | 5 GB свободного места | 20+ GB SSD |
| **Интернет** | Для установки зависимостей | Для YouTube Downloader |

### Программное обеспечение

**Обязательно:**
- ✅ Python 3.10 или выше
- ✅ FFmpeg 4.4+ (с FFprobe)
- ✅ pip (менеджер пакетов Python)

**Опционально:**
- Git (для клонирования репозитория)
- CUDA Toolkit 11.8+ (для GPU ускорения Whisper)
- Docker + Docker Compose (для контейнеризации)

---

## 🚀 Установка

### Быстрая установка (5 минут)

**Для опытных пользователей:**

```bash
# 1. Клонирование
git clone https://github.com/your-repo/video-production-studio.git
cd video-production-studio

# 2. Виртуальное окружение
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или: venv\Scripts\activate  # Windows

# 3. Зависимости
pip install --upgrade pip
pip install -r requirements.txt

# 4. FFmpeg (если нет)
# Windows: choco install ffmpeg
# macOS: brew install ffmpeg
# Linux: sudo apt install ffmpeg

# 5. Запуск
streamlit run app.py
```

Откройте браузер: `http://localhost:8501`

---

### Windows

#### Метод 1: Chocolatey (рекомендуется)

**Шаг 1: Установка Chocolatey**

Откройте **PowerShell от имени администратора**:

```powershell
Set-ExecutionPolicy Bypass -Scope Process -Force
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
```

**Шаг 2: Установка программ**

```powershell
choco install python git ffmpeg -y
```

**Шаг 3: Перезапустите PowerShell** (обычный режим, не администратор)

**Шаг 4: Установка проекта**

```bash
git clone https://github.com/your-repo/video-production-studio.git
cd video-production-studio

python -m venv venv
.\venv\Scripts\activate

pip install --upgrade pip
pip install -r requirements.txt

streamlit run app.py
```

#### Метод 2: Ручная установка

1. **Python:** Скачайте с [python.org](https://www.python.org/downloads/)
   - ⚠️ Отметьте **"Add Python to PATH"**!

2. **Git:** Скачайте с [git-scm.com](https://git-scm.com/download/win)

3. **FFmpeg:**
   - Скачайте с [ffmpeg.org/download.html](https://ffmpeg.org/download.html)
   - Распакуйте в `C:\ffmpeg`
   - Добавьте `C:\ffmpeg\bin` в PATH:
     - "Система" → "Дополнительные параметры системы"
     - "Переменные среды" → "Path" → "Создать"
     - Введите `C:\ffmpeg\bin`

4. **Проверка:**
   ```bash
   python --version
   git --version
   ffmpeg -version
   ```

5. **Установка проекта** — как в Методе 1, шаг 4

---

### macOS

**Через Homebrew:**

```bash
# Установка Homebrew (если нет)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Установка зависимостей
brew install python@3.11 ffmpeg git

# Проверка
python3 --version
ffmpeg -version

# Клонирование проекта
git clone https://github.com/your-repo/video-production-studio.git
cd video-production-studio

# Виртуальное окружение
python3 -m venv venv
source venv/bin/activate

# Зависимости
pip install --upgrade pip
pip install -r requirements.txt

# Запуск
streamlit run app.py
```

---

### Linux

#### Ubuntu / Debian

```bash
# Обновление системы
sudo apt update && sudo apt upgrade -y

# Установка зависимостей
sudo apt install -y python3 python3-pip python3-venv ffmpeg git

# Клонирование
git clone https://github.com/your-repo/video-production-studio.git
cd video-production-studio

# Виртуальное окружение
python3 -m venv venv
source venv/bin/activate

# Зависимости Python
pip install --upgrade pip
pip install -r requirements.txt

# Запуск
streamlit run app.py
```

#### Fedora

```bash
sudo dnf install -y python3 python3-pip ffmpeg git
# Далее аналогично Ubuntu
```

#### Arch Linux

```bash
sudo pacman -S python python-pip ffmpeg git
# Далее аналогично Ubuntu
```

---

### Docker

**Быстрый старт с Docker Compose:**

```bash
# Клонирование
git clone https://github.com/your-repo/video-production-studio.git
cd video-production-studio

# Запуск (фоновый режим)
docker-compose up -d

# Просмотр логов
docker-compose logs -f

# Остановка
docker-compose down
```

**Ручная сборка:**

```bash
# Сборка образа
docker build -t video-studio:latest .

# Запуск контейнера
docker run -d \
  -p 8501:8501 \
  -v $(pwd)/assets:/app/assets \
  --name video-studio \
  video-studio:latest

# Логи
docker logs -f video-studio

# Остановка
docker stop video-studio
docker rm video-studio
```

Приложение доступно: `http://localhost:8501`

---

## ⚡ Быстрый старт

### Первое видео за 3 минуты

**1. Запустите приложение:**

```bash
# Активация виртуального окружения
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate     # Windows

# Запуск
streamlit run app.py
```

**2. Откройте браузер:** `http://localhost:8501`

**3. Создайте первое видео:**

- Выберите **🎵 Background Music** в боковом меню
- Загрузите любое видео (.mp4) и музыку (.mp3)
- Настройте громкость:
  - Музыка: **10%** (0.1)
  - Голос: **100%** (1.0)
- Нажмите **🚀 Обработать видео**
- Скачайте результат!

### Структура интерфейса

```
┌─────────────────────────────────────────────────────────────┐
│  🎬 Video Production Studio                                 │
├───────────────────┬─────────────────────────────────────────┤
│  📂 МОДУЛИ        │  📊 ГЛАВНАЯ СТРАНИЦА                    │
│                   │                                          │
│  🎵 Bg Music      │  ┌──────────┬──────────┬──────────┐     │
│  📝 Subtitles     │  │    42    │     5    │    18    │     │
│  🎤 Mixer         │  │ Операций │ Сегодня  │  Файлов  │     │
│  📐 Convert       │  └──────────┴──────────┴──────────┘     │
│  📥 Download      │                                          │
│                   │  📜 История операций                     │
│  ───────────      │  • 14:32 Background Music: video.mp4    │
│                   │  • 13:45 TikTok Subtitles: clip.mp4     │
│  🎯 Действия      │  • 12:10 Convert 9:16: batch (15 files) │
│  🗑️ Очистить      │                                          │
│  📁 Папки         │  [Подробная статистика]                 │
│                   │                                          │
│  ⚙️ Настройки     │                                          │
│  📚 Справка       │                                          │
└───────────────────┴─────────────────────────────────────────┘
```

---

## 📖 Модули

### 1️⃣ Background Music

**Назначение:** Добавление фоновой музыки к видео с профессиональным микшированием

#### Возможности

- ✅ Автоматическое зацикливание музыки
- ✅ Раздельная регулировка громкости (голос/музыка)
- ✅ Fade-in/Fade-out эффекты
- ✅ Сохранение качества (CRF 18)
- ✅ Поддержка всех популярных форматов

#### CLI использование

**Базовый синтаксис:**
```bash
python modules/background_music.py <video> <audio> [опции]
```

**Опции:**

| Параметр | Описание | По умолчанию |
|----------|----------|--------------|
| `-o, --output` | Путь для сохранения | `video_with_music.mp4` |
| `-m, --music-volume` | Громкость музыки (0.0-2.0) | `0.1` (10%) |
| `-v, --voice-volume` | Громкость голоса (0.0-2.0) | `1.0` (100%) |
| `--fade-in` | Fade-in (секунды) | `0.0` |
| `--fade-out` | Fade-out (секунды) | `0.0` |
| `--no-loop` | Не зацикливать музыку | `False` |
| `--crf` | Качество видео (0-51) | `18` |
| `--preset` | Скорость кодирования | `medium` |
| `--video-bitrate` | Битрейт видео | `8000k` |
| `--audio-bitrate` | Битрейт аудио | `320k` |

**Примеры:**

```bash
# Базовое использование
python modules/background_music.py video.mp4 music.mp3

# С настройками
python modules/background_music.py video.mp4 music.mp3 \
  -o output.mp4 \
  -m 0.15 \
  -v 1.0 \
  --fade-in 2 \
  --fade-out 3

# Высокое качество, медленное кодирование
python modules/background_music.py video.mp4 music.mp3 \
  --crf 15 \
  --preset slow \
  --video-bitrate 10000k
```

#### Python API

```python
from modules.background_music import add_background_music, AudioSettings, VideoConfig

# Настройки аудио
audio_settings = AudioSettings(
    music_volume=0.1,       # 10% громкости
    voice_volume=1.0,       # 100% громкости
    loop_music=True,        # Зациклить музыку
    fade_in_duration=2.0,   # Fade-in 2 сек
    fade_out_duration=3.0   # Fade-out 3 сек
)

# Настройки видео
video_config = VideoConfig(
    crf=18,                 # Высокое качество
    preset='slow',          # Лучшее сжатие
    video_bitrate='8000k',
    audio_bitrate='320k'
)

# Обработка
result = add_background_music(
    video_path='video.mp4',
    music_path='background.mp3',
    output_path='result.mp4',
    audio_settings=audio_settings,
    video_config=video_config,
    force_overwrite=True
)

print(f"Готово: {result}")
```

#### Важные особенности

**⚠️ MoviePy v2:**
Проект использует MoviePy 2.0+. Важные изменения:
- `volumex()` → `multiply_volume()`
- `audio_fadein()` и `audio_fadeout()` работают так же
- `CompositeAudioClip` для микширования

**Поддерживаемые форматы:**
- Видео: `.mp4`, `.avi`, `.mov`, `.mkv`, `.webm`, `.flv`
- Аудио: `.mp3`, `.wav`, `.aac`, `.m4a`, `.flac`, `.ogg`

---

### 2️⃣ TikTok Subtitles

**Назначение:** Создание субтитров с AI-транскрипцией и анимированной подсветкой слов

#### Как это работает

```
┌────────────┐    ┌──────────────┐    ┌────────────────┐    ┌──────────┐
│   Видео    │ →  │   Whisper    │ →  │  ASS генератор │ →  │  FFmpeg  │
│  (любой)   │    │ Транскрипция │    │ (пословная     │    │ Прожиг   │
│            │    │ с timestamp  │    │  подсветка)    │    │ в видео  │
└────────────┘    └──────────────┘    └────────────────┘    └──────────┘
```

#### Возможности

- ✅ AI-транскрипция Whisper (90+ языков)
- ✅ Пословная подсветка с точными timestamp
- ✅ Настройка цветов, шрифтов, размеров
- ✅ Экспорт ASS субтитров
- ✅ Автоопределение языка
- ✅ GPU ускорение (CUDA)

#### Модели Whisper

| Модель | Скорость | Точность | RAM | VRAM (GPU) | Языки | Рекомендация |
|--------|----------|----------|-----|------------|-------|--------------|
| **tiny** | ⚡⚡⚡⚡ | ⭐⭐ | 1 GB | 1 GB | 99 | Тесты |
| **base** | ⚡⚡⚡ | ⭐⭐⭐ | 1 GB | 1 GB | 99 | Черновики |
| **small** | ⚡⚡ | ⭐⭐⭐⭐ | 2 GB | 2 GB | 99 | **Рекомендуется** |
| **medium** | ⚡ | ⭐⭐⭐⭐⭐ | 5 GB | 5 GB | 99 | Высокая точность |
| **large-v2** | 🐌 | ⭐⭐⭐⭐⭐ | 10 GB | 10 GB | 99 | Максимум |

#### CLI использование

**Базовый синтаксис:**
```bash
python modules/tiktok_subs.py -i <input> -o <output> [опции]
```

**Опции Whisper:**

| Параметр | Описание | По умолчанию |
|----------|----------|--------------|
| `--model` | Модель (tiny/base/small/medium/large-v2) | `small` |
| `--language` | Язык (ru/en/None для авто) | `None` |
| `--device` | Устройство (cpu/cuda) | `None` (авто) |
| `--no-vad` | Отключить Voice Activity Detection | `False` |

**Опции стиля:**

| Параметр | Описание | По умолчанию |
|----------|----------|--------------|
| `--green` | Цвет подсветки (#RRGGBB) | `#00FF6A` |
| `--white` | Цвет обычных слов (#RRGGBB) | `#FFFFFF` |
| `--font` | Название шрифта | `Arial` |
| `--font-scale` | Размер (доля от высоты) | `0.07` (7%) |
| `--marginv` | Вертикальный отступ (доля) | `0.13` |

**Примеры:**

```bash
# Базовое использование (автоопределение языка)
python modules/tiktok_subs.py -i video.mp4 -o output.mp4

# Русский язык, модель medium
python modules/tiktok_subs.py -i video.mp4 -o output.mp4 \
  --model medium \
  --language ru

# Кастомные цвета и шрифт
python modules/tiktok_subs.py -i video.mp4 -o output.mp4 \
  --green "#FF00FF" \
  --white "#FFFF00" \
  --font "Impact" \
  --font-scale 0.08

# GPU ускорение
python modules/tiktok_subs.py -i video.mp4 -o output.mp4 \
  --model medium \
  --device cuda
```

#### Python API

```python
from modules.tiktok_subs import TikTokSubtitles, WhisperConfig, SubtitleStyle, VideoConfig

# Конфигурация Whisper
whisper_config = WhisperConfig(
    model='medium',
    language='ru',  # или None для авто
    device='cuda',  # или 'cpu'
    vad=True
)

# Стиль субтитров
subtitle_style = SubtitleStyle(
    highlight_color='#00FF6A',  # Зелёный для текущего слова
    normal_color='#FFFFFF',     # Белый для остальных
    font_name='Impact',
    font_scale=0.08,            # 8% от высоты видео
    bold=True,
    alignment=2                 # Внизу по центру
)

# Конфигурация видео
video_config = VideoConfig(
    crf=18,
    preset='medium'
)

# Создание процессора
processor = TikTokSubtitles(
    whisper_config=whisper_config,
    subtitle_style=subtitle_style,
    video_config=video_config
)

# Обработка
output_video, ass_file = processor.process(
    input_video='video.mp4',
    output_video='output.mp4',
    keep_ass=True  # Сохранить ASS файл
)

print(f"Видео: {output_video}")
print(f"Субтитры: {ass_file}")
```

#### GPU ускорение

**Установка CUDA версии PyTorch:**

```bash
# Удаление CPU версии
pip uninstall torch torchvision torchaudio -y

# Установка CUDA 11.8 версии
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Проверка
python -c "import torch; print('CUDA доступна:', torch.cuda.is_available())"
```

---

### 3️⃣ Audio Mixer

**Назначение:** Добавление аудио к случайному или заданному фрагменту видео

#### Сценарии использования

- 🎵 Добавление музыки к конкретному моменту
- 🎙️ Озвучка фрагмента видео
- 🎬 Создание превью с аудио
- 🧪 Тестирование разных аудио на видео

#### Как это работает

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────┐
│  Видео      │  →  │ Выбор фрагмента  │  →  │  Новое видео│
│  (10 мин)   │     │ (случайный или   │     │  (длина =   │
│             │     │  конкретный)     │     │   аудио)    │
└─────────────┘     └──────────────────┘     └─────────────┘
       ↑                      ↓
       │             ┌──────────────────┐
       └─────────────│  Микширование    │
                     │  аудио дорожек   │
                     └──────────────────┘
```

#### CLI использование

**Режимы работы:**

1. **Случайное время (по умолчанию)**
2. **Диапазон времени**
3. **Конкретное время**

**Опции:**

| Параметр | Описание | По умолчанию |
|----------|----------|--------------|
| `-o, --output` | Путь для сохранения | `video_mixed.mp4` |
| `--min-start` | Минимальное время начала (сек) | `5.0` |
| `--max-start` | Максимальное время начала (сек) | `None` |
| `--start-at` | Конкретное время (игнорирует random) | `None` |
| `--audio-volume` | Громкость добавляемого аудио | `1.0` |
| `--keep-original` | Громкость оригинального аудио | `0.0` |
| `--fade-in` | Fade-in (сек) | `0.0` |
| `--fade-out` | Fade-out (сек) | `0.0` |
| `--random-seed` | Seed для воспроизводимости | `None` |

**Примеры:**

```bash
# Случайное время (5+ сек от начала)
python modules/video_audio_mixer.py video.mp4 audio.mp3

# Диапазон 10-30 сек
python modules/video_audio_mixer.py video.mp4 audio.mp3 \
  --min-start 10 \
  --max-start 30

# Конкретное время 15.5 сек
python modules/video_audio_mixer.py video.mp4 audio.mp3 \
  --start-at 15.5

# С микшированием оригинального аудио
python modules/video_audio_mixer.py video.mp4 audio.mp3 \
  --audio-volume 1.0 \
  --keep-original 0.3 \
  --fade-in 1 \
  --fade-out 2

# Воспроизводимый результат (seed)
python modules/video_audio_mixer.py video.mp4 audio.mp3 \
  --random-seed 42
```

#### Python API

```python
from modules.video_audio_mixer import VideoAudioMixer, AudioSettings, VideoConfig

# Настройки аудио
audio_settings = AudioSettings(
    min_start_time=10.0,      # Не раньше 10 сек
    max_start_time=30.0,      # Не позже 30 сек
    # specific_start_time=15.5,  # Или конкретное время
    audio_volume=1.0,          # Громкость нового аудио
    original_volume=0.3,       # 30% оригинального
    fade_in_duration=1.0,      # Fade-in 1 сек
    fade_out_duration=2.0,     # Fade-out 2 сек
    random_seed=42             # Для повторяемости
)

# Настройки видео
video_config = VideoConfig(
    crf=18,
    preset='medium'
)

# Создание миксера
mixer = VideoAudioMixer(
    audio_settings=audio_settings,
    video_config=video_config
)

# Обработка
result = mixer.process(
    video_path='video.mp4',
    audio_path='audio.mp3',
    output_path='result.mp4',
    force_overwrite=True
)

print(f"Готово: {result}")
```

---

### 4️⃣ Convert to 9:16

**Назначение:** Пакетная конвертация видео в вертикальный формат для социальных сетей

#### Как работает обрезка

**Исходное видео 16:9 (1920x1080):**
```
┌────────────────────────────────────┐
│                                    │  ← Crop position: top
│           ВИДИМАЯ ОБЛАСТЬ          │     (прижать к верху)
│             9:16 (1080x1920)       │
│                                    │
├────────────────────────────────────┤
│         ОБРЕЗАЕТСЯ                 │  ← Crop position: center
│                                    │     (центрировать)
└────────────────────────────────────┘
              ↑
     Crop position: bottom
      (прижать к низу)
```

#### Возможности

- ✅ Автоматическая обрезка в 9:16 (1080x1920)
- ✅ Выбор позиции: top/center/bottom
- ✅ Параллельная обработка (многопоточность)
- ✅ Удаление аудио (опционально)
- ✅ Пропуск уже вертикальных видео
- ✅ JSON-отчёты с детальной статистикой

#### CLI использование

**Базовый синтаксис:**
```bash
python modules/video_converter.py -i <input_dir> -o <output_dir> [опции]
```

**Опции:**

| Параметр | Описание | По умолчанию |
|----------|----------|--------------|
| `-i, --input` | Входная директория | `assets/downloads` |
| `-o, --output` | Выходная директория | `assets/stock_videos` |
| `--crf` | Качество видео (0-51) | `18` |
| `--preset` | Скорость кодирования | `medium` |
| `--position` | Позиция обрезки (top/center/bottom) | `top` |
| `--keep-audio` | Сохранить аудио | `False` |
| `--audio-codec` | Аудио кодек (если сохраняется) | `aac` |
| `--audio-bitrate` | Аудио bitrate | `192k` |
| `--delete-source` | Удалить исходники после обработки | `False` |
| `--no-skip-vertical` | Не пропускать вертикальные | `False` |
| `--workers` | Количество потоков | `None` (авто) |
| `--min-width` | Минимальная ширина | `720` |
| `--min-height` | Минимальная высота | `1280` |

**Примеры:**

```bash
# Базовое использование
python modules/video_converter.py

# Кастомные пути
python modules/video_converter.py \
  -i videos/ \
  -o output/

# Высокое качество, медленное кодирование
python modules/video_converter.py \
  --crf 15 \
  --preset slow

# С сохранением аудио
python modules/video_converter.py \
  --keep-audio \
  --audio-codec aac \
  --audio-bitrate 320k

# Максимальная производительность
python modules/video_converter.py \
  --workers 8 \
  --preset ultrafast

# Позиция обрезки по центру
python modules/video_converter.py \
  --position center
```

#### Python API

```python
from modules.video_converter import BatchConverter, ConversionConfig

# Конфигурация
config = ConversionConfig(
    crf=18,
    preset='medium',
    crop_position='top',       # top/center/bottom
    remove_audio=True,         # Удалить аудио
    skip_if_vertical=True,     # Пропускать вертикальные
    max_workers=4,             # 4 потока
    min_width=720,             # Минимум 720px
    min_height=1280,           # Минимум 1280px
    delete_source=False        # Не удалять исходники
)

# Создание конвертера
converter = BatchConverter(config)

# Обработка директории
stats = converter.process_directory(
    input_dir='videos/',
    output_dir='output/',
    save_report=True  # Сохранить JSON отчёт
)

# Статистика
print(f"Обработано: {stats['success']}/{stats['total']}")
print(f"Ошибок: {stats['failed']}")
print(f"Пропущено: {stats['skipped']}")
```

#### JSON отчёты

Автоматически создаются в выходной директории:

```json
{
  "timestamp": "2024-01-15T14:30:00",
  "statistics": {
    "total": 10,
    "success": 8,
    "failed": 1,
    "skipped": 1,
    "total_input_size_mb": 523.4,
    "total_output_size_mb": 412.1,
    "compression_ratio": 0.787,
    "total_time_seconds": 245.2
  },
  "results": [
    {
      "input_path": "video1.mp4",
      "output_path": "video1_9x16.mp4",
      "success": true,
      "input_size_mb": 52.3,
      "output_size_mb": 41.2,
      "processing_time": 24.5
    }
  ]
}
```

---

### 5️⃣ YouTube Downloader

**Назначение:** Профессиональная загрузка видео с YouTube

#### Возможности

- ✅ Выбор качества: 144p → 8K
- ✅ Загрузка плейлистов
- ✅ Субтитры на любых языках
- ✅ Cookies для приватных видео
- ✅ Возобновление прерванных загрузок
- ✅ Ограничение скорости
- ✅ Пакетная загрузка

#### Доступные качества

| Preset | Разрешение | Битрейт (примерно) | Размер (10 мин) |
|--------|------------|---------------------|-----------------|
| **144p** | 256x144 | 200 kbps | 15 MB |
| **240p** | 426x240 | 400 kbps | 30 MB |
| **360p** | 640x360 | 800 kbps | 60 MB |
| **480p** | 854x480 | 1.5 Mbps | 110 MB |
| **720p** | 1280x720 | 2.5 Mbps | 190 MB |
| **1080p** | 1920x1080 | 4 Mbps | 300 MB |
| **1440p** | 2560x1440 | 8 Mbps | 600 MB |
| **4K** | 3840x2160 | 15 Mbps | 1.1 GB |
| **8K** | 7680x4320 | 40 Mbps | 3 GB |
| **audio** | - | 128-320 kbps | 10-25 MB |

#### CLI использование

**Базовый синтаксис:**
```bash
python modules/youtube_downloader.py "<URL>" [опции]
```

**Опции:**

| Параметр | Описание | По умолчанию |
|----------|----------|--------------|
| `-q, --quality` | Качество видео | `1080p` |
| `-f, --format` | Формат файла (mp4/mkv/webm) | `mp4` |
| `-o, --output` | Выходная директория | `assets/downloads` |
| `--subtitles` | Скачать субтитры | `False` |
| `--subtitle-lang` | Языки субтитров (через запятую) | `en,ru` |
| `--playlist` | Загрузить плейлист | `False` |
| `--playlist-start` | Начать с видео № | `1` |
| `--playlist-end` | Закончить на видео № | `None` |
| `--playlist-items` | Номера видео (1,2,5-7) | `None` |
| `--rate-limit` | Ограничение скорости (1M, 500K) | `None` |
| `--cookies` | Файл cookies | `None` |

**Примеры:**

```bash
# Базовая загрузка
python modules/youtube_downloader.py "https://youtube.com/watch?v=..."

# 4K с субтитрами
python modules/youtube_downloader.py "URL" \
  -q 4K \
  --subtitles \
  --subtitle-lang "en,ru,es"

# Только аудио
python modules/youtube_downloader.py "URL" \
  --quality audio \
  -f m4a

# Плейлист (первые 5 видео)
python modules/youtube_downloader.py "PLAYLIST_URL" \
  --playlist \
  --playlist-items "1-5"

# С ограничением скорости
python modules/youtube_downloader.py "URL" \
  --rate-limit 1M

# Пакетная загрузка из файла
python modules/youtube_downloader.py --batch urls.txt
```

**Файл urls.txt:**
```
https://youtube.com/watch?v=video1
https://youtube.com/watch?v=video2
https://youtube.com/watch?v=video3
```

#### Python API

```python
from modules.youtube_downloader import YouTubeDownloader, DownloadConfig

# Конфигурация
config = DownloadConfig(
    quality='1080p',
    format_preference='mp4',
    write_subtitles=True,
    subtitle_language='en,ru',
    download_playlist=False,
    rate_limit='1M'  # 1 MB/s
)

# Создание загрузчика
downloader = YouTubeDownloader(config)

# Одно видео
result = downloader.download('https://youtube.com/watch?v=...')

if result.success:
    print(f"Скачано: {result.output_path}")
    print(f"Размер: {result.video_info.format_filesize()}")
else:
    print(f"Ошибка: {result.error}")

# Несколько видео
urls = [
    'https://youtube.com/watch?v=...',
    'https://youtube.com/watch?v=...'
]

stats = downloader.download_multiple(urls, save_report=True)
print(f"Успешно: {stats['success']}/{stats['total']}")
```

---

## 🖥 Веб-интерфейс (Streamlit)

### Главная страница (app.py)

**Функции:**
- 📊 Статистика использования
- 📜 История операций (сохраняется в JSON)
- 🎯 Быстрые действия (открытие папок, очистка)
- ⚙️ Глобальные настройки

**Скриншот структуры:**

```
┌─────────────────────────────────────────────────────────┐
│                  🎬 Video Production Studio             │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────┬──────────────┬──────────────┐        │
│  │      42      │       5      │      18      │        │
│  │   Операций   │   Сегодня    │   Файлов     │        │
│  └──────────────┴──────────────┴──────────────┘        │
│                                                         │
│  📜 Последние операции:                                │
│  ┌─────────────────────────────────────────────┐       │
│  │ 14:32 - Background Music - Added music      │       │
│  │   video: clip.mp4, music: bg.mp3            │       │
│  ├─────────────────────────────────────────────┤       │
│  │ 13:45 - TikTok Subtitles - Created subs     │       │
│  │   video: tutorial.mp4, model: small         │       │
│  └─────────────────────────────────────────────┘       │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Страницы модулей (pages/)

Каждый модуль имеет свою страницу с:
- 📁 Загрузка файлов (upload или выбор из папки)
- ⚙️ Настройки модуля
- 🚀 Кнопка обработки
- 📥 Скачивание результата
- 👀 Превью видео

**Пример: Background Music**

```
┌─────────────────────────────────────────────────────────┐
│              🎵 Добавление фоновой музыки               │
├─────────────────────┬───────────────────────────────────┤
│  📁 Загрузка        │  ⚙️ Настройки                     │
│                     │                                   │
│  ○ Загрузить файл   │  Громкость музыки: ▓▓░░░░░ 10%   │
│  ○ Из папки         │  Громкость голоса: ▓▓▓▓▓▓▓ 100%  │
│                     │                                   │
│  Видео:             │  ☑ Зациклить музыку               │
│  [Выбрать файл]     │                                   │
│                     │  Fade-in:  [0.0] сек              │
│  Музыка:            │  Fade-out: [0.0] сек              │
│  [Выбрать файл]     │                                   │
│                     │  🎬 Качество: CRF 18, medium      │
├─────────────────────┴───────────────────────────────────┤
│            [🚀 Обработать видео]                        │
└─────────────────────────────────────────────────────────┘
```

---

## ⚙️ Конфигурация

### Глобальные настройки (config/settings.py)

```python
@dataclass
class AppSettings:
    # Пути
    downloads_dir: Path = Path('assets/downloads')
    output_dir: Path = Path('assets/output')
    temp_dir: Path = Path('assets/temp')
    music_dir: Path = Path('assets/music')
    stock_videos_dir: Path = Path('assets/stock_videos')
    
    # Качество по умолчанию
    default_crf: int = 18           # 0-51, меньше = лучше
    default_preset: str = 'medium'  # ultrafast → veryslow
    default_video_bitrate: str = '8000k'
    default_audio_bitrate: str = '320k'
    
    # Временные файлы
    keep_temp_files: bool = False
    auto_cleanup_days: int = 7
    
    # Производительность
    max_workers: int = 4
    
    # История
    max_history_items: int = 100
```

### Изменение настроек

**Программно:**

```python
from config.settings import AppSettings

settings = AppSettings()
settings.default_crf = 15  # Лучше качество
settings.max_workers = 8   # Больше потоков
settings.keep_temp_files = True
settings.save()
```

**Через переменные окружения (.env):**

```bash
# Создайте файл .env в корне проекта
DEFAULT_CRF=15
DEFAULT_PRESET=slow
MAX_WORKERS=8
KEEP_TEMP_FILES=true
```

### Streamlit конфигурация (.streamlit/config.toml)

```toml
[server]
port = 8501
headless = true
enableCORS = false

[theme]
primaryColor = "#667eea"
backgroundColor = "#0e1117"
secondaryBackgroundColor = "#262730"
textColor = "#fafafa"
font = "sans serif"

[browser]
gatherUsageStats = false
```

---

## 💡 Примеры использования

### Пример 1: Полный цикл для TikTok

**Задача:** Скачать видео с YouTube и подготовить для TikTok

```bash
# 1. Скачать видео (1080p)
python modules/youtube_downloader.py "URL" -q 1080p -o assets/downloads

# 2. Конвертировать в 9:16
python modules/video_converter.py \
  -i assets/downloads \
  -o assets/temp \
  --position top

# 3. Добавить субтитры
python modules/tiktok_subs.py \
  -i assets/temp/video_9x16.mp4 \
  -o assets/temp/video_subs.mp4 \
  --model small \
  --language ru

# 4. Добавить фоновую музыку
python modules/background_music.py \
  assets/temp/video_subs.mp4 \
  assets/music/background.mp3 \
  -o assets/output/final_tiktok.mp4 \
  -m 0.1 -v 1.0
```

### Пример 2: Пакетная обработка

**Задача:** Добавить одну и ту же музыку ко всем видео в папке

```python
from pathlib import Path
from modules.background_music import add_background_music, AudioSettings, VideoConfig

# Настройки
audio_settings = AudioSettings(music_volume=0.1, loop_music=True)
video_config = VideoConfig(crf=18, preset='fast')

# Музыка
music_path = Path('assets/music/background.mp3')

# Обработка всех видео
videos = Path('assets/downloads').glob('*.mp4')
for video in videos:
    output = Path('assets/output') / f"{video.stem}_music.mp4"
    
    print(f"Обработка: {video.name}")
    add_background_music(
        video_path=video,
        music_path=music_path,
        output_path=output,
        audio_settings=audio_settings,
        video_config=video_config
    )
    print(f"✅ Готово: {output.name}")
```

### Пример 3: Автоматизация с расписанием

**Задача:** Автоматически обрабатывать новые видео

```python
import time
from pathlib import Path
from modules.video_converter import BatchConverter, ConversionConfig

config = ConversionConfig(
    crf=18,
    preset='medium',
    max_workers=4
)

converter = BatchConverter(config)
input_dir = Path('assets/downloads')
output_dir = Path('assets/stock_videos')

print("🔄 Мониторинг папки загрузок...")

while True:
    # Проверяем новые файлы
    videos = list(input_dir.glob('*.mp4'))
    processed = list(output_dir.glob('*_9x16.mp4'))
    
    new_videos = [v for v in videos if not any(p.stem.startswith(v.stem) for p in processed)]
    
    if new_videos:
        print(f"🎬 Найдено {len(new_videos)} новых видео")
        stats = converter.process_directory(input_dir, output_dir)
        print(f"✅ Обработано: {stats['success']}")
    
    time.sleep(60)  # Проверка каждые 60 сек
```

### Пример 4: Создание серии видео

**Задача:** Создать серию видео с разными фрагментами музыки

```python
from modules.video_audio_mixer import VideoAudioMixer, AudioSettings

video_path = 'long_video.mp4'
audio_path = 'music.mp3'

# Создаём 5 вариантов с разными случайными фрагментами
for i in range(5):
    settings = AudioSettings(
        min_start_time=0,
        max_start_time=300,  # 5 минут
        audio_volume=1.0,
        random_seed=None  # Каждый раз новый
    )
    
    mixer = VideoAudioMixer(audio_settings=settings)
    output = f'variant_{i+1}.mp4'
    
    mixer.process(video_path, audio_path, output)
    print(f"✅ Создан вариант {i+1}")
```

---

## ⚡ Оптимизация производительности

### Рекомендации по качеству и скорости

| Задача | CRF | Preset | Bitrate | Время (1 мин видео) |
|--------|-----|--------|---------|---------------------|
| **Быстрый тест** | 28 | ultrafast | 3000k | 10 сек |
| **Соцсети** | 23 | fast | 5000k | 20 сек |
| **YouTube** | 18 | medium | 8000k | 45 сек |
| **Архив** | 15 | slow | 10000k | 2 мин |
| **Максимум** | 10 | veryslow | 15000k | 5 мин |

### Многопоточность

```python
# Конвертация видео
config = ConversionConfig(
    max_workers=8,  # По количеству ядер CPU
    preset='fast'
)

# FFmpeg
video_config = VideoConfig(
    threads=8  # Параллельное кодирование
)
```

### GPU ускорение (Whisper)

```bash
# Установка CUDA PyTorch
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Проверка
python -c "import torch; print('CUDA:', torch.cuda.is_available())"
```

**В коде:**

```python
whisper_config = WhisperConfig(
    model='medium',
    device='cuda'  # Вместо 'cpu'
)
```

**Ускорение:**
- CPU (medium): ~10 минут на 1 час видео
- GPU (medium): ~2 минуты на 1 час видео

### Оптимизация памяти

```python
# Обработка больших файлов
video_config = VideoConfig(
    preset='ultrafast',  # Меньше буферизации
    threads=2            # Меньше потоков = меньше RAM
)

# Или обработка по частям
from moviepy import VideoFileClip

video = VideoFileClip('large_video.mp4')

# Разбить на части
chunk_duration = 300  # 5 минут
for i in range(0, int(video.duration), chunk_duration):
    chunk = video.subclip(i, min(i + chunk_duration, video.duration))
    chunk.write_videofile(f'chunk_{i}.mp4')
    chunk.close()

video.close()
```

---

## 🔧 Troubleshooting

### FFmpeg не найден

**Симптомы:**
```
FileNotFoundError: ffmpeg not found in PATH
```

**Решение:**

```bash
# Windows (Chocolatey)
choco install ffmpeg

# macOS
brew install ffmpeg

# Linux (Ubuntu)
sudo apt install ffmpeg

# Проверка
ffmpeg -version
ffprobe -version
```

### MoviePy ошибки

**Симптом 1:** `AttributeError: 'VideoFileClip' object has no attribute 'volumex'`

**Причина:** Используется старая версия MoviePy

**Решение:**
```bash
pip uninstall moviepy -y
pip install moviepy>=2.0.0
```

**Симптом 2:** `ModuleNotFoundError: No module named 'moviepy.editor'`

**Решение:**
```bash
pip install moviepy imageio-ffmpeg
```

### Whisper ошибки

**Симптом:** `RuntimeError: CUDA out of memory`

**Решение:**

1. Используйте меньшую модель:
   ```bash
   --model small  # Вместо medium/large
   ```

2. Или переключитесь на CPU:
   ```bash
   --device cpu
   ```

3. Или увеличьте VRAM (закройте другие приложения)

**Симптом:** Медленная транскрипция на CPU

**Решение:** Установите GPU версию (см. "GPU ускорение")

### Streamlit не запускается

**Симптом:** `streamlit: command not found`

**Решение:**

```bash
# Убедитесь, что виртуальное окружение активировано
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate     # Windows

# Переустановка
pip install --upgrade streamlit

# Проверка
streamlit --version
```

### Большой размер выходных файлов

**Решение:**

```python
# Увеличьте CRF (хуже качество, меньше размер)
VideoConfig(crf=23)  # Было 18

# Уменьшите bitrate
VideoConfig(
    video_bitrate='5000k',  # Было 8000k
    audio_bitrate='192k'    # Было 320k
)

# Используйте более агрессивное сжатие
VideoConfig(preset='veryslow')  # Было 'medium'
```

### Медленная обработка

**Решения:**

1. **Используйте быстрые presets:**
   ```python
   VideoConfig(preset='ultrafast')
   ```

2. **Увеличьте потоки:**
   ```python
   ConversionConfig(max_workers=8)
   VideoConfig(threads=8)
   ```

3. **Используйте SSD вместо HDD**

4. **GPU для Whisper** (см. выше)

5. **Отключите ненужные функции:**
   - Не добавляйте субтитры если не нужны
   - Отключите fade-эффекты
   - Используйте меньшую модель Whisper

### Ошибки кодировки в Windows

**Симптом:** `UnicodeDecodeError` при работе с русскими именами файлов

**Решение:**

```python
# В начале скрипта
import sys
import locale

# Установка UTF-8
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
```

### Docker контейнер не запускается

**Симптом:** Ошибки при `docker-compose up`

**Решение:**

```bash
# Проверка Docker
docker --version
docker-compose --version

# Пересборка образа
docker-compose build --no-cache

# Проверка логов
docker-compose logs -f

# Очистка старых образов
docker system prune -a
```

---

## ❓ FAQ

### Общие вопросы

**Q: Можно ли использовать без веб-интерфейса?**

A: Да! Все модули работают из командной строки (CLI):
```bash
python modules/background_music.py video.mp4 music.mp3
```

**Q: Какое качество видео использовать?**

A: Зависит от цели:
- Соцсети (TikTok/Reels): **CRF 20-23**, preset **fast**
- YouTube: **CRF 18**, preset **medium**
- Архив: **CRF 15**, preset **slow**

**Q: Какую модель Whisper выбрать?**

A:
- **tiny/base** — быстрые тесты
- **small** — рекомендуется (баланс скорость/точность)
- **medium** — высокая точность
- **large** — максимум (требует много ресурсов)

**Q: Поддерживается ли GPU?**

A: Да, для Whisper:
```bash
pip install torch --index-url https://download.pytorch.org/whl/cu118
```

**Q: Какие форматы поддерживаются?**

A:
- Видео: MP4, AVI, MOV, MKV, WebM, FLV
- Аудио: MP3, WAV, AAC, M4A, FLAC, OGG
- Субтитры: ASS (экспорт)

### Технические вопросы

**Q: Можно ли обрабатывать 4K видео?**

A: Да, но:
- Требуется больше RAM (8+ GB)
- Обработка займёт больше времени
- Используйте SSD
- Рекомендуется GPU

**Q: Как ускорить обработку?**

A:
1. Используйте `preset='ultrafast'`
2. Увеличьте `max_workers` и `threads`
3. GPU для Whisper
4. Используйте SSD
5. Увеличьте CRF (хуже качество, быстрее)

**Q: Почему большой размер файлов?**

A: Проект использует высокое качество по умолчанию (CRF 18). Для уменьшения:
```python
VideoConfig(
    crf=23,              # Увеличить
    preset='veryslow',   # Лучшее сжатие
    video_bitrate='5000k'  # Уменьшить
)
```

**Q: Можно ли использовать на слабом ПК?**

A: Да, но с ограничениями:
- Используйте модель **tiny** для Whisper
- `max_workers=1`
- `preset='ultrafast'`
- Обрабатывайте видео по одному
- Не используйте GPU функции

**Q: Как обновить приложение?**

A:
```bash
git pull origin main
pip install -r requirements.txt --upgrade
```

**Q: Безопасно ли использовать YouTube Downloader?**

A: Технически — да (используется yt-dlp), но:
- ⚠️ Соблюдайте авторские права
- ⚠️ Некоторые видео защищены
- ✅ Можно использовать cookies для приватных видео

**Q: Где хранятся обработанные файлы?**

A: По умолчанию:
```
project/
└── assets/
    ├── downloads/      # Загрузки YouTube
    ├── output/         # Результаты обработки
    ├── temp/           # Временные файлы (автоочистка)
    ├── music/          # Ваша музыкальная библиотека
    └── stock_videos/   # Готовые 9:16 видео
```

**Q: Можно ли изменить пути к папкам?**

A: Да, в `config/settings.py`:
```python
settings = AppSettings()
settings.downloads_dir = Path('/custom/path/downloads')
settings.output_dir = Path('/custom/path/output')
settings.save()
```

**Q: Как работает история операций?**

A: Все операции сохраняются в `assets/history.json`:
```json
{
  "timestamp": "2024-01-15T14:32:00",
  "module": "Background Music",
  "action": "Added music",
  "details": {
    "video": "clip.mp4",
    "music": "bg.mp3"
  }
}
```

**Q: Можно ли использовать в коммерческих проектах?**

A: Да, проект под MIT License — свободное использование.

**Q: Какой Python версии требуется?**

A: Python 3.10 или выше. Проверка:
```bash
python --version
```

**Q: Работает ли на Apple Silicon (M1/M2)?**

A: Да, но:
- FFmpeg устанавливается через Homebrew
- Whisper может работать медленнее (нет GPU ускорения)
- Все остальное работает нормально

---

## 🗺️ Backlog улучшений

### Приоритет 1: Quick Wins (1-2 недели)

**Улучшения UX:**
- [ ] Real-time прогресс бары с процентами
- [ ] Предпросмотр видео в браузере (до обработки)
- [ ] Drag & Drop загрузка файлов
- [ ] Темная/светлая тема (переключатель)
- [ ] Горячие клавиши в интерфейсе
- [ ] Поддержка русского языка в UI

**Оптимизация:**
- [ ] Кэширование настроек пользователя
- [ ] Валидация входных файлов (размер, формат, битрейт)
- [ ] Предупреждения о низком качестве исходников
- [ ] Автоматическая очистка temp/ при старте
- [ ] Индикатор использования диска

**Документация:**
- [ ] Интерактивные туториалы в UI
- [ ] Видео-демонстрации модулей (YouTube канал)
- [ ] FAQ раздел в приложении
- [ ] Changelog с версионированием
- [ ] Документация API для разработчиков

### Приоритет 2: Feature Enhancement (1-2 месяца)

**Новые модули:**
- [ ] **Video Trimmer** — обрезка видео (начало/конец/middle)
- [ ] **Watermark Overlay** — добавление водяных знаков/логотипов
- [ ] **Video Merger** — склейка нескольких видео
- [ ] **Batch Rename** — массовое переименование файлов
- [ ] **Video Effects** — фильтры (черно-белое, vintage, blur, sharpen)
- [ ] **Text Overlay** — добавление текста на видео
- [ ] **Image to Video** — создание видео из изображений
- [ ] **GIF Creator** — конвертация видео в GIF

**Улучшение существующих модулей:**
- [ ] Поддержка плейлистов в Audio Mixer
- [ ] Несколько музыкальных дорожек в Background Music
- [ ] Экспорт SRT субтитров (не только ASS)
- [ ] Выбор диапазона видео для конвертации (start/end time)
- [ ] Сохранение шаблонов настроек (presets)
- [ ] Whisper: Поддержка диаризации (разделение спикеров)
- [ ] YouTube Downloader: Поддержка Instagram, Vimeo, Dailymotion

**UI/UX:**
- [ ] Сравнение до/после (side-by-side preview)
- [ ] История операций с откатом (undo)
- [ ] Избранные настройки (user presets)
- [ ] Уведомления по email при завершении длительных задач
- [ ] Очередь задач с приоритетами
- [ ] Bulk operations (массовые операции через UI)

### Приоритет 3: Performance & Scale (2-3 месяца)

**Производительность:**
- [ ] GPU ускорение FFmpeg (NVENC/CUDA для кодирования)
- [ ] Распределённая обработка (Celery + Redis)
- [ ] Кэширование транскрипций Whisper (избегать повторной обработки)
- [ ] Оптимизация памяти для 4K/8K видео
- [ ] Streaming обработка (без полной загрузки в RAM)
- [ ] Hardware acceleration (Intel Quick Sync, AMD VCE)

**Масштабирование:**
- [ ] Multi-user поддержка (авторизация, user accounts)
- [ ] Квоты и лимиты для пользователей
- [ ] Cloud storage интеграция (AWS S3, Google Cloud Storage, Azure)
- [ ] Database для истории (PostgreSQL вместо JSON)
- [ ] Мониторинг и логирование (Prometheus + Grafana)
- [ ] Load balancing для нескольких инстансов

### Приоритет 4: Integration (3-6 месяцев)

**API:**
- [ ] REST API для всех модулей
- [ ] GraphQL API
- [ ] WebSocket для real-time прогресса
- [ ] Webhook notifications
- [ ] Rate limiting и API authentication (JWT)
- [ ] OpenAPI/Swagger документация

**Интеграции:**
- [ ] Zapier/IFTTT интеграция
- [ ] Telegram Bot для управления задачами
- [ ] Discord Bot
- [ ] Slack Bot с notifications
- [ ] Google Drive автоматическая загрузка/выгрузка
- [ ] Dropbox integration
- [ ] OneDrive support

**CI/CD:**
- [ ] GitHub Actions для автоматических тестов
- [ ] Auto-deployment на AWS/GCP/Azure
- [ ] Docker Registry с автоматической сборкой
- [ ] Automatic versioning и GitHub releases
- [ ] Automated testing (unit, integration, e2e)

### Приоритет 5: Advanced Features (6+ месяцев)

**AI-функции:**
- [ ] AI-powered видео редактирование (автоматическая обрезка лучших моментов)
- [ ] Умное кадрирование (распознавание лиц, объектов)
- [ ] Автоматическая цветокоррекция (AI-based)
- [ ] Удаление фона без green screen (ML)
- [ ] Генерация субтитров с эмоциями (анализ интонации)
- [ ] Автоматическое создание превью/thumbnails
- [ ] Scene detection (автоматическое разделение на сцены)
- [ ] Content-aware scaling (умное изменение разрешения)

**Профессиональный редактор:**
- [ ] Timeline редактор с drag-drop
- [ ] Transitions между клипами (fade, wipe, dissolve)
- [ ] Keyframe анимация
- [ ] Audio waveform visualizer
- [ ] Multi-track editing (несколько видео/аудио дорожек)
- [ ] Chroma key (green screen)
- [ ] Color grading панель
- [ ] Video stabilization

**Collaborative работа:**
- [ ] Real-time collaborative editing
- [ ] Комментарии и аннотации на таймлайне
- [ ] Version control для проектов
- [ ] Shared workspaces для команд
- [ ] Approval workflows (рецензирование)
- [ ] Project templates
- [ ] Asset library (shared resources)

**Дополнительные платформы:**
- [ ] Мобильное приложение (iOS/Android - React Native)
- [ ] Desktop приложение (Electron)
- [ ] Chrome/Firefox extension
- [ ] VS Code extension
- [ ] CLI улучшения (interactive mode, autocomplete)

### Приоритет 6: Enterprise (12+ месяцев)

**Enterprise функции:**
- [ ] On-premise deployment решения
- [ ] SSO интеграция (SAML, OAuth 2.0, LDAP)
- [ ] RBAC (Role-Based Access Control)
- [ ] Audit logs с compliance
- [ ] SLA monitoring и reporting
- [ ] Disaster recovery план
- [ ] High availability setup
- [ ] Multi-region deployment

**Коммерциализация:**
- [ ] Subscription billing (Stripe интеграция)
- [ ] Usage analytics и dashboards
- [ ] White-label решения для партнеров
- [ ] Reseller API и программа
- [ ] Partner program с комиссиями
- [ ] Tiered pricing (Free/Pro/Enterprise)
- [ ] Marketplace для плагинов/шаблонов

**Безопасность:**
- [ ] End-to-end encryption для файлов
- [ ] DRM для защищённого контента
- [ ] Watermarking с tracking
- [ ] IP whitelist/blacklist
- [ ] 2FA authentication
- [ ] Security audits и penetration testing

---

## 🤝 Contributing

Мы рады любому вкладу! 🎉

### Как помочь проекту

- 🐛 **Сообщить об ошибке** — создайте [Issue](https://github.com/your-repo/issues)
- 💡 **Предложить функцию** — опишите в Issues с тегом `enhancement`
- 📝 **Улучшить документацию** — исправьте опечатки, добавьте примеры
- 💻 **Отправить Pull Request** — добавьте новую функцию
- ⭐ **Поставить звезду** — если проект понравился!
- 🗣️ **Рассказать друзьям** — поделитесь ссылкой
- 💰 **Поддержать финансово** — [Buy Me a Coffee](https://buymeacoffee.com/yourname)

### Процесс разработки

```bash
# 1. Форкните репозиторий на GitHub

# 2. Клонируйте свой fork
git clone https://github.com/YOURUSERNAME/video-production-studio.git
cd video-production-studio

# 3. Создайте ветку для фичи
git checkout -b feature/amazing-feature

# 4. Установите dev зависимости
pip install -r requirements-dev.txt

# 5. Внесите изменения

# 6. Запустите тесты
pytest tests/ -v

# 7. Проверьте code style
flake8 modules/ pages/
black modules/ pages/ --check

# 8. Commit (следуйте Conventional Commits)
git add .
git commit -m "feat: add amazing feature"

# 9. Push
git push origin feature/amazing-feature

# 10. Создайте Pull Request на GitHub
```

### Code Style

**Python:**
- PEP 8 (проверка: `flake8`)
- Форматирование: `black`
- Type Hints для публичных функций
- Docstrings: Google Style

**Commits:**
Следуйте [Conventional Commits](https://www.conventionalcommits.org/):
- `feat:` — новая функция
- `fix:` — исправление бага
- `docs:` — изменения в документации
- `style:` — форматирование кода
- `refactor:` — рефакторинг
- `test:` — добавление тестов
- `chore:` — обновление зависимостей и т.д.

**Тесты:**
- Обязательны для новых функций
- Покрытие > 80%
- pytest для unit тестов

---

## 📜 Лицензия

Этот проект распространяется под **MIT License**.

```
MIT License

Copyright (c) 2024 Your Name

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## 🙏 Благодарности

Этот проект стал возможен благодаря замечательным open-source библиотекам:

| Проект | Назначение | Лицензия |
|--------|------------|----------|
| **[MoviePy](https://github.com/Zulko/moviepy)** | Обработка видео | MIT |
| **[Streamlit](https://github.com/streamlit/streamlit)** | Веб-фреймворк | Apache 2.0 |
| **[OpenAI Whisper](https://github.com/openai/whisper)** | AI транскрипция | MIT |
| **[stable-ts](https://github.com/jianfch/stable-ts)** | Улучшенный Whisper | MIT |
| **[yt-dlp](https://github.com/yt-dlp/yt-dlp)** | YouTube загрузка | Unlicense |
| **[FFmpeg](https://ffmpeg.org/)** | Мультимедиа фреймворк | LGPL/GPL |
| **[pysubs2](https://github.com/tkarabela/pysubs2)** | Работа с субтитрами | MIT |

Огромное спасибо всем контрибьюторам этих проектов! ❤️

---

## 📞 Контакты и поддержка

- 📧 **Email:** your.email@example.com
- 💬 **Telegram:** [@your_channel](https://t.me/your_channel)
- 🐛 **Issues:** [GitHub Issues](https://github.com/your-repo/issues)
- 💡 **Discussions:** [GitHub Discussions](https://github.com/your-repo/discussions)
- 📖 **Wiki:** [GitHub Wiki](https://github.com/your-repo/wiki)
- 🌟 **Star on GitHub:** [github.com/your-repo](https://github.com/your-repo)

---

<div align="center">

**Сделано с ❤️ для видеомейкеров**

Если проект помог вам — поставьте ⭐ на GitHub!

[⬆ Вернуться к началу](#-video-production-studio)

---

![Footer](https://via.placeholder.com/1200x100/667eea/ffffff?text=Video+Production+Studio+|+Professional+Video+Processing+Tools)

</div>