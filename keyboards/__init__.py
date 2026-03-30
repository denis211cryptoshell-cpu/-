"""
Модуль клавиатур (reply и inline).
"""

from keyboards.reply import get_main_menu
from keyboards.inline import get_channel_buttons, get_content_buttons
from keyboards.admin import (
    get_admin_panel,
    get_content_edit_menu,
    get_buttons_manage_menu,
    get_channels_manage_menu,
    get_broadcast_menu,
    get_back_button,
    get_save_cancel_buttons,
)

__all__ = [
    "get_main_menu",
    "get_channel_buttons",
    "get_content_buttons",
    "get_admin_panel",
    "get_content_edit_menu",
    "get_buttons_manage_menu",
    "get_channels_manage_menu",
    "get_broadcast_menu",
    "get_back_button",
    "get_save_cancel_buttons",
]
