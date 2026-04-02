"""
Сервис управления контентом (CRUD).
Поддерживает SQLite и PostgreSQL через db_adapter.
"""

import bleach
from datetime import datetime
from typing import Optional

from database import db_adapter
from logger import logger


# Разрешённые HTML-теги для Telegram
ALLOWED_TAGS = [
    "b", "strong", "i", "em", "u", "ins", "s", "strike", "del",
    "a", "code", "pre",
]

# Разрешённые атрибуты
ALLOWED_ATTRIBUTES = {"a": ["href"]}


def sanitize_html(text: str) -> str:
    """Очистить HTML от опасных тегов."""
    if not text:
        return ""
    return bleach.clean(text, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES, strip=True)


def sanitize_button_label(label: str) -> str:
    """Очистить название кнопки от всего HTML."""
    if not label:
        return ""
    return bleach.clean(label, tags=[], strip=True)


class ContentManager:
    """
    Сервис для CRUD операций с контентом.

    Используется в админ-панели для редактирования текстов разделов.
    """

    def __init__(self, db):
        self.db = db_adapter

    async def get_content(self, section: str) -> Optional[str]:
        """
        Получить текст раздела.
        Кэширует результат на 300 секунд (5 минут).

        Args:
            section: Ключ раздела (about, tech, faq...)

        Returns:
            Текст раздела или None если не найден
        """
        # Формируем ключ кэша
        cache_key = f"content:get_content:{section}"

        # Проверяем кэш
        from utils.cache import get_cache
        cache_backend = get_cache()
        cached_result = await cache_backend.get(cache_key)
        if cached_result is not None:
            logger.debug(f"Кэш: get_content({section}) -> {cached_result[:50]}...")
            return cached_result

        # Получаем из БД
        row = await self.db.fetchone(
            "SELECT text FROM content WHERE section = ?",
            section,
        )
        result = row[0] if row else None

        # Сохраняем в кэш на 300 секунд
        if result is not None:
            await cache_backend.set(cache_key, result, 300)
            logger.debug(f"Кэш: get_content({section}) -> кэшировано (TTL: 300s)")

        return result

    async def update_content(self, section: str, text: str) -> bool:
        """
        Обновить текст раздела.

        Args:
            section: Ключ раздела
            text: Новый текст (HTML)

        Returns:
            True если успешно
        """
        try:
            # САНТИЗИРУЕМ HTML перед сохранением
            clean_text = sanitize_html(text)

            if clean_text != text:
                logger.warning(f"Контент раздела '{section}' был очищен от опасного HTML")
                logger.debug(f"Исходный: {text[:100]}...")
                logger.debug(f"Очищенный: {clean_text[:100]}...")

            success = await self.db.execute(
                """
                UPDATE content
                SET text = ?, updated_at = ?
                WHERE section = ?
                """,
                clean_text,
                datetime.now().isoformat(),
                section,
            )
            if success:
                # Очищаем кэш для этого раздела
                cache_key = f"content:get_content:{section}"
                from utils.cache import get_cache
                cache_backend = get_cache()
                await cache_backend.delete(cache_key)

                logger.info(f"Контент раздела '{section}' обновлён")
                return True
            return False
        except Exception as e:
            logger.error(f"Ошибка обновления контента {section}: {e}")
            return False

    async def get_all_sections(self) -> list[tuple[str, str]]:
        """
        Получить все разделы с названиями.

        Returns:
            Список кортежей (section_key, section_label)
        """
        return [
            ("about", "👤 Обо мне"),
            ("tech", "🛠 Тех. стек"),
            ("faq", "❓ FAQ"),
            ("reviews", "⭐ Отзывы"),
            ("promo", "🔥 Акции"),
            ("tariffs", "💰 Тарифы"),
            ("contact", "📝 Заказать"),
        ]


