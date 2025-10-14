import os
import google.generativeai as genai
from dotenv import load_dotenv
from pathlib import Path
import json
from datetime import datetime
import re  # Добавляем для очистки JSON от markdown

# --- Конфигурация ---
load_dotenv()
api_key = os.getenv('GEMINI_API_KEY')
if not api_key:
    raise ValueError("GEMINI_API_KEY не найден в .env файле")
genai.configure(api_key=api_key)

# --- Пути ---
current_script_dir = Path(__file__).parent
prompt_file_path = current_script_dir.parent / 'assets' / 'prompts' / 'prompt.md'
results_dir = current_script_dir.parent / 'assets' / 'generated_text'
results_dir.mkdir(exist_ok=True)

# 1. Читаем промпт
with open(prompt_file_path, 'r', encoding='utf-8') as f:
    prompt = f.read()

# 2. Создаем модель и отправляем запрос
model = genai.GenerativeModel('gemini-flash-latest')

# Важно! При запросе на JSON, используйте response_schema
# или явно укажите в промпте, что нужен только JSON.
# Для большей надежности, лучше использовать response_schema (см. Примечание).

print("Отправка запроса к модели...")
response = model.generate_content(prompt)

# Получаем текст ответа
raw_response_text = response.text

# 3. Обработка и очистка JSON строки
# Модели часто оборачивают JSON в markdown блоки, например: ```json\n{...}\n```
# Используем регулярное выражение для извлечения чистого JSON


def clean_json_string(text):
    # Убираем внешние ```json...``` или ```...```
    match = re.search(r"```json\s*(\{.*\})\s*```", text, re.DOTALL)
    if match:
        return match.group(1).strip()

    # Убираем внешние ```...```
    match = re.search(r"```\s*(\{.*\})\s*```", text, re.DOTALL)
    if match:
        return match.group(1).strip()

    return text.strip()


cleaned_json_string = clean_json_string(raw_response_text)

# 4. Преобразование JSON строки в объект Python (парсинг)
try:
    # json.loads() преобразует строку JSON в словарь/список Python
    json_output_data = json.loads(cleaned_json_string)

    # 5. Сохранение объекта в JSON файл
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"model_output_{timestamp_str}.json"
    output_file_path = results_dir / output_filename

    with open(output_file_path, 'w', encoding='utf-8') as f:
        # Теперь мы сохраняем объект Python (json_output_data)
        json.dump(json_output_data, f, indent=4, ensure_ascii=False)

    print(f"✅ Успешно распарсено и сохранено в файл: {output_file_path}")

except json.JSONDecodeError as e:
    print(
        f"❌ Ошибка парсинга JSON: Ответ модели не является корректным JSON. {e}")
    print(f"Некорректный ответ: {raw_response_text}")
except Exception as e:
    print(f"❌ Произошла непредвиденная ошибка: {e}")
