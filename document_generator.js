// Генератор документов для системы управления сервисными контрактами

const fs = require('fs');
const path = require('path');
const puppeteer = require('puppeteer');
const { v4: uuidv4 } = require('uuid');

class DocumentGenerator {
    constructor() {
        this.templatesPath = path.join(__dirname, 'document_templates');
        this.outputPath = path.join(__dirname, 'generated_documents');
        this.ensureOutputDirectory();
    }

    ensureOutputDirectory() {
        if (!fs.existsSync(this.outputPath)) {
            fs.mkdirSync(this.outputPath, { recursive: true });
        }
    }

    // Генерация контракта
    async generateContract(contractData) {
        const templatePath = path.join(this.templatesPath, 'contract_template.html');
        const template = fs.readFileSync(templatePath, 'utf8');
        
        const html = this.replacePlaceholders(template, {
            CONTRACT_NUMBER: contractData.contract_number,
            CONTRACT_DATE: this.formatDate(contractData.start_date),
            START_DATE: this.formatDate(contractData.start_date),
            END_DATE: this.formatDate(contractData.end_date),
            TOTAL_AMOUNT: this.formatCurrency(contractData.total_amount),
            ADVANCE_AMOUNT: this.formatCurrency(contractData.advance_amount),
            CUSTOMER_NAME: contractData.customer_name,
            CUSTOMER_CONTACT: contractData.customer_contact || '',
            COMPANY_NAME: 'ООО "Сервисная компания"',
            COMPANY_ADDRESS: 'г. Москва, ул. Примерная, д. 1',
            CUSTOMER_SIGNATURE: '_________________',
            COMPANY_SIGNATURE: '_________________'
        });

        const filename = `contract_${contractData.contract_number}_${Date.now()}.pdf`;
        const filepath = path.join(this.outputPath, filename);
        
        await this.generatePDF(html, filepath);
        
        return {
            filename,
            filepath,
            type: 'contract',
            contract_id: contractData.id
        };
    }

    // Генерация акта сдачи-приемки
    async generateAct(actData) {
        const templatePath = path.join(this.templatesPath, 'act_template.html');
        const template = fs.readFileSync(templatePath, 'utf8');
        
        const workItemsHtml = this.generateWorkItemsHtml(actData.work_items);
        
        const html = this.replacePlaceholders(template, {
            ACT_NUMBER: actData.act_number || `АКТ-${Date.now()}`,
            ACT_DATE: this.formatDate(new Date()),
            CONTRACT_NUMBER: actData.contract_number,
            CONTRACT_DATE: this.formatDate(actData.contract_date),
            ORDER_NUMBER: actData.order_number,
            ORDER_DATE: this.formatDate(actData.order_date),
            WORK_LOCATION: actData.work_location || '',
            CUSTOMER_NAME: actData.customer_name,
            CUSTOMER_CONTACT: actData.customer_contact || '',
            COMPANY_NAME: 'ООО "Сервисная компания"',
            COMPANY_ADDRESS: 'г. Москва, ул. Примерная, д. 1',
            WORK_ITEMS: workItemsHtml,
            TOTAL_AMOUNT: this.formatCurrency(actData.total_amount),
            VAT_AMOUNT: this.formatCurrency(actData.vat_amount || 0),
            FINAL_AMOUNT: this.formatCurrency(actData.final_amount || actData.total_amount),
            WORK_QUALITY: actData.work_quality || 'Соответствует техническим требованиям',
            WORK_START_DATE: this.formatDate(actData.work_start_date),
            WORK_END_DATE: this.formatDate(actData.work_end_date),
            WARRANTY_PERIOD: actData.warranty_period || 12,
            CUSTOMER_SIGNATURE: '_________________',
            COMPANY_SIGNATURE: '_________________'
        });

        const filename = `act_${actData.act_number || Date.now()}_${Date.now()}.pdf`;
        const filepath = path.join(this.outputPath, filename);
        
        await this.generatePDF(html, filepath);
        
        return {
            filename,
            filepath,
            type: 'act',
            contract_id: actData.contract_id,
            order_id: actData.order_id
        };
    }

