#!/usr/bin/env python3
"""
Читает вкладки «План» и «Факт» из Google Sheets,
рассчитывает отклонения по месяцам (Июль–Декабрь)
и записывает результат в новую вкладку «Сравнение».

Требования: gws CLI (~/.local/bin/gws или ~/bin/gws), авторизованный через gws auth login.
Ссылка на таблицу: переменная BUDGET_SHEET_ID в .env рядом со скриптом.
"""

import json
import os
import subprocess
import sys
from pathlib import Path


# ── Конфиг ──────────────────────────────────────────────────────────────────

GWS = str(Path.home() / "bin" / "gws")

def load_env(path: Path) -> dict:
    env = {}
    if not path.exists():
        return env
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip()
    return env

env = load_env(Path(__file__).parent / ".env")
SHEET_ID = env.get("BUDGET_SHEET_ID", "").strip()

if not SHEET_ID:
    print("Ошибка: BUDGET_SHEET_ID не найден в .env")
    sys.exit(1)

MONTHS = ["Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]


# ── gws helpers ─────────────────────────────────────────────────────────────

def gws(*args) -> dict:
    """Запускает gws команду, возвращает распарсенный JSON."""
    cmd = [GWS] + list(args)
    result = subprocess.run(cmd, capture_output=True, text=True)
    # gws пишет "Using keyring backend" в stdout перед JSON — отрезаем
    stdout = result.stdout
    # Find first '{' or '['
    for i, ch in enumerate(stdout):
        if ch in "{[":
            stdout = stdout[i:]
            break
    try:
        return json.loads(stdout)
    except json.JSONDecodeError as e:
        print(f"gws error: {result.stderr or result.stdout}")
        raise


def get_range(sheet_name: str, cell_range: str) -> list[list[str]]:
    data = gws(
        "sheets", "spreadsheets", "values", "get",
        "--params", json.dumps({"spreadsheetId": SHEET_ID, "range": f"{sheet_name}!{cell_range}"}),
    )
    return data.get("values", [])


def ensure_sheet(title: str) -> int:
    """Создаёт вкладку если её нет. Возвращает sheetId."""
    meta = gws(
        "sheets", "spreadsheets", "get",
        "--params", json.dumps({"spreadsheetId": SHEET_ID}),
    )
    for s in meta.get("sheets", []):
        if s["properties"]["title"] == title:
            return s["properties"]["sheetId"]

    # Создаём
    resp = gws(
        "sheets", "spreadsheets", "batchUpdate",
        "--params", json.dumps({"spreadsheetId": SHEET_ID}),
        "--json", json.dumps({
            "requests": [{"addSheet": {"properties": {"title": title}}}]
        }),
    )
    return resp["replies"][0]["addSheet"]["properties"]["sheetId"]


def clear_and_write(sheet_name: str, rows: list[list]) -> None:
    """Очищает вкладку и записывает данные."""
    # Clear
    gws(
        "sheets", "spreadsheets", "values", "clear",
        "--params", json.dumps({
            "spreadsheetId": SHEET_ID,
            "range": f"{sheet_name}!A1:Z100",
        }),
    )
    # Write
    gws(
        "sheets", "spreadsheets", "values", "update",
        "--params", json.dumps({
            "spreadsheetId": SHEET_ID,
            "range": f"{sheet_name}!A1",
            "valueInputOption": "USER_ENTERED",
        }),
        "--json", json.dumps({"values": rows}),
    )


def format_sheet(sheet_id: int, n_rows: int) -> None:
    """Форматирует вкладку: заголовок жирный + заморозка."""
    requests = [
        # Заголовок — жирный
        {
            "repeatCell": {
                "range": {"sheetId": sheet_id, "startRowIndex": 0, "endRowIndex": 1},
                "cell": {"userEnteredFormat": {"textFormat": {"bold": True}}},
                "fields": "userEnteredFormat.textFormat.bold",
            }
        },
        # Строка «Итого» — жирная
        {
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": n_rows - 1,
                    "endRowIndex": n_rows,
                },
                "cell": {"userEnteredFormat": {"textFormat": {"bold": True}}},
                "fields": "userEnteredFormat.textFormat.bold",
            }
        },
        # Заморозка первой строки
        {
            "updateSheetProperties": {
                "properties": {
                    "sheetId": sheet_id,
                    "gridProperties": {"frozenRowCount": 1},
                },
                "fields": "gridProperties.frozenRowCount",
            }
        },
        # Авторазмер всех колонок
        {
            "autoResizeDimensions": {
                "dimensions": {
                    "sheetId": sheet_id,
                    "dimension": "COLUMNS",
                    "startIndex": 0,
                    "endIndex": 5,
                }
            }
        },
    ]
    gws(
        "sheets", "spreadsheets", "batchUpdate",
        "--params", json.dumps({"spreadsheetId": SHEET_ID}),
        "--json", json.dumps({"requests": requests}),
    )


