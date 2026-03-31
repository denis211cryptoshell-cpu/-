"""
Машина состояний (FSM) для бота.
"""

from aiogram.fsm.state import State, StatesGroup


class AdminStates(StatesGroup):
    """Состояния админ-панели."""

    waiting_for_content = State()  # Ожидание нового текста контента
    waiting_for_button_name = State()  # Ожидание названия кнопки (старый формат)
    waiting_for_button_label = State()  # Ожидание нового названия кнопки
    waiting_for_channel = State()  # Ожидание канала для добавления
    waiting_for_channel_remove = State()  # Ожидание канала для удаления
    waiting_for_broadcast = State()  # Ожидание текста рассылки
    processing_invite_link = State()  # Обработка пригласительной ссылки
    
    # Состояния для управления фото
    waiting_for_greeting_photo = State()  # Ожидание фото для приветствия
    waiting_for_main_menu_photo = State()  # Ожидание фото для главного меню
