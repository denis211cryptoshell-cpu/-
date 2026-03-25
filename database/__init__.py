"""
Модуль работы с базой данных.
Автоматический выбор между SQLite и PostgreSQL.
"""

from config import settings

# Автоматический выбор БД
if settings.database_url:
    # PostgreSQL (Supabase, Neon и др.)
    from database.postgres import db, init_db, get_db
    DB_TYPE = "postgresql"
else:
    # SQLite
    from database.db import db, init_db, get_db
    DB_TYPE = "sqlite"

from database.adapter import DatabaseAdapter, db_adapter

__all__ = ["get_db", "init_db", "db", "DB_TYPE", "DatabaseAdapter", "db_adapter"]
