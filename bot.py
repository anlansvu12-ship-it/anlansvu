import os
import random
import logging
import asyncio
import datetime
from typing import Optional

from telegram import (
    Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    filters, ContextTypes, CallbackQueryHandler
)
from telegram.helpers import escape_markdown

# Попытка импортировать aiocryptopay — если библиотека или токен не доступны,
# переключаемся в демонстрационный режим (mock).
try:
    from aiocryptopay import AioCryptoPay, Networks
    AI_CRYPTOPAY_AVAILABLE = True
except Exception:
    AioCryptoPay = None
    Networks = None
    AI_CRYPTOPAY_AVAILABLE = False

# === Безопасные настройки: читаем из переменных окружения ===
# (оставил твои значения по умолчанию; можешь поменять на env-переменные)
TOKEN = os.getenv("TELEGRAM_TOKEN", "8329789430:AAGSXpU21ibhWFeQsB2c4xHeknoY8QjQtBE")  # установи TELEGRAM_TOKEN или оставь пустым для теста
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "hamyfsexsy")
CRYPTO_PAY_TOKEN = os.getenv("CRYPTO_PAY_TOKEN", "475260:AACjYijHdxDdr75mk0k88g6dKiD9q09rqNV")  # оставь пустым чтобы отключить реальные вызовы
CRYPTO_NETWORK = os.getenv("CRYPTO_NETWORK", "MAIN_NET")  # MAIN_NET или TEST_NET

# === Логирование ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === Windows event loop policy (безопасно, если доступно) ===
try:
    # этот вызов нужен только на Windows; на других ОС просто игнорируем ошибку
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
except Exception:
    pass

# === Инициализация Crypto Pay (если доступно и задан токен) ===
crypto_pay_client: Optional[object] = None
if AI_CRYPTOPAY_AVAILABLE and CRYPTO_PAY_TOKEN:
    try:
        crypto_pay_client = AioCryptoPay(
            token=CRYPTO_PAY_TOKEN,
            network=Networks.MAIN_NET if CRYPTO_NETWORK == "MAIN_NET" else Networks.TEST_NET
        )
        logger.info("CryptoPay client initialized.")
    except Exception as e:
        logger.warning("Не удалось инициализировать CryptoPay client: %s", e)
        crypto_pay_client = None
else:
    if not AI_CRYPTOPAY_AVAILABLE:
        logger.info("aiocryptopay не установлен — работаем в демо-режиме.")
    else:
        logger.info("CRYPTO_PAY_TOKEN не задан — работаем в демо-режиме.")

