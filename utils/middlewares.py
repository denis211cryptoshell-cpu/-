"""
Middleware для обработки запросов.
"""

from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject

from database.db import Database
from config import settings
from services.subscription import SubscriptionService
from services.content_manager import ContentManager, ButtonManager, ChannelManager, StatsManager
from services.broadcaster import Broadcaster
from logger import logger


class DatabaseMiddleware(BaseMiddleware):
    """
    Middleware для внедрения экземпляра БД в хендлеры.
    
    Добавляет `db` в словарь data каждого события.
    """

    def __init__(self, db: Database):
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
    
    Добавляет сервисы в словарь data каждого события.
    """

    def __init__(self, db: Database, bot):
        self.db = db
        self.bot = bot

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        # Внедряем сервисы
        data["subscription_service"] = SubscriptionService(self.bot, settings.channel_ids)
        data["content_manager"] = ContentManager(self.db)
        data["button_manager"] = ButtonManager(self.db)
        data["channel_manager"] = ChannelManager(self.db)
        data["stats_manager"] = StatsManager(self.db)
        data["broadcaster"] = Broadcaster(self.bot, self.db)

        return await handler(event, data)


class AdminMiddleware(BaseMiddleware):
    """
    Middleware для проверки прав администратора.
    
    Блокирует доступ к /admin и кнопкам админки для не-админов.
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

        if user:
            # Проверяем ADMIN_ID
            if user.id != settings.admin_id:
                # Проверяем, является ли запрос к админке
                is_admin_request = False

                if isinstance(event, Message):
                    is_admin_request = (
                        (event.text and event.text.startswith("/admin")) or
                        event.text == "🔧 Админка"
                    )
                elif isinstance(event, CallbackQuery):
                    is_admin_request = event.data.startswith("admin_")

                if is_admin_request:
                    logger.warning(f"Попытка доступа в админку от пользователя {user.id}")
                    return None  # Игнорируем запрос

        return await handler(event, data)
