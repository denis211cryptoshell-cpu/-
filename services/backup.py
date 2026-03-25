"""
Сервис автоматического резервного копирования БД.

Создаёт бекапы раз в сутки в 00:00.
Хранит последние 5 бекапов.
"""

import shutil
from pathlib import Path
from datetime import datetime
from typing import List

from logger import logger


class BackupService:
    """
    Сервис управления бекапами базы данных.
    """

    def __init__(
        self,
        db_path: str = "data/bot.db",
        backup_dir: str = "data/backups",
        max_backups: int = 5,
    ):
        self.db_path = Path(db_path)
        self.backup_dir = Path(backup_dir)
        self.max_backups = max_backups

    def create_backup(self) -> Path | None:
        """
        Создать резервную копию БД.

        Returns:
            Путь к файлу бекапа или None если ошибка
        """
        try:
            # Создаём директорию для бекапов
            self.backup_dir.mkdir(parents=True, exist_ok=True)

            # Формируем имя файла с датой и временем
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"bot_{timestamp}.db"
            backup_path = self.backup_dir / backup_filename

            # Копируем файл БД
            shutil.copy2(self.db_path, backup_path)

            logger.info(f"✅ Создан бекап: {backup_path}")

            # Удаляем старые бекапы
            self._cleanup_old_backups()

            return backup_path

        except Exception as e:
            logger.error(f"❌ Ошибка создания бекапа: {e}")
            return None

    def _cleanup_old_backups(self) -> None:
        """
        Удалить старые бекапы, оставляя только последние max_backups.
        """
        try:
            backups = self._get_all_backups()

            if len(backups) > self.max_backups:
                # Сортируем по дате (старые первые)
                backups_sorted = sorted(backups, key=lambda p: p.stat().st_mtime)
                
                # Удаляем лишние
                to_delete = backups_sorted[:len(backups) - self.max_backups]
                
                for backup_file in to_delete:
                    backup_file.unlink()
                    logger.debug(f"Удалён старый бекап: {backup_file}")

        except Exception as e:
            logger.error(f"Ошибка очистки старых бекапов: {e}")

    def _get_all_backups(self) -> List[Path]:
        """
        Получить список всех файлов бекапов.

        Returns:
            Список путей к файлам бекапов
        """
        if not self.backup_dir.exists():
            return []

        return list(self.backup_dir.glob("bot_*.db"))

    def get_backups_list(self) -> List[dict]:
        """
        Получить информацию о всех бекапах.

        Returns:
            Список словарей с информацией о бекапах
        """
        backups = self._get_all_backups()
        result = []

        for backup_file in sorted(backups, key=lambda p: p.stat().st_mtime, reverse=True):
            stat = backup_file.stat()
            result.append({
                "filename": backup_file.name,
                "path": str(backup_file),
                "size": stat.st_size,
                "created": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            })

        return result

    def restore_from_backup(self, backup_filename: str) -> bool:
        """
        Восстановить БД из бекапа.

        Args:
            backup_filename: Имя файла бекапа

        Returns:
            True если успешно
        """
        try:
            backup_path = self.backup_dir / backup_filename

            if not backup_path.exists():
                logger.error(f"Бекап не найден: {backup_filename}")
                return False

            # Копируем бекап на место основной БД
            shutil.copy2(backup_path, self.db_path)

            logger.info(f"✅ БД восстановлена из бекапа: {backup_filename}")
            return True

        except Exception as e:
            logger.error(f"❌ Ошибка восстановления из бекапа: {e}")
            return False

    def delete_backup(self, backup_filename: str) -> bool:
        """
        Удалить конкретный бекап.

        Args:
            backup_filename: Имя файла бекапа

        Returns:
            True если успешно
        """
        try:
            backup_path = self.backup_dir / backup_filename

            if not backup_path.exists():
                logger.error(f"Бекап не найден: {backup_filename}")
                return False

            backup_path.unlink()
            logger.info(f"✅ Бекап удалён: {backup_filename}")
            return True

        except Exception as e:
            logger.error(f"❌ Ошибка удаления бекапа: {e}")
            return False


# Глобальный экземпляр сервиса
backup_service = BackupService()
