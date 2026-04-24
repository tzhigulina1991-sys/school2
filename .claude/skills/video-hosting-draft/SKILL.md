# Скилл: генерация черновиков видео (/video-hosting-draft)

Когда пользователь вызывает `/video-hosting-draft`, прочитай транскрипты из Google Drive, сгенерируй заголовки, описания и обложки для каждого видео, запиши черновики в Google Sheets «Video Drafts».

## Константы

```
TRANSCRIPTS_FOLDER_ID = 1yS6HK7dve0t58gRdlRhD4Koq3do5awHW
THUMBNAILS_FOLDER_ID  = 1YSrjae4EoobUrNclZhCYS-2q7EAtfUaW
VIDEOS_FOLDER_ID      = 17FesbItWYwIMjq8fpVDuM8iYgSToplkh
PARENT_FOLDER_ID      = 1M6ctUOzwY3PME_Lq9XFq3-hGWw7JkUGR

SUBJECT_FOLDERS:
  biology → 1lyLVQjoMUo52ITTM12TyDNosTZ2KbXTj  (template ID: 1jI8ixp9mbaPvtlvIe16wp4GIvikGwPwY)
  math    → 16PWDjXvv24U71XRk0GqPWGjVCz8tals4   (template ID: 1ZRxyY3ILsBuKfUI9WuzJKgV-I3Tm-a0w)
  physics → 1dmK3-WRaGqsXoIrhFQGA2gY1EIDh1Yjz   (template ID: 1kzPXDQC4sy2-wTH3ns-Mf8GxlLhs)
  russian → 10Nwn7niBi1w09ltzHiooJUN4R63JYcRs   (template ID: 1qNxMg5mCU9jtJtIf1ltpSqNnpkxnL03p)

DRAFTS_DIR = ~/school2/video-hosting/drafts/thumbnails/
```

---

## Шаги

### 1. Подготовь рабочую папку

```bash
mkdir -p ~/school2/video-hosting/drafts/thumbnails
```

### 2. Получи список транскриптов из Drive

```bash
~/bin/gws drive files list \
  --params '{"q":"\"1yS6HK7dve0t58gRdlRhD4Koq3do5awHW\" in parents","fields":"files(id,name)","pageSize":100}' 2>/dev/null
```

Для каждого файла `clip_XXXXXX.txt` определи `clip_id` = имя без расширения.

### 3. Скачай и прочитай каждый транскрипт

```bash
~/bin/gws drive files get \
  --params '{"fileId":"FILE_ID","alt":"media"}' 2>/dev/null
cat download.bin   # содержимое транскрипта
```

### 4. Определи предмет (subject) по содержимому транскрипта

По ключевым словам в тексте:
- **biology** — клетка, организм, биосфера, ДНК, экосистема, фотосинтез, эволюция
- **math** — уравнение, дробь, функция, теорема, площадь, число, процент
- **physics** — сила, энергия, скорость, ток, напряжение, масса, температура
- **russian** — существительное, глагол, предложение, суффикс, падеж, синтаксис

Если предмет неоднозначен — выбери наиболее вероятный.

### 5. Сгенерируй 3 варианта заголовка

**Правила из SPEC.md (обязательно):**
- Длина: 12–55 символов
- Sentence case (первая буква заглавная, остальные строчные)
- Нельзя: эмодзи, `!`, `?`, `…` в конце, ALL CAPS слова длиннее 3 букв, номера серий, упоминание класса, бренд
- Можно: двоеточие, тире, цифры
- Структура: тема: уточнение OR краткий хук

Три варианта — разные по длине и углу:
- Вариант 1: короткий хук (12–25 символов)
- Вариант 2: тема с уточнением (26–45 символов, оптимум)
- Вариант 3: развёрнутый (40–55 символов)

### 6. Сгенерируй 3 варианта описания

Каждое описание — 2–3 предложения, 200–400 символов:
- Что ученик узнает / научится делать
- Для какого класса актуально (вынести из контекста транскрипта)
- Без эмодзи, без ссылок

### 7. Сгенерируй 3 обложки

Для каждого заголовка (`заголовок1`, `заголовок2`, `заголовок3`) создай отдельный PNG.

**7а. Скачай шаблон предмета:**

```bash
~/bin/gws drive files get \
  --params '{"fileId":"TEMPLATE_FILE_ID","alt":"media"}' 2>/dev/null
mv download.bin ~/school2/video-hosting/drafts/thumbnails/template_SUBJECT.png
```

**7б. Запусти Python-скрипт оверлея:**

