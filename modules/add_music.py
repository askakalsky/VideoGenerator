import os
import argparse
from moviepy import VideoFileClip, AudioFileClip, CompositeAudioClip
import numpy as np


def add_background_music(video_path, music_path, output_path=None,
                         music_volume=0.1, voice_volume=1.0, loop_music=True):
    """
    Добавляет фоновую музыку к видео с аудиокнигой.
    """
    # Проверяем существование файлов
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Видео не найдено: {video_path}")
    if not os.path.exists(music_path):
        raise FileNotFoundError(f"Музыка не найдена: {music_path}")

    # Определяем путь вывода
    if output_path is None:
        base, ext = os.path.splitext(video_path)
        output_path = f"{base}_with_music{ext}"

    print("📹 Загружаю видео...")
    video = VideoFileClip(video_path)
    video_duration = video.duration

    print("🎵 Загружаю музыку...")
    music = AudioFileClip(music_path)
    music_duration = music.duration

    # Зацикливаем музыку если нужно
    if loop_music and music_duration < video_duration:
        loops_needed = int(video_duration / music_duration) + 1
        print(f"🔁 Зацикливаю музыку {loops_needed} раз...")
        music = music.loop(n=loops_needed)

    # Обрезаем музыку под длительность видео
    music = music.subclipped(0, min(music.duration, video_duration))

    # Настраиваем громкость через transform
    print(
        f"🔊 Настраиваю громкость (музыка: {music_volume*100:.0f}%, голос: {voice_volume*100:.0f}%)...")

    def volume_transform_music(get_frame, t):
        return get_frame(t) * music_volume

    def volume_transform_voice(get_frame, t):
        return get_frame(t) * voice_volume

    music = music.transform(volume_transform_music, apply_to=['audio'])

    # Получаем оригинальное аудио из видео
    if video.audio is not None:
        voice = video.audio.transform(
            volume_transform_voice, apply_to=['audio'])
        # Микшируем голос и музыку
        final_audio = CompositeAudioClip([voice, music])
    else:
        print("⚠️ В видео нет аудио, добавляю только музыку")
        final_audio = music

    # Применяем новое аудио к видео
    final_video = video.with_audio(final_audio)

    # Сохраняем
    print(f"💾 Создаю {output_path}...")
    final_video.write_videofile(
        output_path,
        codec='libx264',
        audio_codec='aac',
        audio_bitrate='320k'
    )

    # Освобождаем ресурсы
    final_video.close()
    video.close()
    music.close()

    print("✅ Готово:", output_path)
    return output_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Добавить фоновую музыку к видео с аудиокнигой')

    parser.add_argument('video', help='Путь к видео с аудиокнигой')
    parser.add_argument('music', help='Путь к файлу фоновой музыки')
    parser.add_argument(
        '-o', '--output', help='Путь для сохранения', default=None)
    parser.add_argument('-m', '--music-volume', type=float, default=0.1,
                        help='Громкость музыки (0.0-1.0, по умолчанию 0.1)')
    parser.add_argument('-v', '--voice-volume', type=float, default=1.0,
                        help='Громкость голоса (0.0-1.0, по умолчанию 1.0)')
    parser.add_argument('--no-loop', action='store_true',
                        help='Не зацикливать музыку')

    args = parser.parse_args()

    add_background_music(
        video_path=args.video,
        music_path=args.music,
        output_path=args.output,
        music_volume=args.music_volume,
        voice_volume=args.voice_volume,
        loop_music=not args.no_loop
    )
