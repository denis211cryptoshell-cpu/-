#!/bin/bash

# ============================================================================
# Скрипт развёртывания Telegram Bot на VPS через SSH
# ============================================================================
# Использование: ./deploy.sh <user>@<host>
# Пример: ./deploy.sh root@192.168.1.100
# ============================================================================

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Проверка аргументов
if [ -z "$1" ]; then
    echo -e "${RED}Ошибка: Укажите SSH пользователя и хост${NC}"
    echo "Использование: $0 <user>@<host>"
    echo "Пример: $0 root@192.168.1.100"
    exit 1
fi

SSH_USER_HOST=$1
PROJECT_NAME="telegram-bot"
REMOTE_DIR="/opt/$PROJECT_NAME"

# Функция для вывода сообщений
log_info() {
    echo -e "${BLUE}>>> $1${NC}"
}

log_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

log_error() {
    echo -e "${RED}✗ $1${NC}"
}

# ============================================================================
# Шаг 1: Проверка подключений
# ============================================================================
log_info "Проверка SSH подключения к $SSH_USER_HOST..."

if ! ssh -o ConnectTimeout=5 -o BatchMode=yes "$SSH_USER_HOST" "exit" 2>/dev/null; then
    log_error "Не удалось подключиться по SSH. Проверьте:"
    echo "  1. SSH ключи: ssh-copy-id $SSH_USER_HOST"
    echo "  2. Или используйте пароль (не рекомендуется для скриптов)"
    exit 1
fi
log_success "SSH подключение успешно"

# ============================================================================
# Шаг 2: Проверка Docker на удалённом сервере
# ============================================================================
log_info "Проверка Docker на удалённом сервере..."

if ! ssh "$SSH_USER_HOST" "docker --version" 2>/dev/null; then
    log_error "Docker не установлен на сервере"
    echo "Установите Docker:"
    echo "  curl -fsSL https://get.docker.com | sh"
    exit 1
fi
log_success "Docker установлен"

# ============================================================================
# Шаг 3: Проверка Docker Compose
# ============================================================================
log_info "Проверка Docker Compose..."

if ! ssh "$SSH_USER_HOST" "docker compose version" 2>/dev/null; then
    log_warning "Docker Compose v2 не найден, пробуем v1..."
    if ! ssh "$SSH_USER_HOST" "docker-compose --version" 2>/dev/null; then
        log_error "Docker Compose не установлен"
        exit 1
    fi
    COMPOSE_CMD="docker-compose"
else
    COMPOSE_CMD="docker compose"
fi
log_success "Docker Compose установлен ($COMPOSE_CMD)"

# ============================================================================
# Шаг 4: Создание директории проекта
# ============================================================================
log_info "Создание директории проекта на сервере..."

ssh "$SSH_USER_HOST" "sudo mkdir -p $REMOTE_DIR"
ssh "$SSH_USER_HOST" "sudo chown \$USER:\$USER $REMOTE_DIR"
log_success "Директория создана: $REMOTE_DIR"

# ============================================================================
# Шаг 5: Копирование файлов на сервер
# ============================================================================
log_info "Копирование файлов на сервер..."

# Копируем только необходимые файлы
rsync -avz --exclude-from='.dockerignore' \
    ./ \
    "$SSH_USER_HOST:$REMOTE_DIR/"

log_success "Файлы скопированы"

# ============================================================================
# Шаг 6: Создание .env файла
# ============================================================================
log_info "Проверка .env файла..."

if ssh "$SSH_USER_HOST" "test -f $REMOTE_DIR/.env" 2>/dev/null; then
    log_warning ".env файл уже существует на сервере"
    read -p "Перезаписать? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        scp .env.example "$SSH_USER_HOST:$REMOTE_DIR/.env"
        log_warning "Скопирован .env.example. Отредактируйте .env на сервере!"
        log_info "SSH подключитесь и заполните .env:"
        echo "  ssh $SSH_USER_HOST"
        echo "  cd $REMOTE_DIR"
        echo "  nano .env"
    fi
else
    scp .env.example "$SSH_USER_HOST:$REMOTE_DIR/.env"
    log_success ".env файл создан"
    log_warning "Отредактируйте .env на сервере перед запуском!"
    log_info "SSH подключитесь и заполните:"
    echo "  ssh $SSH_USER_HOST"
    echo "  cd $REMOTE_DIR"
    echo "  nano .env"
fi

# ============================================================================
# Шаг 7: Сборка и запуск контейнеров
# ============================================================================
log_info "Сборка Docker образов..."

ssh "$SSH_USER_HOST" "cd $REMOTE_DIR && $COMPOSE_CMD build"

log_success "Образы собраны"

# ============================================================================
# Шаг 8: Запуск контейнеров
# ============================================================================
log_info "Запуск контейнеров..."

ssh "$SSH_USER_HOST" "cd $REMOTE_DIR && $COMPOSE_CMD up -d"

log_success "Контейнеры запущены"

# ============================================================================
# Шаг 9: Проверка статуса
# ============================================================================
log_info "Проверка статуса контейнеров..."

ssh "$SSH_USER_HOST" "cd $REMOTE_DIR && $COMPOSE_CMD ps"

# ============================================================================
# Шаг 10: Вывод логов
# ============================================================================
log_info "Последние логи бота:"

ssh "$SSH_USER_HOST" "cd $REMOTE_DIR && $COMPOSE_CMD logs --tail=20 bot"

# ============================================================================
# Завершение
# ============================================================================
echo ""
log_success "Развёртывание завершено!"
echo ""
echo "Полезные команды:"
echo "  ssh $SSH_USER_HOST"
echo "  cd $REMOTE_DIR"
echo ""
echo "  # Просмотр логов"
echo "  $COMPOSE_CMD logs -f bot"
echo ""
echo "  # Перезапуск бота"
echo "  $COMPOSE_CMD restart bot"
echo ""
echo "  # Остановка бота"
echo "  $COMPOSE_CMD down"
echo ""
echo "  # Обновление"
echo "  git pull && $COMPOSE_CMD up -d --build"
echo ""
