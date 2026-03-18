"""
Сервис проверки обязательной подписки.
"""

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from typing import List

from logger import logger


class SubscriptionService:
    """
    Сервис проверки подписки пользователя на каналы.
    
    Бот должен быть администратором в каналах для работы проверки.
    """

    def __init__(self, bot: Bot, channel_ids: List[str]):
        self.bot = bot
        self.channel_ids = channel_ids

    async def check_subscription(self, user_id: int) -> bool:
        """
        Проверить подписку пользователя на все обязательные каналы.
        
        Args:
            user_id: Telegram ID пользователя
        
        Returns:
            True если подписан на все каналы, иначе False
        """
        if not self.channel_ids:
            # Если каналов нет в конфиге — считаем что подписка не требуется
            return True

        for channel in self.channel_ids:
            is_member = await self._check_channel(user_id, channel)
            if not is_member:
                logger.debug(f"Пользователь {user_id} не подписан на {channel}")
                return False

        logger.debug(f"Пользователь {user_id} подписан на все каналы")
        return True

    async def _check_channel(self, user_id: int, channel_id: str) -> bool:
        """
        Проверить подписку на один канал.
        
        Args:
            user_id: Telegram ID пользователя
            channel_id: ID или @username канала
        
        Returns:
            True если подписан, иначе False
        """
        try:
            member = await self.bot.get_chat_member(chat_id=channel_id, user_id=user_id)
            # Проверяем статусы членства
            return member.status in ("member", "administrator", "creator")

        except TelegramBadRequest as e:
            # Бот не админ в канале или канал недоступен
            logger.error(f"Ошибка проверки канала {channel_id}: {e}")
            return False

        except Exception as e:
            logger.error(f"Неожиданная ошибка при проверке {channel_id}: {e}")
            return False