# === Переводы и текстовые ключи ===
translations = {
    "ru": {
        "choose_language": "🌐 Выберите язык:",
        "lang_ru": "🇷🇺 Русский",
        "lang_en": "🇬🇧 English",
        "welcome": "👋 Привет, {name}! Добро пожаловать в *veriFFka*.\nВыбери действие 👇",
        "help": "ℹ️ *Помощь*\n\n1️⃣ Выберите категорию и товар.\n2️⃣ Оплатите счёт (если включён платёжный режим).\n3️⃣ После оплаты — следуйте инструкциям.",
        "info": (
            "🗂 *Информация*\n\n"
            "💼 *veriFFka* — это высший стандарт верификаций.\n"
            "💼 Мы гарантируем качественную верификацию аккаунтов.\n"
            "💼 С максимальной безопасностью и полным соблюдением конфиденциальности.\n"
            "⚡️ Среднее время выполнения: 10–30 минут.\n"
        ),
        "main_menu": [["🛒 Купить верификацию"], ["ℹ️ Помощь"], ["🗂 Информация"]],
        "categories": [["💎 Кошельки"], ["📈 Биржи"], ["🏦 Банки"],
                       ["💰 Платёжные системы"], ["🎰 Казино"], ["🧩 Прочее"], ["↩️ Назад в меню"]],
        "choose_category": "📂 Выбери категорию 👇",
        "back_to_menu": "🏠 Главное меню:",
        "unknown": "❓ Не понимаю. Используй кнопки меню.",
        "create_invoice_demo_text": "🛒 *(ДЕМО) Заявка на {platform} оформлена!*\n\n💳 Ссылка для оплаты (демо):\n{url}\n\nПосле «оплаты» нажми «🔄 Проверить оплату (демо)».",
        "create_invoice_real_text": "🛒 *Заявка на {platform} оформлена!*\n\n💳 Оплата через CryptoBot:\n{url}\n\nПосле оплаты нажми «🔄 Проверить оплату».",
        "check_payment_btn_demo": "🔄 Проверить оплату (демо)",
        "check_payment_btn": "🔄 Проверить оплату",
        "payment_received": "✅ Оплата получена!\n\n🧾 Верификация *{platform}* начнётся скоро.\nСвяжись с админом: @{admin}",
        "payment_notification_user": "💬 Спасибо за оплату!\nВерификация *{platform}* уже запущена.\nЕсли нужно уточнение — свяжись с @{admin}.",
        "no_invoice": "⚠️ Нет активного счёта для проверки.",
        "payment_wait": "⏳ Платёж ещё не получен. Попробуй позже.",
        "payment_status": "⚠️ Статус платежа: {status}",
        "payment_error": "❌ Ошибка при проверке оплаты: {error}",
        "admin_no_access": "❌ У вас нет доступа к админ-панели.",
        "admin_stats": "📊 *Статистика заказов*\n\nВсего заказов: {total}\nОплаченных: {paid}",
        "admin_no_orders": "📂 Пока нет заказов.",
        "admin_last_orders_title": "🧾 *Последние заказы:*",
        "reminder_text": "💡 Напоминание: вы ещё не оплатили заказ *{platform}*.\nПоторопитесь, чтобы начать верификацию быстрее ⚡️",
        "order_logged": "{username} | {platform} | {invoice_id} | {status}\n",
        "notify_admin_new_order": "💰 Новый оплаченный заказ!\n👤 Пользователь: @{username}\n💎 Товар: {platform}\n🕒 Время: {time}",
        "notify_admin_new_order_short": "💰 Новый оплаченный заказ: {platform} от @{username}",
    },
    "en": {
        "choose_language": "🌐 Choose your language:",
        "lang_ru": "🇷🇺 Russian",
        "lang_en": "🇬🇧 English",
        "welcome": "👋 Hello, {name}! Welcome to *veriFFka*.\nChoose an action 👇",
        "help": "ℹ️ *Help*\n\n1️⃣ Choose a category and product.\n2️⃣ Pay the invoice (if payment mode is enabled).\n3️⃣ After payment — follow the instructions.",
        "info": (
            "🗂 *Information*\n\n"
            "💼 *veriFFka* — the highest verification standard.\n"
            "💼 We guarantee quality account verification.\n"
            "💼 With maximum security and confidentiality.\n"
            "⚡️ Average completion time: 10–30 minutes.\n"
        ),
        "main_menu": [["🛒 Buy verification"], ["ℹ️ Help"], ["🗂 Info"]],
        "categories": [["💎 Wallets"], ["📈 Exchanges"], ["🏦 Banks"],
                       ["💰 Payment systems"], ["🎰 Casinos"], ["🧩 Other"], ["↩️ Back to menu"]],
        "choose_category": "📂 Choose a category 👇",
        "back_to_menu": "🏠 Main menu:",
        "unknown": "❓ I don’t understand. Use the menu buttons.",
        "create_invoice_demo_text": "🛒 *(DEMO) Order for {platform} created!*\n\n💳 Payment link (demo):\n{url}\n\nAfter 'payment' press «🔄 Check payment (demo)».",
        "create_invoice_real_text": "🛒 *Order for {platform} created!*\n\n💳 Pay via CryptoBot:\n{url}\n\nAfter payment press «🔄 Check payment».",
        "check_payment_btn_demo": "🔄 Check payment (demo)",
        "check_payment_btn": "🔄 Check payment",
        "payment_received": "✅ Payment received!\n\n🧾 Verification for *{platform}* will start soon.\nContact admin: @{admin}",
        "payment_notification_user": "💬 Thanks for the payment!\nVerification for *{platform}* has been started.\nIf you need details — contact @{admin}.",
        "no_invoice": "⚠️ No active invoice to check.",
        "payment_wait": "⏳ Payment not yet received. Try again later.",
        "payment_status": "⚠️ Payment status: {status}",
        "payment_error": "❌ Error checking payment: {error}",
        "admin_no_access": "❌ You don't have access to the admin panel.",
        "admin_stats": "📊 *Order statistics*\n\nTotal orders: {total}\nPaid: {paid}",
        "admin_no_orders": "📂 No orders yet.",
        "admin_last_orders_title": "🧾 *Last orders:*",
        "reminder_text": "💡 Reminder: you haven’t paid for *{platform}* yet.\nHurry up to start verification faster ⚡️",
        "order_logged": "{username} | {platform} | {invoice_id} | {status}\n",
        "notify_admin_new_order": "💰 New paid order!\n👤 User: @{username}\n💎 Product: {platform}\n🕒 Time: {time}",
        "notify_admin_new_order_short": "💰 New paid order: {platform} from @{username}",
    }
}

def t(key: str, lang: str = "ru", **kwargs):
    text = translations.get(lang, translations["ru"]).get(key, key)
    return text.format(**kwargs) if kwargs else text

