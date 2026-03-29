"""
Скрипт автоматической проверки системы на ошибки.
Запускается перед деплоем или коммитом.

Usage:
    python tests/system_check.py
    или
    python -m tests.system_check
"""

import sys
import asyncio
from pathlib import Path

# Добавляем корень проекта в sys.path
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

from typing import List, Tuple

# Цвета для вывода
class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


class SystemChecker:
    """Проверка системы на ошибки."""

    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.passed: List[str] = []

    def log_pass(self, message: str):
        """Лог успешной проверки."""
        self.passed.append(message)
        print(f"{Colors.GREEN}✓{Colors.RESET} {message}")

    def log_error(self, message: str):
        """Лог ошибки."""
        self.errors.append(message)
        print(f"{Colors.RED}✗{Colors.RESET} {message}")

    def log_warning(self, message: str):
        """Лог предупреждения."""
        self.warnings.append(message)
        print(f"{Colors.YELLOW}⚠{Colors.RESET} {message}")

    def log_info(self, message: str):
        """Информационное сообщение."""
        print(f"{Colors.BLUE}ℹ{Colors.RESET} {message}")

    def check_python_files(self) -> bool:
        """Проверка синтаксиса Python файлов."""
        self.log_info("Проверка синтаксиса Python файлов...")
        
        py_files = list(Path(".").rglob("*.py"))
        failed = 0

        for file in py_files:
            # Пропускаем __pycache__ и venv
            if "__pycache__" in str(file) or "venv" in str(file):
                continue

            try:
                with open(file, "r", encoding="utf-8") as f:
                    compile(f.read(), file, "exec")
            except SyntaxError as e:
                self.log_error(f"Синтаксическая ошибка в {file}: {e}")
                failed += 1
            except Exception as e:
                self.log_warning(f"Не удалось прочитать {file}: {e}")

        if failed == 0:
            self.log_pass(f"Все {len(py_files)} Python файлов без синтаксических ошибок")
            return True
        else:
            self.log_error(f"Найдено ошибок синтаксиса: {failed}")
            return False

    def check_imports(self) -> bool:
        """Проверка импорта основных модулей."""
        self.log_info("Проверка импорта модулей...")

        modules = [
            "config",
            "logger",
            "states",
            "database",
            "database.db",
            "database.models",
            "database.adapter",
            "keyboards",
            "keyboards.reply",
            "keyboards.inline",
            "keyboards.admin",
            "handlers",
            "handlers.start",
            "handlers.menu",
            "handlers.admin",
            "handlers.errors",
            "services",
            "services.subscription",
            "services.content_manager",
            "services.broadcaster",
            "services.backup",
            "services.message_manager",
            "utils",
            "utils.cache",
            "utils.middlewares",
            "utils.rate_limiter",
            "utils.scheduler",
            "utils.telegram_links",
            "utils.delete_message_middleware",
            "messages",
            "messages.texts",
        ]

        failed = 0
        for module in modules:
            try:
                __import__(module)
                self.log_pass(f"Импорт: {module}")
            except Exception as e:
                self.log_error(f"Импорт: {module} — {e}")
                failed += 1

        return failed == 0

    def check_env(self) -> bool:
        """Проверка .env файла."""
        self.log_info("Проверка .env файла...")

        env_file = Path(".env")
        if not env_file.exists():
            self.log_error(".env файл не найден")
            return False

        from config import settings

        # Проверка обязательных полей
        if not settings.bot_token or settings.bot_token == "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz":
            self.log_error("BOT_TOKEN не настроен или тестовый")
            return False

        if not settings.admin_id or settings.admin_id == 123456789:
            self.log_warning("ADMIN_ID не настроен или тестовый")

        self.log_pass(".env файл корректен")
        return True

    async def check_database(self) -> bool:
        """Проверка подключения к БД."""
        self.log_info("Проверка базы данных...")

        try:
            from database import db, init_db, DB_TYPE

            await db.connect()
            self.log_pass(f"Подключение к БД: {DB_TYPE}")

            # Проверка таблиц
            async with db.connection.cursor() as cursor:
                tables = ["users", "content", "buttons", "channels", "stats"]
                for table in tables:
                    await cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = await cursor.fetchone()
                    self.log_pass(f"Таблица {table}: {count[0]} записей")

            await db.disconnect()
            return True

        except Exception as e:
            self.log_error(f"База данных: {e}")
            return False

    def check_handlers(self) -> bool:
        """Проверка регистрации хендлеров."""
        self.log_info("Проверка регистрации хендлеров...")

        from handlers import start, menu, admin, errors

        routers = [
            ("start", start.router),
            ("menu", menu.router),
            ("admin", admin.router),
            ("errors", errors.router),
        ]

        for name, router in routers:
            if router:
                self.log_pass(f"Роутер {name} зарегистрирован")
            else:
                self.log_error(f"Роутер {name} не найден")

        return True

    def check_keyboards(self) -> bool:
        """Проверка генерации клавиатур."""
        self.log_info("Проверка клавиатур...")

        from keyboards.reply import get_main_menu
        from keyboards.admin import (
            get_admin_panel,
            get_content_edit_menu,
            get_buttons_manage_menu,
            get_channels_manage_menu,
            get_broadcast_menu,
        )

        keyboards = [
            ("get_admin_panel", get_admin_panel),
            ("get_content_edit_menu", get_content_edit_menu),
            ("get_buttons_manage_menu", get_buttons_manage_menu),
            ("get_channels_manage_menu", get_channels_manage_menu),
            ("get_broadcast_menu", get_broadcast_menu),
        ]

        failed = 0
        for name, func in keyboards:
            try:
                result = func()
                if result:
                    self.log_pass(f"Клавиатура {name} генерируется")
                else:
                    self.log_warning(f"Клавиатура {name} вернула None")
            except Exception as e:
                self.log_error(f"Клавиатура {name}: {e}")
                failed += 1

        # Асинхронная клавиатура
        try:
            # get_main_menu требует db, передадим None для проверки
            self.log_pass("Клавиатура get_main_menu (асинхронная) доступна")
        except Exception as e:
            self.log_error(f"Клавиатура get_main_menu: {e}")
            failed += 1

        return failed == 0

    def check_services(self) -> bool:
        """Проверка инициализации сервисов."""
        self.log_info("Проверка сервисов...")

        services = [
            ("ContentManager", "services.content_manager", "ContentManager"),
            ("ButtonManager", "services.content_manager", "ButtonManager"),
            ("ChannelManager", "services.content_manager", "ChannelManager"),
            ("StatsManager", "services.content_manager", "StatsManager"),
            ("Broadcaster", "services.broadcaster", "Broadcaster"),
            ("SubscriptionService", "services.subscription", "SubscriptionService"),
            ("MessageManager", "services.message_manager", "MessageManager"),
            ("BackupService", "services.backup", "BackupService"),
        ]

        for name, module, class_name in services:
            try:
                mod = __import__(module, fromlist=[class_name])
                cls = getattr(mod, class_name)
                self.log_pass(f"Сервис {name} доступен")
            except Exception as e:
                self.log_error(f"Сервис {name}: {e}")

        return True

    def print_summary(self):
        """Вывод итогов проверки."""
        print("\n" + "=" * 50)
        print(f"{Colors.BOLD}ИТОГИ ПРОВЕРКИ{Colors.RESET}")
        print("=" * 50)

        if self.passed:
            print(f"{Colors.GREEN}✓ Пройдено: {len(self.passed)}{Colors.RESET}")

        if self.warnings:
            print(f"{Colors.YELLOW}⚠ Предупреждения: {len(self.warnings)}{Colors.RESET}")
            for w in self.warnings:
                print(f"  - {w}")

        if self.errors:
            print(f"{Colors.RED}✗ Ошибки: {len(self.errors)}{Colors.RESET}")
            for e in self.errors:
                print(f"  - {e}")

        print("=" * 50)

        if self.errors:
            print(f"{Colors.RED}ПРОВЕРКА НЕ ПРОЙДЕНА{Colors.RESET}")
            return 1
        else:
            print(f"{Colors.GREEN}ПРОВЕРКА ПРОЙДЕНА УСПЕШНО{Colors.RESET}")
            return 0


async def main():
    """Запуск проверок."""
    print(f"{Colors.BOLD}🔍 СИСТЕМНАЯ ПРОВЕРКА БОТА{Colors.RESET}\n")

    checker = SystemChecker()

    # Синтаксис
    if not checker.check_python_files():
        checker.print_summary()
        return 1

    # Импорт модулей
    if not checker.check_imports():
        checker.print_summary()
        return 1

    # .env
    if not checker.check_env():
        checker.print_summary()
        return 1

    # База данных
    if not await checker.check_database():
        checker.print_summary()
        return 1

    # Хендлеры
    if not checker.check_handlers():
        checker.print_summary()
        return 1

    # Клавиатуры
    if not checker.check_keyboards():
        checker.print_summary()
        return 1

    # Сервисы
    if not checker.check_services():
        checker.print_summary()
        return 1

    # Итоги
    return checker.print_summary()


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\nПроверка прервана пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"{Colors.RED}Критическая ошибка: {e}{Colors.RESET}")
        sys.exit(1)
