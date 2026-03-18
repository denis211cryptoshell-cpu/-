"""
Обработчики админ-панели.
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from config import settings
from keyboards.admin import (
    get_admin_panel,
    get_content_edit_menu,
    get_buttons_manage_menu,
    get_channels_manage_menu,
    get_broadcast_menu,
    get_back_button,
    get_buttons_list,
)
from keyboards.inline import get_view_result_button
from keyboards.reply import get_main_menu
from services.content_manager import ContentManager, ButtonManager, ChannelManager, StatsManager
from services.broadcaster import Broadcaster
from messages.texts import (
    ADMIN_PANEL_TEXT,
    CONTENT_EDIT_TEXT,
    BUTTONS_MANAGE_TEXT,
    CHANNELS_MANAGE_TEXT,
    BROADCAST_TEXT,
    STATS_TEXT,
    CONFIRM_SAVE,
)
from logger import logger

router = Router()

# Импорт состояний FSM
from states import AdminStates


# ========== ВХОД В АДМИНКУ ==========

@router.message(Command("admin"))
async def cmd_admin(message: Message, db):
    """
    Вход в админ-панель по команде /admin.
    """
    if message.from_user.id != settings.admin_id:
        logger.warning(f"Попытка доступа в админку от {message.from_user.id}")
        return

    keyboard = get_admin_panel()
    await message.answer(text=ADMIN_PANEL_TEXT, reply_markup=keyboard)


@router.message(F.text == "🔧 Админка")
async def btn_admin(message: Message, db):
    """
    Вход в админ-панель по кнопке из главного меню.
    """
    if message.from_user.id != settings.admin_id:
        logger.warning(f"Попытка доступа в админку от {message.from_user.id}")
        return

    keyboard = get_admin_panel()
    await message.answer(text=ADMIN_PANEL_TEXT, reply_markup=keyboard)


# ========== ГЛАВНОЕ МЕНЮ АДМИНКИ ==========

@router.callback_query(F.data == "admin_main")
async def admin_main(callback: CallbackQuery):
    """
    Вернуться в главное меню админки.
    """
    keyboard = get_admin_panel()
    await callback.message.edit_text( text=ADMIN_PANEL_TEXT, reply_markup=keyboard)


# ========== РЕДАКТИРОВАНИЕ КОНТЕНТА ==========

@router.callback_query(F.data == "admin_content")
async def admin_content(callback: CallbackQuery, content_manager: ContentManager):
    """
    Меню выбора раздела для редактирования.
    """
    keyboard = get_content_edit_menu()

    await callback.message.edit_text( 
        text=CONTENT_EDIT_TEXT,
        reply_markup=keyboard,
    )


@router.callback_query(F.data.startswith("edit_content_"))
async def edit_content(callback: CallbackQuery, state: FSMContext, content_manager: ContentManager):
    """
    Начало редактирования раздела.
    """
    section = callback.data.split("_", 2)[2]

    # Получаем текущий контент
    current_text = await content_manager.get_content(section)

    # Сохраняем в состояние
    await state.update_data(section=section, current_text=current_text)
    await state.set_state(AdminStates.waiting_for_content)

    keyboard = get_back_button("admin_content")

    # Обрезаем текст для предпросмотра
    preview = current_text[:500] + "..." if len(current_text or "") > 500 else current_text

    await callback.message.edit_text( 
        text=f"📝 <b>Редактирование: {section}</b>\n\n"
             f"Отправьте новый текст для этого раздела.\n\n"
             f"<i>Текущий текст:</i>\n{preview}",
        reply_markup=keyboard,
        parse_mode="HTML",
    )


@router.message(AdminStates.waiting_for_content)
async def save_content(message: Message, state: FSMContext, content_manager: ContentManager):
    """
    Сохранение нового контента.
    """
    data = await state.get_data()
    section = data.get("section")

    if not section:
        await message.answer("❌ Ошибка: раздел не определён")
        await state.clear()
        return

    new_text = message.text

    # Обновляем БД
    success = await content_manager.update_content(section, new_text)

    if success:
        keyboard = get_view_result_button(section)
        await message.answer(
            text=CONFIRM_SAVE.format(section=section),
            reply_markup=keyboard,
        )
    else:
        await message.answer("❌ Ошибка при сохранении. Попробуйте снова.")

    await state.clear()


@router.callback_query(F.data.startswith("view_"))
async def view_result(callback: CallbackQuery, content_manager: ContentManager):
    """
    Просмотр результата после сохранения.
    """
    section = callback.data.split("_", 1)[1]
    content = await content_manager.get_content(section)

    await callback.message.answer(text=content, parse_mode="HTML")


# ========== УПРАВЛЕНИЕ КНОПКАМИ ==========

@router.callback_query(F.data == "admin_buttons")
async def admin_buttons(callback: CallbackQuery, button_manager: ButtonManager):
    """
    Меню управления кнопками главного меню.
    """
    keyboard = get_buttons_manage_menu()
    await callback.message.edit_text( text=BUTTONS_MANAGE_TEXT, reply_markup=keyboard)


@router.callback_query(F.data == "btn_toggle_visibility")
async def btn_toggle_visibility(callback: CallbackQuery, button_manager: ButtonManager):
    """
    Показать/скрыть кнопки меню.
    """
    buttons = await button_manager.get_all_buttons()
    keyboard = get_buttons_list(buttons)

    await callback.message.edit_text( 
        text="👁️ <b>Управление видимостью кнопок</b>\n\n"
             "Нажмите на кнопку, чтобы изменить её статус:",
        reply_markup=keyboard,
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("btn_edit_"))
async def toggle_button(callback: CallbackQuery, button_manager: ButtonManager):
    """
    Переключение видимости конкретной кнопки.
    """
    button_name = callback.data.split("_", 2)[2]

    # Получаем текущий статус
    buttons = await button_manager.get_all_buttons()
    current_status = None
    for name, label, is_active in buttons:
        if name == button_name:
            current_status = is_active
            break

    if current_status is None:
        await callback.answer("❌ Кнопка не найдена", show_alert=True)
        return

    # Переключаем статус
    new_status = not current_status
    await button_manager.toggle_visibility(button_name, new_status)

    # Обновляем список
    buttons = await button_manager.get_all_buttons()
    keyboard = get_buttons_list(buttons)

    status_text = "активна" if new_status else "скрыта"
    await callback.message.edit_text( 
        text=f"✅ Кнопка теперь {status_text}\n\n"
             "👁️ <b>Управление видимостью кнопок</b>\n\n"
             "Нажмите на кнопку, чтобы изменить её статус:",
        reply_markup=keyboard,
        parse_mode="HTML",
    )


@router.callback_query(F.data == "btn_edit_labels")
async def btn_edit_labels(callback: CallbackQuery, state: FSMContext):
    """
    Редактирование названий кнопок.
    """
    await state.set_state(AdminStates.waiting_for_button_name)

    keyboard = get_back_button("admin_buttons")

    await callback.message.edit_text( 
        text="✏️ <b>Изменение названия кнопки</b>\n\n"
             "Отправьте название кнопки в формате:\n"
             "<code>ключ|новое название</code>\n\n"
             "Пример: <code>about|👤 Обо мне</code>",
        reply_markup=keyboard,
        parse_mode="HTML",
    )


@router.message(AdminStates.waiting_for_button_name)
async def save_button_label(message: Message, state: FSMContext, button_manager: ButtonManager):
    """
    Сохранение нового названия кнопки.
    """
    text = message.text.strip()

    if "|" not in text:
        await message.answer("❌ Неверный формат. Используйте: <code>ключ|название</code>", parse_mode="HTML")
        return

    parts = text.split("|", 1)
    if len(parts) != 2:
        await message.answer("❌ Неверный формат. Используйте: <code>ключ|название</code>", parse_mode="HTML")
        return

    button_key, new_label = parts

    success = await button_manager.update_label(button_key.strip(), new_label.strip())

    if success:
        await message.answer(f"✅ Название кнопки '{button_key}' обновлено")
    else:
        await message.answer("❌ Ошибка при обновлении. Проверьте ключ кнопки.")

    await state.clear()


# ========== УПРАВЛЕНИЕ КАНАЛАМИ ==========

@router.callback_query(F.data == "admin_channels")
async def admin_channels(callback: CallbackQuery, channel_manager: ChannelManager):
    """
    Меню управления каналами.
    """
    channels = await channel_manager.get_all_channels()

    text = "📢 <b>Управление каналами</b>\n\n"
    if channels:
        for _, channel_id, is_required in channels:
            status = "🔒" if is_required else "📢"
            text += f"{status} <code>{channel_id}</code>\n"
    else:
        text += "<i>Каналы не добавлены</i>"

    keyboard = get_channels_manage_menu()

    await callback.message.edit_text( text=text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data == "channel_add")
async def channel_add(callback: CallbackQuery, state: FSMContext):
    """
    Добавление канала.
    """
    await state.set_state(AdminStates.waiting_for_channel)

    keyboard = get_back_button("admin_channels")

    await callback.message.edit_text( 
        text="➕ <b>Добавление канала</b>\n\n"
             "Отправьте ID или @username канала:\n"
             "Пример: <code>@mychannel</code> или <code>-1001234567890</code>",
        reply_markup=keyboard,
        parse_mode="HTML",
    )


@router.message(AdminStates.waiting_for_channel)
async def save_channel(message: Message, state: FSMContext, channel_manager: ChannelManager):
    """
    Сохранение нового канала.
    """
    channel_id = message.text.strip()

    if not channel_id:
        await message.answer("❌ Введите корректный ID или @username")
        return

    success = await channel_manager.add_channel(channel_id)

    if success:
        await message.answer(f"✅ Канал '{channel_id}' добавлен")
    else:
        await message.answer("❌ Ошибка. Возможно, канал уже существует.")

    await state.clear()


@router.callback_query(F.data == "channel_remove")
async def channel_remove(callback: CallbackQuery, state: FSMContext):
    """
    Удаление канала.
    """
    await state.set_state(AdminStates.waiting_for_channel_remove)

    keyboard = get_back_button("admin_channels")

    await callback.message.edit_text( 
        text="🗑️ <b>Удаление канала</b>\n\n"
             "Отправьте ID или @username канала для удаления:",
        reply_markup=keyboard,
        parse_mode="HTML",
    )


@router.message(AdminStates.waiting_for_channel_remove)
async def delete_channel(message: Message, state: FSMContext, channel_manager: ChannelManager):
    """
    Удаление канала из БД.
    """
    channel_id = message.text.strip()

    success = await channel_manager.remove_channel(channel_id)

    if success:
        await message.answer(f"✅ Канал '{channel_id}' удалён")
    else:
        await message.answer("❌ Канал не найден.")

    await state.clear()


# ========== СТАТИСТИКА ==========

@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery, stats_manager: StatsManager):
    """
    Показ статистики бота.
    """
    users_count = await stats_manager.get_users_count()
    clicks_stats = await stats_manager.get_stats()

    text = STATS_TEXT.format(
        users_count=users_count,
        clicks="\n".join(f"• {name}: {clicks}" for name, clicks in clicks_stats),
    )

    keyboard = get_back_button("admin_main")

    await callback.message.edit_text( text=text, reply_markup=keyboard, parse_mode="HTML")


# ========== РАССЫЛКА ==========

@router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast(callback: CallbackQuery):
    """
    Меню рассылки.
    """
    keyboard = get_broadcast_menu()
    await callback.message.edit_text( text=BROADCAST_TEXT, reply_markup=keyboard)


@router.callback_query(F.data == "broadcast_start")
async def broadcast_start(callback: CallbackQuery, state: FSMContext):
    """
    Начало рассылки.
    """
    await state.set_state(AdminStates.waiting_for_broadcast)

    keyboard = get_back_button("admin_broadcast")

    await callback.message.edit_text( 
        text="📨 <b>Рассылка сообщений</b>\n\n"
             "Отправьте текст сообщения для всех пользователей бота.\n\n"
             "<i>Поддерживается HTML-разметка.</i>",
        reply_markup=keyboard,
        parse_mode="HTML",
    )


@router.message(AdminStates.waiting_for_broadcast)
async def send_broadcast(message: Message, state: FSMContext, db, broadcaster: Broadcaster):
    """
    Отправка рассылки.
    """
    text = message.text

    # Получаем всех пользователей
    async with db.connection.cursor() as cursor:
        await cursor.execute("SELECT telegram_id FROM users")
        users = await cursor.fetchall()

    count = len(users)
    await message.answer(f"📨 Начало рассылки для {count} пользователей...")

    # Запускаем рассылку
    stats = await broadcaster.broadcast(text)

    await message.answer(
        f"✅ Рассылка завершена!\n\n"
        f"📬 Доставлено: {stats['success']}\n"
        f"🚫 Заблокировано: {stats['blocked']}\n"
        f"❌ Ошибок: {stats['errors']}"
    )

    await state.clear()


# ========== ВЫХОД ИЗ АДМИНКИ ==========

@router.callback_query(F.data == "admin_exit")
async def admin_exit(callback: CallbackQuery, db):
    """
    Выход из админки в главное меню.
    """
    keyboard = await get_main_menu(db)

    await callback.message.edit_text( 
        text="🔙 Возврат в главное меню",
        reply_markup=keyboard,
    )