# === Каталог товаров (включая переводы и стиль на английском) ===
# internal_id: use as stable identifier (no emojis here)
catalog = {
    "wallet": {
        "label": {"ru": "💰 Wallet", "en": "💰 Wallet"},
        "price_usd": 18,
        "desc": {
            "ru": "Верификация Wallet — доступ ко всем функциям.",
            "en": "Full Wallet verification for unrestricted access and transfers."
        },
        "time": {"ru": "15–25 минут", "en": "15–25 minutes"}
    },
    "cryptobot": {
        "label": {"ru": "🤖 CryptoBot", "en": "🤖 CryptoBot"},
        "price_usd": 19,
        "desc": {
            "ru": "Верификация CryptoBot для крипто-переводов.",
            "en": "CryptoBot account verification for secure crypto operations."
        },
        "time": {"ru": "10–20 минут", "en": "10–20 minutes"}
    },
    "bitpapa": {
        "label": {"ru": "🪙 BitPapa", "en": "🪙 BitPapa"},
        "price_usd": 17,
        "desc": {
            "ru": "Верификация BitPapa для торговли криптой.",
            "en": "BitPapa KYC for trading and withdrawals."
        },
        "time": {"ru": "10–20 минут", "en": "10–20 minutes"}
    },
    "fkwallet": {
        "label": {"ru": "💼 Fkwallet", "en": "💼 Fkwallet"},
        "price_usd": 16,
        "desc": {
            "ru": "Верификация Fkwallet для снятия ограничений.",
            "en": "Fkwallet verification to lift account restrictions."
        },
        "time": {"ru": "15–25 минут", "en": "15–25 minutes"}
    },
    "coinbase": {
        "label": {"ru": "🔵 Coinbase", "en": "🔵 Coinbase"},
        "price_usd": 22,
        "desc": {
            "ru": "Coinbase — подтверждение личности для торговли.",
            "en": "Coinbase ID verification for full trading access."
        },
        "time": {"ru": "20–30 минут", "en": "20–30 minutes"}
    },
    "webmoney": {
        "label": {"ru": "🌐 Webmoney", "en": "🌐 Webmoney"},
        "price_usd": 19,
        "desc": {
            "ru": "Верификация Webmoney для полного доступа.",
            "en": "WebMoney verification to restore full account features."
        },
        "time": {"ru": "15–25 минут", "en": "15–25 minutes"}
    },
    "paypal": {
        "label": {"ru": "💳 PayPal", "en": "💳 PayPal"},
        "price_usd": 23,
        "desc": {
            "ru": "Верификация PayPal для покупок и переводов.",
            "en": "PayPal verification for purchases and transfers."
        },
        "time": {"ru": "20–30 минут", "en": "20–30 minutes"}
    },
    # Exchanges
    "bybit": {
        "label": {"ru": "📈 ByBit", "en": "📈 ByBit"},
        "price_usd": 23,
        "desc": {
            "ru": "Верификация ByBit для торговли и вывода.",
            "en": "ByBit verification for trading and withdrawals."
        },
        "time": {"ru": "15–25 минут", "en": "15–25 minutes"}
    },
    "bingx": {
        "label": {"ru": "📊 Bingx", "en": "📊 BingX"},
        "price_usd": 20,
        "desc": {
            "ru": "BingX — подтверждение личности для криптоопераций.",
            "en": "BingX account verification for crypto operations."
        },
        "time": {"ru": "15–25 минут", "en": "15–25 minutes"}
    },
    "mexc": {
        "label": {"ru": "💹 Mexc", "en": "💹 MEXC"},
        "price_usd": 19,
        "desc": {
            "ru": "MEXC — быстрая верификация для торговли.",
            "en": "MEXC quick KYC for active trading."
        },
        "time": {"ru": "15–25 минут", "en": "15–25 minutes"}
    },
    "okx": {
        "label": {"ru": "🧾 OKX", "en": "🧾 OKX"},
        "price_usd": 21,
        "desc": {
            "ru": "OKX — доступ к торгам и выводу средств.",
            "en": "OKX verification to enable trading and withdrawals."
        },
        "time": {"ru": "20–30 минут", "en": "20–30 minutes"}
    },
    "option": {
        "label": {"ru": "📉 Option", "en": "📉 Option"},
        "price_usd": 18,
        "desc": {
            "ru": "Option — верификация для безопасной торговли.",
            "en": "Option platform verification for secure trading."
        },
        "time": {"ru": "10–20 минут", "en": "10–20 minutes"}
    },
    # Banks
    "sber": {
        "label": {"ru": "💳 Сбербанк", "en": "💳 Sberbank"},
        "price_usd": 18,
        "desc": {
            "ru": "Сбербанк — подтверждение личности.",
            "en": "Sberbank verification for account confirmation."
        },
        "time": {"ru": "15–25 минут", "en": "15–25 minutes"}
    },
    "tinkoff": {
        "label": {"ru": "🏦 Тинькофф", "en": "🏦 Tinkoff"},
        "price_usd": 19,
        "desc": {
            "ru": "Тинькофф — для онлайн-операций.",
            "en": "Tinkoff verification for online banking operations."
        },
        "time": {"ru": "20 минут", "en": "20 minutes"}
    },
    "vtbank": {
        "label": {"ru": "🏧 ВТБанк", "en": "🏧 VTB"},
        "price_usd": 18,
        "desc": {
            "ru": "ВТБ — для подтверждения аккаунта.",
            "en": "VTB account verification for banking services."
        },
        "time": {"ru": "20–30 минут", "en": "20–30 minutes"}
    },
    "kaspi": {
        "label": {"ru": "💵 Kaspi", "en": "💵 Kaspi"},
        "price_usd": 17,
        "desc": {
            "ru": "Kaspi — для переводов и покупок.",
            "en": "Kaspi verification for transfers and purchases."
        },
        "time": {"ru": "15–25 минут", "en": "15–25 minutes"}
    },
    # Payment systems
    "qiwi": {
        "label": {"ru": "💰 QIWI", "en": "💰 QIWI"},
        "price_usd": 15,
        "desc": {
            "ru": "QIWI — снятие лимитов и переводов.",
            "en": "QIWI verification to lift limits and enable transfers."
        },
        "time": {"ru": "10–15 минут", "en": "10–15 minutes"}
    },
    "yumani": {
        "label": {"ru": "💼 Юмани", "en": "💼 YooMoney"},
        "price_usd": 16,
        "desc": {
            "ru": "ЮMoney — подтверждение личности.",
            "en": "YooMoney (formerly Yandex.Money) verification for full functionality."
        },
        "time": {"ru": "10–20 минут", "en": "10–20 minutes"}
    },
    # Casinos
    "fonbet": {
        "label": {"ru": "🎯 Fonbet", "en": "🎯 Fonbet"},
        "price_usd": 22,
        "desc": {
            "ru": "Fonbet — для ставок и вывода выигрышей.",
            "en": "Fonbet verification for betting and withdrawal of winnings."
        },
        "time": {"ru": "15–25 минут", "en": "15–25 minutes"}
    },
    "winline": {
        "label": {"ru": "🔥 Winline", "en": "🔥 Winline"},
        "price_usd": 21,
        "desc": {
            "ru": "Winline — безопасные ставки и бонусы.",
            "en": "Winline KYC for safe betting and bonuses."
        },
        "time": {"ru": "10–20 минут", "en": "10–20 minutes"}
    },
    "stake": {
        "label": {"ru": "💎 Stake", "en": "💎 Stake"},
        "price_usd": 24,
        "desc": {
            "ru": "Stake — верификация крипто-ставок.",
            "en": "Stake verification tailored for crypto-based betting."
        },
        "time": {"ru": "20–30 минут", "en": "20–30 minutes"}
    },
    "onewin": {
        "label": {"ru": "🎲 1win", "en": "🎲 1win"},
        "price_usd": 23,
        "desc": {
            "ru": "1win — для вывода выигрышей.",
            "en": "1win verification to enable withdrawals and full access."
        },
        "time": {"ru": "15–25 минут", "en": "15–25 minutes"}
    },
    "betera": {
        "label": {"ru": "🏆 Betera", "en": "🏆 Betera"},
        "price_usd": 20,
        "desc": {
            "ru": "Betera — подтверждение для ставок.",
            "en": "Betera account confirmation for betting activities."
        },
        "time": {"ru": "10–20 минут", "en": "10–20 minutes"}
    },
    # Other
    "fragment": {
        "label": {"ru": "💬 Fragment", "en": "💬 Fragment"},
        "price_usd": 25,
        "desc": {
            "ru": "Fragment — Telegram username аукционы.",
            "en": "Fragment — assistance with Telegram username auctions."
        },
        "time": {"ru": "15–25 минут", "en": "15–25 minutes"}
    },
    "avito": {
        "label": {"ru": "🏠 Avito", "en": "🏠 Avito"},
        "price_usd": 18,
        "desc": {
            "ru": "Avito — подтверждение для торговли.",
            "en": "Avito verification for safer buying and selling."
        },
        "time": {"ru": "15–25 минут", "en": "15–25 minutes"}
    },
    "faceit": {
        "label": {"ru": "🎮 Faceit", "en": "🎮 Faceit"},
        "price_usd": 17,
        "desc": {
            "ru": "Faceit — верификация для турниров.",
            "en": "Faceit account verification for tournaments and matchmaking."
        },
        "time": {"ru": "15–25 минут", "en": "15–25 minutes"}
    },
    "tinder_female": {
        "label": {"ru": "💋 Tinder (Женский)", "en": "💋 Tinder (Female)"},
        "price_usd": 28,
        "desc": {
            "ru": "Tinder — женская верификация для премиум-аккаунта.",
            "en": "Tinder profile verification (female) for premium features."
        },
        "time": {"ru": "20–30 минут", "en": "20–30 minutes"}
    },
    "badoo": {
        "label": {"ru": "💞 Badoo", "en": "💞 Badoo"},
        "price_usd": 20,
        "desc": {
            "ru": "Badoo — подтверждение личности.",
            "en": "Badoo verification to increase trust and access."
        },
        "time": {"ru": "15–25 минут", "en": "15–25 minutes"}
    },
    "yandex_pay": {
        "label": {"ru": "💳 Яндекс Pay", "en": "💳 Yandex Pay"},
        "price_usd": 19,
        "desc": {
            "ru": "Яндекс Pay — для покупок и переводов.",
            "en": "Yandex Pay verification for payments and transfers."
        },
        "time": {"ru": "15–25 минут", "en": "15–25 minutes"}
    },
    "funpay": {
        "label": {"ru": "🎮 Funpay", "en": "🎮 Funpay"},
        "price_usd": 21,
        "desc": {
            "ru": "Funpay — торговля игровыми предметами.",
            "en": "Funpay verification for game-item trading and store access."
        },
        "time": {"ru": "15–25 минут", "en": "15–25 minutes"}
    },
}