    // Генерация удостоверения военпреда
    async generateMilitaryRepresentativeCertificate(certData) {
        const template = `
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Удостоверение военного представителя</title>
    <style>
        body {
            font-family: 'Times New Roman', serif;
            font-size: 12pt;
            line-height: 1.5;
            margin: 0;
            padding: 20px;
            color: #000;
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
        }
        .header h1 {
            font-size: 16pt;
            font-weight: bold;
            margin: 0 0 10px 0;
            text-transform: uppercase;
        }
        .content {
            margin-bottom: 20px;
        }
        .content p {
            margin: 0 0 10px 0;
            text-align: justify;
        }
        .signatures {
            margin-top: 40px;
        }
        .signature-table {
            width: 100%;
            border-collapse: collapse;
        }
        .signature-table td {
            padding: 10px;
            vertical-align: top;
            width: 50%;
        }
        .signature-line {
            border-bottom: 1px solid #000;
            height: 40px;
            margin-top: 20px;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>Удостоверение военного представителя</h1>
        <h2>№ {{CERT_NUMBER}}</h2>
    </div>

    <div class="content">
        <p>Настоящим удостоверяю, что работы по сервисному обслуживанию оборудования, выполненные {{COMPANY_NAME}} по контракту № {{CONTRACT_NUMBER}} от {{CONTRACT_DATE}}, соответствуют техническим требованиям и приняты военным представителем.</p>
        
        <p><strong>Объект работ:</strong> {{WORK_OBJECT}}</p>
        <p><strong>Место выполнения:</strong> {{WORK_LOCATION}}</p>
        <p><strong>Период выполнения:</strong> с {{WORK_START_DATE}} по {{WORK_END_DATE}}</p>
        <p><strong>Качество работ:</strong> {{WORK_QUALITY}}</p>
        <p><strong>Соответствие ТТЗ:</strong> {{COMPLIANCE_STATUS}}</p>
    </div>

    <div class="signatures">
        <table class="signature-table">
            <tr>
                <td>
                    <p><strong>ВОЕННЫЙ ПРЕДСТАВИТЕЛЬ:</strong></p>
                    <div class="signature-line"></div>
                    <p style="text-align: center; margin-top: 5px;">(подпись)</p>
                    <p style="text-align: center; margin-top: 20px;">{{MILITARY_REP_SIGNATURE}}</p>
                </td>
                <td>
                    <p><strong>ИСПОЛНИТЕЛЬ:</strong></p>
                    <div class="signature-line"></div>
                    <p style="text-align: center; margin-top: 5px;">(подпись)</p>
                    <p style="text-align: center; margin-top: 20px;">{{COMPANY_SIGNATURE}}</p>
                </td>
            </tr>
        </table>
    </div>
</body>
</html>`;

        const html = this.replacePlaceholders(template, {
            CERT_NUMBER: certData.cert_number || `УВП-${Date.now()}`,
            COMPANY_NAME: 'ООО "Сервисная компания"',
            CONTRACT_NUMBER: certData.contract_number,
            CONTRACT_DATE: this.formatDate(certData.contract_date),
            WORK_OBJECT: certData.work_object || 'Оборудование',
            WORK_LOCATION: certData.work_location || '',
            WORK_START_DATE: this.formatDate(certData.work_start_date),
            WORK_END_DATE: this.formatDate(certData.work_end_date),
            WORK_QUALITY: certData.work_quality || 'Соответствует требованиям',
            COMPLIANCE_STATUS: certData.compliance_status || 'Полное соответствие',
            MILITARY_REP_SIGNATURE: '_________________',
            COMPANY_SIGNATURE: '_________________'
        });

        const filename = `military_cert_${certData.cert_number || Date.now()}_${Date.now()}.pdf`;
        const filepath = path.join(this.outputPath, filename);
        
        await this.generatePDF(html, filepath);
        
        return {
            filename,
            filepath,
            type: 'military_certificate',
            contract_id: certData.contract_id,
            order_id: certData.order_id
        };
    }

