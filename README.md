# Бот «Формула Маккаллума»

Telegram-бот считает индивидуальные идеальные обхваты по запястью, собирает фактические замеры и присылает **PNG-картинку отчёта** (высокое разрешение: макет как на странице — пергамент, формулы, иллюстрация, таблица с % от идеала; рендер через WeasyPrint → PyMuPDF) и напоминает о повторных замерах.

## Зависимости системы (WeasyPrint)

WeasyPrint для PDF требует нативные библиотеки. Примеры:

- **Arch / Steam Deck:** `sudo pacman -S pango gdk-pixbuf2 libffi cairo`
- **Debian/Ubuntu:** `sudo apt install libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libffi-dev shared-mime-info fonts-dejavu-core`

Шрифты **DejaVu** нужны, чтобы в PDF/PNG таблица с цифрами рендерилась без сетевых Google Fonts (на сервере CDN часто недоступен).

После установки: `pip install -r requirements.txt`

## Запуск локально

```bash
cd mccallum-bot
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Укажите BOT_TOKEN от @BotFather
python -m mccallum_bot.main
```

Проверка без Telegram:

```bash
PYTHONPATH=. python scripts/selftest.py
```

## Возможности

- Расчёт идеала по формуле Маккаллума (грудь от запястья, остальное — доли от груди).
- Ввод фактических замеров по одному, кнопка «Исправить предыдущий замер».
- После последнего замера — **фото-отчёт (PNG)** в чат: полноразмерный фон страницы без белых полей, обрезка пустого низа, растр ~3.6× для чёткости.
- Раздел «Замеры»: только **текст** методики по зонам (без картинок).
- Напоминания (интервал 7/14/30/90 дней или выкл), планировщик раз в минуту.
- История замеров в SQLite (`measurements`).

## Стек

Python 3.11+, aiogram 3, Jinja2, WeasyPrint, PyMuPDF (pymupdf), aiosqlite, APScheduler.
