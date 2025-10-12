# Руководство по развертыванию системы управления сервисными контрактами

## Подготовка сервера

### Системные требования

**Минимальные требования:**
- CPU: 2 ядра
- RAM: 4GB
- Диск: 50GB SSD
- ОС: Ubuntu 20.04 LTS / CentOS 8 / Windows Server 2019

**Рекомендуемые требования:**
- CPU: 4 ядра
- RAM: 8GB
- Диск: 100GB SSD
- ОС: Ubuntu 22.04 LTS

### Установка зависимостей

#### Ubuntu/Debian
```bash
# Обновление системы
sudo apt update && sudo apt upgrade -y

# Установка Node.js 18
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# Установка PostgreSQL
sudo apt install postgresql postgresql-contrib -y

# Установка дополнительных пакетов
sudo apt install git nginx certbot python3-certbot-nginx -y
```

#### CentOS/RHEL
```bash
# Установка Node.js 18
curl -fsSL https://rpm.nodesource.com/setup_18.x | sudo bash -
sudo yum install -y nodejs

# Установка PostgreSQL
sudo yum install postgresql-server postgresql-contrib -y
sudo postgresql-setup initdb
sudo systemctl enable postgresql
sudo systemctl start postgresql

# Установка дополнительных пакетов
sudo yum install git nginx certbot python3-certbot-nginx -y
```

#### Windows Server
1. Скачайте и установите Node.js 18+ с официального сайта
2. Установите PostgreSQL 12+ с официального сайта
3. Установите Git для Windows
4. Установите Nginx для Windows

## Настройка базы данных

### Создание пользователя и базы данных

```bash
# Переключение на пользователя postgres
sudo -u postgres psql

# Создание пользователя
CREATE USER service_user WITH PASSWORD 'secure_password';

# Создание базы данных
CREATE DATABASE service_contracts_db OWNER service_user;

# Предоставление прав
GRANT ALL PRIVILEGES ON DATABASE service_contracts_db TO service_user;

# Выход
\q
```

### Настройка PostgreSQL

Отредактируйте файл конфигурации PostgreSQL:

```bash
# Ubuntu/Debian
sudo nano /etc/postgresql/14/main/postgresql.conf

# CentOS/RHEL
sudo nano /var/lib/pgsql/data/postgresql.conf
```

Найдите и измените следующие параметры:
```
listen_addresses = '*'
max_connections = 100
shared_buffers = 256MB
effective_cache_size = 1GB
```

Настройте аутентификацию:
```bash
# Ubuntu/Debian
sudo nano /etc/postgresql/14/main/pg_hba.conf

# CentOS/RHEL
sudo nano /var/lib/pgsql/data/pg_hba.conf
```

Добавьте строку:
```
host    service_contracts_db    service_user    0.0.0.0/0    md5
```

Перезапустите PostgreSQL:
```bash
sudo systemctl restart postgresql
```

## Развертывание приложения

### Клонирование репозитория

```bash
# Создание директории для приложения
sudo mkdir -p /opt/service-contracts
sudo chown $USER:$USER /opt/service-contracts
cd /opt/service-contracts

# Клонирование репозитория
git clone <repository-url> .

# Установка зависимостей
npm install --production
```

### Настройка переменных окружения

Создайте файл `.env`:
```bash
nano .env
```

Добавьте следующие переменные:
```env
# База данных
DB_HOST=localhost
DB_PORT=5432
DB_NAME=service_contracts_db
DB_USER=service_user
DB_PASSWORD=secure_password

# JWT
JWT_SECRET=your_very_secure_jwt_secret_key_here

# Сервер
PORT=3000
NODE_ENV=production

# Email (опционально)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USER=your_email@gmail.com
EMAIL_PASS=your_app_password
EMAIL_FROM=your_email@gmail.com
EMAIL_TO=admin@company.com

# Пути для файлов
UPLOAD_PATH=/opt/service-contracts/uploads
DOCUMENTS_PATH=/opt/service-contracts/generated_documents
REPORTS_PATH=/opt/service-contracts/reports
```

### Инициализация базы данных

```bash
# Запуск SQL скрипта
psql -h localhost -U service_user -d service_contracts_db -f database_schema.sql

# Ввод пароля при запросе
```

### Создание директорий для файлов