class ButtonManager:
    """
    Сервис для управления кнопками главного меню.
    """

    def __init__(self, db):
        self.db = db_adapter

    async def get_all_buttons(self) -> list[tuple[str, str, bool]]:
        """
        Получить все кнопки меню.

        Returns:
            Список кортежей (name, label, is_active)
        """
        try:
            result = await self.db.fetchall("SELECT name, label, is_active FROM buttons ORDER BY id")
            logger.debug(f"ButtonManager.get_all_buttons: получено {len(result)} кнопок: {result}")
            return result
        except Exception as e:
            logger.error(f"ButtonManager.get_all_buttons: ошибка: {e}", exc_info=True)
            return []

    async def update_label(self, name: str, new_label: str) -> bool:
        """
        Обновить название кнопки.

        Args:
            name: Ключ кнопки
            new_label: Новое видимое название

        Returns:
            True если успешно
        """
        try:
            # САНТИЗИРУЕМ название кнопки (убираем весь HTML)
            clean_label = sanitize_button_label(new_label)
            
            if clean_label != new_label:
                logger.warning(f"Название кнопки '{name}' было очищено от HTML")
                logger.debug(f"Исходное: {new_label}")
                logger.debug(f"Очищенное: {clean_label}")

            success = await self.db.execute(
                "UPDATE buttons SET label = ? WHERE name = ?",
                clean_label,
                name,
            )
            if success:
                logger.info(f"Название кнопки '{name}' обновлено на '{clean_label}'")
                return True
            logger.warning(f"ButtonManager.update_label: запрос не выполнился, кнопка '{name}'")
            return False
        except Exception as e:
            logger.error(f"ButtonManager.update_label: ошибка: {e}", exc_info=True)
            return False

    async def toggle_visibility(self, name: str, is_active: bool) -> bool:
        """
        Переключить видимость кнопки.

        Args:
            name: Ключ кнопки
            is_active: Статус активности

        Returns:
            True если успешно
        """
        try:
            success = await self.db.execute(
                "UPDATE buttons SET is_active = ? WHERE name = ?",
                1 if is_active else 0,
                name,
            )
            if success:
                logger.info(f"Видимость кнопки '{name}' установлена в {is_active}")
                return True
            return False
        except Exception as e:
            logger.error(f"Ошибка переключения кнопки {name}: {e}")
            return False


class ChannelManager:
    """
    Сервис для управления каналами подписки.
    """

    def __init__(self, db):
        self.db = db_adapter

    async def get_all_channels(self) -> list[tuple[int, str, bool]]:
        """
        Получить все каналы.

        Returns:
            Список кортежей (id, channel_id, is_required)
        """
        return await self.db.fetchall("SELECT id, channel_id, is_required FROM channels ORDER BY id")

    async def add_channel(self, channel_id: str) -> bool:
        """
        Добавить канал.

        Args:
            channel_id: ID или @username канала

        Returns:
            True если успешно
        """
        try:
            # Для PostgreSQL используем ON CONFLICT
            if db_adapter.db_type == "postgresql":
                success = await self.db.execute(
                    "INSERT INTO channels (channel_id, is_required) VALUES (?, TRUE) ON CONFLICT (channel_id) DO NOTHING",
                    channel_id,
                )
            else:
                success = await self.db.execute(
                    "INSERT OR IGNORE INTO channels (channel_id, is_required) VALUES (?, 1)",
                    channel_id,
                )
            if success:
                logger.info(f"Канал '{channel_id}' добавлен")
                return True
            return False
        except Exception as e:
            logger.error(f"Ошибка добавления канала {channel_id}: {e}")
            return False

    async def remove_channel(self, channel_id: str) -> bool:
        """
        Удалить канал.

        Args:
            channel_id: ID или @username канала

        Returns:
            True если успешно
        """
        try:
            success = await self.db.execute(
                "DELETE FROM channels WHERE channel_id = ?",
                channel_id,
            )
            if success:
                logger.info(f"Канал '{channel_id}' удалён")
                return True
            return False
        except Exception as e:
            logger.error(f"Ошибка удаления канала {channel_id}: {e}")
            return False


