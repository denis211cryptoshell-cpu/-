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
        if user.id == settings.admin_id:
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
