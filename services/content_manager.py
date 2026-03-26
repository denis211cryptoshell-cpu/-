"""
Сервис управления контентом (CRUD).
Поддерживает SQLite и PostgreSQL через db_adapter.
"""

from datetime import datetime
from typing import Optional

from database import db_adapter
from logger import logger


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
        from utils.cache import cache as cache_service
        cached_result = await cache_service.get(cache_key)
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
            await cache_service.set(cache_key, result, 300)
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
            success = await self.db.execute(
                """
                UPDATE content
                SET text = ?, updated_at = ?
                WHERE section = ?
                """,
                text,
                datetime.now().isoformat(),
                section,
            )
            if success:
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
        return await self.db.fetchall("SELECT name, label, is_active FROM buttons ORDER BY id")

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
            success = await self.db.execute(
                "UPDATE buttons SET label = ? WHERE name = ?",
                new_label,
                name,
            )
            if success:
                logger.info(f"Название кнопки '{name}' обновлено на '{new_label}'")
                return True
            return False
        except Exception as e:
            logger.error(f"Ошибка обновления кнопки {name}: {e}")
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

    async def increment_click(self, button_name: str) -> None:
        """
        Увеличить счётчик нажатий кнопки.

        Args:
            button_name: Ключ кнопки
        """
        try:
            if db_adapter.db_type == "postgresql":
                await self.db.execute(
                    """
                    INSERT INTO stats (button_name, clicks) VALUES (?, 1)
                    ON CONFLICT (button_name) DO UPDATE SET clicks = stats.clicks + 1
                    """,
                    button_name,
                )
            else:
                await self.db.execute(
                    """
                    INSERT INTO stats (button_name, clicks)
                    VALUES (?, 1)
                    ON CONFLICT(button_name)
                    DO UPDATE SET clicks = clicks + 1
                    """,
                    button_name,
                )
        except Exception as e:
            logger.error(f"Ошибка обновления статистики {button_name}: {e}")

    async def get_stats(self) -> list[tuple[str, int]]:
        """
        Получить статистику нажатий.

        Returns:
            Список кортежей (button_name, clicks)
        """
        return await self.db.fetchall("SELECT button_name, clicks FROM stats ORDER BY clicks DESC")

    async def get_users_count(self) -> int:
        """
        Получить количество пользователей.

        Returns:
            Количество пользователей
        """
        row = await self.db.fetchone("SELECT COUNT(*) FROM users")
        return row[0] if row else 0
