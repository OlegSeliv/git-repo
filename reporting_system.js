// Система отчетности и аналитики для управления сервисными контрактами

const ExcelJS = require('exceljs');
const { Pool } = require('pg');
const moment = require('moment');
const path = require('path');

class ReportingSystem {
    constructor(dbConfig) {
        this.pool = new Pool(dbConfig);
        this.reportsPath = path.join(__dirname, 'reports');
        this.ensureReportsDirectory();
    }

    ensureReportsDirectory() {
        const fs = require('fs');
        if (!fs.existsSync(this.reportsPath)) {
            fs.mkdirSync(this.reportsPath, { recursive: true });
        }
    }

    // Генерация отчета по контрактам
    async generateContractsReport(filters = {}) {
        const workbook = new ExcelJS.Workbook();
        const worksheet = workbook.addWorksheet('Контракты');

        // Заголовки
        worksheet.columns = [
            { header: 'Номер контракта', key: 'contract_number', width: 20 },
            { header: 'Заказчик', key: 'customer_name', width: 30 },
            { header: 'Дата начала', key: 'start_date', width: 15 },
            { header: 'Дата окончания', key: 'end_date', width: 15 },
            { header: 'Общая сумма', key: 'total_amount', width: 15 },
            { header: 'Аванс', key: 'advance_amount', width: 15 },
            { header: 'Остаток', key: 'remaining_amount', width: 15 },
            { header: 'Статус', key: 'status', width: 15 },
            { header: 'Количество заказов', key: 'orders_count', width: 15 },
            { header: 'Выполнено заказов', key: 'completed_orders', width: 15 }
        ];

        // Стилизация заголовков
        worksheet.getRow(1).font = { bold: true };
        worksheet.getRow(1).fill = {
            type: 'pattern',
            pattern: 'solid',
            fgColor: { argb: 'FFE0E0E0' }
        };

        // Получение данных
        const query = this.buildContractsQuery(filters);
        const result = await this.pool.query(query);

        // Заполнение данными
        result.rows.forEach(row => {
            const remainingAmount = (row.total_amount || 0) - (row.advance_amount || 0);
            worksheet.addRow({
                contract_number: row.contract_number,
                customer_name: row.customer_name,
                start_date: this.formatDate(row.start_date),
                end_date: this.formatDate(row.end_date),
                total_amount: this.formatCurrency(row.total_amount),
                advance_amount: this.formatCurrency(row.advance_amount),
                remaining_amount: this.formatCurrency(remainingAmount),
                status: this.translateStatus(row.status),
                orders_count: row.orders_count || 0,
                completed_orders: row.completed_orders || 0
            });
        });

        // Добавление итогов
        const totalRow = worksheet.addRow({});
        totalRow.getCell(1).value = 'ИТОГО:';
        totalRow.getCell(1).font = { bold: true };
        totalRow.getCell(5).value = this.formatCurrency(result.rows.reduce((sum, row) => sum + (row.total_amount || 0), 0));
        totalRow.getCell(6).value = this.formatCurrency(result.rows.reduce((sum, row) => sum + (row.advance_amount || 0), 0));
        totalRow.getCell(7).value = this.formatCurrency(result.rows.reduce((sum, row) => sum + ((row.total_amount || 0) - (row.advance_amount || 0)), 0));

        const filename = `contracts_report_${moment().format('YYYY-MM-DD_HH-mm-ss')}.xlsx`;
        const filepath = path.join(this.reportsPath, filename);
        await workbook.xlsx.writeFile(filepath);

        return { filename, filepath, recordCount: result.rows.length };
    }

