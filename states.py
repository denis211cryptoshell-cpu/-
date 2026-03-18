"""
Машина состояний (FSM) для бота.
"""

from aiogram.fsm.state import State, StatesGroup


class AdminStates(StatesGroup):
    """Состояния админ-панели."""

    waiting_for_content = State()  # Ожидание нового текста контента
    waiting_for_button_name = State()  # Ожидание названия кнопки
    waiting_for_channel = State()  # Ожидание канала для добавления
    waiting_for_channel_remove = State()  # Ожидание канала для удаления
    waiting_for_broadcast = State()  # Ожидание текста рассылки
