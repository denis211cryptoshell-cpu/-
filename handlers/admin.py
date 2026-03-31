"""
Обработчики админ-панели.
"""

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from config import settings
from database import db_adapter
from keyboards.admin import (
    get_admin_panel,
    get_content_edit_menu,
    get_buttons_manage_menu,
    get_channels_manage_menu,
    get_broadcast_menu,
    get_back_button,
    get_buttons_list,
    get_buttons_edit_list,
    get_button_edit_menu,
    get_photos_manage_menu,
    get_photo_edit_menu,
    get_back_to_photos_menu,
)
from keyboards.inline import get_view_result_button
from keyboards.reply import get_main_menu
from services.content_manager import ContentManager, ButtonManager, ChannelManager, StatsManager, PhotoManager
from services.broadcaster import Broadcaster
from services.subscription import SubscriptionService
from messages.texts import (
    ADMIN_PANEL_TEXT,
    CONTENT_EDIT_TEXT,
    BUTTONS_MANAGE_TEXT,
    CHANNELS_MANAGE_TEXT,
    BROADCAST_TEXT,
    STATS_TEXT,
    CONFIRM_SAVE,
    PHOTOS_MANAGE_TEXT,
    PHOTO_EDIT_TEXT,
)
from utils.telegram_links import get_channel_id_from_link, parse_channel_input
from logger import logger

router = Router()

# Импорт состояний FSM
from states import AdminStates


@router.message(Command("fix"))
async def cmd_fix(message: Message, db):
    """
    Исправить все проблемы с HTML тегами в контенте.
    Доступно только админу.
    """
    if not settings.is_admin(message.from_user.id):
        return

    # PostgreSQL не поддерживает REPLACE в том же формате
    # Используем универсальный подход
    await db_adapter.execute("UPDATE content SET text = REPLACE(text, '</b>', '')")
    await db_adapter.execute("UPDATE content SET text = REPLACE(text, '</i>', '')")
    await db_adapter.execute("UPDATE content SET text = REPLACE(text, '</u>', '')")

    await message.answer("✅ Все HTML теги исправлены!\n\nУдалены лишние закрывающие теги </b>, </i>, </u>")


@router.message(Command("fixhtml"))
async def cmd_fixhtml(message: Message, db):
    """
    Исправить лишние закрывающие теги </b> во всём контенте.
    Доступно только админу.
    """
    if not settings.is_admin(message.from_user.id):
        return

    await db_adapter.execute("UPDATE content SET text = REPLACE(text, '</b>', '')")

    await message.answer(f"✅ Теги исправлены!\n\nТег </b> удалён из всех записей.")


# ========== ВХОД В АДМИНКУ ==========

@router.message(Command("admin"))
async def cmd_admin(message: Message, db):
    """
    Вход в админ-панель по команде /admin.
    """
    if not settings.is_admin(message.from_user.id):
        logger.warning(f"Попытка доступа в админку от {message.from_user.id}")
        return

    keyboard = get_admin_panel()
    await message.answer(text=ADMIN_PANEL_TEXT, reply_markup=keyboard)


@router.message(F.text == "🔧 Админка")
async def btn_admin(message: Message, db):
    """
    Вход в админ-панель по кнопке из главного меню.
    """
    if not settings.is_admin(message.from_user.id):
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


@router.callback_query(F.data.startswith("btn_toggle_"))
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
async def btn_edit_labels(callback: CallbackQuery, button_manager: ButtonManager):
    """
    Редактирование названий кнопок — показ списка кнопок.
    """
    logger.debug(f"btn_edit_labels: пользователь {callback.from_user.id}")
    
    try:
        buttons = await button_manager.get_all_buttons()
        logger.debug(f"btn_edit_labels: получено кнопок: {len(buttons)}")
        logger.debug(f"btn_edit_labels: кнопки: {buttons}")
        
        keyboard = get_buttons_edit_list(buttons)

        await callback.message.edit_text(
            text="✏️ <b>Изменение названия кнопки</b>\n\n"
                 "Выберите кнопку для редактирования:\n\n"
                 "✅ — активна, ❌ — скрыта",
            reply_markup=keyboard,
            parse_mode="HTML",
        )
        logger.info(f"btn_edit_labels: меню отображено успешно")
    except Exception as e:
        logger.error(f"btn_edit_labels: ошибка: {e}", exc_info=True)
        await callback.answer(f"❌ Ошибка: {e}", show_alert=True)


