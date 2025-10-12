// Система уведомлений и напоминаний для управления сервисными контрактами

const { Pool } = require('pg');
const nodemailer = require('nodemailer');
const cron = require('node-cron');
const moment = require('moment');

class NotificationSystem {
    constructor(dbConfig, emailConfig = {}) {
        this.pool = new Pool(dbConfig);
        this.emailConfig = emailConfig;
        this.setupEmailTransporter();
        this.setupCronJobs();
    }

    setupEmailTransporter() {
        if (this.emailConfig.host) {
            this.transporter = nodemailer.createTransporter({
                host: this.emailConfig.host,
                port: this.emailConfig.port || 587,
                secure: false,
                auth: {
                    user: this.emailConfig.user,
                    pass: this.emailConfig.pass
                }
            });
        }
    }

    setupCronJobs() {
        // Проверка дефицита материалов каждый день в 9:00
        cron.schedule('0 9 * * *', () => {
            this.checkMaterialsDeficit();
        });

        // Проверка просроченных заказов каждый день в 10:00
        cron.schedule('0 10 * * *', () => {
            this.checkOverdueOrders();
        });

        // Проверка истекающих контрактов каждый день в 11:00
        cron.schedule('0 11 * * *', () => {
            this.checkExpiringContracts();
        });

        // Проверка командировок каждый день в 12:00
        cron.schedule('0 12 * * *', () => {
            this.checkBusinessTrips();
        });

        // Проверка финансовых операций каждый день в 13:00
        cron.schedule('0 13 * * *', () => {
            this.checkFinancialOperations();
        });
    }

    // Проверка дефицита материалов
    async checkMaterialsDeficit() {
        try {
            const query = `
                SELECT 
                    m.material_code,
                    m.name,
                    m.unit,
                    COALESCE(ws.quantity, 0) as stock_quantity,
                    COALESCE(ws.reserved_quantity, 0) as reserved_quantity,
                    COALESCE(ws.quantity, 0) - COALESCE(ws.reserved_quantity, 0) as available_quantity,
                    SUM(om.required_quantity) as total_required
                FROM materials m
                LEFT JOIN warehouse_stock ws ON m.id = ws.material_id
                LEFT JOIN order_materials om ON m.id = om.material_id
                LEFT JOIN orders o ON om.order_id = o.id
                WHERE o.status IN ('pending', 'in_progress')
                GROUP BY m.id, m.material_code, m.name, m.unit, ws.quantity, ws.reserved_quantity
                HAVING COALESCE(ws.quantity, 0) - COALESCE(ws.reserved_quantity, 0) < SUM(om.required_quantity)
                ORDER BY (SUM(om.required_quantity) - (COALESCE(ws.quantity, 0) - COALESCE(ws.reserved_quantity, 0))) DESC
            `;

            const result = await this.pool.query(query);
            
            if (result.rows.length > 0) {
                const message = this.formatMaterialsDeficitMessage(result.rows);
                await this.createNotification('materials_deficit', 'Дефицит материалов', message);
                
                if (this.transporter) {
                    await this.sendEmailNotification('Дефицит материалов', message);
                }
            }
        } catch (error) {
            console.error('Ошибка проверки дефицита материалов:', error);
        }
    }

    // Проверка просроченных заказов
    async checkOverdueOrders() {
        try {
            const query = `
                SELECT o.*, c.contract_number, c.customer_name
                FROM orders o
                LEFT JOIN contracts c ON o.contract_id = c.id
                WHERE o.status IN ('pending', 'in_progress')
                AND o.order_date < CURRENT_DATE - INTERVAL '7 days'
                ORDER BY o.order_date ASC
            `;

            const result = await this.pool.query(query);
            
            if (result.rows.length > 0) {
                const message = this.formatOverdueOrdersMessage(result.rows);
                await this.createNotification('overdue_orders', 'Просроченные заказы', message);
                
                if (this.transporter) {
                    await this.sendEmailNotification('Просроченные заказы', message);
                }
            }
        } catch (error) {
            console.error('Ошибка проверки просроченных заказов:', error);
        }
    }