    // Генерация отчета по заказам
    async generateOrdersReport(filters = {}) {
        const workbook = new ExcelJS.Workbook();
        const worksheet = workbook.addWorksheet('Заказы');

        worksheet.columns = [
            { header: 'Номер заказа', key: 'order_number', width: 20 },
            { header: 'Контракт', key: 'contract_number', width: 20 },
            { header: 'Заказчик', key: 'customer_name', width: 30 },
            { header: 'Описание', key: 'description', width: 40 },
            { header: 'Местоположение', key: 'location', width: 25 },
            { header: 'Дата заказа', key: 'order_date', width: 15 },
            { header: 'Приоритет', key: 'priority', width: 12 },
            { header: 'Статус', key: 'status', width: 15 },
            { header: 'Плановая стоимость', key: 'estimated_cost', width: 15 },
            { header: 'Фактическая стоимость', key: 'actual_cost', width: 15 },
            { header: 'Отклонение', key: 'deviation', width: 15 }
        ];

        worksheet.getRow(1).font = { bold: true };
        worksheet.getRow(1).fill = {
            type: 'pattern',
            pattern: 'solid',
            fgColor: { argb: 'FFE0E0E0' }
        };

        const query = this.buildOrdersQuery(filters);
        const result = await this.pool.query(query);

        result.rows.forEach(row => {
            const deviation = (row.actual_cost || 0) - (row.estimated_cost || 0);
            worksheet.addRow({
                order_number: row.order_number,
                contract_number: row.contract_number,
                customer_name: row.customer_name,
                description: row.description,
                location: row.location,
                order_date: this.formatDate(row.order_date),
                priority: this.translatePriority(row.priority),
                status: this.translateStatus(row.status),
                estimated_cost: this.formatCurrency(row.estimated_cost),
                actual_cost: this.formatCurrency(row.actual_cost),
                deviation: this.formatCurrency(deviation)
            });
        });

        const filename = `orders_report_${moment().format('YYYY-MM-DD_HH-mm-ss')}.xlsx`;
        const filepath = path.join(this.reportsPath, filename);
        await workbook.xlsx.writeFile(filepath);

        return { filename, filepath, recordCount: result.rows.length };
    }

    // Генерация отчета по материалам
    async generateMaterialsReport(filters = {}) {
        const workbook = new ExcelJS.Workbook();
        const worksheet = workbook.addWorksheet('Материалы');

        worksheet.columns = [
            { header: 'Код материала', key: 'material_code', width: 20 },
            { header: 'Наименование', key: 'name', width: 40 },
            { header: 'Единица измерения', key: 'unit', width: 15 },
            { header: 'Цена за единицу', key: 'unit_price', width: 15 },
            { header: 'На складе', key: 'stock_quantity', width: 12 },
            { header: 'Зарезервировано', key: 'reserved_quantity', width: 15 },
            { header: 'Доступно', key: 'available_quantity', width: 12 },
            { header: 'Поставщик', key: 'supplier', width: 25 },
            { header: 'Категория', key: 'category', width: 20 },
            { header: 'Статус дефицита', key: 'deficit_status', width: 15 }
        ];

        worksheet.getRow(1).font = { bold: true };
        worksheet.getRow(1).fill = {
            type: 'pattern',
            pattern: 'solid',
            fgColor: { argb: 'FFE0E0E0' }
        };

        const query = this.buildMaterialsQuery(filters);
        const result = await this.pool.query(query);

        result.rows.forEach(row => {
            const available = (row.stock_quantity || 0) - (row.reserved_quantity || 0);
            const deficitStatus = available < 0 ? 'ДЕФИЦИТ' : available < 10 ? 'НИЗКИЙ ОСТАТОК' : 'НОРМА';
            
            worksheet.addRow({
                material_code: row.material_code,
                name: row.name,
                unit: row.unit,
                unit_price: this.formatCurrency(row.unit_price),
                stock_quantity: row.stock_quantity || 0,
                reserved_quantity: row.reserved_quantity || 0,
                available_quantity: available,
                supplier: row.supplier,
                category: row.category,
                deficit_status: deficitStatus
            });
        });

        const filename = `materials_report_${moment().format('YYYY-MM-DD_HH-mm-ss')}.xlsx`;
        const filepath = path.join(this.reportsPath, filename);
        await workbook.xlsx.writeFile(filepath);

        return { filename, filepath, recordCount: result.rows.length };
    }

