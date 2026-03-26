"""
Сервис проверки обязательной подписки.
"""

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from typing import List, Dict, Optional
from datetime import datetime, timedelta

from logger import logger


class SubscriptionService:
    """
    Сервис проверки подписки пользователя на каналы.

    Бот должен быть администратором в каналах для работы проверки.
    Создаёт пригласительные ссылки для каждого канала.
    """

    def __init__(self, bot: Bot, channel_ids: List[str]):
        self.bot = bot
        self.channel_ids = channel_ids
        # Кэш пригласительных ссылок: {channel_id: {"link": str, "expires": datetime}}
        self._invite_cache: Dict[str, dict] = {}

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
        Кэширует результат на 60 секунд.

        Args:
            user_id: Telegram ID пользователя
            channel_id: ID или @username канала

        Returns:
            True если подписан, иначе False
        """
        # Формируем ключ кэша
        cache_key = f"subscription:_check_channel:{user_id}:{channel_id}"
        
        # Проверяем кэш
        from utils.cache import cache as cache_service
        cached_result = await cache_service.get(cache_key)
        if cached_result is not None:
            logger.debug(f"Кэш: {_check_channel.__name__} -> {cached_result}")
            return cached_result

        try:
            member = await self.bot.get_chat_member(chat_id=channel_id, user_id=user_id)
            # Проверяем статусы членства
            result = member.status in ("member", "administrator", "creator")

            # Сохраняем в кэш на 60 секунд
            await cache_service.set(cache_key, result, 60)
            logger.debug(f"Кэш: {_check_channel.__name__} -> {result} (TTL: 60s)")
            return result

        except TelegramBadRequest as e:
            # Бот не админ в канале или канал недоступен
            logger.error(f"Ошибка проверки канала {channel_id}: {e}")
            return False

        except Exception as e:
            logger.error(f"Неожиданная ошибка при проверке {channel_id}: {e}")
            return False

    async def get_invite_links(self) -> Dict[str, str]:
        """
        Получить пригласительные ссылки для всех каналов.

        Создаёт новые ссылки если:
        - Ссылки нет в кэше
        - Истёк срок действия (2 часа)

        Returns:
            Словарь {channel_id: invite_link}
        """
        invite_links = {}
        now = datetime.now()

        for channel_id in self.channel_ids:
            # Проверяем кэш
            cached = self._invite_cache.get(channel_id)
            
            if cached and cached["expires"] > now:
                # Ссылка ещё действительна
                invite_links[channel_id] = cached["link"]
                logger.debug(f"Используем кэшированную ссылку для {channel_id}")
            else:
                # Создаём новую ссылку
                try:
                    invite_link = await self._create_invite_link(channel_id)
                    if invite_link:
                        invite_links[channel_id] = invite_link
                        # Кэшируем на 2 часа
                        self._invite_cache[channel_id] = {
                            "link": invite_link,
                            "expires": now + timedelta(hours=2)
                        }
                        logger.info(f"Создана новая ссылка для {channel_id}")
                except Exception as e:
                    logger.error(f"Не удалось создать ссылку для {channel_id}: {e}")
                    # Фолбэк на обычную ссылку
                    if channel_id.startswith("@"):
                        invite_links[channel_id] = f"https://t.me/{channel_id}"
                    else:
                        invite_links[channel_id] = f"https://t.me/{channel_id.lstrip('-')}"

        return invite_links

    async def _create_invite_link(self, channel_id: str) -> Optional[str]:
        """
        Создать пригласительную ссылку для канала.

        Args:
            channel_id: ID канала

        Returns:
            Ссылка или None если не удалось
        """
        try:
            # Создаём многоразовую ссылку на 2 часа
            invite = await self.bot.create_chat_invite_link(
                chat_id=channel_id,
                expire_date=datetime.now() + timedelta(hours=2),
                creates_join_request=False,  # Автоматическое вступление
            )
            return invite.invite_link

        except TelegramBadRequest as e:
            logger.error(f"Не удалось создать ссылку для {channel_id}: {e}")
            return None

        except Exception as e:
            logger.error(f"Ошибка создания ссылки для {channel_id}: {e}")
            return None

    def clear_cache(self) -> None:
        """Очистить кэш ссылок (например, после изменения списка каналов)."""
        self._invite_cache.clear()
        logger.debug("Кэш пригласительных ссылок очищен")