@router.callback_query(F.data.startswith("btn_edit_label_"))
async def btn_edit_label_start(callback: CallbackQuery, state: FSMContext, button_manager: ButtonManager):
    """
    Начало редактирования названия конкретной кнопки.
    """
    logger.debug(f"btn_edit_label_start: callback_data={callback.data}, from_user={callback.from_user.id}")
    
    try:
        button_name = callback.data.split("_", 3)[3]
        logger.debug(f"btn_edit_label_start: извлечено имя кнопки: {button_name}")
        
        # Получаем текущее название
        buttons = await button_manager.get_all_buttons()
        logger.debug(f"btn_edit_label_start: получено кнопок: {len(buttons)}")
        
        current_label = None
        for name, label, is_active in buttons:
            if name == button_name:
                current_label = label
                break

        if current_label is None:
            logger.error(f"btn_edit_label_start: кнопка '{button_name}' не найдена")
            await callback.answer("❌ Кнопка не найдена", show_alert=True)
            return

        logger.debug(f"btn_edit_label_start: текущее название: {current_label}")

        # Сохраняем в состояние
        await state.update_data(button_name=button_name, current_label=current_label)
        await state.set_state(AdminStates.waiting_for_button_label)
        logger.debug(f"btn_edit_label_start: состояние установлено: waiting_for_button_label")

        keyboard = get_button_edit_menu(button_name, current_label)

        await callback.message.edit_text(
            text=f"✏️ <b>Редактирование кнопки</b>\n\n"
                 f"Ключ: <code>{button_name}</code>\n"
                 f"Текущее название: <code>{current_label}</code>\n\n"
                 "Отправьте новое название для этой кнопки:",
            reply_markup=keyboard,
            parse_mode="HTML",
        )
        logger.info(f"btn_edit_label_start: меню редактирования отображено для кнопки '{button_name}'")
    except Exception as e:
        logger.error(f"btn_edit_label_start: ошибка: {e}", exc_info=True)
        await callback.answer(f"❌ Ошибка: {e}", show_alert=True)


@router.message(AdminStates.waiting_for_button_label)
async def save_button_label(message: Message, state: FSMContext, button_manager: ButtonManager):
    """
    Сохранение нового названия кнопки.
    """
    logger.debug(f"save_button_label: пользователь {message.from_user.id}, текст: {message.text}")
    
    try:
        data = await state.get_data()
        logger.debug(f"save_button_label: данные состояния: {data}")
        
        button_name = data.get("button_name")

        if not button_name:
            logger.error("save_button_label: кнопка не определена в состоянии")
            await message.answer("❌ Ошибка: кнопка не определена")
            await state.clear()
            return

        new_label = message.text.strip()
        logger.debug(f"save_button_label: обновление кнопки '{button_name}' на '{new_label}'")

        success = await button_manager.update_label(button_name, new_label)
        logger.debug(f"save_button_label: результат обновления: {success}")

        if success:
            await message.answer(f"✅ Название кнопки обновлено на '{new_label}'")
            
            # Возвращаемся к списку кнопок
            buttons = await button_manager.get_all_buttons()
            keyboard = get_buttons_edit_list(buttons)
            await message.answer(
                text="✏️ <b>Изменение названия кнопки</b>\n\n"
                     "Выберите кнопку для редактирования:",
                reply_markup=keyboard,
                parse_mode="HTML",
            )
            logger.info(f"save_button_label: кнопка '{button_name}' успешно обновлена")
        else:
            await message.answer("❌ Ошибка при обновлении. Попробуйте снова.")
            logger.error(f"save_button_label: не удалось обновить кнопку '{button_name}'")

        await state.clear()
    except Exception as e:
        logger.error(f"save_button_label: ошибка: {e}", exc_info=True)
        await message.answer(f"❌ Ошибка: {e}")
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
             "Отправьте одно из:\n"
             "• ID: <code>-1001234567890</code>\n"
             "• Username: <code>@mychannel</code>\n"
             "• Ссылка: <code>t.me/+AbCdEfGhIjK12345</code>\n\n"
             "<i>Бот должен быть администратором в канале!</i>",
        reply_markup=keyboard,
        parse_mode="HTML",
    )


