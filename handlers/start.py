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
from services.message_manager import MessageManager
from services.content_manager import ContentManager
from messages.texts import SUBSCRIPTION_REQUIRED, SUBSCRIPTION_DENIED
from logger import logger

router = Router()


@router.message(Command("start"))
async def cmd_start(
    message: Message,
    db,
    bot: Bot,
    subscription_service: SubscriptionService,
    message_manager: MessageManager,
    content_manager: ContentManager,
):
    """
    Обработчик команды /start.

    Проверяет подписку пользователя на каналы.
    Если не подписан — показывает кнопки каналов.
    Если подписан — открывает главное меню.
    """
    user_id = message.from_user.id
    username = message.from_user.username
    chat_id = message.chat.id

    # Сохраняем пользователя в БД
    await _save_user(db, user_id, username)

    # Проверяем подписку
    is_subscribed = await subscription_service.check_subscription(user_id)

    if is_subscribed:
        # Пользователь подписан — показываем меню
        await _show_main_menu(message, db, bot, message_manager, user_id, chat_id, content_manager)
    else:
        # Не подписан — требуем подписку
        channels = subscription_service.channel_ids

        # Получаем пригласительные ссылки
        invite_links = await subscription_service.get_invite_links()

        keyboard = get_channel_buttons(channels, invite_links)

        # Сбрасываем last_message_id чтобы всегда отправлять новое сообщение
        await message_manager.clear_last_message_id(user_id)
        
        # Отправляем новое сообщение с кнопками подписки
        msg = await bot.send_message(
            chat_id=chat_id,
            text=SUBSCRIPTION_REQUIRED,
            reply_markup=keyboard,
            parse_mode="HTML",
        )
        # Сохраняем message_id чтобы потом редактировать
        await message_manager.set_last_message_id(user_id, msg.message_id)
        
        logger.info(f"Пользователь {user_id} должен подписаться на каналы")


@router.callback_query(F.data == "check_subscription")
async def check_subscription(
    callback: CallbackQuery,
    bot: Bot,
    db,
    subscription_service: SubscriptionService,
    message_manager: MessageManager,
    content_manager: ContentManager,
):
    """
    Проверка подписки после нажатия кнопки "✅ Я подписался".
    """
    user_id = callback.from_user.id

    is_subscribed = await subscription_service.check_subscription(user_id)

    if is_subscribed:
        # Подписка подтверждена
        await callback.message.delete()
        # Очищаем last_message_id чтобы следующее сообщение было новым
        await message_manager.clear_last_message_id(user_id)
        await _show_main_menu(callback.message, db, bot, message_manager, user_id, callback.message.chat.id, content_manager)
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


async def _show_main_menu(
    message: Message,
    db,
    bot: Bot,
    message_manager: MessageManager,
    user_id: int,
    chat_id: int,
    content_manager: ContentManager = None,
) -> None:
    """
    Показать главное меню пользователю.

    Args:
        message: Сообщение для получения контекста
        db: Экземпляр БД
        bot: Экземпляр бота
        message_manager: Менеджер сообщений
        user_id: Telegram ID пользователя
        chat_id: ID чата
        content_manager: Менеджер контента (опционально)
    """
    keyboard = await get_main_menu(db)

    # Получаем приветствие из БД
    greeting_text = await content_manager.get_content("greeting") if content_manager else None
    if not greeting_text:
        greeting_text = "👋 <b>Привет! Я бот-визитка разработчика.</b>\n\nВыберите раздел в меню ниже, чтобы узнать больше обо мне и моих услугах."

    await message_manager.send_or_edit(
        bot=bot,
        user_id=user_id,
        chat_id=chat_id,
        text=greeting_text,
        reply_markup=keyboard,
        parse_mode="HTML",
    )
