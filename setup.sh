#!/bin/bash

# Завершать скрипт при ошибках
set -e

# Функция для получения внешнего IP сервера
get_ip() {
    local ip
    ip=$(curl -s https://ifconfig.me || curl -s https://ipify.org || echo "IP_NOT_FOUND")
    echo "$ip"
}

# Функция для создания файла servers.json
create_json() {
    local ip=$1
    local user=$2
    local pass=$3
    local name=$4

    cat <<EOF > servers.json
{
    "1":{
        "name":"$name",
        "ip":"$ip",
        "login":"$user",
        "key":"$pass",
        "prtkl":"ss",
        "location":"just here",
        "max_amount":10
    }
}
EOF
    echo -e "\n[+] Файл servers.json успешно создан в текущей директории."
}

echo "=== Скрипт настройки Shadowsocks ==="
read -p "Установить shadowsocks-libev на этот сервер для теста? (да/нет): " answer

# Приводим ответ к нижнему регистру для надежности
answer=$(echo "$answer" | tr '[:upper:]' '[:lower:]')

if [[ "$answer" == "да" || "$answer" == "y" || "$answer" == "yes" ]]; then
    echo -e "\n[1] Обновление пакетов и установка shadowsocks-libev..."
#    sudo apt update
#    sudo apt install -y shadowsocks-libev curl

    echo -e "\n[2] Создание директории для ACL..."
    sudo mkdir -p /etc/shadowsocks-libev/acl

    echo -e "\n[3] Скачивание файла server_block_chn.acl..."
    # Скачиваем именно raw-версию файла, чтобы не скачался HTML-код гитхаба
    sudo curl -L "https://raw.githubusercontent.com/shadowsocks/shadowsocks-c/master/acl/server_block_local.acl" -o /etc/shadowsocks-libev/acl/server_block_local.acl

    echo -e "\n[4] Сбор данных для servers.json..."
    server_ip=$(get_ip)
    current_user=$(whoami)

    # Запрашиваем пароль от SSH (ввод скрывается для безопасности)
    read -sp "Введите пароль пользователя $current_user (для SSH-доступа бота): " ssh_password
    echo "" # Перенос строки после скрытого ввода

    create_json "$server_ip" "$current_user" "$ssh_password" "for test"

else
    echo -e "\nШаг установки пропущен. Пожалуйста, введите данные существующего сервера Shadowsocks."
    
    read -p "Введите IP сервера: " user_ip
    read -p "Введите имя пользователя (логин): " user_login
    read -p "Введите пароль (ключ): " user_key
    read -p "Введите название подключения (например: my server): " user_name

    # Если имя не введено, ставим дефолтное
    if [ -z "$user_name" ]; then user_name="existing server"; fi

    create_json "$user_ip" "$user_login" "$user_key" "$user_name"
fi

echo -e "\n Настройка окружения Python и установка зависимостей..."

# Устанавливаем системные пакеты для виртуального окружения и pip
sudo apt update
sudo apt install -y python3-venv python3-pip

# Создаем виртуальное окружение в папке со скриптом
python3 -m venv venv

# Активируем виртуальное окружение
source venv/bin/activate

# Обновляем pip внутри окружения (рекомендуется)
pip install --upgrade pip

# Устанавливаем внешние библиотеки для бота
pip install aiogram fabric

# Деактивируем виртуальное окружение
deactivate

echo -e "\n[+] Виртуальное окружение venv успешно создано, библиотеки установлены."

echo -e "\n Конфигурация Telegram-бота и создание Systemd-сервиса..."

# Запрашиваем токен и ID администраторов
read -p "Введите токен вашего Telegram-бота: " bot_token
read -p "Введите ID администраторов через запятую (например: 123456,789012): " admin_ids

# Автоматически определяем текущего пользователя и путь к папке
current_user=$(whoami)
script_dir=$(pwd)

echo "Создание файла службы /etc/systemd/system/shadowsockstg.service..."

# Создаем файл systemd-сервиса
sudo tee /etc/systemd/system/shadowsockstg.service > /dev/null <<EOF
[Unit]
Description=Telegram Bot
After=network.target

[Service]
Type=simple
User=$current_user
WorkingDirectory=$script_dir
ExecStart=$script_dir/venv/bin/python bot.py
Environment="BOT_TOKEN=$bot_token"
Environment="ADMIN_IDS=$admin_ids"
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Перезапускаем демон systemd, чтобы он увидел новый сервис
#sudo systemctl daemon-reload

# Включаем автозапуск сервиса при старте системы
#sudo systemctl enable shadowsockstg.service

echo -e "\n[+] Systemd-сервис успешно создан и добавлен в автозапуск."
echo "Управлять ботом можно командами:"
echo "  Запуск:   sudo systemctl start shadowsockstg"
echo "  Остановка: sudo systemctl stop shadowsockstg"
echo "  Статус:    sudo systemctl status shadowsockstg"