```python
#!/usr/bin/env python3
# thumbnail_overlay.py
import sys
from PIL import Image, ImageDraw, ImageFont
import textwrap

def render(template_path, title, out_path):
    # Validate
    if not (12 <= len(title) <= 55):
        raise ValueError(f"Title length {len(title)} outside 12-55")
    forbidden = ['!', '?', '…']
    if title[-1] in forbidden:
        raise ValueError(f"Title ends with forbidden char: {title[-1]}")

    img = Image.open(template_path).convert('RGBA')
    W, H = img.size  # 1280x720
    draw = ImageDraw.Draw(img)

    # Font paths to try (macOS + Linux fallbacks)
    font_paths = [
        '/Library/Fonts/HelveticaNeue.ttc',
        '/System/Library/Fonts/Helvetica.ttc',
        '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
    ]

    TEXT_COLOR = (255, 255, 255)
    SHADOW_COLOR = (0, 0, 0)
    LEFT_MARGIN = int(W * 0.05)
    RIGHT_MARGIN = int(W * 0.60)
    MAX_WIDTH = RIGHT_MARGIN - LEFT_MARGIN
    MAX_LINES = 3

    def try_render(size):
        font = None
        for fp in font_paths:
            try:
                font = ImageFont.truetype(fp, size, index=1)
                break
            except:
                try:
                    font = ImageFont.truetype(fp, size)
                    break
                except:
                    continue
        if not font:
            font = ImageFont.load_default()

        words = title.split()
        lines = []
        current = []
        for word in words:
            test = ' '.join(current + [word])
            bbox = draw.textbbox((0, 0), test, font=font)
            if bbox[2] - bbox[0] > MAX_WIDTH and current:
                lines.append(' '.join(current))
                current = [word]
            else:
                current.append(word)
        if current:
            lines.append(' '.join(current))
        return lines, font

    # Auto-size: 128px → 44px step 2
    chosen_lines, chosen_font, chosen_size = None, None, None
    for size in range(128, 42, -2):
        lines, font = try_render(size)
        if len(lines) <= MAX_LINES:
            chosen_lines, chosen_font, chosen_size = lines, font, size
            break

    if not chosen_lines:
        raise ValueError("Cannot fit title in 3 lines even at 44px")

    # Measure total text block
    line_height = chosen_size * 1.25
    total_h = len(chosen_lines) * line_height
    y_start = (H - total_h) / 2

    # Draw shadow then text
    for i, line in enumerate(chosen_lines):
        y = y_start + i * line_height
        draw.text((LEFT_MARGIN + 3, y + 5), line, font=chosen_font, fill=SHADOW_COLOR)
        draw.text((LEFT_MARGIN, y), line, font=chosen_font, fill=TEXT_COLOR)

    img.convert('RGB').save(out_path, 'PNG')
    print(f"Saved: {out_path} (size={chosen_size}px, lines={len(chosen_lines)})")

if __name__ == '__main__':
    render(sys.argv[1], sys.argv[2], sys.argv[3])
```

Запусти для каждого варианта:

```bash
python3 thumbnail_overlay.py \
  ~/school2/video-hosting/drafts/thumbnails/template_SUBJECT.png \
  "Заголовок 1" \
  ~/school2/video-hosting/drafts/thumbnails/CLIP_ID_v1.png
```

Повтори для v2 и v3. Сохрани абсолютные пути.

> Если Pillow не установлен: `pip3 install Pillow`

### 8. Найди или создай таблицу «Video Drafts»

Поищи в Drive:

```bash
~/bin/gws drive files list \
  --params '{"q":"name=\"Video Drafts\" and mimeType=\"application/vnd.google-apps.spreadsheet\"","fields":"files(id,name)"}' 2>/dev/null
```

Если не найдена — создай:

```bash
~/bin/gws sheets spreadsheets create \
  --body '{"properties":{"title":"Video Drafts"},"sheets":[{"properties":{"title":"Drafts","sheetId":0}}]}' 2>/dev/null
```

Запомни `spreadsheetId`.

### 9. Инициализируй заголовки (если таблица новая)

```bash
~/bin/gws sheets spreadsheets values update \
  --params '{"spreadsheetId":"SHEET_ID","range":"Drafts!A1:L1","valueInputOption":"RAW"}' \
  --body '{"values":[["clip_id","subject","заголовок1","заголовок2","заголовок3","описание1","описание2","описание3","обложка1","обложка2","обложка3","одобрено"]]}' 2>/dev/null
```

### 10. Запиши черновик для каждого клипа

```bash
~/bin/gws sheets spreadsheets values append \
  --params '{"spreadsheetId":"SHEET_ID","range":"Drafts!A:L","valueInputOption":"RAW","insertDataOption":"INSERT_ROWS"}' \
  --body '{"values":[["clip_id","subject","заг1","заг2","заг3","оп1","оп2","оп3","путь/v1.png","путь/v2.png","путь/v3.png",""]]}' 2>/dev/null
```

### 11. Выведи итог

```
✅ Обработано: N клипов
📊 Таблица: https://docs.google.com/spreadsheets/d/{SHEET_ID}
📁 Обложки: ~/school2/video-hosting/drafts/thumbnails/

Для публикации:
1. Открой таблицу
2. В колонке «одобрено» проставь 1, 2 или 3 для нужных строк
3. Запусти /video-hosting-publish
```

---

## Правила

- Заголовки генерируй строго по контракту SPEC.md (12–55 символов, sentence case)
- Не повторяй формулировки между вариантами одного клипа
- Если предмет не определился — пиши `unknown` в колонку subject и пропускай шаг 7
- Не перезаписывай строки с уже заполненной колонкой «одобрено»
- Если таблица уже есть — дописывай строки в конец, не пересоздавай