# быстрый map: label text -> internal id для каждой локали (используется при обработке сообщений)
label_to_id = {}
for pid, info in catalog.items():
    for lang in ("ru", "en"):
        label = info["label"][lang]
        label_to_id.setdefault(lang, {})[label] = pid

# === Кнопочные меню для подкатегорий (возвращают ReplyKeyboardMarkup в зависимости от языка) ===
def main_menu(lang="ru"):
    return ReplyKeyboardMarkup(translations[lang]["main_menu"], resize_keyboard=True)

def category_menu(lang="ru"):
    return ReplyKeyboardMarkup(translations[lang]["categories"], resize_keyboard=True)

# Подменю — составлены для RU и EN автоматически, сохраняя оригинальные кнопки/порядок,
# но подписи должен увидеть пользователь на выбранном языке.
def wallet_menu(lang="ru"):
    items = [
        catalog["wallet"]["label"][lang],
        catalog["cryptobot"]["label"][lang],
        catalog["bitpapa"]["label"][lang],
        catalog["fkwallet"]["label"][lang],
        catalog["coinbase"]["label"][lang],
        catalog["webmoney"]["label"][lang],
        catalog["paypal"]["label"][lang],
        "⬅️ " + ( "Назад к категориям" if lang == "ru" else "Back to categories")
    ]
    # Arrange as rows for ReplyKeyboardMarkup: we'll use single-column layout for readability
    return ReplyKeyboardMarkup([[i] for i in items], resize_keyboard=True)

