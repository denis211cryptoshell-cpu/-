# 🔧 Настройка Redis для кэширования

## 📋 Обзор

Система кэширования поддерживает два бэкенда:

| Бэкенд | Описание | Когда использовать |
|--------|----------|-------------------|
| **Local** (In-Memory) | Кэш в оперативной памяти процесса | ✅ По умолчанию<br>✅ Один инстанс бота<br>✅ Быстрая разработка |
| **Redis** | Внешний Redis-сервер | ✅ Несколько инстансов бота<br>✅ Персистентность кэша<br>✅ Масштабирование |

---

## 🚀 Быстрый старт

### 1. Использование Local (по умолчанию)

Ничего делать не нужно — бот использует In-Memory кэш автоматически.

В `.env`:
```bash
CACHE_BACKEND=local
```

### 2. Использование Redis

#### Шаг 1: Установите Redis

**Windows:**
- Скачайте с [GitHub Releases](https://github.com/microsoftarchive/redis/releases)
- Или используйте Docker: `docker run -d -p 6379:6379 redis:latest`

**Linux:**
```bash
sudo apt-get install redis-server  # Debian/Ubuntu
sudo systemctl start redis         # Запуск
```

**macOS:**
```bash
brew install redis
brew services start redis
```

#### Шаг 2: Настройте `.env`

```bash
CACHE_BACKEND=redis
REDIS_URL=redis://localhost:6379/0
```

#### Шаг 3: Перезапустите бота

```bash
python main.py
```

---

## 📁 Изменённые файлы

| Файл | Изменения |
|------|-----------|
| `utils/cache.py` | Полностью переписан: абстрактный класс, Local/Redis бэкенды |
| `config.py` | Добавлены `CACHE_BACKEND` и `REDIS_URL` |
| `main.py` | Инициализация кэша при старте, отключение при останове |
| `services/subscription.py` | Обновлён вызов кэша |
| `services/content_manager.py` | Обновлены вызовы кэша (5 мест) |
| `handlers/admin.py` | Обновлена команда `/cache` |
| `requirements.txt` | Добавлен `redis>=5.0.0` |
| `.env.example` | Добавлены переменные для кэша |

---

## 🔐 Безопасность внедрения

### ✅ Что сделано для безопасности:

1. **Абстрактный интерфейс** — оба бэкенда имеют одинаковый API
2. **Fallback на Local** — если Redis недоступен, бот продолжит работать с In-Memory
3. **JSON сериализация** — безопаснее pickle (нет выполнения кода)
4. **Префиксы ключей** — изоляция от других приложений в Redis
5. **Логирование** — все операции кэша логируются
6. **TTL** — автоматическое удаление просроченных данных

### 🛡️ Рекомендации по безопасности Redis:

1. **Не открывайте Redis в интернет** без пароля
2. **Используйте пароль** для Redis:
   ```bash
   # redis.conf
   requirepass your_secure_password
   ```
   
   ```bash
   # .env
   REDIS_URL=redis://:your_secure_password@localhost:6379/0
   ```

3. **Ограничьте доступ по IP** (файрвол)
4. **Используйте Unix socket** (локально):
   ```bash
   # .env
   REDIS_URL=unix:///var/run/redis/redis.sock
   ```

---

## 🧪 Тестирование

Запуск тестов кэширования:

```bash
python tests/test_cache.py
```

Тесты проверяют:
- ✅ LocalCacheBackend (In-Memory)
- ✅ RedisCacheBackend (если Redis доступен)
- ✅ Сериализацию сложных объектов
- ✅ TTL (автоматическое удаление)
- ✅ Статистику и очистку

---

## 📊 Мониторинг

### Команды администратора

```bash
/cache stats   # Статистика кэша
/cache clear   # Очистить весь кэш
```

### Логи

Все операции кэша логируются с префиксом:
- `[LocalCache]` — для In-Memory
- `[RedisCache]` — для Redis

---

## 🎯 API кэша

### Базовые методы

```python
from utils.cache import get_cache

cache = get_cache()

# Получить
value = await cache.get("key")

# Установить (с TTL)
await cache.set("key", value, ttl=300)  # 5 минут

# Удалить
await cache.delete("key")

# Очистить всё
await cache.clear()

# Статистика
stats = await cache.stats()
```

### Декоратор для кэширования

```python
from utils.cache import cached

@cached(ttl=300, prefix="user")
async def get_user_profile(user_id: int):
    return await bot.get_user_profile_photos(user_id)
```

---

## 🔧 Конфигурация Redis

### Переменные окружения

| Переменная | Значение по умолчанию | Описание |
|------------|----------------------|----------|
| `CACHE_BACKEND` | `local` | Бэкенд: `local` или `redis` |
| `REDIS_URL` | `None` | URL подключения к Redis |

### Формат REDIS_URL

```bash
# Локальный Redis
REDIS_URL=redis://localhost:6379/0

# С паролем
REDIS_URL=redis://:password@localhost:6379/0

# Удалённый сервер
REDIS_URL=redis://user:password@redis.example.com:6379/1

# Redis Cluster
REDIS_URL=redis://user:password@node1:6379,node2:6379/0

# Unix socket (Linux)
REDIS_URL=unix:///var/run/redis/redis.sock
```

---

## 🐛 Troubleshooting

### Ошибка подключения к Redis

```
[RedisCache] Ошибка подключения к Redis: Connection refused
```

**Решение:**
1. Проверьте, запущен ли Redis: `redis-cli ping` → должен вернуть `PONG`
2. Проверьте порт: `netstat -an | grep 6379`
3. Временно переключитесь на Local: `CACHE_BACKEND=local`

### Кэш не работает

**Проверка:**
```python
# В консоли бота
from utils.cache import get_cache, get_cache_stats
import asyncio

cache = get_cache()
print(type(cache))  # Покажет тип бэкенда
print(asyncio.run(get_cache_stats()))
```

---

## 📚 Дополнительные ресурсы

- [Redis Documentation](https://redis.io/docs/)
- [redis-py (Python клиент)](https://redis.readthedocs.io/)
- [APScheduler для очистки кэша](https://apscheduler.readthedocs.io/)
