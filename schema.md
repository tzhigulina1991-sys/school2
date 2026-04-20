# Схема базы данных — romashka (PostgreSQL)

Источник: Metabase, БД `romashka`, engine `postgres`.  
Всего таблиц: 6

---

## public.students

Основная таблица учеников.

| Поле | Тип | Описание / Значения |
|------|-----|---------------------|
| `id` | integer | PK |
| `last_name` | text | Фамилия |
| `first_name` | text | Имя |
| `patronymic` | text | Отчество |
| `class` | text | Класс: `1А`–`11В` (33 класса) |
| `grade_level` | integer | Год обучения: `1`–`11` |
| `tariff` | text | **Тариф**: `Без зачисления`, `Без учителя`, `Онлайн-школа`, `Персональный` |
| `start_date` | date | Дата начала обучения |
| `status` | text | **Статус**: `active`, `graduated`, `left` |
| `homeroom_teacher_id` | integer | FK → `teachers.id` |

---

## public.payments

Платежи по ученикам (помесячно).

| Поле | Тип | Описание / Значения |
|------|-----|---------------------|
| `id` | integer | PK |
| `student_id` | integer | FK → `students.id` |
| `month` | text | Месяц: `2025-09` … `2026-05` |
| `amount` | decimal | Сумма платежа |
| `due_date` | date | Дата оплаты по договору |
| `paid_date` | date | Фактическая дата оплаты |
| `status` | text | **Статус**: `paid`, `overdue`, `partial`, `annual_prepaid` |
| `tariff` | text | **Тариф**: `Без зачисления`, `Без учителя`, `Онлайн-школа`, `Персональный` |

---

## public.renewals

Продления на следующий год.

| Поле | Тип | Описание / Значения |
|------|-----|---------------------|
| `id` | integer | PK |
| `student_id` | integer | FK → `students.id` |
| `current_year` | text | Учебный год: `2025-2026` |
| `renewal_status` | text | **Статус**: `renewed`, `declined`, `pending`, `no_response` |
| `renewal_date` | date | Дата решения |
| `next_year_tariff` | text | **Тариф на след. год**: `Без зачисления`, `Без учителя`, `Онлайн-школа`, `Персональный` (или NULL) |
| `comment` | text | Комментарий |

---

## public.satisfaction

Оценки удовлетворённости (NPS/CSI).

| Поле | Тип | Описание / Значения |
|------|-----|---------------------|
| `id` | integer | PK |
| `student_id` | integer | FK → `students.id` |
| `score` | integer | Оценка: `1`–`10` |
| `comment` | text | Комментарий |
| `survey_date` | date | Дата опроса |

---

## public.courses

Курсы / предметы.

| Поле | Тип | Описание / Значения |
|------|-----|---------------------|
| `id` | integer | PK |
| `name` | text | Название курса |
| `teacher_id` | integer | FK → `teachers.id` |
| `grade_level` | integer | Для какого класса (1–11) |
| `price_monthly` | decimal | Цена в месяц |

---

## public.teachers

Учителя.

| Поле | Тип | Описание / Значения |
|------|-----|---------------------|
| `id` | integer | PK |
| `name` | text | ФИО учителя |
| `subject` | text | **Предмет**: Английский язык, Биология, География, ИЗО, Информатика, История, Литература, Математика, Музыка, Обществознание, Русский язык, Технология, Физика, Физкультура, Химия |

---

## Связи между таблицами

```
students ──< payments       (students.id = payments.student_id)
students ──< renewals       (students.id = renewals.student_id)
students ──< satisfaction   (students.id = satisfaction.student_id)
students >── teachers       (students.homeroom_teacher_id = teachers.id)
courses  >── teachers       (courses.teacher_id = teachers.id)
```

---

## Справочник значений

### Тарифы (students.tariff, payments.tariff, renewals.next_year_tariff)
| Значение | Описание |
|----------|----------|
| `Онлайн-школа` | Базовый тариф |
| `Персональный` | Персональное сопровождение |
| `Без учителя` | Самостоятельное обучение без куратора |
| `Без зачисления` | Без официального зачисления |

### Статус ученика (students.status)
| Значение | Описание |
|----------|----------|
| `active` | Активный |
| `graduated` | Окончил |
| `left` | Выбыл |

### Статус оплаты (payments.status)
| Значение | Описание |
|----------|----------|
| `paid` | Оплачен |
| `overdue` | Просрочен |
| `partial` | Оплачен частично |
| `annual_prepaid` | Предоплата за год |

### Статус продления (renewals.renewal_status)
| Значение | Описание |
|----------|----------|
| `renewed` | Продлил |
| `declined` | Отказал |
| `pending` | В процессе |
| `no_response` | Не ответил |