def exchange_menu(lang="ru"):
    items = [
        catalog["bybit"]["label"][lang],
        catalog["bingx"]["label"][lang],
        catalog["mexc"]["label"][lang],
        catalog["okx"]["label"][lang],
        catalog["option"]["label"][lang],
        "⬅️ " + ( "Назад к категориям" if lang == "ru" else "Back to categories")
    ]
    return ReplyKeyboardMarkup([[i] for i in items], resize_keyboard=True)

def bank_menu(lang="ru"):
    items = [
        catalog["sber"]["label"][lang],
        catalog["tinkoff"]["label"][lang],
        catalog["vtbank"]["label"][lang],
        catalog["kaspi"]["label"][lang],
        "⬅️ " + ( "Назад к категориям" if lang == "ru" else "Back to categories")
    ]
    return ReplyKeyboardMarkup([[i] for i in items], resize_keyboard=True)

def pay_menu(lang="ru"):
    items = [
        catalog["qiwi"]["label"][lang],
        catalog["yumani"]["label"][lang],
        catalog["webmoney"]["label"][lang],
        "⬅️ " + ( "Назад к категориям" if lang == "ru" else "Back to categories")
    ]
    return ReplyKeyboardMarkup([[i] for i in items], resize_keyboard=True)

def casino_menu(lang="ru"):
    items = [
        catalog["fonbet"]["label"][lang],
        catalog["winline"]["label"][lang],
        catalog["stake"]["label"][lang],
        catalog["onewin"]["label"][lang],
        catalog["betera"]["label"][lang],
        "⬅️ " + ( "Назад к категориям" if lang == "ru" else "Back to categories")
    ]
    return ReplyKeyboardMarkup([[i] for i in items], resize_keyboard=True)

def other_menu(lang="ru"):
    items = [
        catalog["fragment"]["label"][lang],
        catalog["avito"]["label"][lang],
        catalog["faceit"]["label"][lang],
        catalog["tinder_female"]["label"][lang],
        catalog["badoo"]["label"][lang],
        catalog["yandex_pay"]["label"][lang],
        catalog["yumani"]["label"][lang],
        catalog["funpay"]["label"][lang],
        "⬅️ " + ( "Назад к категориям" if lang == "ru" else "Back to categories")
    ]
    return ReplyKeyboardMarkup([[i] for i in items], resize_keyboard=True)

