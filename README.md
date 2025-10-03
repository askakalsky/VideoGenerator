# Добавляем субтитры к видео

```bash
python add_captions.py -i input.mp4 -o out.mp4 --model medium --language ru --font "Orchidea Pro Medium Italic"
```

# Скачиваем видео с YouTube
```bash
python youtube_downloader.py https://www.youtube.com/watch?v=VIDEO_ID
```

# Обрезает видео в формат 9:16 и убирает аудио

```bash
python convert_videos_to_9x16.py
```

# Базовый вариант
```bash
python add_audio.py "video.mp4" "audio.mp3"
```

# С указанием выходного файла
```bash
python add_audio.py "video.mp4" "audio.mp3" -o "result.mp4"
```

# С минимальным временем старта
```bash
python add_audio.py "video.mp4" "audio.mp3" --min-start 10.0
```

# Базовый вариант (музыка 10% громкости)
```bash
python add_music.py "video_with_audio.mp4" "background_music.mp3"
```

# С указанием выходного файла
```bash
python add_music.py "video.mp4" "music.mp3" -o "final_video.mp4"
```

# Настройка громкости (музыка 15%, голос 100%)
```bash
python add_music.py "video.mp4" "music.mp3" -m 0.15 -v 1.0
```

# Музыка тише (5%)
```bash
python add_music.py "video.mp4" "music.mp3" -m 0.05
```

# Не зацикливать музыку
```bash
python add_music.py "video.mp4" "music.mp3" --no-loop
```