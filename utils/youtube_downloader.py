import yt_dlp
import sys
import os


def download_video(url, output_path=None):
    """
    Скачивает видео с YouTube в качестве 1080p

    Args:
        url: ссылка на YouTube видео
        output_path: папка для сохранения видео
    """

    # Получаем путь к текущему файлу (youtube_downloader.py)
    # поднимаемся из utils в project
    base_dir = os.path.dirname(os.path.dirname(__file__))
    downloads_dir = os.path.join(base_dir, "assets", "downloads")

    # Если явно не передан output_path, сохраняем в downloads
    if output_path is None:
        output_path = downloads_dir

    # Создаем папку, если ее нет
    os.makedirs(output_path, exist_ok=True)

    # Настройки для загрузки
    ydl_opts = {
        'format': 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080]/best',
        'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
        'merge_output_format': 'mp4',
        'quiet': False,
        'no_warnings': False,
        'progress_hooks': [progress_hook],
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            print(f"Начинаем загрузку видео: {url}")
            info = ydl.extract_info(url, download=False)
            print(f"Название: {info.get('title', 'Неизвестно')}")
            print(f"Длительность: {info.get('duration', 0) // 60} мин")

            # Загружаем видео
            ydl.download([url])
            print("\n✅ Видео успешно загружено!")

    except Exception as e:
        print(f"❌ Ошибка при загрузке: {str(e)}")
        return False

    return True


def progress_hook(d):
    """Отображение прогресса загрузки"""
    if d['status'] == 'downloading':
        percent = d.get('_percent_str', 'N/A')
        speed = d.get('_speed_str', 'N/A')
        print(f"\rЗагрузка: {percent} | Скорость: {speed}", end='')
    elif d['status'] == 'finished':
        print("\nОбработка файла...")


def main():
    print("=== YouTube Video Downloader (1080p) ===\n")

    # Получаем URL от пользователя
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        url = input("Введите ссылку на YouTube видео: ").strip()

    if not url:
        print("❌ Ссылка не может быть пустой!")
        return

    # Проверяем, что это YouTube ссылка
    if 'youtube.com' not in url and 'youtu.be' not in url:
        print("❌ Это не похоже на YouTube ссылку!")
        return

    # Загружаем видео
    download_video(url)


if __name__ == "__main__":
    main()