    // Генерация протокола совещания
    async generateMeetingProtocol(protocolData) {
        const template = `
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Протокол совещания</title>
    <style>
        body {
            font-family: 'Times New Roman', serif;
            font-size: 12pt;
            line-height: 1.5;
            margin: 0;
            padding: 20px;
            color: #000;
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
        }
        .header h1 {
            font-size: 16pt;
            font-weight: bold;
            margin: 0 0 10px 0;
            text-transform: uppercase;
        }
        .protocol-info {
            margin-bottom: 20px;
        }
        .protocol-info table {
            width: 100%;
            border-collapse: collapse;
        }
        .protocol-info td {
            padding: 5px;
            vertical-align: top;
        }
        .protocol-info .label {
            font-weight: bold;
            width: 30%;
        }
        .content {
            margin-bottom: 20px;
        }
        .content p {
            margin: 0 0 10px 0;
            text-align: justify;
        }
        .participants {
            margin: 20px 0;
        }
        .participants ul {
            margin: 0;
            padding-left: 20px;
        }
        .decisions {
            margin: 20px 0;
        }
        .decisions ol {
            margin: 0;
            padding-left: 20px;
        }
        .tasks {
            margin: 20px 0;
        }
        .tasks table {
            width: 100%;
            border-collapse: collapse;
            border: 1px solid #000;
        }
        .tasks th,
        .tasks td {
            border: 1px solid #000;
            padding: 8px;
            text-align: left;
        }
        .tasks th {
            background-color: #f0f0f0;
            font-weight: bold;
        }
        .signatures {
            margin-top: 40px;
        }
        .signature-table {
            width: 100%;
            border-collapse: collapse;
        }
        .signature-table td {
            padding: 10px;
            vertical-align: top;
            width: 50%;
        }
        .signature-line {
            border-bottom: 1px solid #000;
            height: 40px;
            margin-top: 20px;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>Протокол совещания</h1>
        <h2>№ {{PROTOCOL_NUMBER}}</h2>
    </div>

    <div class="protocol-info">
        <table>
            <tr>
                <td class="label">Дата проведения:</td>
                <td>{{MEETING_DATE}}</td>
            </tr>
            <tr>
                <td class="label">Время:</td>
                <td>{{MEETING_TIME}}</td>
            </tr>
            <tr>
                <td class="label">Место проведения:</td>
                <td>{{MEETING_LOCATION}}</td>
            </tr>
            <tr>
                <td class="label">Контракт:</td>
                <td>№ {{CONTRACT_NUMBER}} от {{CONTRACT_DATE}}</td>
            </tr>
        </table>
    </div>

    <div class="content">
        <h3>ПОВЕСТКА ДНЯ:</h3>
        <p>{{AGENDA}}</p>

        <div class="participants">
            <h3>УЧАСТНИКИ:</h3>
            <ul>
                {{PARTICIPANTS}}
            </ul>
        </div>

        <div class="decisions">
            <h3>ПРИНЯТЫЕ РЕШЕНИЯ:</h3>
            <ol>
                {{DECISIONS}}
            </ol>
        </div>

        <div class="tasks">
            <h3>ЗАДАЧИ И ОТВЕТСТВЕННЫЕ:</h3>
            <table>
                <thead>
                    <tr>
                        <th>№</th>
                        <th>Задача</th>
                        <th>Ответственный</th>
                        <th>Срок</th>
                    </tr>
                </thead>
                <tbody>
                    {{TASKS}}
                </tbody>
            </table>
        </div>
    </div>

    <div class="signatures">
        <table class="signature-table">
            <tr>
                <td>
                    <p><strong>ЗАКАЗЧИК:</strong></p>
                    <div class="signature-line"></div>
                    <p style="text-align: center; margin-top: 5px;">(подпись)</p>
                    <p style="text-align: center; margin-top: 20px;">{{CUSTOMER_SIGNATURE}}</p>
                </td>
                <td>
                    <p><strong>ИСПОЛНИТЕЛЬ:</strong></p>
                    <div class="signature-line"></div>
                    <p style="text-align: center; margin-top: 5px;">(подпись)</p>
                    <p style="text-align: center; margin-top: 20px;">{{COMPANY_SIGNATURE}}</p>
                </td>
            </tr>
        </table>
    </div>
</body>
</html>`;

        const participantsHtml = protocolData.participants.map(p => `<li>${p}</li>`).join('');
        const decisionsHtml = protocolData.decisions.map(d => `<li>${d}</li>`).join('');
        const tasksHtml = protocolData.tasks.map((task, index) => 
            `<tr><td>${index + 1}</td><td>${task.description}</td><td>${task.responsible}</td><td>${this.formatDate(task.deadline)}</td></tr>`
        ).join('');

        const html = this.replacePlaceholders(template, {
            PROTOCOL_NUMBER: protocolData.protocol_number || `ПР-${Date.now()}`,
            MEETING_DATE: this.formatDate(protocolData.meeting_date),
            MEETING_TIME: protocolData.meeting_time || '10:00',
            MEETING_LOCATION: protocolData.meeting_location || '',
            CONTRACT_NUMBER: protocolData.contract_number,
            CONTRACT_DATE: this.formatDate(protocolData.contract_date),
            AGENDA: protocolData.agenda || '',
            PARTICIPANTS: participantsHtml,
            DECISIONS: decisionsHtml,
            TASKS: tasksHtml,
            CUSTOMER_SIGNATURE: '_________________',
            COMPANY_SIGNATURE: '_________________'
        });

        const filename = `protocol_${protocolData.protocol_number || Date.now()}_${Date.now()}.pdf`;
        const filepath = path.join(this.outputPath, filename);
        
        await this.generatePDF(html, filepath);
        
        return {
            filename,
            filepath,
            type: 'protocol',
            contract_id: protocolData.contract_id
        };
    }