@router.message(AdminStates.waiting_for_channel)
async def save_channel(message: Message, state: FSMContext, channel_manager: ChannelManager, bot: Bot, subscription_service: SubscriptionService):
    """
    Сохранение нового канала.
    Поддерживает: ID, @username, пригласительные ссылки.
    """
    text = message.text.strip()

    if not text:
        await message.answer("❌ Введите корректное значение")
        return

    # Разбираем ввод
    channel_id, error = parse_channel_input(text)

    if error == "LINK":
        # Это пригласительная ссылка — получаем ID
        await message.answer("🔄 Получаю информацию о канале...")

        channel_id = await get_channel_id_from_link(bot, text)

        if not channel_id:
            await message.answer(
                "❌ Не удалось получить ID канала из ссылки.\n\n"
                "Убедитесь что:\n"
                "• Ссылка действительна\n"
                "• Бот является администратором в канале"
            )
            return

        # Сохраняем полученный ID
        success = await channel_manager.add_channel(channel_id)

        if success:
            # Очищаем кэш ссылок
            subscription_service.clear_cache()
            await message.answer(f"✅ Канал добавлен!\n\nID: <code>{channel_id}</code>", parse_mode="HTML")
        else:
            await message.answer("❌ Ошибка. Возможно, канал уже существует.")

        await state.clear()
        return

    if error:
        await message.answer(error)
        return

    # Обычный режим (ID или username)
    success = await channel_manager.add_channel(channel_id)

    if success:
        # Очищаем кэш ссылок
        subscription_service.clear_cache()
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
async def delete_channel(message: Message, state: FSMContext, channel_manager: ChannelManager, subscription_service: SubscriptionService):
    """
    Удаление канала из БД.
    """
    channel_id = message.text.strip()

    success = await channel_manager.remove_channel(channel_id)

    if success:
        # Очищаем кэш ссылок
        subscription_service.clear_cache()
        await message.answer(f"✅ Канал '{channel_id}' удалён")
    else:
        await message.answer("❌ Канал не найден.")

    await state.clear()


# ========== УПРАВЛЕНИЕ ФОТО ==========

@router.callback_query(F.data == "admin_photos")
async def admin_photos(callback: CallbackQuery, photo_manager: PhotoManager):
    """
    Меню управления фото.
    """
    keyboard = get_photos_manage_menu()
    await callback.message.edit_text(text=PHOTOS_MANAGE_TEXT, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data == "photo_greeting")
