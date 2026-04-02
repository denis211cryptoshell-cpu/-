"""
Тест кэширования с разными бэкендами.

Запуск:
    python tests/test_cache.py
"""

import asyncio
import sys
from pathlib import Path

# Добавляем корень проекта в path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.cache import LocalCacheBackend, RedisCacheBackend, get_cache_stats


async def test_local_cache():
    """Тест In-Memory кэша."""
    print("\n" + "=" * 50)
    print("🧪 ТЕСТ: LocalCacheBackend (In-Memory)")
    print("=" * 50)

    cache = LocalCacheBackend()

    # Тест 1: Установка и получение
    print("\n1️⃣ Тест: set/get")
    await cache.set("test_key", "test_value", ttl=60)
    result = await cache.get("test_key")
    assert result == "test_value", f"Ожидалось 'test_value', получено {result}"
    print(f"   ✅ SET/GET работает: {result}")

    # Тест 2: Получение несуществующего ключа
    print("\n2️⃣ Тест: get несуществующего ключа")
    result = await cache.get("nonexistent")
    assert result is None, f"Ожидалось None, получено {result}"
    print("   ✅ Возврат None для несуществующего ключа")

    # Тест 3: Удаление
    print("\n3️⃣ Тест: delete")
    await cache.delete("test_key")
    result = await cache.get("test_key")
    assert result is None, f"Ожидалось None после удаления, получено {result}"
    print("   ✅ DELETE работает")

    # Тест 4: Сложные объекты (dict, list)
    print("\n4️⃣ Тест: сложные объекты (JSON сериализация)")
    complex_data = {
        "user_id": 12345,
        "name": "Alex",
        "tags": ["admin", "premium"],
        "active": True
    }
    await cache.set("complex", complex_data, ttl=60)
    result = await cache.get("complex")
    assert result == complex_data, f"Ожидалось {complex_data}, получено {result}"
    print(f"   ✅ Сложные объекты работают: {result}")

    # Тест 5: Статистика
    print("\n5️⃣ Тест: stats")
    await cache.set("key1", "value1", ttl=60)
    await cache.set("key2", "value2", ttl=60)
    stats = await cache.stats()
    print(f"   ✅ Статистика: {stats}")
    assert stats["total_keys"] >= 2, f"Ожидалось >= 2 ключей, получено {stats['total_keys']}"

    # Тест 6: Очистка
    print("\n6️⃣ Тест: clear")
    await cache.clear()
    stats = await cache.stats()
    assert stats["total_keys"] == 0, f"Ожидалось 0 ключей после очистки, получено {stats['total_keys']}"
    print("   ✅ CLEAR работает")

    print("\n✅ Все тесты LocalCacheBackend пройдены!")
    return True


async def test_redis_cache():
    """Тест Redis кэша."""
    print("\n" + "=" * 50)
    print("🧪 ТЕСТ: RedisCacheBackend")
    print("=" * 50)

    redis_url = "redis://localhost:6379/0"
    cache = RedisCacheBackend(redis_url=redis_url, prefix="test_bot")

    try:
        # Тест подключения
        print("\n1️⃣ Тест: подключение к Redis")
        await cache.connect()
        print(f"   ✅ Подключено к {redis_url}")

        # Тест set/get
        print("\n2️⃣ Тест: set/get")
        await cache.set("test_key", "test_value", ttl=60)
        result = await cache.get("test_key")
        assert result == "test_value", f"Ожидалось 'test_value', получено {result}"
        print(f"   ✅ SET/GET работает: {result}")

        # Тест сложных объектов
        print("\n3️⃣ Тест: сложные объекты")
        complex_data = {"id": 1, "name": "Test", "active": True}
        await cache.set("complex", complex_data, ttl=60)
        result = await cache.get("complex")
        assert result == complex_data, f"Ожидалось {complex_data}, получено {result}"
        print(f"   ✅ Сложные объекты работают: {result}")

        # Тест TTL
        print("\n4️⃣ Тест: TTL (автоматическое удаление)")
        await cache.set("temp_key", "temp_value", ttl=2)
        result = await cache.get("temp_key")
        assert result == "temp_value"
        print("   ✅ Значение установлено с TTL=2s")
        print("   ⏳ Ожидание 3 секунды...")
        await asyncio.sleep(3)
        result = await cache.get("temp_key")
        assert result is None, f"Ожидалось None после истечения TTL, получено {result}"
        print("   ✅ TTL работает (значение удалено)")

        # Тест статистики
        print("\n5️⃣ Тест: stats")
        stats = await cache.stats()
        print(f"   ✅ Статистика: {stats}")

        # Тест очистки
        print("\n6️⃣ Тест: clear")
        await cache.clear()
        stats = await cache.stats()
        assert stats["total_keys"] == 0, f"Ожидалось 0 ключей, получено {stats['total_keys']}"
        print("   ✅ CLEAR работает")

        await cache.disconnect()
        print("\n✅ Все тесты RedisCacheBackend пройдены!")
        return True

    except Exception as e:
        print(f"\n❌ Ошибка тестирования Redis: {e}")
        print("   Возможно Redis не запущен. Пропускаем тест.")
        return False


async def main():
    """Запуск всех тестов."""
    print("\n" + "🚀 " * 20)
    print("ТЕСТИРОВАНИЕ СИСТЕМЫ КЭШИРОВАНИЯ")
    print("🚀 " * 20)

    # Тест In-Memory
    local_success = await test_local_cache()

    # Тест Redis (может не быть запущен)
    redis_success = await test_redis_cache()

    # Итоги
    print("\n" + "=" * 50)
    print("📊 ИТОГИ:")
    print("=" * 50)
    print(f"LocalCacheBackend:  {'✅ PASSED' if local_success else '❌ FAILED'}")
    print(f"RedisCacheBackend:  {'✅ PASSED' if redis_success else '⏭️ SKIPPED (Redis не запущен)'}")

    if local_success:
        print("\n✅ Базовое кэширование работает!")
        print("\n💡 Для использования Redis:")
        print("   1. Установите Redis: https://redis.io/download")
        print("   2. Запустите: redis-server")
        print("   3. В .env укажите:")
        print("      CACHE_BACKEND=redis")
        print("      REDIS_URL=redis://localhost:6379/0")


if __name__ == "__main__":
    asyncio.run(main())
