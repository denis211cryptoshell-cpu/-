"""
Модели данных (таблицы) для SQLite и PostgreSQL.
Определение схем и SQL-запросов для создания таблиц.
"""

# SQL-скрипт создания таблиц (SQLite)
CREATE_TABLES_SQL = """
-- Таблица пользователей
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER UNIQUE NOT NULL,
    username TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_seen DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Таблица контента (тексты разделов)
CREATE TABLE IF NOT EXISTS content (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    section TEXT UNIQUE NOT NULL,
    text TEXT NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Таблица кнопок главного меню
CREATE TABLE IF NOT EXISTS buttons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    label TEXT NOT NULL,
    is_active BOOLEAN DEFAULT 1
);

-- Таблица каналов для подписки
CREATE TABLE IF NOT EXISTS channels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id TEXT UNIQUE NOT NULL,
    is_required BOOLEAN DEFAULT 1
);

-- Таблица статистики (счётчик нажатий)
CREATE TABLE IF NOT EXISTS stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    button_name TEXT NOT NULL,
    clicks INTEGER DEFAULT 0,
    UNIQUE(button_name)
);

-- Индексы для ускорения
CREATE INDEX IF NOT EXISTS idx_users_telegram ON users(telegram_id);
CREATE INDEX IF NOT EXISTS idx_content_section ON content(section);
CREATE INDEX IF NOT EXISTS idx_buttons_active ON buttons(is_active);
CREATE INDEX IF NOT EXISTS idx_channels_required ON channels(is_required);
"""

# SQL-скрипт создания таблиц (PostgreSQL)
CREATE_TABLES_POSTGRES_SQL = """
-- Таблица пользователей
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    username TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица контента (тексты разделов)
CREATE TABLE IF NOT EXISTS content (
    id SERIAL PRIMARY KEY,
    section TEXT UNIQUE NOT NULL,
    text TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица кнопок главного меню
CREATE TABLE IF NOT EXISTS buttons (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    label TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE
);

-- Таблица каналов для подписки
CREATE TABLE IF NOT EXISTS channels (
    id SERIAL PRIMARY KEY,
    channel_id TEXT UNIQUE NOT NULL,
    is_required BOOLEAN DEFAULT TRUE
);

-- Таблица статистики (счётчик нажатий)
CREATE TABLE IF NOT EXISTS stats (
    id SERIAL PRIMARY KEY,
    button_name TEXT NOT NULL,
    clicks INTEGER DEFAULT 0,
    UNIQUE(button_name)
);

-- Индексы для ускорения
CREATE INDEX IF NOT EXISTS idx_users_telegram ON users(telegram_id);
CREATE INDEX IF NOT EXISTS idx_content_section ON content(section);
CREATE INDEX IF NOT EXISTS idx_buttons_active ON buttons(is_active);
CREATE INDEX IF NOT EXISTS idx_channels_required ON channels(is_required);
"""

# SQL-скрипт заполнения дефолтными данными (SQLite)
INSERT_DEFAULTS_SQL = """
-- Контент разделов (дефолтные тексты)
INSERT OR IGNORE INTO content (section, text) VALUES
    ('greeting', '👋 <b>Привет! Я бот-визитка разработчика.</b>\n\nВыберите раздел в меню ниже, чтобы узнать больше обо мне и моих услугах.'),
    ('about', '<b>👤 Обо мне</b>\n\nПривет! Я — профессиональный разработчик с опытом создания Telegram-ботов и веб-приложений.\n\n🔹 Python, Aiogram, FastAPI\n🔹 Асинхронная архитектура\n🔹 Чистый и поддерживаемый код\n\nСвяжитесь со мной для обсуждения проекта!'),
    ('tech', '<b>🛠 Технический стек</b>\n\n<b>Backend:</b>\n• Python 3.10+\n• FastAPI, Aiogram 3.x\n• SQLAlchemy, aiosqlite\n• Redis, Celery\n\n<b>Frontend:</b>\n• React, TypeScript\n• Bootstrap, Material UI\n\n<b>DevOps:</b>\n• Docker, Docker Compose\n• Nginx, Gunicorn\n• Git, CI/CD'),
    ('faq', '<b>❓ FAQ</b>\n\n<b>1. Как заказать разработку?</b>\nНажмите кнопку "📝 Заказать" и опишите задачу.\n\n<b>2. Какие сроки?</b>\nОт 3 дней для простых ботов, от 2 недель для сложных систем.\n\n<b>3. Есть ли гарантия?</b>\nДа, 30 дней бесплатной поддержки после сдачи.\n\n<b>4. Как происходит оплата?</b>\n50% предоплата, 50% после принятия работы.'),
    ('reviews', '<b>⭐ Отзывы клиентов</b>\n\n<i>Отзывы будут добавлены после первых проектов.</i>\n\nХотите оставить отзыв? Напишите мне в личные сообщения!'),
    ('promo', '<b>🔥 Акции и спецпредложения</b>\n\n🎁 <b>Скидка 10%</b> на разработку бота-визитки до конца месяца!\n\n🎁 <b>Бесплатно:</b> хостинг на 1 месяц при заказе от 50 000 руб.\n\n<i>Акции обновляются ежемесячно. Следите за обновлениями!</i>'),
    ('tariffs', '<b>💰 Тарифы на разработку</b>\n\n<b>1. Бот-визитка</b> — от 15 000 руб.\n• Главное меню (5-7 кнопок)\n• Админ-панель\n• Интеграция с каналами\n\n<b>2. Бот с FSM</b> — от 30 000 руб.\n• Машина состояний\n• Приём платежей\n• Работа с данными\n\n<b>3. Индивидуальный</b> — от 50 000 руб.\n• Сложная логика\n• Интеграции с API\n• База данных\n\n<i>* Точная стоимость зависит от ТЗ</i>'),
    ('contact', '<b>📝 Связаться со мной</b>\n\n📬 <b>Telegram:</b> @your_username\n📧 <b>Email:</b> your@email.com\n🌐 <b>Сайт:</b> yoursite.com\n\nНажмите кнопку ниже, чтобы написать мне:');

-- Кнопки главного меню
INSERT OR IGNORE INTO buttons (name, label, is_active) VALUES
    ('about', '👤 Обо мне', 1),
    ('tech', '🛠 Тех. стек', 1),
    ('faq', '❓ FAQ', 1),
    ('reviews', '⭐ Отзывы', 1),
    ('promo', '🔥 Акции', 1),
    ('tariffs', '💰 Тарифы', 1),
    ('contact', '📝 Заказать', 1);

-- Статистика (пустые счётчики)
INSERT OR IGNORE INTO stats (button_name, clicks) VALUES
    ('about', 0),
    ('tech', 0),
    ('faq', 0),
    ('reviews', 0),
    ('promo', 0),
    ('tariffs', 0),
    ('contact', 0);
"""