    // Проверка истекающих контрактов
    async checkExpiringContracts() {
        try {
            const query = `
                SELECT *
                FROM contracts
                WHERE status = 'active'
                AND end_date IS NOT NULL
                AND end_date <= CURRENT_DATE + INTERVAL '30 days'
                ORDER BY end_date ASC
            `;

            const result = await this.pool.query(query);
            
            if (result.rows.length > 0) {
                const message = this.formatExpiringContractsMessage(result.rows);
                await this.createNotification('expiring_contracts', 'Истекающие контракты', message);
                
                if (this.transporter) {
                    await this.sendEmailNotification('Истекающие контракты', message);
                }
            }
        } catch (error) {
            console.error('Ошибка проверки истекающих контрактов:', error);
        }
    }

    // Проверка командировок
    async checkBusinessTrips() {
        try {
            // Проверка командировок, которые должны начаться завтра
            const tomorrowQuery = `
                SELECT bt.*, e.full_name as employee_name, o.order_number, c.contract_number
                FROM business_trips bt
                LEFT JOIN employees e ON bt.employee_id = e.id
                LEFT JOIN orders o ON bt.order_id = o.id
                LEFT JOIN contracts c ON o.contract_id = c.id
                WHERE bt.status = 'planned'
                AND bt.start_date = CURRENT_DATE + INTERVAL '1 day'
            `;

            const tomorrowResult = await this.pool.query(tomorrowQuery);
            
            if (tomorrowResult.rows.length > 0) {
                const message = this.formatBusinessTripsMessage(tomorrowResult.rows, 'завтра');
                await this.createNotification('business_trips_tomorrow', 'Командировки завтра', message);
            }

            // Проверка командировок, которые должны закончиться завтра
            const endingQuery = `
                SELECT bt.*, e.full_name as employee_name, o.order_number, c.contract_number
                FROM business_trips bt
                LEFT JOIN employees e ON bt.employee_id = e.id
                LEFT JOIN orders o ON bt.order_id = o.id
                LEFT JOIN contracts c ON o.contract_id = c.id
                WHERE bt.status = 'in_progress'
                AND bt.end_date = CURRENT_DATE + INTERVAL '1 day'
            `;

            const endingResult = await this.pool.query(endingQuery);
            
            if (endingResult.rows.length > 0) {
                const message = this.formatBusinessTripsMessage(endingResult.rows, 'заканчиваются завтра');
                await this.createNotification('business_trips_ending', 'Командировки заканчиваются', message);
            }
        } catch (error) {
            console.error('Ошибка проверки командировок:', error);
        }
    }

    // Проверка финансовых операций
    async checkFinancialOperations() {
        try {
            // Проверка контрактов с недостаточным финансированием
            const query = `
                SELECT 
                    c.contract_number,
                    c.customer_name,
                    c.total_amount,
                    COALESCE(SUM(CASE WHEN fo.operation_type = 'advance' THEN fo.amount ELSE 0 END), 0) as advances,
                    COALESCE(SUM(CASE WHEN fo.operation_type = 'payment' THEN fo.amount ELSE 0 END), 0) as payments,
                    COALESCE(SUM(CASE WHEN fo.operation_type = 'expense' THEN fo.amount ELSE 0 END), 0) as expenses
                FROM contracts c
                LEFT JOIN financial_operations fo ON c.id = fo.contract_id
                WHERE c.status = 'active'
                GROUP BY c.id, c.contract_number, c.customer_name, c.total_amount
                HAVING (c.total_amount - COALESCE(SUM(CASE WHEN fo.operation_type = 'advance' THEN fo.amount ELSE 0 END), 0) - COALESCE(SUM(CASE WHEN fo.operation_type = 'payment' THEN fo.amount ELSE 0 END), 0)) < 0
                ORDER BY (c.total_amount - COALESCE(SUM(CASE WHEN fo.operation_type = 'advance' THEN fo.amount ELSE 0 END), 0) - COALESCE(SUM(CASE WHEN fo.operation_type = 'payment' THEN fo.amount ELSE 0 END), 0)) ASC
            `;

            const result = await this.pool.query(query);
            
            if (result.rows.length > 0) {
                const message = this.formatFinancialOperationsMessage(result.rows);
                await this.createNotification('insufficient_funding', 'Недостаточное финансирование', message);
                
                if (this.transporter) {
                    await this.sendEmailNotification('Недостаточное финансирование', message);
                }
            }
        } catch (error) {
            console.error('Ошибка проверки финансовых операций:', error);
        }
    }

