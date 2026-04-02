# 🤖 Telegram Bot Визитка

Профессиональный Telegram бот-визитка для разработчика с админ-панелью, кэшированием и статистикой.

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![Aiogram](https://img.shields.io/badge/Aiogram-3.x-green.svg)](https://docs.aiogram.dev/)
[![Redis](https://img.shields.io/badge/Redis-7-orange.svg)](https://redis.io/)
[![Docker](https://img.shields.io/badge/Docker-✓-blue.svg)](https://www.docker.com/)

---

## 📋 Оглавление

- [Возможности](#-возможности)
- [Технологии](#-технологии)
- [Быстрый старт](#-быстрый-старт)
- [Развёртывание на VPS](#-развёртывание-на-vps)
- [Структура проекта](#-структура-проекта)
- [Конфигурация](#-конфигурация)
- [Админ-панель](#-админ-панель)
- [API и хендлеры](#-api-и-хендлеры)
- [База данных](#-база-данных)
- [Кэширование](#-кэширование)
- [Логирование](#-логирование)
- [Бекапы](#-бекапы)
- [Мониторинг](#-мониторинг)
- [Troubleshooting](#-troubleshooting)

---

## ✨ Возможности

### Для пользователей:
- 📱 **Главное меню** с интерактивными кнопками
- 🖼 **Фото-контент** для разделов
- 📝 **Информативные разделы**: Обо мне, Тех. стек, FAQ, Отзывы, Акции, Тарифы, Контакты
- ⚡ **Быстрая загрузка** благодаря Redis кэшированию

### Для администраторов:
- 🔧 **Админ-панель** с полным управлением контентом
- 📊 **Статистика**: пользователи, нажатия кнопок, активность
- 📨 **Рассылка** сообщений всем пользователям
- 🖼 **Управление фото** для разделов
- 🔘 **Редактирование** кнопок меню
- 📢 **Управление каналами** обязательной подписки

---

## 🛠 Технологии

### Backend:
- **Python 3.12** — современный асинхронный код
- **Aiogram 3.x** — фреймворк для Telegram ботов
- **Redis 7** — быстрое кэширование (L2)
- **SQLite/PostgreSQL** — хранение данных

### Инфраструктура:
- **Docker & Docker Compose** — контейнеризация
- **APScheduler** — планировщик задач (авто-бекапы)
- **Loguru** — красивое логирование
- **Pydantic** — валидация настроек

### Кэширование:
- **L1: In-Memory** — быстрый доступ (~0.1ms)
- **L2: Redis** — персистентность и масштабирование (~1-5ms)

---

## 🚀 Быстрый старт

### 1. Клонирование репозитория

```bash
git clone https://github.com/yourusername/telegram-bot-visitka.git
cd telegram-bot-visitka
```

### 2. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 3. Настройка .env

```bash
cp .env.example .env
nano .env
```

**Обязательные переменные:**
```bash
# Telegram
BOT_TOKEN=1234567890:AAFqpJp5s2531j3Ckx656xm3xzxme5skuRY
ADMIN_ID=1260886378

# Кэширование
CACHE_BACKEND=redis
REDIS_URL=redis://localhost:6379/0

# База данных
DATABASE_PATH=data/bot.db
```

### 4. Запуск Redis (локально)

**Linux:**
```bash
sudo apt-get install redis-server
sudo systemctl start redis
```

**Windows:**
- Скачайте с [GitHub Releases](https://github.com/microsoftarchive/redis/releases)
- Или используйте Docker: `docker run -d -p 6379:6379 redis:latest`

**macOS:**
```bash
brew install redis
brew services start redis
```

### 5. Запуск бота

```bash
python main.py
```

---

## 📦 Развёртывание на VPS

### Требования:
- Ubuntu 20.04+ / Debian 11+
- Docker 20+
- Docker Compose v2+
- SSH доступ

### Автоматическое развёртывание:

```bash
# Сделайте скрипт исполняемым
chmod +x deploy.sh

# Запустите развёртывание
./deploy.sh root@your-vps-ip.com
```

**Скрипт автоматически:**
1. ✅ Проверит SSH подключение
2. ✅ Проверит Docker и Docker Compose
3. ✅ Скопирует файлы на сервер
4. ✅ Создаст .env файл
5. ✅ Соберёт Docker образы
6. ✅ Запустит контейнеры

### Ручное развёртывание:

```bash
# 1. Подключитесь к серверу
ssh root@your-vps-ip.com

# 2. Установите Docker
curl -fsSL https://get.docker.com | sh

# 3. Создайте директорию
mkdir -p /opt/telegram-bot
cd /opt/telegram-bot

# 4. Скопируйте файлы (с локальной машины)
scp -r ./* root@your-vps-ip.com:/opt/telegram-bot/

# 5. Настройте .env
cp .env.example .env
nano .env

# 6. Запустите через Docker Compose
docker compose up -d

# 7. Проверьте логи
docker compose logs -f bot
```

### Docker Compose команды:

```bash
# Просмотр логов
docker compose logs -f bot

# Перезапуск
docker compose restart bot

# Остановка
docker compose down

# Обновление
git pull && docker compose up -d --build

# Статус
docker compose ps
```

---

## 📁 Структура проекта

```
telegram-bot-visitka/
├── main.py                 # Точка входа
├── config.py               # Настройки и переменные окружения
├── states.py               # FSM состояния для админки
├── logger.py               # Настройка логирования
│
├── database/               # Работа с БД
│   ├── __init__.py
│   ├── db.py               # SQLite подключение
│   ├── postgres.py         # PostgreSQL подключение
│   ├── adapter.py          # Универсальный адаптер
│   ├── models.py           # Модели данных
│   └── migrations/         # Миграции БД
│
├── handlers/               # Обработчики сообщений
│   ├── start.py            # Команда /start и подписка
│   ├── menu.py             # Кнопки главного меню
│   ├── admin.py            # Админ-панель
│   └── errors.py           # Обработка ошибок
│
├── keyboards/              # Клавиатуры
│   ├── reply.py            # Reply клавиатуры (главное меню)
│   ├── inline.py           # Inline клавиатуры (админка)
│   └── admin.py            # Админские кнопки
│
├── services/               # Бизнес-логика
│   ├── subscription.py     # Проверка подписки
│   ├── content_manager.py  # Управление контентом
│   ├── broadcaster.py      # Рассылка сообщений
│   ├── message_manager.py  # Управление сообщениями
│   └── backup.py           # Авто-бекапы БД
│
├── utils/                  # Утилиты
│   ├── cache.py            # Кэширование (Local + Redis)
│   ├── middlewares.py      # Middleware для обработки
│   ├── rate_limiter.py     # Rate limiting
│   ├── scheduler.py        # Планировщик задач
│   └── html_sanitizer.py   # Очистка HTML
│
├── messages/               # Тексты
│   └── texts.py
│
├── data/                   # Данные
│   ├── bot.db              # SQLite база
│   └── backups/            # Бекапы БД
│
├── logs/                   # Логи
│   └── bot.log
│
├── tests/                  # Тесты
│   ├── system_check.py     # Системная проверка
│   └── test_cache.py       # Тесты кэширования
│
├── docker-compose.yml      # Docker Compose конфигурация
├── Dockerfile              # Docker образ
├── deploy.sh               # Скрипт развёртывания
├── requirements.txt        # Python зависимости
└── .env.example            # Пример конфигурации
```

---

## ⚙️ Конфигурация

### Переменные окружения (.env):

```bash
# Telegram Bot
BOT_TOKEN=1234567890:AAFqpJp5s2531j3Ckx656xm3xzxme5skuRY
ADMIN_ID=1260886378
ADMIN_IDS=123456789,987654321  # Дополнительные админы
CHANNEL_IDS=@channel1,@channel2  # Каналы для подписки

# Кэширование
CACHE_BACKEND=redis  # local или redis
REDIS_URL=redis://localhost:6379/0

# База данных
DATABASE_PATH=data/bot.db
DATABASE_URL=postgresql://user:pass@host:5432/dbname  # Опционально

# Rate Limiting
RATE_LIMIT_MAX_REQUESTS=10
RATE_LIMIT_WINDOW=60

# Логирование
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR
```

---

## 🔧 Админ-панель

### Доступ к админке:

Отправьте боту команду `/admin` или нажмите кнопку "🔧 Админка" (только для ADMIN_ID).

### Функции админ-панели:

| Кнопка | Описание |
|--------|----------|
| 📝 Контент | Редактирование текстов разделов |
| 🔘 Кнопки меню | Управление названиями кнопок |
| 📢 Каналы | Управление каналами подписки |
| 📊 Статистика | Просмотр статистики бота |
| 🖼 Фото | Установка фото для разделов |
| 📨 Рассылка | Отправка сообщений всем пользователям |
| 🔙 Выйти в меню | Возврат к главному меню |

### Статистика:

```
📊 Статистика бота

👥 Пользователи:
• Всего: 150
• За 24 часа: +5
• За 7 дней: +12

🔘 Нажатия кнопок:
• 👤 Обо мне: 45
• 🛠 Тех. стек: 32
• ❓ FAQ: 28
• ⭐ Отзывы: 15
• 🔥 Акции: 12
• 💰 Тарифы: 10
• 📝 Заказать: 8

[🔙 Назад]
[⚠️ Сбросить статистику]
```

---

## 🌐 API и хендлеры

### Пользовательские команды:

| Команда | Описание |
|---------|----------|
| `/start` | Запуск бота, проверка подписки |

### Админские команды:

| Команда | Описание |
|---------|----------|
| `/admin` | Открытие админ-панели |
| `/cache stats` | Статистика кэша |
| `/cache clear` | Очистка кэша |

---

## 🗄 База данных

### Таблицы:

**users** — пользователи:
- `id`, `telegram_id`, `username`, `created_at`, `last_seen`

**content** — контент разделов:
- `id`, `section`, `text`, `updated_at`

**buttons** — кнопки меню:
- `id`, `name`, `label`, `is_active`

**channels** — каналы подписки:
- `id`, `channel_id`, `is_required`

**stats** — статистика нажатий:
- `id`, `button_name`, `button_label`, `clicks`, `last_clicked`

**photos** — фото разделов:
- `id`, `photo_type`, `file_id`, `updated_at`

### Миграции:

Автоматически применяются при старте бота.

```bash
# Проверка версии схемы
/cache stats
```

---

## 💾 Кэширование

### Уровни кэширования:

**L1: Local (In-Memory)**
- Скорость: ~0.1ms
- Хранение: в оперативной памяти
- Персистентность: ❌

**L2: Redis**
- Скорость: ~1-5ms
- Хранение: внешний Redis сервер
- Персистентность: ✅

### Что кэшируется:

| Данные | TTL | Бэкенд |
|--------|-----|--------|
| Контент разделов | 5 мин | L1/L2 |
| Фото (file_id) | 5 мин | L1/L2 |
| Проверка подписки | 1 мин | L1/L2 |
| Пригласительные ссылки | 2 часа | L1 |

### Переключение бэкенда:

```bash
# In-Memory (по умолчанию)
CACHE_BACKEND=local

# Redis
CACHE_BACKEND=redis
REDIS_URL=redis://localhost:6379/0
```

---

## 📝 Логирование

### Уровни логов:

- **DEBUG** — детальная отладка
- **INFO** — общая информация
- **WARNING** — предупреждения
- **ERROR** — ошибки

### Формат логов:

```
2026-04-02 20:00:00 | ℹ️ INFO | handlers.menu:handle_menu_button:115 - Пользователь 123456 открыл раздел about
```

### Просмотр логов:

```bash
# Локально
tail -f logs/bot.log

# Docker
docker compose logs -f bot
```

---

## 💾 Бекапы

### Автоматические бекапы:

- **Время:** 00:00 ежедневно
- **Хранение:** 7 дней
- **Расположение:** `data/backups/`

### Ручной бекап:

```bash
# SQLite
cp data/bot.db data/backups/bot_$(date +%Y%m%d_%H%M%S).db

# Docker
docker compose exec bot cp /app/data/bot.db /app/data/backups/backup.db
```

### Восстановление:

```bash
cp data/backups/bot_20260402_120000.db data/bot.db
docker compose restart bot
```

---

## 📊 Мониторинг

### Проверка статуса:

```bash
# Docker
docker compose ps

# Логи
docker compose logs --tail=50 bot

# Статистика бота
/cache stats
```

### Health checks:

- Redis: `redis-cli ping` → `PONG`
- Бот: отправьте `/start`

---

## 🔧 Troubleshooting

### Бот не запускается:

```bash
# Проверьте логи
docker compose logs bot

# Проверьте .env
cat .env

# Проверьте подключение к Redis
redis-cli ping
```

### Ошибка "table stats has no column":

```bash
# Примените миграции
python apply_migrations.py

# Или пересоздайте БД
rm data/bot.db
python main.py
```

### Redis не подключается:

```bash
# Проверьте Redis
redis-cli ping

# Перезапустите Redis
sudo systemctl restart redis

# Проверьте REDIS_URL в .env
cat .env | grep REDIS_URL
```

---

## 📞 Поддержка

Вопросы и предложения: @your_username

---

## 📄 Лицензия

MIT License

---

## 🎯 Roadmap

- [ ] Интеграция с платежными системами
- [ ] Web App для расширенной админки
- [ ] Экспорт статистики в CSV/Excel
- [ ] Уведомления в Telegram о проблемах
- [ ] Мультиязычность (i18n)
