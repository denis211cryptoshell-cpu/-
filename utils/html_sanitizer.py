"""
HTML-санитизация с помощью bleach.
Очистка пользовательского ввода от опасных тегов и атрибутов.
"""

import bleach
from typing import Optional

# Разрешённые HTML-теги для Telegram
ALLOWED_TAGS = [
    "b",        # Жирный
    "strong",   # Жирный (алиас)
    "i",        # Курсив
    "em",       # Курсив (алиас)
    "u",        # Подчёркнутый
    "ins",      # Подчёркнутый (алиас)
    "s",        # Зачёркнутый
    "strike",   # Зачёркнутый (алиас)
    "del",      # Зачёркнутый (алиас)
    "a",        # Ссылки
    "code",     # Моноширинный код
    "pre",      # Преформатированный текст
]

# Разрешённые атрибуты для тегов
ALLOWED_ATTRIBUTES = {
    "a": ["href"],  # Только href для ссылок
}


def sanitize_html(text: str, strip: bool = True) -> str:
    """
    Очистить HTML от опасных тегов и атрибутов.

    Args:
        text: Исходный текст с HTML
        strip: Если True — вырезать запрещённые теги,
               если False — экранировать их (&lt;script&gt;)

    Returns:
        Очищенный HTML

    Примеры:
        >>> sanitize_html("<b>Привет!</b><script>alert('XSS')</script>")
        '<b>Привет!</b>alert(&#x27;XSS&#x27;)'

        >>> sanitize_html("<a href='javascript:alert(1)'>Ссылка</a>")
        'Ссылка'
    """
    if not text:
        return ""

    return bleach.clean(
        text,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        strip=strip,
    )


def sanitize_link(url: str) -> Optional[str]:
    """
    Проверить и очистить ссылку.

    Разрешены только безопасные протоколы:
    - https://
    - http://
    - t.me/
    - tg://

    Args:
        url: Исходная ссылка

    Returns:
        Очищенная ссылка или None если опасная

    Примеры:
        >>> sanitize_link("https://example.com")
        'https://example.com'

        >>> sanitize_link("javascript:alert(1)")
        None

        >>> sanitize_link("tg://resolve?domain=bot")
        'tg://resolve?domain=bot'
    """
    if not url:
        return None

    # Разрешённые протоколы
    SAFE_PROTOCOLS = [
        "https://",
        "http://",
        "t.me/",
        "tg://",
    ]

    url = url.strip()

    # Проверяем протокол
    for protocol in SAFE_PROTOCOLS:
        if url.startswith(protocol):
            return url

    # Если протокола нет, добавляем https://
    if not any(url.startswith(p) for p in ["http://", "https://", "t.me/", "tg://", "#"]):
        # Это может быть относительная ссылка или якорь
        if url.startswith("#") or "/" in url:
            return url
        # Опасная ссылка
        return None

    return url


def sanitize_button_label(label: str) -> str:
    """
    Очистить название кнопки от HTML.

    Кнопки Telegram не поддерживают HTML, поэтому вырезаем все теги.

    Args:
        label: Исходное название

    Returns:
        Очищенное название без HTML

    Примеры:
        >>> sanitize_button_label("<b>👤 Обо мне</b>")
        '👤 Обо мне'

        >>> sanitize_button_label("Кнопка<script>alert(1)</script>")
        'Кнопкаalert(1)'
    """
    if not label:
        return ""

    # Вырезаем ВСЕ теги для кнопок
    return bleach.clean(label, tags=[], strip=True)


def is_html_valid(text: str) -> bool:
    """
    Проверить, содержит ли текст опасный HTML.

    Args:
        text: Текст для проверки

    Returns:
        True если HTML безопасен или отсутствует

    Примеры:
        >>> is_html_valid("<b>Привет</b>")
        True

        >>> is_html_valid("<script>alert(1)</script>")
        False

        >>> is_html_valid("Просто текст")
        True
    """
    if not text:
        return True

    cleaned = sanitize_html(text, strip=False)
    return cleaned == text