    // Генерация отчета по командировкам
    async generateBusinessTripsReport(filters = {}) {
        const workbook = new ExcelJS.Workbook();
        const worksheet = workbook.addWorksheet('Командировки');

        worksheet.columns = [
            { header: 'Сотрудник', key: 'employee_name', width: 25 },
            { header: 'Заказ', key: 'order_number', width: 20 },
            { header: 'Контракт', key: 'contract_number', width: 20 },
            { header: 'Направление', key: 'destination', width: 30 },
            { header: 'Дата начала', key: 'start_date', width: 15 },
            { header: 'Дата окончания', key: 'end_date', width: 15 },
            { header: 'Продолжительность (дни)', key: 'duration', width: 18 },
            { header: 'Статус', key: 'status', width: 15 },
            { header: 'Плановая стоимость', key: 'estimated_cost', width: 18 },
            { header: 'Фактическая стоимость', key: 'actual_cost', width: 18 },
            { header: 'Цель', key: 'purpose', width: 40 }
        ];

        worksheet.getRow(1).font = { bold: true };
        worksheet.getRow(1).fill = {
            type: 'pattern',
            pattern: 'solid',
            fgColor: { argb: 'FFE0E0E0' }
        };

        const query = this.buildBusinessTripsQuery(filters);
        const result = await this.pool.query(query);

        result.rows.forEach(row => {
            const startDate = moment(row.start_date);
            const endDate = moment(row.end_date);
            const duration = endDate.isValid() ? endDate.diff(startDate, 'days') : 0;

            worksheet.addRow({
                employee_name: row.employee_name,
                order_number: row.order_number,
                contract_number: row.contract_number,
                destination: row.destination,
                start_date: this.formatDate(row.start_date),
                end_date: this.formatDate(row.end_date),
                duration: duration,
                status: this.translateStatus(row.status),
                estimated_cost: this.formatCurrency(row.estimated_cost),
                actual_cost: this.formatCurrency(row.actual_cost),
                purpose: row.purpose
            });
        });

        const filename = `business_trips_report_${moment().format('YYYY-MM-DD_HH-mm-ss')}.xlsx`;
        const filepath = path.join(this.reportsPath, filename);
        await workbook.xlsx.writeFile(filepath);

        return { filename, filepath, recordCount: result.rows.length };
    }

    // Генерация финансового отчета
    async generateFinancialReport(filters = {}) {
        const workbook = new ExcelJS.Workbook();
        
        // Лист по операциям
        const operationsSheet = workbook.addWorksheet('Финансовые операции');
        operationsSheet.columns = [
            { header: 'Дата', key: 'operation_date', width: 15 },
            { header: 'Тип операции', key: 'operation_type', width: 20 },
            { header: 'Контракт', key: 'contract_number', width: 20 },
            { header: 'Заказчик', key: 'customer_name', width: 30 },
            { header: 'Сумма', key: 'amount', width: 15 },
            { header: 'Описание', key: 'description', width: 40 },
            { header: 'Номер документа', key: 'document_number', width: 20 }
        ];

        operationsSheet.getRow(1).font = { bold: true };
        operationsSheet.getRow(1).fill = {
            type: 'pattern',
            pattern: 'solid',
            fgColor: { argb: 'FFE0E0E0' }
        };

        const operationsQuery = this.buildFinancialOperationsQuery(filters);
        const operationsResult = await this.pool.query(operationsQuery);

        operationsResult.rows.forEach(row => {
            operationsSheet.addRow({
                operation_date: this.formatDate(row.operation_date),
                operation_type: this.translateOperationType(row.operation_type),
                contract_number: row.contract_number,
                customer_name: row.customer_name,
                amount: this.formatCurrency(row.amount),
                description: row.description,
                document_number: row.document_number
            });
        });

        // Лист сводки по контрактам
        const summarySheet = workbook.addWorksheet('Сводка по контрактам');
        summarySheet.columns = [
            { header: 'Контракт', key: 'contract_number', width: 20 },
            { header: 'Заказчик', key: 'customer_name', width: 30 },
            { header: 'Общая сумма', key: 'total_amount', width: 15 },
            { header: 'Авансы', key: 'advances', width: 15 },
            { header: 'Доплаты', key: 'additional_payments', width: 15 },
            { header: 'Расходы', key: 'expenses', width: 15 },
            { header: 'Остаток', key: 'balance', width: 15 },
            { header: 'Статус', key: 'status', width: 15 }
        ];

        summarySheet.getRow(1).font = { bold: true };
        summarySheet.getRow(1).fill = {
            type: 'pattern',
            pattern: 'solid',
            fgColor: { argb: 'FFE0E0E0' }
        };

        const summaryQuery = this.buildFinancialSummaryQuery(filters);
        const summaryResult = await this.pool.query(summaryQuery);

        summaryResult.rows.forEach(row => {
            const balance = (row.total_amount || 0) - (row.advances || 0) - (row.additional_payments || 0) - (row.expenses || 0);
            summarySheet.addRow({
                contract_number: row.contract_number,
                customer_name: row.customer_name,
                total_amount: this.formatCurrency(row.total_amount),
                advances: this.formatCurrency(row.advances),
                additional_payments: this.formatCurrency(row.additional_payments),
                expenses: this.formatCurrency(row.expenses),
                balance: this.formatCurrency(balance),
                status: this.translateStatus(row.status)
            });
        });

        const filename = `financial_report_${moment().format('YYYY-MM-DD_HH-mm-ss')}.xlsx`;
        const filepath = path.join(this.reportsPath, filename);
        await workbook.xlsx.writeFile(filepath);

        return { filename, filepath, recordCount: operationsResult.rows.length };
    }

