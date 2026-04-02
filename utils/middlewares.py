"""
Middleware для обработки запросов.
"""

from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject

from database import db, DB_TYPE
from config import settings
from services.subscription import SubscriptionService
from services.content_manager import ContentManager, ButtonManager, ChannelManager, StatsManager, PhotoManager
from services.broadcaster import Broadcaster
from services.message_manager import MessageManager
from logger import logger


class DatabaseMiddleware(BaseMiddleware):
    """
    Middleware для внедрения экземпляра БД в хендлеры.

    Добавляет `db` в словарь data каждого события.
    """

    def __init__(self, db):
        self.db = db

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        data["db"] = self.db
        return await handler(event, data)


class ServiceMiddleware(BaseMiddleware):
    """
    Middleware для внедрения сервисов в хендлеры.

    Создаёт сервисы один раз при инициализации и переиспользует их.
    """

    def __init__(self, db, bot):
        self.db = db
        self.bot = bot
        # Создаём сервисы один раз
        self._subscription_service = None
        self._content_manager = None
        self._button_manager = None
        self._channel_manager = None
        self._stats_manager = None
        self._photo_manager = None
        self._broadcaster = None
        self._message_manager = None

    async def _init_services(self):
        """Ленивая инициализация сервисов."""
        if self._subscription_service is None:
            # Получаем каналы из БД
            channel_ids = await self._get_channel_ids_from_db()
            
            # Создаём сервисы
            self._subscription_service = SubscriptionService(self.bot, channel_ids)
            self._content_manager = ContentManager(self.db)
            self._button_manager = ButtonManager(self.db)
            self._channel_manager = ChannelManager(self.db)
            self._stats_manager = StatsManager(self.db)
            self._photo_manager = PhotoManager(self.db)
            self._broadcaster = Broadcaster(self.bot)
            self._message_manager = MessageManager()

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        # Инициализируем сервисы при первом вызове
        await self._init_services()

        # Внедряем сервисы
        data["subscription_service"] = self._subscription_service
        data["content_manager"] = self._content_manager
        data["button_manager"] = self._button_manager
        data["channel_manager"] = self._channel_manager
        data["stats_manager"] = self._stats_manager
        data["photo_manager"] = self._photo_manager
        data["broadcaster"] = self._broadcaster
        data["message_manager"] = self._message_manager

        return await handler(event, data)
    
    async def _get_channel_ids_from_db(self) -> list[str]:
        """
        Получить список каналов для подписки из БД.
        
        Returns:
            Список channel_id из таблицы channels
        """
        try:
            async with self.db.connection.cursor() as cursor:
                await cursor.execute("SELECT channel_id FROM channels WHERE is_required = 1")
                rows = await cursor.fetchall()
                return [row[0] for row in rows] if rows else []
        except Exception:
            # Если БД недоступна — возвращаем пустой список
            return []


class AdminMiddleware(BaseMiddleware):
    """
    Middleware для проверки прав администратора.

    Блокирует доступ к /admin и кнопкам админки для не-админов.
    Пропускает все остальные запросы.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        # Получаем пользователя из события
        user = None

        if isinstance(event, Message):
            user = event.from_user
        elif isinstance(event, CallbackQuery):
            user = event.from_user

        # Если нет пользователя — пропускаем (системные события)
        if not user:
            return await handler(event, data)

        # Проверяем, является ли запрос к админке
        is_admin_request = self._check_admin_request(event)

        # Если это НЕ админка — пропускаем всех
        if not is_admin_request:
            return await handler(event, data)

        # Это админка — проверяем права
        if settings.is_admin(user.id):
            # Админ — пропускаем
            logger.debug(f"Админ {user.id} получил доступ к админке")
            return await handler(event, data)
        else:
            # НЕ админ — блокируем
            logger.warning(
                f"🚫 БЛОКИРОВКА: Пользователь {user.id} (@{user.username}) "
                f"попытался получить доступ к админке"
            )
            # Возвращаем None — хендлер не выполнится
            return None

    def _check_admin_request(self, event: TelegramObject) -> bool:
        """
        Проверить, является ли запрос к админке.
        
        Args:
            event: Событие Telegram
        
        Returns:
            True если это запрос к админке
        """
        # Команда /admin
        if isinstance(event, Message):
            if event.text:
                if event.text.startswith("/admin"):
                    return True
                if event.text == "🔧 Админка":
                    return True
        
        # Callback админки
        if isinstance(event, CallbackQuery):
            if event.data:
                # Все callback админки начинаются с admin_
                if event.data.startswith("admin_"):
                    return True
                # Кнопки управления каналами
                if event.data.startswith("channel_"):
                    return True
                # Кнопки управления кнопками
                if event.data.startswith("btn_"):
                    return True
                # Кнопки рассылки
                if event.data.startswith("broadcast_"):
                    return True
        
        return False