    // Создание уведомления в базе данных
    async createNotification(type, title, message, userId = 'admin', relatedEntityType = null, relatedEntityId = null) {
        try {
            const query = `
                INSERT INTO notifications (user_id, title, message, type, related_entity_type, related_entity_id)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING *
            `;

            const result = await this.pool.query(query, [userId, title, message, type, relatedEntityType, relatedEntityId]);
            return result.rows[0];
        } catch (error) {
            console.error('Ошибка создания уведомления:', error);
            throw error;
        }
    }

    // Отправка email уведомления
    async sendEmailNotification(subject, message, recipients = null) {
        if (!this.transporter) {
            console.log('Email transporter не настроен');
            return;
        }

        try {
            const mailOptions = {
                from: this.emailConfig.from || this.emailConfig.user,
                to: recipients || this.emailConfig.to || 'admin@company.com',
                subject: `[Сервисные контракты] ${subject}`,
                html: this.formatEmailMessage(message)
            };

            await this.transporter.sendMail(mailOptions);
            console.log('Email уведомление отправлено');
        } catch (error) {
            console.error('Ошибка отправки email:', error);
        }
    }

    // Форматирование сообщений
    formatMaterialsDeficitMessage(materials) {
        let message = '<h3>Обнаружен дефицит материалов:</h3><ul>';
        
        materials.forEach(material => {
            const deficit = material.total_required - material.available_quantity;
            message += `<li><strong>${material.name}</strong> (${material.material_code}): дефицит ${deficit.toFixed(2)} ${material.unit}</li>`;
        });
        
        message += '</ul>';
        return message;
    }

    formatOverdueOrdersMessage(orders) {
        let message = '<h3>Просроченные заказы:</h3><ul>';
        
        orders.forEach(order => {
            const daysOverdue = moment().diff(moment(order.order_date), 'days');
            message += `<li><strong>${order.order_number}</strong> (${order.contract_number}): просрочен на ${daysOverdue} дней</li>`;
        });
        
        message += '</ul>';
        return message;
    }

    formatExpiringContractsMessage(contracts) {
        let message = '<h3>Истекающие контракты:</h3><ul>';
        
        contracts.forEach(contract => {
            const daysLeft = moment(contract.end_date).diff(moment(), 'days');
            message += `<li><strong>${contract.contract_number}</strong> (${contract.customer_name}): осталось ${daysLeft} дней</li>`;
        });
        
        message += '</ul>';
        return message;
    }

    formatBusinessTripsMessage(trips, action) {
        let message = `<h3>Командировки ${action}:</h3><ul>`;
        
        trips.forEach(trip => {
            message += `<li><strong>${trip.employee_name}</strong> - ${trip.destination} (${trip.order_number})</li>`;
        });
        
        message += '</ul>';
        return message;
    }

    formatFinancialOperationsMessage(contracts) {
        let message = '<h3>Контракты с недостаточным финансированием:</h3><ul>';
        
        contracts.forEach(contract => {
            const deficit = contract.total_amount - contract.advances - contract.payments;
            message += `<li><strong>${contract.contract_number}</strong> (${contract.customer_name}): дефицит ${this.formatCurrency(deficit)}</li>`;
        });
        
        message += '</ul>';
        return message;
    }

