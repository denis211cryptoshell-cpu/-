"""
Inline-клавиатуры (под сообщениями).
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import List, Optional, Dict


def get_channel_buttons(channels: List[str], invite_links: Optional[Dict[str, str]] = None) -> InlineKeyboardMarkup:
    """
    Кнопки с пригласительными ссылками на каналы для подписки.

    Args:
        channels: Список каналов (ID или @username)
        invite_links: Словарь пригласительных ссылок {channel_id: link}
    """
    keyboard: list[list[InlineKeyboardButton]] = []

    for channel in channels:
        # Получаем ссылку из кэша или формируем стандартную
        invite_url = None
        if invite_links:
            invite_url = invite_links.get(channel)
        
        if not invite_url:
            # Фолбэк: обычная ссылка
            if channel.startswith("@"):
                invite_url = f"https://t.me/{channel}"
            elif channel.startswith("-100"):
                invite_url = f"https://t.me/+{channel.lstrip('-')}"
            else:
                invite_url = f"https://t.me/{channel.lstrip('@')}"

        # Формируем отображаемое имя
        display_name = channel.replace("@", "")
        if channel.startswith("-100"):
            display_name = f"Канал {channel[-6:]}"

        keyboard.append(
            [InlineKeyboardButton(text=f"📢 {display_name}", url=invite_url)]
        )

    keyboard.append([InlineKeyboardButton(text="✅ Я подписался", callback_data="check_subscription")])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_content_buttons(sections: List[tuple]) -> InlineKeyboardMarkup:
    """Кнопки для выбора раздела контента (админка)."""
    keyboard: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []

    for section_key, section_label in sections:
        row.append(InlineKeyboardButton(text=section_label, callback_data=f"edit_content_{section_key}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []

    if row:
        keyboard.append(row)

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_preview_buttons(section: str) -> InlineKeyboardMarkup:
    """Кнопки после предпросмотра контента."""
    keyboard = [
        [
            InlineKeyboardButton(text="💾 Сохранить", callback_data=f"save_content_{section}"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_edit"),
        ],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_content")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_yes_no_buttons(yes_callback: str, no_callback: str) -> InlineKeyboardMarkup:
    """Универсальные кнопки Да/Нет."""
    keyboard = [
        [
            InlineKeyboardButton(text="✅ Да", callback_data=yes_callback),
            InlineKeyboardButton(text="❌ Нет", callback_data=no_callback),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_view_result_button(section: str) -> InlineKeyboardMarkup:
    """Кнопка просмотра результата после сохранения."""
    keyboard = [
        [InlineKeyboardButton(text="👁️ Просмотреть", callback_data=f"view_{section}")],
        [InlineKeyboardButton(text="🔙 В админку", callback_data="admin_main")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