```bash
mkdir -p uploads/documents
mkdir -p uploads/scans
mkdir -p generated_documents
mkdir -p reports
mkdir -p logs

# Установка прав доступа
chmod 755 uploads generated_documents reports logs
```

## Настройка Nginx

### Создание конфигурации

```bash
sudo nano /etc/nginx/sites-available/service-contracts
```

Добавьте следующую конфигурацию:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    # Редирект на HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    # SSL сертификаты
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    # SSL настройки
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;

    # Основное приложение
    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }

    # Статические файлы
    location /uploads/ {
        alias /opt/service-contracts/uploads/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Максимальный размер загружаемых файлов
    client_max_body_size 50M;
}
```

### Активация конфигурации

```bash
# Создание символической ссылки
sudo ln -s /etc/nginx/sites-available/service-contracts /etc/nginx/sites-enabled/

# Удаление дефолтной конфигурации
sudo rm /etc/nginx/sites-enabled/default

# Проверка конфигурации
sudo nginx -t

# Перезапуск Nginx
sudo systemctl restart nginx
```

## Настройка SSL сертификата

### Получение Let's Encrypt сертификата

```bash
# Установка certbot
sudo apt install certbot python3-certbot-nginx -y

# Получение сертификата
sudo certbot --nginx -d your-domain.com

# Настройка автообновления
sudo crontab -e
# Добавьте строку:
# 0 12 * * * /usr/bin/certbot renew --quiet
```

## Настройка systemd сервиса

### Создание сервиса

```bash
sudo nano /etc/systemd/system/service-contracts.service
```

Добавьте следующую конфигурацию:
```ini
[Unit]
Description=Service Contracts Management System
After=network.target postgresql.service

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/service-contracts
ExecStart=/usr/bin/node server.js
Restart=always
RestartSec=10
Environment=NODE_ENV=production

# Логирование
StandardOutput=journal
StandardError=journal
SyslogIdentifier=service-contracts

[Install]
WantedBy=multi-user.target
```

### Активация сервиса

```bash
# Перезагрузка systemd
sudo systemctl daemon-reload

# Включение автозапуска
sudo systemctl enable service-contracts

# Запуск сервиса
sudo systemctl start service-contracts

# Проверка статуса
sudo systemctl status service-contracts
```

## Настройка бэкапов

### Создание скрипта бэкапа

```bash
sudo nano /opt/scripts/backup-service-contracts.sh
```

Добавьте следующий код:
```bash
#!/bin/bash

# Настройки
BACKUP_DIR="/opt/backups/service-contracts"
DB_NAME="service_contracts_db"
DB_USER="service_user"
APP_DIR="/opt/service-contracts"
DATE=$(date +%Y%m%d_%H%M%S)

# Создание директории для бэкапов
mkdir -p $BACKUP_DIR

# Бэкап базы данных
pg_dump -h localhost -U $DB_USER $DB_NAME > $BACKUP_DIR/db_backup_$DATE.sql

# Бэкап файлов приложения
tar -czf $BACKUP_DIR/files_backup_$DATE.tar.gz -C $APP_DIR uploads generated_documents reports

# Удаление старых бэкапов (старше 30 дней)
find $BACKUP_DIR -name "*.sql" -mtime +30 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete

echo "Backup completed: $DATE"
```

### Настройка прав и cron

```bash
# Установка прав на выполнение
sudo chmod +x /opt/scripts/backup-service-contracts.sh

# Добавление в cron (ежедневно в 2:00)
sudo crontab -e
# Добавьте строку:
# 0 2 * * * /opt/scripts/backup-service-contracts.sh
```

## Мониторинг и логи

### Настройка логирования

```bash
# Создание директории для логов
sudo mkdir -p /var/log/service-contracts
sudo chown www-data:www-data /var/log/service-contracts

# Настройка logrotate
sudo nano /etc/logrotate.d/service-contracts
```

Добавьте:
```
/var/log/service-contracts/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 www-data www-data
    postrotate
        systemctl reload service-contracts
    endscript
}
```

### Мониторинг системы

```bash
# Установка htop для мониторинга
sudo apt install htop -y

# Мониторинг логов в реальном времени
sudo journalctl -u service-contracts -f

# Проверка использования диска
df -h