    // Генерация HTML для позиций работ
    generateWorkItemsHtml(workItems) {
        if (!workItems || workItems.length === 0) {
            return '<tr><td colspan="5">Работы не указаны</td></tr>';
        }

        return workItems.map((item, index) => `
            <tr>
                <td class="number">${index + 1}</td>
                <td class="description">${item.description}</td>
                <td class="unit">${item.unit || 'шт.'}</td>
                <td class="quantity">${item.quantity || 1}</td>
                <td class="price">${this.formatCurrency(item.price || 0)}</td>
            </tr>
        `).join('');
    }

    // Замена плейсхолдеров в шаблоне
    replacePlaceholders(template, data) {
        let result = template;
        for (const [key, value] of Object.entries(data)) {
            const placeholder = `{{${key}}}`;
            result = result.replace(new RegExp(placeholder, 'g'), value || '');
        }
        return result;
    }

    // Генерация PDF из HTML
    async generatePDF(html, outputPath) {
        const browser = await puppeteer.launch({
            headless: true,
            args: ['--no-sandbox', '--disable-setuid-sandbox']
        });

        try {
            const page = await browser.newPage();
            await page.setContent(html, { waitUntil: 'networkidle0' });
            
            const pdf = await page.pdf({
                path: outputPath,
                format: 'A4',
                printBackground: true,
                margin: {
                    top: '20mm',
                    right: '15mm',
                    bottom: '20mm',
                    left: '15mm'
                }
            });

            return pdf;
        } finally {
            await browser.close();
        }
    }

    // Форматирование даты
    formatDate(date) {
        if (!date) return '';
        const d = new Date(date);
        return d.toLocaleDateString('ru-RU');
    }

    // Форматирование валюты
    formatCurrency(amount) {
        if (!amount) return '0';
        return new Intl.NumberFormat('ru-RU', {
            style: 'currency',
            currency: 'RUB',
            minimumFractionDigits: 0,
            maximumFractionDigits: 2
        }).format(amount);
    }

    // Пакетная генерация документов
    async generateDocumentPackage(contractData, orderData, workItems) {
        const results = [];

        try {
            // Генерируем контракт
            const contract = await this.generateContract(contractData);
            results.push(contract);

            // Генерируем акт сдачи-приемки
            const actData = {
                ...orderData,
                contract_number: contractData.contract_number,
                contract_date: contractData.start_date,
                work_items: workItems,
                total_amount: workItems.reduce((sum, item) => sum + (item.price || 0) * (item.quantity || 1), 0)
            };
            const act = await this.generateAct(actData);
            results.push(act);

            // Генерируем удостоверение военпреда
            const certData = {
                contract_number: contractData.contract_number,
                contract_date: contractData.start_date,
                work_object: orderData.description || 'Оборудование',
                work_location: orderData.location || '',
                work_start_date: orderData.order_date,
                work_end_date: new Date()
            };
            const certificate = await this.generateMilitaryRepresentativeCertificate(certData);
            results.push(certificate);

            return results;
        } catch (error) {
            console.error('Ошибка генерации пакета документов:', error);
            throw error;
        }
    }
}

module.exports = DocumentGenerator;