class StatsManager:
    """
    Сервис для работы со статистикой.
    """

    def __init__(self, db):
        self.db = db_adapter

    async def increment_click(self, button_name: str, button_label: str = "") -> None:
        """
        Увеличить счётчик нажатий кнопки.

        Args:
            button_name: Ключ кнопки (например, 'about')
            button_label: Читаемое название кнопки (например, '👤 Обо мне')
        """
        try:
            # Обновляем label если он передан
            if button_label:
                if db_adapter.db_type == "postgresql":
                    await self.db.execute(
                        """
                        INSERT INTO stats (button_name, button_label, clicks, last_clicked) 
                        VALUES (?, ?, 1, CURRENT_TIMESTAMP)
                        ON CONFLICT (button_name) DO UPDATE SET 
                            clicks = stats.clicks + 1,
                            button_label = EXCLUDED.button_label,
                            last_clicked = CURRENT_TIMESTAMP
                        """,
                        button_name, button_label,
                    )
                else:
                    await self.db.execute(
                        """
                        INSERT INTO stats (button_name, button_label, clicks, last_clicked)
                        VALUES (?, ?, 1, CURRENT_TIMESTAMP)
                        ON CONFLICT(button_name)
                        DO UPDATE SET 
                            clicks = clicks + 1,
                            button_label = ?,
                            last_clicked = CURRENT_TIMESTAMP
                        """,
                        button_name, button_label, button_label,
                    )
            else:
                if db_adapter.db_type == "postgresql":
                    await self.db.execute(
                        """
                        INSERT INTO stats (button_name, clicks, last_clicked) VALUES (?, 1, CURRENT_TIMESTAMP)
                        ON CONFLICT (button_name) DO UPDATE SET clicks = stats.clicks + 1,
                            last_clicked = CURRENT_TIMESTAMP
                        """,
                        button_name,
                    )
                else:
                    await self.db.execute(
                        """
                        INSERT INTO stats (button_name, clicks, last_clicked)
                        VALUES (?, 1, CURRENT_TIMESTAMP)
                        ON CONFLICT(button_name)
                        DO UPDATE SET clicks = clicks + 1,
                            last_clicked = CURRENT_TIMESTAMP
                        """,
                        button_name,
                    )
            logger.debug(f"📊 StatsManager: счётчик '{button_name}' ({button_label}) увеличен")
        except Exception as e:
            logger.error(f"❌ StatsManager: ошибка обновления статистики {button_name}: {e}")

    async def get_stats(self) -> list[tuple[str, str, int]]:
        """
        Получить статистику нажатий с читаемыми названиями.

        Returns:
            Список кортежей (button_name, button_label, clicks)
        """
        logger.debug("📊 StatsManager: получение статистики нажатий")
        result = await self.db.fetchall(
            "SELECT button_name, button_label, clicks FROM stats ORDER BY clicks DESC"
        )
        logger.debug(f"📊 StatsManager: получено {len(result)} записей статистики")
        return result

    async def reset_stats(self) -> bool:
        """
        Сбросить всю статистику.

        Returns:
            True если успешно
        """
        try:
            logger.info("📊 StatsManager: сброс статистики")
            if db_adapter.db_type == "postgresql":
                await self.db.execute("UPDATE stats SET clicks = 0, last_clicked = CURRENT_TIMESTAMP")
            else:
                await self.db.execute("UPDATE stats SET clicks = 0, last_clicked = CURRENT_TIMESTAMP")
            logger.info("✅ StatsManager: статистика сброшена")
            return True
        except Exception as e:
            logger.error(f"❌ StatsManager: ошибка сброса статистики: {e}")
            return False

    async def get_users_count(self) -> int:
        """Получить количество пользователей."""
        logger.debug("📊 StatsManager: получение количества пользователей")
        row = await self.db.fetchone("SELECT COUNT(*) FROM users")
        return row[0] if row else 0

    async def get_new_users_count(self, hours: int = 24) -> int:
        """
        Получить количество новых пользователей за последние N часов.

        Args:
            hours: Количество часов

        Returns:
            Количество пользователей
        """
        try:
            if db_adapter.db_type == "postgresql":
                row = await self.db.fetchone(
                    """
                    SELECT COUNT(*) FROM users 
                    WHERE created_at >= NOW() - INTERVAL '%s hours'
                    """ % hours,
                )
            else:
                row = await self.db.fetchone(
                    """
                    SELECT COUNT(*) FROM users 
                    WHERE created_at >= datetime('now', ? || ' hours')
                    """,
                    f"-{hours}",
                )
            result = row[0] if row else 0
            logger.debug(f"📊 StatsManager: новых пользователей за {hours}ч: {result}")
            return result
        except Exception as e:
            logger.error(f"❌ StatsManager: ошибка получения новых пользователей: {e}")
            return 0


