"""
Сервис рассылки сообщений пользователям.
"""

import bleach
from aiogram import Bot
from aiogram.types import Message
from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter
from typing import Optional, Callable
import asyncio

from database import db_adapter
from logger import logger


# Разрешённые HTML-теги для Telegram
ALLOWED_TAGS = [
    "b", "strong", "i", "em", "u", "ins", "s", "strike", "del",
    "a", "code", "pre",
]
ALLOWED_ATTRIBUTES = {"a": ["href"]}


def sanitize_html(text: str) -> str:
    """Очистить HTML от опасных тегов."""
    if not text:
        return ""
    return bleach.clean(text, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES, strip=True)


class Broadcaster:
    """
    Сервис массовой рассылки сообщений.

    Обрабатывает ошибки блокировки бота и лимитов.
    """

    def __init__(self, bot: Bot):
        self.bot = bot
        self.db = db_adapter

    async def broadcast(
        self,
        text: str,
        parse_mode: str = "HTML",
        reply_markup=None,
        progress_callback: Optional[Callable] = None,
    ) -> dict:
        """
        Отправить сообщение всем пользователям.

        Args:
            text: Текст сообщения
            parse_mode: Режим разметки (HTML/Markdown)
            reply_markup: Клавиатура (опционально)
            progress_callback: Callback для отслеживания прогресса

        Returns:
            Словарь со статистикой {success, blocked, errors}
        """
        # САНТИЗИРУЕМ текст рассылки
        clean_text = sanitize_html(text)

        if clean_text != text:
            logger.warning("Текст рассылки был очищен от опасного HTML")
            logger.debug(f"Исходный: {text[:100]}...")
            logger.debug(f"Очищенный: {clean_text[:100]}...")

        stats = {"success": 0, "blocked": 0, "errors": 0}

        # Получаем всех пользователей
        users = await self.db.fetchall("SELECT telegram_id FROM users")

        total = len(users)
        logger.info(f"📨 Рассылка: начало для {total} пользователей")

        for i, (user_id,) in enumerate(users, 1):
            try:
                logger.debug(f"📨 Рассылка [{i}/{total}]: отправка пользователю {user_id}")
                
                await self.bot.send_message(
                    chat_id=user_id,
                    text=clean_text,
                    parse_mode=parse_mode,
                    reply_markup=reply_markup,
                )
                stats["success"] += 1
                logger.debug(f"✅ Рассылка [{i}/{total}]: доставлено пользователю {user_id}")

                # Лимит Telegram: ~30 сообщений в секунду
                await asyncio.sleep(0.035)

            except TelegramRetryAfter as e:
                # Лимит рассылки — ждём указанное время
                logger.warning(f"⏳ Рассылка: лимит Telegram, ждём {e.retry_after} сек")
                await asyncio.sleep(e.retry_after)
                stats["success"] += 1

            except TelegramBadRequest as e:
                error_msg = str(e).lower()
                if "bot was blocked" in error_msg or "blocked" in error_msg:
                    stats["blocked"] += 1
                    logger.debug(f"🚫 Рассылка [{i}/{total}]: пользователь {user_id} заблокировал бота")
                else:
                    stats["errors"] += 1
                    logger.error(f"❌ Рассылка [{i}/{total}]: ошибка пользователю {user_id}: {e}")

            except Exception as e:
                stats["errors"] += 1
                logger.error(f"❌ Рассылка [{i}/{total}]: неожиданная ошибка пользователю {user_id}: {e}", exc_info=True)

            # Callback для прогресса
            if progress_callback:
                await progress_callback(i, total)

        logger.info(
            f"✅ Рассылка завершена: "
            f"Всего={total}, "
            f"Доставлено={stats['success']}, "
            f"Заблокировано={stats['blocked']}, "
            f"Ошибок={stats['errors']}"
        )
        return stats
