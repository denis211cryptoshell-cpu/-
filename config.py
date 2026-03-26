"""
Модуль конфигурации проекта.
Загрузка настроек из .env с валидацией через Pydantic Settings.
"""

from typing import List
from pathlib import Path
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator

# Загружаем .env вручную перед созданием класса
load_dotenv(Path(__file__).parent / ".env")


class Settings(BaseSettings):
    """Настройки приложения."""

    model_config = SettingsConfigDict(
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )

    # Telegram
    bot_token: str = Field(..., alias="BOT_TOKEN", description="Токен бота от @BotFather")
    admin_id: int = Field(..., alias="ADMIN_ID", description="Telegram ID основного администратора")
    admin_ids_raw: str = Field(
        default="",
        alias="ADMIN_IDS",
        description="Дополнительные Telegram ID администраторов (через запятую)",
    )

    # Каналы для подписки (сырое значение из .env)
    channel_ids_raw: str = Field(
        default="",
        alias="CHANNEL_IDS",
        description="Список каналов для обязательной подписки (через запятую)",
    )

    # База данных
    database_path: str = Field(
        default="data/bot.db",
        alias="DATABASE_PATH",
        description="Путь к файлу базы данных SQLite",
    )
    
    # PostgreSQL (опционально, для внешних БД)
    database_url: str | None = Field(
        default=None,
        alias="DATABASE_URL",
        description="URL подключения к PostgreSQL (Supabase, Neon и т.д.)",
    )

    # Логирование
    log_level: str = Field(
        default="INFO",
        alias="LOG_LEVEL",
        description="Уровень логирования (DEBUG, INFO, WARNING, ERROR)",
    )

    # Rate Limiting
    rate_limit_max_requests: int = Field(
        default=10,
        alias="RATE_LIMIT_MAX_REQUESTS",
        description="Максимальное количество запросов в окно времени",
    )
    rate_limit_window: int = Field(
        default=60,
        alias="RATE_LIMIT_WINDOW",
        description="Окно времени для rate limiting (в секундах)",
    )

    @field_validator("channel_ids_raw", mode="before")
    @classmethod
    def parse_channel_ids(cls, value: str) -> str:
        """Обработка пустого значения для каналов."""
        if value is None or value.strip() == "":
            return ""
        return value

    @property
    def channel_ids(self) -> List[str]:
        """Получить список каналов (разделение по запятой)."""
        if not self.channel_ids_raw or self.channel_ids_raw.strip() == "":
            return []
        return [ch.strip() for ch in self.channel_ids_raw.split(",") if ch.strip()]

    @property
    def channels_str(self) -> str:
        """Каналы как строка через запятую (для кнопок)."""
        return ", ".join(self.channel_ids) if self.channel_ids else ""

    @property
    def admin_ids(self) -> List[int]:
        """Получить список всех ID администраторов."""
        ids = [self.admin_id]  # Основной админ
        if self.admin_ids_raw and self.admin_ids_raw.strip():
            ids.extend(int(id.strip()) for id in self.admin_ids_raw.split(",") if id.strip())
        return ids

    def is_admin(self, user_id: int) -> bool:
        """Проверить, является ли пользователь администратором."""
        return user_id in self.admin_ids


# Глобальный экземпляр настроек
settings = Settings()