@router.callback_query(F.data == "photo_main_menu")
async def photo_menu(callback: CallbackQuery, photo_manager: PhotoManager):
    """
    Меню редактирования конкретного фото.
    """
    try:
        logger.debug(f"photo_menu: пользователь {callback.from_user.id}, callback_data={callback.data}")

        # Извлекаем photo_type из callback_data
        photo_type = callback.data.split("photo_", 1)[1]
        logger.debug(f"photo_menu: извлечено photo_type={photo_type}")

        if photo_type not in ["greeting", "main_menu"]:
            logger.error(f"photo_menu: неверный тип фото '{photo_type}'")
            await callback.answer("❌ Неверный тип фото", show_alert=True)
            return

        logger.debug(f"photo_menu: проверка наличия фото для photo_type={photo_type}")
        has_photo = await photo_manager.has_photo(photo_type)
        logger.debug(f"photo_menu: has_photo={has_photo}")

        keyboard = get_photo_edit_menu(photo_type, has_photo)

        status = "✅ Установлено" if has_photo else "❌ Не установлено"

        # Извлекаем название фото без HTML-тегов
        photo_label = PHOTO_EDIT_TEXT[photo_type].split('</b>')[0].split('<b>')[-1].replace('👋 ', '').replace('🏠 ', '').strip()

        text = f"🖼 <b>Фото: {photo_label}</b>\n\n"
        text += f"Статус: <b>{status}</b>\n\n"
        text += "Выберите действие:"

        await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
        logger.info(f"photo_menu: меню отображено для photo_type={photo_type}")
    except Exception as e:
        logger.error(f"photo_menu: ошибка: {e}", exc_info=True)
        await callback.answer("❌ Ошибка при отображении меню фото", show_alert=True)


@router.callback_query(F.data.startswith("photo_upload_"))
async def photo_upload_start(callback: CallbackQuery, state: FSMContext):
    """
    Начало загрузки фото.
    """
    try:
        logger.debug(f"photo_upload_start: пользователь {callback.from_user.id}, callback_data={callback.data}")

        # Извлекаем photo_type - разбиваем по "_" и берём всё после "photo_upload_"
        parts = callback.data.split("_")
        logger.debug(f"photo_upload_start: части callback_data: {parts}")

        # photo_upload_greeting -> ['photo', 'upload', 'greeting']
        # photo_upload_main_menu -> ['photo', 'upload', 'main', 'menu']
        if len(parts) < 3:
            logger.error(f"photo_upload_start: неверный формат callback_data, частей: {len(parts)}")
            await callback.answer("❌ Неверный формат кнопки", show_alert=True)
            return

        # Берём всё после "photo_upload_"
        photo_type = "_".join(parts[2:])
        logger.debug(f"photo_upload_start: извлечено photo_type={photo_type}")

        if photo_type not in ["greeting", "main_menu"]:
            logger.error(f"photo_upload_start: неверный тип фото '{photo_type}', разрешены: greeting, main_menu")
            await callback.answer("❌ Неверный тип фото", show_alert=True)
            return

        # Устанавливаем состояние
        await state.update_data(photo_type=photo_type)
        logger.debug(f"photo_upload_start: состояние обновлено, photo_type={photo_type}")

        if photo_type == "greeting":
            await state.set_state(AdminStates.waiting_for_greeting_photo)
            logger.debug(f"photo_upload_start: установлено состояние waiting_for_greeting_photo")
        else:
            await state.set_state(AdminStates.waiting_for_main_menu_photo)
            logger.debug(f"photo_upload_start: установлено состояние waiting_for_main_menu_photo")

        keyboard = get_back_to_photos_menu(photo_type)

        await callback.message.edit_text(
            text=PHOTO_EDIT_TEXT[photo_type],
            reply_markup=keyboard,
            parse_mode="HTML",
        )
        logger.info(f"photo_upload_start: меню загрузки фото '{photo_type}' отображено")
    except Exception as e:
        logger.error(f"photo_upload_start: ошибка: {e}", exc_info=True)
        await callback.answer("❌ Ошибка при загрузке меню фото", show_alert=True)