# SQL-скрипт заполнения дефолтными данными (PostgreSQL)
INSERT_DEFAULTS_POSTGRES_SQL = """
-- Контент разделов (дефолтные тексты)
INSERT INTO content (section, text) VALUES
    ('greeting', '👋 <b>Привет! Я бот-визитка разработчика.</b>\n\nВыберите раздел в меню ниже, чтобы узнать больше обо мне и моих услугах.'),
    ('about', '<b>👤 Обо мне</b>\n\nПривет! Я — профессиональный разработчик с опытом создания Telegram-ботов и веб-приложений.\n\n🔹 Python, Aiogram, FastAPI\n🔹 Асинхронная архитектура\n🔹 Чистый и поддерживаемый код\n\nСвяжитесь со мной для обсуждения проекта!'),
    ('tech', '<b>🛠 Технический стек</b>\n\n<b>Backend:</b>\n• Python 3.10+\n• FastAPI, Aiogram 3.x\n• SQLAlchemy, aiosqlite\n• Redis, Celery\n\n<b>Frontend:</b>\n• React, TypeScript\n• Bootstrap, Material UI\n\n<b>DevOps:</b>\n• Docker, Docker Compose\n• Nginx, Gunicorn\n• Git, CI/CD'),
    ('faq', '<b>❓ FAQ</b>\n\n<b>1. Как заказать разработку?</b>\nНажмите кнопку "📝 Заказать" и опишите задачу.\n\n<b>2. Какие сроки?</b>\nОт 3 дней для простых ботов, от 2 недель для сложных систем.\n\n<b>3. Есть ли гарантия?</b>\nДа, 30 дней бесплатной поддержки после сдачи.\n\n<b>4. Как происходит оплата?</b>\n50% предоплата, 50% после принятия работы.'),
    ('reviews', '<b>⭐ Отзывы клиентов</b>\n\n<i>Отзывы будут добавлены после первых проектов.</i>\n\nХотите оставить отзыв? Напишите мне в личные сообщения!'),
    ('promo', '<b>🔥 Акции и спецпредложения</b>\n\n🎁 <b>Скидка 10%</b> на разработку бота-визитки до конца месяца!\n\n🎁 <b>Бесплатно:</b> хостинг на 1 месяц при заказе от 50 000 руб.\n\n<i>Акции обновляются ежемесячно. Следите за обновлениями!</i>'),
    ('tariffs', '<b>💰 Тарифы на разработку</b>\n\n<b>1. Бот-визитка</b> — от 15 000 руб.\n• Главное меню (5-7 кнопок)\n• Админ-панель\n• Интеграция с каналами\n\n<b>2. Бот с FSM</b> — от 30 000 руб.\n• Машина состояний\n• Приём платежей\n• Работа с данными\n\n<b>3. Индивидуальный</b> — от 50 000 руб.\n• Сложная логика\n• Интеграции с API\n• База данных\n\n<i>* Точная стоимость зависит от ТЗ</i>'),
    ('contact', '<b>📝 Связаться со мной</b>\n\n📬 <b>Telegram:</b> @your_username\n📧 <b>Email:</b> your@email.com\n🌐 <b>Сайт:</b> yoursite.com\n\nНажмите кнопку ниже, чтобы написать мне:')
ON CONFLICT (section) DO NOTHING;

-- Кнопки главного меню
INSERT INTO buttons (name, label, is_active) VALUES
    ('about', '👤 Обо мне', TRUE),
    ('tech', '🛠 Тех. стек', TRUE),
    ('faq', '❓ FAQ', TRUE),
    ('reviews', '⭐ Отзывы', TRUE),
    ('promo', '🔥 Акции', TRUE),
    ('tariffs', '💰 Тарифы', TRUE),
    ('contact', '📝 Заказать', TRUE)
ON CONFLICT (name) DO NOTHING;

-- Статистика (пустые счётчики)
INSERT INTO stats (button_name, clicks) VALUES
    ('about', 0),
    ('tech', 0),
    ('faq', 0),
    ('reviews', 0),
    ('promo', 0),
    ('tariffs', 0),
    ('contact', 0)
ON CONFLICT (button_name) DO NOTHING;
"""


async def create_tables(cursor) -> None:
    """Создать все таблицы (SQLite)."""
    await cursor.executescript(CREATE_TABLES_SQL)


async def insert_defaults(cursor) -> None:
    """Вставить дефолтные данные (SQLite)."""
    await cursor.executescript(INSERT_DEFAULTS_SQL)