# === Карточка товара ===
def create_verif_card(pid: str, info: dict, lang: str):
    # order id
    order_id = f"VERIF-{random.randint(1000,9999)}"
    desc = info["desc"][lang]
    desc_escaped = escape_markdown(desc, version=2)
    label = info["label"][lang]
    text = (
        "╭─────────────────────────────╮\n"
        f"💰 *Цена:* {info['price_usd']} $\n\n"
        f"{desc_escaped}\n\n"
        f"⏱ *Время выполнения:* {info['time'][lang]}\n"
        f"🔢 *Номер заказа:* `{order_id}`\n"
        f"⭐️⭐️⭐️⭐️⭐️\n"
        "╰─────────────────────────────╯"
    )
    buttons = [
        [InlineKeyboardButton(t("buy_btn", lang) if lang == "ru" else t("buy_btn", lang), callback_data=f"buy_{pid}")],
        [InlineKeyboardButton("⬅️ " + ( "Назад к категориям" if lang == "ru" else "Back to categories"), callback_data="back_all")]
    ]
    return text, InlineKeyboardMarkup(buttons), order_id

# Добавим ключи для кнопок покупки в переводах (используются в create_verif_card)
translations["ru"]["buy_btn"] = "✅ Купить"
translations["en"]["buy_btn"] = "✅ Buy"