@router.message(AdminStates.waiting_for_greeting_photo, F.photo)
@router.message(AdminStates.waiting_for_main_menu_photo, F.photo)
async def save_photo(message: Message, state: FSMContext, photo_manager: PhotoManager):
    """
    Сохранение фото.
    """
    try:
        logger.debug(f"save_photo: пользователь {message.from_user.id}, получено фото")

        data = await state.get_data()
        logger.debug(f"save_photo: данные состояния: {data}")

        photo_type = data.get("photo_type")

        if not photo_type:
            logger.error("save_photo: тип фото не определён в состоянии")
            await message.answer("❌ Ошибка: тип фото не определён")
            await state.clear()
            return

        # Получаем file_id фото (берём фото наилучшего качества)
        photo = message.photo[-1]
        file_id = photo.file_id
        file_unique_id = photo.file_unique_id
        file_size = photo.file_size

        logger.debug(f"save_photo: photo_type={photo_type}, file_id={file_id[:20]}..., "
                     f"file_unique_id={file_unique_id}, file_size={file_size}")

        # Сохраняем в БД
        success = await photo_manager.set_photo(photo_type, file_id)
        logger.debug(f"save_photo: результат сохранения: {success}")

        if success:
            logger.info(f"save_photo: фото '{photo_type}' успешно загружено пользователем {message.from_user.id}")
            await message.answer(
                f"✅ Фото успешно загружено!\n\n"
                f"Теперь оно будет отображаться в боте.",
                parse_mode="HTML",
            )
        else:
            logger.error(f"save_photo: не удалось сохранить фото '{photo_type}'")
            await message.answer("❌ Ошибка при сохранении фото. Попробуйте снова.")

        await state.clear()

    except Exception as e:
        logger.error(f"save_photo: ошибка: {e}", exc_info=True)
        await message.answer("❌ Произошла ошибка при загрузке фото.")
        await state.clear()


