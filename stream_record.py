import subprocess
import signal
import sys

url = "https://www.youtube.com/live/hV-Qr1WQ6LE?si=R7iPZf4bz7OIKVu8"
output_file = r"E:\MyProjects\serious\project\stream.mp4"

print("🔴 Начинаю запись трансляции...")
print("Нажмите Ctrl+C чтобы остановить")

try:
    # Запись с текущего момента
    process = subprocess.Popen([
        'streamlink',
        url,
        'best',
        '-o', output_file,
        '--force'  # Перезаписать файл если существует
    ])

    process.wait()  # Ждём завершения

except KeyboardInterrupt:
    print("\n⏹️ Остановка записи...")
    process.terminate()
    print(f"✅ Видео сохранено в {output_file}")