# Проверка использования памяти
free -h
```

## Настройка файрвола

### UFW (Ubuntu)

```bash
# Включение UFW
sudo ufw enable

# Разрешение SSH
sudo ufw allow ssh

# Разрешение HTTP и HTTPS
sudo ufw allow 80
sudo ufw allow 443

# Проверка статуса
sudo ufw status
```

### Firewalld (CentOS)

```bash
# Включение firewalld
sudo systemctl enable firewalld
sudo systemctl start firewalld

# Разрешение HTTP и HTTPS
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https

# Перезагрузка правил
sudo firewall-cmd --reload
```

## Тестирование развертывания

### Проверка сервисов

```bash
# Проверка статуса всех сервисов
sudo systemctl status postgresql
sudo systemctl status nginx
sudo systemctl status service-contracts

# Проверка портов
sudo netstat -tlnp | grep :3000
sudo netstat -tlnp | grep :80
sudo netstat -tlnp | grep :443
```

### Проверка веб-интерфейса

1. Откройте браузер и перейдите по адресу `https://your-domain.com`
2. Войдите с учетными данными по умолчанию (admin/admin)
3. Смените пароль в настройках
4. Проверьте основные функции системы

### Проверка API

```bash
# Тест API
curl -X GET https://your-domain.com/api/contracts \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## Обновление системы

### Процедура обновления

```bash
# 1. Создание бэкапа
sudo /opt/scripts/backup-service-contracts.sh

# 2. Остановка сервиса
sudo systemctl stop service-contracts

# 3. Обновление кода
cd /opt/service-contracts
git pull origin main

# 4. Установка новых зависимостей
npm install --production

# 5. Запуск миграций (если есть)
# psql -h localhost -U service_user -d service_contracts_db -f migrations/update.sql

# 6. Запуск сервиса
sudo systemctl start service-contracts

# 7. Проверка статуса
sudo systemctl status service-contracts
```

## Устранение неполадок

### Частые проблемы

#### Сервис не запускается
```bash
# Проверка логов
sudo journalctl -u service-contracts -n 50

# Проверка конфигурации
sudo systemctl status service-contracts
```

#### Ошибки базы данных
```bash
# Проверка подключения
psql -h localhost -U service_user -d service_contracts_db

# Проверка логов PostgreSQL
sudo tail -f /var/log/postgresql/postgresql-14-main.log
```

#### Проблемы с Nginx
```bash
# Проверка конфигурации
sudo nginx -t

# Проверка логов
sudo tail -f /var/log/nginx/error.log
```

### Восстановление из бэкапа

```bash
# Остановка сервиса
sudo systemctl stop service-contracts

# Восстановление базы данных
psql -h localhost -U service_user -d service_contracts_db < /opt/backups/service-contracts/db_backup_YYYYMMDD_HHMMSS.sql

# Восстановление файлов
tar -xzf /opt/backups/service-contracts/files_backup_YYYYMMDD_HHMMSS.tar.gz -C /opt/service-contracts

# Запуск сервиса
sudo systemctl start service-contracts
```

## Безопасность

### Рекомендации по безопасности

1. **Регулярно обновляйте систему:**
```bash
sudo apt update && sudo apt upgrade -y
```

2. **Используйте сильные пароли:**
```bash
# Генерация случайного пароля
openssl rand -base64 32
```

3. **Настройте fail2ban:**
```bash
sudo apt install fail2ban -y
sudo systemctl enable fail2ban
```

4. **Ограничьте доступ к базе данных:**
```bash
# В pg_hba.conf разрешите доступ только с localhost
host    service_contracts_db    service_user    127.0.0.1/32    md5
```

5. **Настройте мониторинг безопасности:**
```bash
# Установка AIDE для мониторинга файлов
sudo apt install aide -y
sudo aideinit
```

## Заключение

После выполнения всех шагов у вас будет полностью функциональная система управления сервисными контрактами, развернутая в продакшене с:

- ✅ Веб-интерфейсом для Windows
- ✅ Мобильным приложением для Android
- ✅ Автоматическими бэкапами
- ✅ SSL сертификатом
- ✅ Мониторингом и логированием
- ✅ Системой уведомлений
- ✅ Отчетностью и аналитикой

Система готова к использованию в производственной среде!