@router.message(AdminStates.waiting_for_greeting_photo)
@router.message(AdminStates.waiting_for_main_menu_photo)
async def invalid_photo_format(message: Message, state: FSMContext):
    """
    Обработка неверного формата фото (когда пользователь отправил текст вместо фото).
    """
    try:
        logger.debug(f"invalid_photo_format: пользователь {message.from_user.id} отправил текст вместо фото. "
                     f"Текст: {message.text[:100] if message.text else 'пусто'}")

        data = await state.get_data()
        photo_type = data.get("photo_type", "неизвестно")

        logger.warning(f"invalid_photo_format: пользователь {message.from_user.id} отправил неверный формат "
                       f"для photo_type={photo_type}")

        await message.answer(
            "❌ <b>Неверный формат!</b>\n\n"
            "Пожалуйста, отправьте <b>фото</b> (изображение), а не текст.\n\n"
            "Поддерживаемые форматы: JPG, PNG",
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error(f"invalid_photo_format: ошибка: {e}", exc_info=True)


@router.callback_query(F.data.startswith("photo_view_"))
async def photo_view(callback: CallbackQuery, bot: Bot, photo_manager: PhotoManager):
    """
    Просмотр фото.
    """
    try:
        logger.debug(f"photo_view: пользователь {callback.from_user.id}, callback_data={callback.data}")

        # Извлекаем photo_type
        parts = callback.data.split("_")
        if len(parts) < 3:
            logger.error(f"photo_view: неверный формат callback_data")
            await callback.answer("❌ Неверный формат кнопки", show_alert=True)
            return

        photo_type = "_".join(parts[2:])
        logger.debug(f"photo_view: извлечено photo_type={photo_type}")

        if photo_type not in ["greeting", "main_menu"]:
            logger.error(f"photo_view: неверный тип фото '{photo_type}'")
            await callback.answer("❌ Неверный тип фото", show_alert=True)
            return

        file_id = await photo_manager.get_photo(photo_type)
        logger.debug(f"photo_view: file_id={file_id[:20] if file_id else None}...")

        if not file_id:
            logger.warning(f"photo_view: фото не найдено photo_type={photo_type}")
            await callback.answer("❌ Фото не найдено", show_alert=True)
            return

        # Отправляем фото
        await bot.send_photo(
            chat_id=callback.from_user.id,
            photo=file_id,
            caption=f"🖼 <b>Просмотр фото: {photo_type}</b>",
            parse_mode="HTML",
        )

        logger.info(f"photo_view: фото отправлено пользователю {callback.from_user.id}")
        await callback.answer("✅ Фото отправлено в чат")
    except Exception as e:
        logger.error(f"photo_view: ошибка: {e}", exc_info=True)
        await callback.answer("❌ Ошибка при просмотре фото", show_alert=True)


@router.callback_query(F.data.startswith("photo_delete_"))
async def photo_delete_confirm(callback: CallbackQuery, photo_manager: PhotoManager):
    """
    Подтверждение удаления фото.
    """
    try:
        logger.debug(f"photo_delete_confirm: пользователь {callback.from_user.id}, callback_data={callback.data}")

        # Извлекаем photo_type
        parts = callback.data.split("_")
        if len(parts) < 3:
            logger.error(f"photo_delete_confirm: неверный формат callback_data")
            await callback.answer("❌ Неверный формат кнопки", show_alert=True)
            return

        photo_type = "_".join(parts[2:])
        logger.debug(f"photo_delete_confirm: извлечено photo_type={photo_type}")

        if photo_type not in ["greeting", "main_menu"]:
            logger.error(f"photo_delete_confirm: неверный тип фото '{photo_type}'")
            await callback.answer("❌ Неверный тип фото", show_alert=True)
            return

        # Удаляем фото
        success = await photo_manager.delete_photo(photo_type)
        logger.debug(f"photo_delete_confirm: результат удаления: {success}")

        if success:
            # Обновляем меню
            keyboard = get_photo_edit_menu(photo_type, False)

            # Извлекаем название фото без HTML-тегов
            photo_label = PHOTO_EDIT_TEXT[photo_type].split('</b>')[0].split('<b>')[-1].replace('👋 ', '').replace('🏠 ', '').strip()

            text = f"🖼 <b>Фото: {photo_label}</b>\n\n"
            text += f"Статус: ❌ Не установлено\n\n"
            text += "Выберите действие:"

            await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
            logger.info(f"photo_delete_confirm: фото '{photo_type}' удалено")
            await callback.answer("✅ Фото удалено")
        else:
            logger.warning(f"photo_delete_confirm: фото не найдено для удаления photo_type={photo_type}")
            await callback.answer("❌ Ошибка при удалении фото", show_alert=True)
    except Exception as e:
        logger.error(f"photo_delete_confirm: ошибка: {e}", exc_info=True)
        await callback.answer("❌ Ошибка при удалении фото", show_alert=True)


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
    users = await db_adapter.fetchall("SELECT telegram_id FROM users")

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
async def admin_exit(callback: CallbackQuery, db, message_manager):
    """
    Выход из админки в главное меню.

    Сбрасываем last_message_id и отправляем новое сообщение с меню.
    """
    # Получаем главное меню (ReplyKeyboardMarkup)
    keyboard = await get_main_menu(db)

    # Сбрасываем last_message_id чтобы следующее нажатие кнопки создало новое сообщение
    await message_manager.clear_last_message_id(callback.from_user.id)

    # Отправляем сообщение с главным меню
    await callback.message.answer(
        text="🔙 Возврат в главное меню",
        reply_markup=keyboard,
    )

    # Удаляем сообщение админ-панели
    await callback.message.delete()


# ========== УПРАВЛЕНИЕ КЭШЕМ ==========

@router.message(Command("cache"))
async def cmd_cache(message: Message):
    """
    Управление кэшем: статистика и очистка.
    Доступно только админу.
    """
    if not settings.is_admin(message.from_user.id):
        return

    from utils.cache import get_cache_stats, cache

    args = message.text.split(maxsplit=1)
    command = args[1] if len(args) > 1 else "stats"

    if command == "stats":
        # Показать статистику кэша
        stats_text = await get_cache_stats()
        await message.answer(stats_text)

    elif command == "clear":
        # Очистить весь кэш
        await cache.clear()
        await message.answer("🧹 Кэш полностью очищен")

    else:
        await message.answer(
            "📊 Управление кэшем:\n\n"
            "/cache stats - Статистика кэша\n"
            "/cache clear - Очистить весь кэш"
        )
