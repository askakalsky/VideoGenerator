#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
convert_videos_to_9x16.py

Скрипт пакетно конвертирует видео:
- обрезает в формат 9:16 (auto crop, центр по ширине, прижат к верху)
- удаляет аудио
- сохраняет в максимальном качестве (lossless, без ухудшения)
- берёт файлы из ../assets/downloads
- сохраняет в ../assets/stock_videos
- удаляет исходники после успешной конвертации
"""

import shutil
import subprocess
from pathlib import Path
from multiprocessing import Pool, cpu_count


VIDEO_EXTS = {'.mp4', '.mov', '.mkv', '.avi',
              '.flv', '.wmv', '.webm', '.mpeg', '.mpg', '.m4v'}


def check_ffmpeg():
    if shutil.which('ffmpeg') is None:
        raise RuntimeError(
            "ffmpeg не найден в PATH. Установите ffmpeg и попробуйте снова.")


def build_filter() -> str:
    """
    Обрезка в 9:16 без рескейла:
    - ширина = высота * 9/16
    - по горизонтали центрируем
    - по вертикали прижимаем к верху
    """
    return "crop=in_h*9/16:in_h:(in_w-in_h*9/16)/2:0"


def convert_file(infile: Path, outdir: Path, overwrite: bool = True):
    outdir.mkdir(parents=True, exist_ok=True)
    basename = infile.stem
    out_path = outdir / f"{basename}_9x16.mp4"

    if out_path.exists() and not overwrite:
        return f"Пропущено {infile.name} (файл уже существует)."

    vf = build_filter()
    cmd = [
        'ffmpeg',
        '-hide_banner',
        '-loglevel', 'error',
        '-y' if overwrite else '-n',
        '-i', str(infile),
        '-vf', vf,
        '-c:v', 'libx264',
        '-preset', 'veryslow',
        '-crf', '0',        # максимально возможное качество (lossless)
        '-pix_fmt', 'yuv420p',
        '-an',              # удалить аудио
        str(out_path)
    ]

    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT)
        infile.unlink()  # удаляем исходник после успешной конвертации
        return f"✅ Готово: {infile.name} -> {out_path.name} (исходник удалён)"
    except subprocess.CalledProcessError as e:
        return f"❌ Ошибка {infile.name}: {e.output.decode('utf-8', errors='replace')}"


def find_videos(folder: Path):
    return [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in VIDEO_EXTS]


def main():
    # текущая папка = project/utils
    base_dir = Path(__file__).resolve().parent.parent  # project/
    downloads = base_dir / "assets" / "downloads"
    stock = base_dir / "assets" / "stock_videos"

    if not downloads.exists() or not downloads.is_dir():
        print("Папка ../assets/downloads не существует.")
        return

    try:
        check_ffmpeg()
    except RuntimeError as e:
        print(e)
        return

    videos = find_videos(downloads)
    if not videos:
        print("Видео не найдены в ../assets/downloads.")
        return

    print(f"Найдено {len(videos)} видео. Конвертация в 9:16 без аудио...")
    print(f"Выходная папка: {stock}")

    tasks = [(v, stock) for v in videos]

    with Pool(processes=cpu_count()) as pool:
        for result in pool.starmap(convert_file, tasks):
            print(result)


if __name__ == '__main__':
    main()