    // Генерация отчета по дефициту материалов
    async generateMaterialsDeficitReport() {
        const workbook = new ExcelJS.Workbook();
        const worksheet = workbook.addWorksheet('Дефицит материалов');

        worksheet.columns = [
            { header: 'Код материала', key: 'material_code', width: 20 },
            { header: 'Наименование', key: 'name', width: 40 },
            { header: 'Единица', key: 'unit', width: 15 },
            { header: 'Требуется', key: 'required_quantity', width: 15 },
            { header: 'Доступно', key: 'available_quantity', width: 15 },
            { header: 'Дефицит', key: 'deficit', width: 15 },
            { header: 'Поставщик', key: 'supplier', width: 25 },
            { header: 'Критичность', key: 'criticality', width: 15 }
        ];

        worksheet.getRow(1).font = { bold: true };
        worksheet.getRow(1).fill = {
            type: 'pattern',
            pattern: 'solid',
            fgColor: { argb: 'FFE0E0E0' }
        };

        const query = `
            SELECT 
                m.material_code,
                m.name,
                m.unit,
                m.supplier,
                COALESCE(ws.quantity, 0) as stock_quantity,
                COALESCE(ws.reserved_quantity, 0) as reserved_quantity,
                COALESCE(ws.quantity, 0) - COALESCE(ws.reserved_quantity, 0) as available_quantity,
                SUM(om.required_quantity) as total_required
            FROM materials m
            LEFT JOIN warehouse_stock ws ON m.id = ws.material_id
            LEFT JOIN order_materials om ON m.id = om.material_id
            LEFT JOIN orders o ON om.order_id = o.id
            WHERE o.status IN ('pending', 'in_progress')
            GROUP BY m.id, m.material_code, m.name, m.unit, m.supplier, ws.quantity, ws.reserved_quantity
            HAVING COALESCE(ws.quantity, 0) - COALESCE(ws.reserved_quantity, 0) < SUM(om.required_quantity)
            ORDER BY (SUM(om.required_quantity) - (COALESCE(ws.quantity, 0) - COALESCE(ws.reserved_quantity, 0))) DESC
        `;

        const result = await this.pool.query(query);

        result.rows.forEach(row => {
            const deficit = row.total_required - row.available_quantity;
            const criticality = deficit > 100 ? 'КРИТИЧЕСКИЙ' : deficit > 50 ? 'ВЫСОКИЙ' : 'СРЕДНИЙ';
            
            worksheet.addRow({
                material_code: row.material_code,
                name: row.name,
                unit: row.unit,
                required_quantity: row.total_required,
                available_quantity: row.available_quantity,
                deficit: deficit,
                supplier: row.supplier,
                criticality: criticality
            });
        });

        const filename = `materials_deficit_report_${moment().format('YYYY-MM-DD_HH-mm-ss')}.xlsx`;
        const filepath = path.join(this.reportsPath, filename);
        await workbook.xlsx.writeFile(filepath);

        return { filename, filepath, recordCount: result.rows.length };
    }

