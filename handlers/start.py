"""
Обработчики команды /start и логика обязательной подписки.
"""

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command

from database import db_adapter
from keyboards.inline import get_channel_buttons
from keyboards.reply import get_main_menu
from services.subscription import SubscriptionService
from messages.texts import START_MESSAGE, SUBSCRIPTION_REQUIRED, SUBSCRIPTION_DENIED
from logger import logger

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message, db, bot: Bot, subscription_service: SubscriptionService):
    """
    Обработчик команды /start.

    Проверяет подписку пользователя на каналы.
    Если не подписан — показывает кнопки каналов.
    Если подписан — открывает главное меню.
    """
    user_id = message.from_user.id
    username = message.from_user.username

    # Сохраняем пользователя в БД
    await _save_user(db, user_id, username)

    # Проверяем подписку
    is_subscribed = await subscription_service.check_subscription(user_id)

    if is_subscribed:
        # Пользователь подписан — показываем меню
        await _show_main_menu(message, db)
    else:
        # Не подписан — требуем подписку
        channels = subscription_service.channel_ids
        
        # Получаем пригласительные ссылки
        invite_links = await subscription_service.get_invite_links()
        
        keyboard = get_channel_buttons(channels, invite_links)

        await message.answer(
            text=SUBSCRIPTION_REQUIRED,
            reply_markup=keyboard,
        )
        logger.info(f"Пользователь {user_id} должен подписаться на каналы")


@router.callback_query(F.data == "check_subscription")
async def check_subscription(callback: CallbackQuery, bot: Bot, db, subscription_service: SubscriptionService):
    """
    Проверка подписки после нажатия кнопки "✅ Я подписался".
    """
    user_id = callback.from_user.id

    is_subscribed = await subscription_service.check_subscription(user_id)

    if is_subscribed:
        # Подписка подтверждена
        await callback.message.delete()
        await _show_main_menu(callback.message, db)
        logger.info(f"Пользователь {user_id} подписался на каналы")
    else:
        # Всё ещё не подписан — обновляем ссылки (вдруг истекли)
        channels = subscription_service.channel_ids
        invite_links = await subscription_service.get_invite_links()
        keyboard = get_channel_buttons(channels, invite_links)
        
        await callback.message.edit_text(
            text=SUBSCRIPTION_REQUIRED,
            reply_markup=keyboard,
        )
        await callback.answer(
            text=SUBSCRIPTION_DENIED,
            show_alert=True,
        )
        logger.debug(f"Пользователь {user_id} всё ещё не подписан")


async def _save_user(db, telegram_id: int, username: str | None) -> None:
    """
    Сохранить пользователя в БД (или обновить last_seen).
    """
    from datetime import datetime

    # Проверяем существование
    exists = await db_adapter.fetchone(
        "SELECT id FROM users WHERE telegram_id = ?",
        telegram_id,
    )

    if exists:
        # Обновляем last_seen
        await db_adapter.execute(
            "UPDATE users SET last_seen = ? WHERE telegram_id = ?",
            datetime.now().isoformat(),
            telegram_id,
        )
    else:
        # Создаём нового пользователя
        await db_adapter.execute(
            "INSERT INTO users (telegram_id, username) VALUES (?, ?)",
            telegram_id,
            username,
        )


async def _show_main_menu(message: Message, db) -> None:
    """
    Показать главное меню пользователю.
    """
    keyboard = await get_main_menu(db)

    await message.answer(
        text=START_MESSAGE,
        reply_markup=keyboard,
    )
