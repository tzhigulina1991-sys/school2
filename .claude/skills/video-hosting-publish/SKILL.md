# Скилл: публикация одобренных видео (/video-hosting-publish)

Когда пользователь вызывает `/video-hosting-publish`, прочитай таблицу «Video Drafts», возьми строки с заполненной колонкой «одобрено» и опубликуй каждое видео через API видеохостинга.

## Константы

```
API_BASE  = http://localhost:3001
API_TOKEN = osh1-vh-2026-sk-9f3a
VIDEOS_FOLDER_ID = 17FesbItWYwIMjq8fpVDuM8iYgSToplkh
DRAFTS_THUMBS = ~/school2/video-hosting/drafts/thumbnails/
```

---

## Шаги

### 1. Найди таблицу «Video Drafts»

```bash
~/bin/gws drive files list \
  --params '{"q":"name=\"Video Drafts\" and mimeType=\"application/vnd.google-apps.spreadsheet\"","fields":"files(id,name)"}' 2>/dev/null
```

Если таблица не найдена — остановись: «Таблица Video Drafts не найдена. Сначала запусти /video-hosting-draft».

Запомни `spreadsheetId`.

### 2. Прочитай все строки

```bash
~/bin/gws sheets spreadsheets values get \
  --params '{"spreadsheetId":"SHEET_ID","range":"Drafts!A:L"}' 2>/dev/null
```

Структура колонок (индексы 0-based):
```
A=0  clip_id
B=1  subject
C=2  заголовок1
D=3  заголовок2
E=4  заголовок3
F=5  описание1
G=6  описание2
H=7  описание3
I=8  обложка1  (абсолютный путь к PNG)
J=9  обложка2
K=10 обложка3
L=11 одобрено  (1, 2 или 3 — какой вариант использовать)
```

### 3. Отфильтруй строки к публикации

Берёт строки где:
- `одобрено` (L) не пустое
- `одобрено` содержит число 1, 2 или 3

Пропускай строку-заголовок (первую строку).

Для каждой подходящей строки запомни:
- `clip_id`, `subject`
- `N` = число из колонки «одобрено» (1, 2 или 3)
- `title` = `заголовокN`
- `description` = `описаниеN`
- `thumbnail_path` = `обложкаN`

### 4. Проверь, что видео не опубликовано ранее

```bash
curl -s http://localhost:3001/api/videos/CLIP_ID
```

Если ответ `{"error":"Not found"}` — продолжай. Если видео уже есть — выведи предупреждение и пропусти (не перезаписывай).

### 5. Скачай видеофайл из Drive

Найди файл `CLIP_ID.mp4` в папке videos:

```bash
~/bin/gws drive files list \
  --params '{"q":"\"17FesbItWYwIMjq8fpVDuM8iYgSToplkh\" in parents and name=\"CLIP_ID.mp4\"","fields":"files(id,name)"}' 2>/dev/null
```

Скачай:

```bash
~/bin/gws drive files get \
  --params '{"fileId":"VIDEO_FILE_ID","alt":"media"}' 2>/dev/null
mv download.bin CLIP_ID.mp4
```

Скачай транскрипт если есть:

```bash
~/bin/gws drive files list \
  --params '{"q":"\"1yS6HK7dve0t58gRdlRhD4Koq3do5awHW\" in parents and name=\"CLIP_ID.txt\"","fields":"files(id,name)"}' 2>/dev/null
# Если найден:
~/bin/gws drive files get --params '{"fileId":"TXT_ID","alt":"media"}' 2>/dev/null
mv download.bin CLIP_ID_transcript.txt
```

### 6. Опубликуй через API

```bash
curl -X POST http://localhost:3001/api/videos \
  -H "X-Api-Token: osh1-vh-2026-sk-9f3a" \
  -F "video=@CLIP_ID.mp4" \
  -F "thumbnail=@THUMBNAIL_PATH" \
  -F "clip_id=CLIP_ID" \
  -F "title=TITLE" \
  -F "subject=SUBJECT" \
  -F "description=DESCRIPTION" \
  -F "transcript=<CLIP_ID_transcript.txt"
```

Если транскрипта нет — не включай поле `transcript`.
Если `thumbnail_path` не существует — предупреди, но публикуй без обложки.

Проверь ответ: если HTTP 201 — успех. Если ошибка — выведи детали и пропусти клип.

### 7. Удали временные файлы

```bash
rm -f CLIP_ID.mp4 CLIP_ID_transcript.txt
```

### 8. Обнови колонку «одобрено» в таблице

После успешной публикации замени значение в колонке `одобрено` на `published` чтобы не публиковать повторно:

Найди номер строки (row number, 1-based с учётом заголовка) и обнови:

```bash
~/bin/gws sheets spreadsheets values update \
  --params '{"spreadsheetId":"SHEET_ID","range":"Drafts!L{ROW}","valueInputOption":"RAW"}' \
  --body '{"values":[["published"]]}' 2>/dev/null
```

### 9. Выведи итог

```
✅ Опубликовано: N видео
⏭  Пропущено (уже было): M
❌ Ошибки: K

Галерея: http://localhost:5173/video-hosting/
```

---

## Правила

- Никогда не перезаписывай видео с уже существующим `clip_id` — только пропускай
- Строки со значением `published` в колонке «одобрено» — пропускай
- Если API недоступен (connection refused) — останови выполнение с инструкцией: «Запусти сервер: cd ~/school2/video-hosting && npm run dev»
- Скачивай видео по одному, не держи всё в памяти
- После завершения удаляй все временные файлы