    // Построение SQL запросов
    buildContractsQuery(filters) {
        let query = `
            SELECT c.*, 
                   COUNT(o.id) as orders_count,
                   COUNT(CASE WHEN o.status = 'completed' THEN 1 END) as completed_orders
            FROM contracts c
            LEFT JOIN orders o ON c.id = o.contract_id
        `;

        const conditions = [];
        const params = [];
        let paramCount = 1;

        if (filters.start_date) {
            conditions.push(`c.start_date >= $${paramCount}`);
            params.push(filters.start_date);
            paramCount++;
        }

        if (filters.end_date) {
            conditions.push(`c.start_date <= $${paramCount}`);
            params.push(filters.end_date);
            paramCount++;
        }

        if (filters.status) {
            conditions.push(`c.status = $${paramCount}`);
            params.push(filters.status);
            paramCount++;
        }

        if (filters.customer_name) {
            conditions.push(`c.customer_name ILIKE $${paramCount}`);
            params.push(`%${filters.customer_name}%`);
            paramCount++;
        }

        if (conditions.length > 0) {
            query += ` WHERE ${conditions.join(' AND ')}`;
        }

        query += ` GROUP BY c.id ORDER BY c.created_at DESC`;

        return { text: query, values: params };
    }

    buildOrdersQuery(filters) {
        let query = `
            SELECT o.*, c.contract_number, c.customer_name
            FROM orders o
            LEFT JOIN contracts c ON o.contract_id = c.id
        `;

        const conditions = [];
        const params = [];
        let paramCount = 1;

        if (filters.contract_id) {
            conditions.push(`o.contract_id = $${paramCount}`);
            params.push(filters.contract_id);
            paramCount++;
        }

        if (filters.status) {
            conditions.push(`o.status = $${paramCount}`);
            params.push(filters.status);
            paramCount++;
        }

        if (filters.start_date) {
            conditions.push(`o.order_date >= $${paramCount}`);
            params.push(filters.start_date);
            paramCount++;
        }

        if (filters.end_date) {
            conditions.push(`o.order_date <= $${paramCount}`);
            params.push(filters.end_date);
            paramCount++;
        }

        if (conditions.length > 0) {
            query += ` WHERE ${conditions.join(' AND ')}`;
        }

        query += ` ORDER BY o.created_at DESC`;

        return { text: query, values: params };
    }

    buildMaterialsQuery(filters) {
        let query = `
            SELECT m.*, ws.quantity as stock_quantity, ws.reserved_quantity
            FROM materials m
            LEFT JOIN warehouse_stock ws ON m.id = ws.material_id
        `;

        const conditions = [];
        const params = [];
        let paramCount = 1;

        if (filters.search) {
            conditions.push(`(m.name ILIKE $${paramCount} OR m.material_code ILIKE $${paramCount})`);
            params.push(`%${filters.search}%`);
            paramCount++;
        }

        if (filters.category) {
            conditions.push(`m.category = $${paramCount}`);
            params.push(filters.category);
            paramCount++;
        }

        if (filters.supplier) {
            conditions.push(`m.supplier = $${paramCount}`);
            params.push(filters.supplier);
            paramCount++;
        }

        if (conditions.length > 0) {
            query += ` WHERE ${conditions.join(' AND ')}`;
        }

        query += ` ORDER BY m.name`;

        return { text: query, values: params };
    }

    buildBusinessTripsQuery(filters) {
        let query = `
            SELECT bt.*, e.full_name as employee_name, o.order_number, c.contract_number
            FROM business_trips bt
            LEFT JOIN employees e ON bt.employee_id = e.id
            LEFT JOIN orders o ON bt.order_id = o.id
            LEFT JOIN contracts c ON o.contract_id = c.id
        `;

        const conditions = [];
        const params = [];
        let paramCount = 1;

        if (filters.employee_id) {
            conditions.push(`bt.employee_id = $${paramCount}`);
            params.push(filters.employee_id);
            paramCount++;
        }

        if (filters.status) {
            conditions.push(`bt.status = $${paramCount}`);
            params.push(filters.status);
            paramCount++;
        }

        if (filters.start_date) {
            conditions.push(`bt.start_date >= $${paramCount}`);
            params.push(filters.start_date);
            paramCount++;
        }

        if (filters.end_date) {
            conditions.push(`bt.start_date <= $${paramCount}`);
            params.push(filters.end_date);
            paramCount++;
        }

        if (conditions.length > 0) {
            query += ` WHERE ${conditions.join(' AND ')}`;
        }

        query += ` ORDER BY bt.start_date DESC`;

        return { text: query, values: params };
    }