# === Команды ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name or ( "friend" if context.user_data.get("lang") == "en" else "друг")
    # если язык ещё не выбран — предлагаем выбор
    if "lang" not in context.user_data:
        # reply with language choices as simple keyboard
        lang_menu = ReplyKeyboardMarkup([[translations["ru"]["lang_ru"], translations["ru"]["lang_en"]]], resize_keyboard=True)
        await update.message.reply_text(translations["ru"]["choose_language"], reply_markup=lang_menu)
        return

    lang = context.user_data["lang"]
    await update.message.reply_text(
        t("welcome", lang, name=user_name),
        parse_mode="Markdown",
        reply_markup=main_menu(lang)
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang", "ru")
    await update.message.reply_text(
        t("help", lang),
        parse_mode="Markdown",
        reply_markup=main_menu(lang)
    )

async def info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang", "ru")
    await update.message.reply_text(t("info", lang), parse_mode="Markdown", reply_markup=main_menu(lang))

# === Показ карточки товара ===
async def show_verif_info(update_obj, context: ContextTypes.DEFAULT_TYPE, pid: str):
    lang = context.user_data.get("lang", "ru")
    info = catalog.get(pid)
    if not info:
        await update_obj.message.reply_text(t("unknown", lang))
        return
    text, markup, order_id = create_verif_card(pid, info, lang)
    # сохраняем order_id в user_data (если нужно)
    context.user_data["last_order_id"] = order_id
    # Используем MarkdownV2 для безопасного отображения (мы экранировали описание)
    await update_obj.message.reply_text(text, parse_mode="MarkdownV2", reply_markup=markup)

# === Callback ===
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    await query.answer()
    data = query.data
    lang = context.user_data.get("lang", "ru")

    # покупка
    if data.startswith("buy_"):
        pid = data.replace("buy_", "")
        info = catalog.get(pid)
        if not info:
            await query.message.reply_text("❌ Ошибка: неизвестный товар.")
            return

        display_name = info["label"][lang]

        # если CryptoPay доступен — создаём реальный инвойс, иначе — демонстрация
        if crypto_pay_client:
            try:
                invoice = await crypto_pay_client.create_invoice(asset="USDT", amount=info["price_usd"])
                pay_url = getattr(invoice, "bot_invoice_url", None) or getattr(invoice, "pay_url", None)
                invoice_id = getattr(invoice, "invoice_id", None)
                # сохраняем в user_data
                context.user_data["invoice_id"] = invoice_id
                context.user_data["platform"] = pid

                buttons = [
                    [InlineKeyboardButton(t("check_payment_btn", lang), callback_data="check_payment")],
                    [InlineKeyboardButton("⬅️ " + ( "Назад к категориям" if lang == "ru" else "Back to categories"), callback_data="back_all")]
                ]

                await query.message.edit_text(
                    t("create_invoice_real_text", lang, platform=display_name, url=pay_url),
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup(buttons)
                )

            except Exception as e:
                logger.exception("Ошибка при создании счета: %s", e)
                await query.message.reply_text(f"❌ Ошибка при создании счёта: {e}")

        else:
            # демонстрационный режим: генерируем "временный" invoice_id и ссылку-заглушку
            invoice_id = f"DEMO-{random.randint(100000,999999)}"
            demo_url = f"https://example.com/pay/{invoice_id}"
            context.user_data["invoice_id"] = invoice_id
            context.user_data["platform"] = pid

            buttons = [
                [InlineKeyboardButton(t("check_payment_btn_demo", lang), callback_data="check_payment")],
                [InlineKeyboardButton("⬅️ " + ( "Назад к категориям" if lang == "ru" else "Back to categories"), callback_data="back_all")]
            ]

            await query.message.edit_text(
                t("create_invoice_demo_text", lang, platform=display_name, url=demo_url),
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(buttons)
            )

    # проверка оплаты
    elif data == "check_payment":
        invoice_id = context.user_data.get("invoice_id")
        pid = context.user_data.get("platform")
        lang = context.user_data.get("lang", "ru")
        display_name = catalog.get(pid, {}).get("label", {}).get(lang, pid)
        if not invoice_id:
            await query.message.reply_text(t("no_invoice", lang))
            return

        try:
            status = None
            # реальная проверка
            if crypto_pay_client:
                invoices = await crypto_pay_client.get_invoices(invoice_ids=invoice_id)
                invoice = invoices[0] if isinstance(invoices, list) else invoices
                status = getattr(invoice, "status", None)
            else:
                # демо: считаем, что оплата случается, если invoice_id заканчивается на чётную цифру (только для теста)
                try:
                    status = "paid" if int(str(invoice_id)[-1]) % 2 == 0 else "new"
                except Exception:
                    status = "new"

            if status == "paid":
                await query.message.edit_text(
                    t("payment_received", lang, platform=display_name, admin=ADMIN_USERNAME),
                    parse_mode="Markdown"
                )

                # уведомление пользователю
                try:
                    await context.bot.send_message(
                        chat_id=update.effective_user.id,
                        text=t("payment_notification_user", lang, platform=display_name, admin=ADMIN_USERNAME),
                        parse_mode="Markdown"
                    )
                except Exception as notify_err:
                    logger.warning("Не удалось отправить уведомление пользователю: %s", notify_err)

                # уведомление админу (если указан admin username)
                try:
                    if ADMIN_USERNAME:
                        now_str = datetime.datetime.now().strftime('%H:%M %d.%m.%Y')
                        await context.bot.send_message(
                            chat_id=f"@{ADMIN_USERNAME}",
                            text=t("notify_admin_new_order", lang, username=update.effective_user.username or "unknown", platform=display_name, time=now_str)
                        )
                except Exception as admin_err:
                    logger.warning("Не удалось уведомить админа: %s", admin_err)

                # запись в лог
                try:
                    with open("orders_log.txt", "a", encoding="utf-8") as f:
                        f.write(t("order_logged", lang, username=update.effective_user.username or "unknown", platform=display_name, invoice_id=invoice_id, status="paid"))
                except Exception as file_err:
                    logger.warning("Не удалось записать заказ в лог: %s", file_err)

            elif status in ("active", "new"):
                await query.message.reply_text(t("payment_wait", lang))
            else:
                await query.message.reply_text(t("payment_status", lang, status=status))

        except Exception as e:
            logger.exception("Ошибка при проверке оплаты: %s", e)
            await query.message.reply_text(t("payment_error", lang, error=str(e)))

    elif data == "back_all":
        # возвращаемся к списку категорий
        try:
            await query.message.delete()
        except Exception:
            pass
        await query.message.chat.send_message(t("choose_category", context.user_data.get("lang", "ru")), reply_markup=category_menu(context.user_data.get("lang", "ru")))

# === Напоминание об оплате ===
async def remind_unpaid(context: ContextTypes.DEFAULT_TYPE, user_id: int, pid: str, minutes: int):
    await asyncio.sleep(minutes * 60)
    try:
        lang = "ru"  # для напоминаний используем русский по-умолчанию, можно расширить
        platform_name = catalog.get(pid, {}).get("label", {}).get(lang, pid)
        await context.bot.send_message(
            chat_id=user_id,
            text=t("reminder_text", lang, platform=platform_name),
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.warning("Не удалось отправить напоминание: %s", e)

# === Админ-команды ===
async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang", "ru")
    if update.effective_user.username != ADMIN_USERNAME:
        await update.message.reply_text(t("admin_no_access", lang))
        return
    try:
        with open("orders_log.txt", "r", encoding="utf-8") as f:
            lines = f.readlines()
        total_orders = len(lines)
        paid_orders = sum(1 for l in lines if "paid" in l or "paid" in l.lower())
        await update.message.reply_text(
            t("admin_stats", lang, total=total_orders, paid=paid_orders),
            parse_mode="Markdown"
        )
    except FileNotFoundError:
        await update.message.reply_text(t("admin_no_orders", lang))

async def admin_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang", "ru")
    if update.effective_user.username != ADMIN_USERNAME:
        await update.message.reply_text(t("admin_no_access", lang))
        return
    try:
        with open("orders_log.txt", "r", encoding="utf-8") as f:
            logs = f.read()[-2000:]
        if not logs:
            await update.message.reply_text(t("admin_no_orders", lang))
            return
        await update.message.reply_text(f"{t('admin_last_orders_title', lang)}\n\n{logs}", parse_mode="Markdown")
    except FileNotFoundError:
        await update.message.reply_text(t("admin_no_orders", lang))

async def admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang", "ru")
    if update.effective_user.username != ADMIN_USERNAME:
        await update.message.reply_text(t("admin_no_access", lang))
        return
    msg = " ".join(context.args) if context.args else ""
    if not msg:
        await update.message.reply_text("📢 Используй формат:\n`/message_all текст`", parse_mode="Markdown")
        return
    # Для безопасности — просто подтверждаем, что сообщение принято.
    await update.message.reply_text(f"✅ Рассылка подготовлена (сообщение: {msg})")

# === Текстовые сообщения ===
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tmsg = update.message.text.strip()
    # выбор языка
    if tmsg in [translations["ru"]["lang_ru"], translations["ru"]["lang_en"]]:
        # русская кнопка выбора языка (пользователь видит русскую надпись)
        if tmsg == translations["ru"]["lang_ru"]:
            context.user_data["lang"] = "ru"
            await update.message.reply_text("✅ Язык установлен: Русский", reply_markup=main_menu("ru"))
            return
        else:
            context.user_data["lang"] = "en"
            await update.message.reply_text("✅ Language set: English", reply_markup=main_menu("en"))
            return
    # английская версия кнопок (на случай, если keyboard показывает английские подписи)
    if tmsg in [translations["en"]["lang_ru"], translations["en"]["lang_en"]]:
        if tmsg == translations["en"]["lang_ru"]:
            context.user_data["lang"] = "ru"
            await update.message.reply_text("✅ Язык установлен: Русский", reply_markup=main_menu("ru"))
            return
        else:
            context.user_data["lang"] = "en"
            await update.message.reply_text("✅ Language set: English", reply_markup=main_menu("en"))
            return

    lang = context.user_data.get("lang", "ru")

    # Меню управления
    if tmsg in [translations["ru"]["main_menu"][0][0], translations["en"]["main_menu"][0][0]]:
        # Купить верификацию / Buy verification
        await update.message.reply_text(t("choose_category", lang), reply_markup=category_menu(lang))
        return
    if tmsg in [translations["ru"]["main_menu"][1][0], translations["en"]["main_menu"][1][0]]:
        await help_command(update, context)
        return
    if tmsg in [translations["ru"]["main_menu"][2][0], translations["en"]["main_menu"][2][0]]:
        await info_command(update, context)
        return

    # Категории
    # Determine category selection by exact match of category labels
    # Wallets
    if tmsg == translations[lang]["categories"][0][0]:
        await update.message.reply_text(translations[lang]["categories"][0][0].replace("\n", " "), reply_markup=wallet_menu(lang))
        return
    if tmsg == translations[lang]["categories"][1][0]:
        await update.message.reply_text(translations[lang]["categories"][1][0].replace("\n", " "), reply_markup=exchange_menu(lang))
        return
    if tmsg == translations[lang]["categories"][2][0]:
        await update.message.reply_text(translations[lang]["categories"][2][0].replace("\n", " "), reply_markup=bank_menu(lang))
        return
    if tmsg == translations[lang]["categories"][3][0]:
        await update.message.reply_text(translations[lang]["categories"][3][0].replace("\n", " "), reply_markup=pay_menu(lang))
        return
    if tmsg == translations[lang]["categories"][4][0]:
        await update.message.reply_text(translations[lang]["categories"][4][0].replace("\n", " "), reply_markup=casino_menu(lang))
        return
    if tmsg == translations[lang]["categories"][5][0]:
        await update.message.reply_text(translations[lang]["categories"][5][0].replace("\n", " "), reply_markup=other_menu(lang))
        return

    # Навигация назад
    if tmsg in ["⬅️ Назад к категориям", "⬅️ Back to categories", "↩️ Назад в меню", "↩️ Back to menu"]:
        await update.message.reply_text(t("back_to_menu", lang), reply_markup=main_menu(lang))
        return

    # Если пользователь нажал на один из товаров — сопоставляем по label -> internal id
    # сначала попытаемся найти в словаре для текущего языка
    pid = label_to_id.get(lang, {}).get(tmsg)
    if not pid:
        # также попробуем найти по другой локали (на случай, если кнопки как-то смешались)
        other_lang = "en" if lang == "ru" else "ru"
        pid = label_to_id.get(other_lang, {}).get(tmsg)
        if pid:
            # если нашли в другой локали — обновим user lang на неё (юзер нажал английский текст)
            context.user_data["lang"] = other_lang
            lang = other_lang

    if pid:
        await show_verif_info(update, context, pid)
        return

    # Админ команды обрабатываются через /stats, /orders, /message_all - не здесь

    # Если ничего не подошло
    await update.message.reply_text(t("unknown", lang), reply_markup=main_menu(lang))

# === Запуск ===
def main():
    if not TOKEN:
        logger.warning("TELEGRAM_TOKEN не задан. Установи переменную окружения TELEGRAM_TOKEN, чтобы бот работал с Telegram.")
        print("TELEGRAM_TOKEN не задан. Бот запущен в режиме без подключения к Telegram (для отладки это нормально).")
        # Если токен отсутствует, всё ещё можно завершить или запустить демо-режим.
        # Для удобства — выходим.
        return

    app = ApplicationBuilder().token(TOKEN).build()

    # Команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("info", info_command))
    # Админ
    app.add_handler(CommandHandler("stats", admin_stats))
    app.add_handler(CommandHandler("orders", admin_orders))
    app.add_handler(CommandHandler("message_all", admin_broadcast))

    # Обработчики
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(CallbackQueryHandler(handle_callback))

    logger.info("✅ Бот запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()