    formatEmailMessage(message) {
        return `
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>Уведомление системы</title>
                <style>
                    body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                    .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                    .header { background: #f4f4f4; padding: 20px; text-align: center; }
                    .content { padding: 20px; }
                    ul { padding-left: 20px; }
                    li { margin-bottom: 5px; }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>Система управления сервисными контрактами</h1>
                    </div>
                    <div class="content">
                        ${message}
                    </div>
                </div>
            </body>
            </html>
        `;
    }

    formatCurrency(amount) {
        return new Intl.NumberFormat('ru-RU', {
            style: 'currency',
            currency: 'RUB'
        }).format(amount);
    }

    // Получение уведомлений для пользователя
    async getUserNotifications(userId, limit = 50) {
        try {
            const query = `
                SELECT * FROM notifications 
                WHERE user_id = $1 
                ORDER BY created_at DESC 
                LIMIT $2
            `;

            const result = await this.pool.query(query, [userId, limit]);
            return result.rows;
        } catch (error) {
            console.error('Ошибка получения уведомлений:', error);
            throw error;
        }
    }

    // Отметка уведомления как прочитанного
    async markNotificationAsRead(notificationId, userId) {
        try {
            const query = `
                UPDATE notifications 
                SET is_read = true 
                WHERE id = $1 AND user_id = $2
                RETURNING *
            `;

            const result = await this.pool.query(query, [notificationId, userId]);
            return result.rows[0];
        } catch (error) {
            console.error('Ошибка обновления уведомления:', error);
            throw error;
        }
    }

    // Отметка всех уведомлений как прочитанных
    async markAllNotificationsAsRead(userId) {
        try {
            const query = `
                UPDATE notifications 
                SET is_read = true 
                WHERE user_id = $1 AND is_read = false
            `;

            await this.pool.query(query, [userId]);
        } catch (error) {
            console.error('Ошибка обновления уведомлений:', error);
            throw error;
        }
    }

    // Получение количества непрочитанных уведомлений
    async getUnreadCount(userId) {
        try {
            const query = `
                SELECT COUNT(*) as count 
                FROM notifications 
                WHERE user_id = $1 AND is_read = false
            `;

            const result = await this.pool.query(query, [userId]);
            return parseInt(result.rows[0].count);
        } catch (error) {
            console.error('Ошибка получения количества уведомлений:', error);
            throw error;
        }
    }

    // Удаление старых уведомлений (старше 30 дней)
    async cleanupOldNotifications() {
        try {
            const query = `
                DELETE FROM notifications 
                WHERE created_at < CURRENT_DATE - INTERVAL '30 days'
            `;

            const result = await this.pool.query(query);
            console.log(`Удалено ${result.rowCount} старых уведомлений`);
        } catch (error) {
            console.error('Ошибка очистки старых уведомлений:', error);
        }
    }

    // Ручная отправка уведомления
    async sendManualNotification(userId, title, message, type = 'info', relatedEntityType = null, relatedEntityId = null) {
        try {
            const notification = await this.createNotification(type, title, message, userId, relatedEntityType, relatedEntityId);
            
            if (this.transporter && type === 'error') {
                await this.sendEmailNotification(title, message);
            }
            
            return notification;
        } catch (error) {
            console.error('Ошибка отправки ручного уведомления:', error);
            throw error;
        }
    }

    // Настройка email конфигурации
    setEmailConfig(config) {
        this.emailConfig = { ...this.emailConfig, ...config };
        this.setupEmailTransporter();
    }

    // Остановка системы уведомлений
    stop() {
        cron.getTasks().forEach(task => task.destroy());
        this.pool.end();
    }
}

module.exports = NotificationSystem;