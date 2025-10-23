# veriFFka — Telegram бот (готовый к загрузке на GitHub)

Этот репозиторий содержит Python-бота для Telegram (файл `bot.py`) — адаптированную версию присланного `maon.py`.
Проект готов к загрузке на GitHub: в архив включены инструкции, зависимости и `.gitignore`.

## Содержание архива
- `bot.py` — основной файл бота (исходник присланного `maon.py`).
- `requirements.txt` — список зависимостей.
- `.gitignore` — файлы/папки, которые не следует коммитить.
- `LICENSE` — MIT License.
- `README.md` — этот файл.
- `orders_log.txt` — файл логов (по умолчанию создаётся ботом при заказах).

## Быстрый старт (локально)
1. Установите Python 3.9+ и создайте виртуальное окружение:
```bash
python -m venv venv
source venv/bin/activate    # Linux / macOS
venv\Scripts\activate     # Windows
```

2. Установите зависимости:
```bash
pip install -r requirements.txt
```

3. Задайте переменные окружения (рекомендуется через `.env` или систему CI/CD):
- `TELEGRAM_TOKEN` — токен бота.
- `ADMIN_USERNAME` — username администратора (без `@`).
- `CRYPTO_PAY_TOKEN` — (опционально) токен aiocryptopay, если используете реальные инвойсы.
- `CRYPTO_NETWORK` — `MAIN_NET` или `TEST_NET` (по умолчанию `MAIN_NET`).

Пример (Linux/macOS):
```bash
export TELEGRAM_TOKEN="123456:ABC..."
export ADMIN_USERNAME="adminuser"
export CRYPTO_PAY_TOKEN=""
```

4. Запустите бота:
```bash
python bot.py
```

## Примечания
- В исходнике предусмотрен демонстрационный режим, если библиотека `aiocryptopay` не установлена или `CRYPTO_PAY_TOKEN` не заданы.
- Логи заказов записываются в `orders_log.txt`.

## Лицензия
MIT — см. файл `LICENSE`.