    buildFinancialOperationsQuery(filters) {
        let query = `
            SELECT fo.*, c.contract_number, c.customer_name
            FROM financial_operations fo
            LEFT JOIN contracts c ON fo.contract_id = c.id
        `;

        const conditions = [];
        const params = [];
        let paramCount = 1;

        if (filters.contract_id) {
            conditions.push(`fo.contract_id = $${paramCount}`);
            params.push(filters.contract_id);
            paramCount++;
        }

        if (filters.operation_type) {
            conditions.push(`fo.operation_type = $${paramCount}`);
            params.push(filters.operation_type);
            paramCount++;
        }

        if (filters.start_date) {
            conditions.push(`fo.operation_date >= $${paramCount}`);
            params.push(filters.start_date);
            paramCount++;
        }

        if (filters.end_date) {
            conditions.push(`fo.operation_date <= $${paramCount}`);
            params.push(filters.end_date);
            paramCount++;
        }

        if (conditions.length > 0) {
            query += ` WHERE ${conditions.join(' AND ')}`;
        }

        query += ` ORDER BY fo.operation_date DESC`;

        return { text: query, values: params };
    }

    buildFinancialSummaryQuery(filters) {
        let query = `
            SELECT 
                c.contract_number,
                c.customer_name,
                c.total_amount,
                c.status,
                COALESCE(SUM(CASE WHEN fo.operation_type = 'advance' THEN fo.amount ELSE 0 END), 0) as advances,
                COALESCE(SUM(CASE WHEN fo.operation_type = 'payment' THEN fo.amount ELSE 0 END), 0) as additional_payments,
                COALESCE(SUM(CASE WHEN fo.operation_type = 'expense' THEN fo.amount ELSE 0 END), 0) as expenses
            FROM contracts c
            LEFT JOIN financial_operations fo ON c.id = fo.contract_id
        `;

        const conditions = [];
        const params = [];
        let paramCount = 1;

        if (filters.start_date) {
            conditions.push(`c.start_date >= $${paramCount}`);
            params.push(filters.start_date);
            paramCount++;
        }

        if (filters.end_date) {
            conditions.push(`c.start_date <= $${paramCount}`);
            params.push(filters.end_date);
            paramCount++;
        }

        if (filters.status) {
            conditions.push(`c.status = $${paramCount}`);
            params.push(filters.status);
            paramCount++;
        }

        if (conditions.length > 0) {
            query += ` WHERE ${conditions.join(' AND ')}`;
        }

        query += ` GROUP BY c.id, c.contract_number, c.customer_name, c.total_amount, c.status ORDER BY c.created_at DESC`;

        return { text: query, values: params };
    }

    // Утилиты
    formatDate(date) {
        if (!date) return '';
        return moment(date).format('DD.MM.YYYY');
    }

    formatCurrency(amount) {
        if (!amount) return '0 ₽';
        return new Intl.NumberFormat('ru-RU', {
            style: 'currency',
            currency: 'RUB'
        }).format(amount);
    }

    translateStatus(status) {
        const statusMap = {
            'active': 'Активный',
            'suspended': 'Приостановлен',
            'completed': 'Завершен',
            'terminated': 'Расторгнут',
            'pending': 'Ожидает',
            'in_progress': 'В работе',
            'cancelled': 'Отменен'
        };
        return statusMap[status] || status;
    }

    translatePriority(priority) {
        const priorityMap = {
            'low': 'Низкий',
            'normal': 'Обычный',
            'high': 'Высокий',
            'urgent': 'Срочный'
        };
        return priorityMap[priority] || priority;
    }

    translateOperationType(type) {
        const typeMap = {
            'advance': 'Аванс',
            'payment': 'Оплата',
            'additional_payment': 'Доплата',
            'expense': 'Расход'
        };
        return typeMap[type] || type;
    }

    // Генерация комплексного отчета
    async generateComprehensiveReport(filters = {}) {
        const results = {};

        try {
            results.contracts = await this.generateContractsReport(filters);
            results.orders = await this.generateOrdersReport(filters);
            results.materials = await this.generateMaterialsReport(filters);
            results.businessTrips = await this.generateBusinessTripsReport(filters);
            results.financial = await this.generateFinancialReport(filters);
            results.materialsDeficit = await this.generateMaterialsDeficitReport();

            return {
                success: true,
                results,
                generatedAt: new Date().toISOString()
            };
        } catch (error) {
            console.error('Ошибка генерации комплексного отчета:', error);
            return {
                success: false,
                error: error.message,
                generatedAt: new Date().toISOString()
            };
        }
    }
}

module.exports = ReportingSystem;