# ── Основная логика ──────────────────────────────────────────────────────────

def parse_totals(rows: list[list[str]], itogo_label: str = "Итого") -> dict[str, float]:
    """Ищет строку «Итого» и возвращает {месяц: сумма}."""
    header = rows[0] if rows else []
    for row in rows[1:]:
        if row and row[0].strip() == itogo_label:
            result = {}
            for i, month in enumerate(MONTHS):
                col = i + 1  # колонка 1 = Июль
                if col < len(row):
                    try:
                        result[month] = float(row[col].replace(" ", "").replace("\xa0", ""))
                    except (ValueError, AttributeError):
                        result[month] = 0.0
                else:
                    result[month] = 0.0
            return result
    raise ValueError(f"Строка «{itogo_label}» не найдена в таблице")


def main():
    print("Читаю «План»...")
    plan_rows = get_range("План", "A1:H10")
    plan = parse_totals(plan_rows)

    print("Читаю «Факт»...")
    fact_rows = get_range("Факт", "A1:H10")
    fact = parse_totals(fact_rows, itogo_label="Итого")

    # Рассчитываем отклонения
    result_rows = [["Месяц", "План (₽)", "Факт (₽)", "Отклонение (₽)", "Отклонение (%)"]]

    total_plan = 0.0
    total_fact = 0.0

    for month in MONTHS:
        p = plan.get(month, 0.0)
        f = fact.get(month, 0.0)
        delta_rub = f - p
        delta_pct = round((delta_rub / p * 100), 1) if p != 0 else 0.0
        total_plan += p
        total_fact += f
        result_rows.append([
            month,
            int(p),
            int(f),
            int(delta_rub),
            f"{delta_pct}%",
        ])

    # Строка итого
    total_delta_rub = total_fact - total_plan
    total_delta_pct = round((total_delta_rub / total_plan * 100), 1) if total_plan != 0 else 0.0
    result_rows.append([
        "Итого",
        int(total_plan),
        int(total_fact),
        int(total_delta_rub),
        f"{total_delta_pct}%",
    ])

    # Печатаем в терминал
    print("\n" + "─" * 70)
    header = result_rows[0]
    print(f"{'Месяц':<12} {'План (₽)':>12} {'Факт (₽)':>12} {'Откл. (₽)':>12} {'Откл. (%)':>10}")
    print("─" * 70)
    for row in result_rows[1:]:
        month, p, f, d, dp = row
        marker = " 🔴" if isinstance(d, int) and d > 0 else ""
        print(f"{month:<12} {p:>12,} {f:>12,} {d:>12,} {dp:>10}{marker}")
    print("─" * 70)

    # Записываем в Google Sheets
    print("\nСоздаю вкладку «Сравнение»...")
    sheet_id = ensure_sheet("Сравнение")

    print("Записываю данные...")
    clear_and_write("Сравнение", result_rows)

    print("Форматирую...")
    format_sheet(sheet_id, len(result_rows))

    print(f"\n✓ Готово! Вкладка «Сравнение» обновлена.")
    print(f"  Итог: план {int(total_plan):,} ₽ / факт {int(total_fact):,} ₽ / перерасход {int(total_delta_rub):,} ₽ ({total_delta_pct}%)")


if __name__ == "__main__":
    main()
