import os
import random
import argparse
from moviepy import AudioFileClip, VideoFileClip


def add_audio_to_video(video_path, audio_path, output_path=None, min_start=5.0):
    """
    Добавляет аудио к случайному фрагменту видео.

    Args:
        video_path: путь к видео файлу
        audio_path: путь к аудио файлу
        output_path: путь для сохранения (если None, сохраняет рядом с видео)
        min_start: минимальное время начала аудио в секундах

    Returns:
        str: путь к созданному файлу
    """
    # Проверяем существование файлов
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Видео не найдено: {video_path}")
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Аудио не найдено: {audio_path}")

    # Определяем путь вывода
    if output_path is None:
        output_dir = os.path.dirname(video_path) or "."
        output_path = os.path.join(output_dir, "video_with_audio.mp4")

    # Загружаем аудио и видео
    audio = AudioFileClip(audio_path)
    audio_duration = audio.duration

    video = VideoFileClip(video_path)
    video_duration = video.duration

    # Случайная позиция вставки аудио
    max_start = video_duration - audio_duration
    start_time = min_start if max_start < min_start else random.uniform(
        min_start, max_start)
    end_time = start_time + audio_duration

    print(f"Вырезаю видео: {start_time:.2f}s — {end_time:.2f}s")

    # Вырезаем нужный фрагмент видео
    video_clip = video.subclipped(start_time, end_time)

    # Добавляем аудио
    final_clip = video_clip.with_audio(audio)

    # Сохраняем
    print(f"Создаю {output_path}...")
    final_clip.write_videofile(
        output_path,
        codec='libx264',
        audio_codec='aac',
        audio_bitrate='320k'
    )

    # Освобождаем ресурсы
    final_clip.close()
    video.close()
    audio.close()

    print("✅ Готово:", output_path)
    return output_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Добавить аудио к случайному фрагменту видео')
    parser.add_argument('video', help='Путь к видео файлу')
    parser.add_argument('audio', help='Путь к аудио файлу')
    parser.add_argument(
        '-o', '--output', help='Путь для сохранения результата', default=None)
    parser.add_argument('-m', '--min-start', type=float, default=5.0,
                        help='Минимальное время начала аудио (сек)')

    args = parser.parse_args()

    add_audio_to_video(
        video_path=args.video,
        audio_path=args.audio,
        output_path=args.output,
        min_start=args.min_start
    )
