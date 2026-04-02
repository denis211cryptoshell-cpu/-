"""
Inline-клавиатуры для админ-панели.
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_admin_panel() -> InlineKeyboardMarkup:
    """
    Главное меню админ-панели.

    Returns:
        InlineKeyboardMarkup с основными разделами админки
    """
    keyboard = [
        [
            InlineKeyboardButton(text="📝 Контент", callback_data="admin_content"),
            InlineKeyboardButton(text="🔘 Кнопки меню", callback_data="admin_buttons"),
        ],
        [
            InlineKeyboardButton(text="📢 Каналы", callback_data="admin_channels"),
            InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats"),
        ],
        [
            InlineKeyboardButton(text="🖼 Фото", callback_data="admin_photos"),
            InlineKeyboardButton(text="📨 Рассылка", callback_data="admin_broadcast"),
        ],
        [
            InlineKeyboardButton(text="🔙 Выйти в меню", callback_data="admin_exit"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_content_edit_menu() -> InlineKeyboardMarkup:
    """
    Меню выбора раздела для редактирования.

    Returns:
        InlineKeyboardMarkup с разделами контента
    """
    sections = [
        ("greeting", "👋 Приветствие"),
        ("about", "👤 Обо мне"),
        ("tech", "🛠 Тех. стек"),
        ("faq", "❓ FAQ"),
        ("reviews", "⭐ Отзывы"),
        ("promo", "🔥 Акции"),
        ("tariffs", "💰 Тарифы"),
        ("contact", "📝 Заказать"),
    ]

    keyboard: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []

    for section_key, section_label in sections:
        row.append(InlineKeyboardButton(text=section_label, callback_data=f"edit_content_{section_key}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []

    if row:
        keyboard.append(row)

    keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="admin_main")])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_buttons_manage_menu() -> InlineKeyboardMarkup:
    """
    Меню управления кнопками главного меню.

    Returns:
        InlineKeyboardMarkup со списком кнопок
    """
    keyboard = [
        [InlineKeyboardButton(text="✏️ Изменить названия", callback_data="btn_edit_labels")],
        [InlineKeyboardButton(text="👁️ Показать/скрыть", callback_data="btn_toggle_visibility")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_main")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_buttons_edit_list(buttons: list[tuple]) -> InlineKeyboardMarkup:
    """
    Список кнопок для редактирования названий.

    Args:
        buttons: Список кортежей (name, label, is_active)

    Returns:
        InlineKeyboardMarkup со списком кнопок для редактирования
    """
    keyboard: list[list[InlineKeyboardButton]] = []

    for name, label, is_active in buttons:
        status = "✅" if is_active else "❌"
        keyboard.append([
            InlineKeyboardButton(text=f"{status} {label}", callback_data=f"btn_edit_label_{name}")
        ])

    keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="admin_buttons")])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_button_edit_menu(button_name: str, current_label: str) -> InlineKeyboardMarkup:
    """
    Меню редактирования конкретной кнопки.

    Args:
        button_name: Ключ кнопки
        current_label: Текущее название

    Returns:
        InlineKeyboardMarkup с кнопкой отмены
    """
    keyboard = [
        [InlineKeyboardButton(text="❌ Отмена", callback_data="btn_edit_labels")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_channels_manage_menu() -> InlineKeyboardMarkup:
    """
    Меню управления каналами подписки.
    
    Returns:
        InlineKeyboardMarkup с управлением каналами
    """
    keyboard = [
        [InlineKeyboardButton(text="➕ Добавить канал", callback_data="channel_add")],
        [InlineKeyboardButton(text="🗑️ Удалить канал", callback_data="channel_remove")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_main")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_broadcast_menu() -> InlineKeyboardMarkup:
    """
    Меню рассылки сообщений.

    Returns:
        InlineKeyboardMarkup с опциями рассылки
    """
    keyboard = [
        [InlineKeyboardButton(text="📨 Отправить всем", callback_data="broadcast_start")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_main")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_back_button(callback: str) -> InlineKeyboardMarkup:
    """
    Кнопка "Назад".
    
    Args:
        callback: Callback data для кнопки
    
    Returns:
        InlineKeyboardMarkup с одной кнопкой
    """
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data=callback)]])


def get_save_cancel_buttons(section: str) -> InlineKeyboardMarkup:
    """
    Кнопки Сохранить / Отмена для редактора.
    
    Args:
        section: Ключ раздела
    
    Returns:
        InlineKeyboardMarkup с кнопками
    """
    keyboard = [
        [
            InlineKeyboardButton(text="💾 Сохранить", callback_data=f"save_content_{section}"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="admin_content"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_button_toggle_row(button_name: str, is_active: bool) -> InlineKeyboardMarkup:
    """
    Кнопка переключения видимости конкретной кнопки меню.
    
    Args:
        button_name: Ключ кнопки
        is_active: Текущий статус (активна/неактивна)
    
    Returns:
        InlineKeyboardMarkup с кнопкой переключения
    """
    action = "🔘 Скрыть" if is_active else "👁️ Показать"
    callback = f"btn_toggle_{button_name}_{0 if is_active else 1}"

    keyboard = [
        [InlineKeyboardButton(text=action, callback_data=callback)],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_buttons")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_buttons_list(buttons: list[tuple]) -> InlineKeyboardMarkup:
    """
    Список кнопок меню с индикатором активности.

    Args:
        buttons: Список кортежей (name, label, is_active)

    Returns:
        InlineKeyboardMarkup со списком кнопок
    """
    keyboard: list[list[InlineKeyboardButton]] = []

    for name, label, is_active in buttons:
        status = "✅" if is_active else "❌"
        keyboard.append([
            InlineKeyboardButton(text=f"{status} {label}", callback_data=f"btn_toggle_{name}")
        ])

    keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="admin_main")])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_photos_manage_menu() -> InlineKeyboardMarkup:
    """
    Меню управления фото.

    Returns:
        InlineKeyboardMarkup с опциями управления фото
    """
    keyboard = [
        [InlineKeyboardButton(text="👋 Фото приветствия", callback_data="photo_greeting")],
        [InlineKeyboardButton(text="🏠 Фото главного меню", callback_data="photo_main_menu")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_main")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_photo_edit_menu(photo_type: str, has_photo: bool) -> InlineKeyboardMarkup:
    """
    Меню редактирования конкретного фото.

    Args:
        photo_type: Тип фото ('greeting' или 'main_menu')
        has_photo: Есть ли уже фото

    Returns:
        InlineKeyboardMarkup с кнопками управления
    """
    photo_label = "Приветствие" if photo_type == "greeting" else "Главное меню"
    
    keyboard = [
        [InlineKeyboardButton(text="📸 Загрузить фото", callback_data=f"photo_upload_{photo_type}")],
    ]
    
    if has_photo:
        keyboard.append(
            [InlineKeyboardButton(text="👁️ Просмотреть", callback_data=f"photo_view_{photo_type}")]
        )
        keyboard.append(
            [InlineKeyboardButton(text="🗑️ Удалить фото", callback_data=f"photo_delete_{photo_type}")]
        )
    
    keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="admin_photos")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_back_to_photos_menu(photo_type: str) -> InlineKeyboardMarkup:
    """
    Кнопка возврата к меню управления фото.

    Args:
        photo_type: Тип фото

    Returns:
        InlineKeyboardMarkup с кнопкой назад
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_photos")]
    ])