class PhotoManager:
    """
    Сервис для управления фото (приветствие и главное меню).
    """

    def __init__(self, db):
        self.db = db_adapter

    async def get_photo(self, photo_type: str) -> str | None:
        """
        Получить file_id фото по типу.

        Args:
            photo_type: Тип фото ('greeting' или 'main_menu')

        Returns:
            file_id фото или None если не найдено
        """
        try:
            # Формируем ключ кэша
            cache_key = f"photo:get_photo:{photo_type}"
            logger.debug(f"PhotoManager.get_photo: запрос photo_type={photo_type}")

            # Проверяем кэш
            from utils.cache import get_cache
            cache_backend = get_cache()
            cached_result = await cache_backend.get(cache_key)
            if cached_result is not None:
                logger.debug(f"PhotoManager.get_photo: найдено в кэше photo_type={photo_type}, file_id={cached_result[:20]}...")
                return cached_result

            # Получаем из БД
            row = await self.db.fetchone(
                "SELECT file_id FROM photos WHERE photo_type = ?",
                photo_type,
            )
            result = row[0] if row else None

            if result:
                logger.debug(f"PhotoManager.get_photo: получено из БД photo_type={photo_type}, file_id={result[:20]}...")
                # Сохраняем в кэш на 300 секунд
                await cache_backend.set(cache_key, result, 300)
                logger.debug(f"PhotoManager.get_photo: сохранено в кэш photo_type={photo_type} (TTL: 300s)")
            else:
                logger.debug(f"PhotoManager.get_photo: фото не найдено photo_type={photo_type}")

            return result
        except Exception as e:
            logger.error(f"PhotoManager.get_photo: ошибка при получении фото {photo_type}: {e}", exc_info=True)
            return None

    async def set_photo(self, photo_type: str, file_id: str) -> bool:
        """
        Установить фото (добавить или обновить).

        Args:
            photo_type: Тип фото ('greeting' или 'main_menu')
            file_id: Telegram file_id фото

        Returns:
            True если успешно
        """
        try:
            logger.debug(f"PhotoManager.set_photo: запрос на сохранение photo_type={photo_type}, file_id={file_id[:20]}...")

            # Для PostgreSQL используем ON CONFLICT
            if db_adapter.db_type == "postgresql":
                success = await self.db.execute(
                    """
                    INSERT INTO photos (photo_type, file_id) VALUES (?, ?)
                    ON CONFLICT (photo_type) DO UPDATE SET file_id = ?, updated_at = CURRENT_TIMESTAMP
                    """,
                    photo_type, file_id, file_id,
                )
            else:
                success = await self.db.execute(
                    """
                    INSERT OR REPLACE INTO photos (photo_type, file_id, updated_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                    """,
                    photo_type, file_id,
                )

            if success:
                # Очищаем кэш для этого типа фото
                cache_key = f"photo:get_photo:{photo_type}"
                from utils.cache import get_cache
                cache_backend = get_cache()
                await cache_backend.delete(cache_key)
                logger.debug(f"PhotoManager.set_photo: кэш очищен для photo_type={photo_type}")

                logger.info(f"PhotoManager.set_photo: фото '{photo_type}' установлено (file_id: {file_id[:20]}...)")
                return True
            else:
                logger.warning(f"PhotoManager.set_photo: запрос не выполнился photo_type={photo_type}")
                return False
        except Exception as e:
            logger.error(f"PhotoManager.set_photo: ошибка при сохранении фото {photo_type}: {e}", exc_info=True)
            return False

    async def delete_photo(self, photo_type: str) -> bool:
        """
        Удалить фото.

        Args:
            photo_type: Тип фото ('greeting' или 'main_menu')

        Returns:
            True если успешно
        """
        try:
            logger.debug(f"PhotoManager.delete_photo: запрос на удаление photo_type={photo_type}")

            success = await self.db.execute(
                "DELETE FROM photos WHERE photo_type = ?",
                photo_type,
            )
            if success:
                # Очищаем кэш
                cache_key = f"photo:get_photo:{photo_type}"
                from utils.cache import get_cache
                cache_backend = get_cache()
                await cache_backend.delete(cache_key)
                logger.debug(f"PhotoManager.delete_photo: кэш очищен для photo_type={photo_type}")

                logger.info(f"PhotoManager.delete_photo: фото '{photo_type}' удалено")
                return True
            else:
                logger.warning(f"PhotoManager.delete_photo: фото не найдено для удаления photo_type={photo_type}")
                return False
        except Exception as e:
            logger.error(f"PhotoManager.delete_photo: ошибка при удалении фото {photo_type}: {e}", exc_info=True)
            return False

    async def has_photo(self, photo_type: str) -> bool:
        """
        Проверить наличие фото.

        Args:
            photo_type: Тип фото

        Returns:
            True если фото существует
        """
        try:
            logger.debug(f"PhotoManager.has_photo: проверка наличия photo_type={photo_type}")

            row = await self.db.fetchone(
                "SELECT 1 FROM photos WHERE photo_type = ?",
                photo_type,
            )
            result = row is not None
            logger.debug(f"PhotoManager.has_photo: photo_type={photo_type} -> {'найдено' if result else 'не найдено'}")
            return result
        except Exception as e:
            logger.error(f"PhotoManager.has_photo: ошибка при проверке фото {photo_type}: {e}", exc_info=True)
            return False
