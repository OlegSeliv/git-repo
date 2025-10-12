// Основной JavaScript для системы управления контрактами

document.addEventListener('DOMContentLoaded', function() {
    // Инициализация всех tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Инициализация всех popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function(popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Автоматическое скрытие алертов
    setTimeout(function() {
        var alerts = document.querySelectorAll('.alert-dismissible');
        alerts.forEach(function(alert) {
            var bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);

    // Подтверждение удаления
    var deleteButtons = document.querySelectorAll('[data-action="delete"]');
    deleteButtons.forEach(function(button) {
        button.addEventListener('click', function(e) {
            if (!confirm('Вы уверены, что хотите удалить этот элемент?')) {
                e.preventDefault();
            }
        });
    });
});

// Функции для работы с API
class ContractAPI {
    static async getBalance(contractId) {
        try {
            const response = await fetch(`/api/contract_balance/${contractId}`);
            return await response.json();
        } catch (error) {
            console.error('Ошибка получения баланса:', error);
            return { error: 'Ошибка сети' };
        }
    }

    static async updateStatus(contractId, status) {
        try {
            const response = await fetch(`/api/contract/${contractId}/status`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ status: status })
            });
            return await response.json();
        } catch (error) {
            console.error('Ошибка обновления статуса:', error);
            return { error: 'Ошибка сети' };
        }
    }
}

// Утилиты для работы с формами
class FormUtils {
    static validateRequired(form) {
        const requiredFields = form.querySelectorAll('[required]');
        let isValid = true;
        
        requiredFields.forEach(field => {
            if (!field.value.trim()) {
                field.classList.add('is-invalid');
                isValid = false;
            } else {
                field.classList.remove('is-invalid');
            }
        });
        
        return isValid;
    }

    static formatCurrency(input) {
        let value = input.value.replace(/[^\d.,]/g, '');
        value = value.replace(',', '.');
        
        if (value && !isNaN(value)) {
            input.value = parseFloat(value).toLocaleString('ru-RU', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            });
        }
    }

    static formatNumber(input) {
        let value = input.value.replace(/[^\d]/g, '');
        if (value) {
            input.value = parseInt(value).toLocaleString('ru-RU');
        }
    }
}

// Функции для работы с таблицами
class TableUtils {
    static sortTable(table, column, direction = 'asc') {
        const tbody = table.querySelector('tbody');
        const rows = Array.from(tbody.querySelectorAll('tr'));
        
        rows.sort((a, b) => {
            const aText = a.cells[column].textContent.trim();
            const bText = b.cells[column].textContent.trim();
            
            // Попытка сравнить как числа
            const aNum = parseFloat(aText.replace(/[^\d.-]/g, ''));
            const bNum = parseFloat(bText.replace(/[^\d.-]/g, ''));
            
            if (!isNaN(aNum) && !isNaN(bNum)) {
                return direction === 'asc' ? aNum - bNum : bNum - aNum;
            }
            
            // Сравнение как строки
            return direction === 'asc' 
                ? aText.localeCompare(bText, 'ru')
                : bText.localeCompare(aText, 'ru');
        });
        
        rows.forEach(row => tbody.appendChild(row));
    }

    static filterTable(table, searchTerm) {
        const tbody = table.querySelector('tbody');
        const rows = tbody.querySelectorAll('tr');
        
        rows.forEach(row => {
            const text = row.textContent.toLowerCase();
            const match = text.includes(searchTerm.toLowerCase());
            row.style.display = match ? '' : 'none';
        });
    }
}

// Уведомления
class Notifications {
    static show(message, type = 'info', duration = 5000) {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
        alertDiv.style.cssText = `
            top: 20px;
            right: 20px;
            z-index: 1060;
            min-width: 300px;
        `;
        
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(alertDiv);
        
        // Автоматическое удаление
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.remove();
            }
        }, duration);
    }

    static success(message) {
        this.show(message, 'success');
    }

    static error(message) {
        this.show(message, 'danger');
    }

    static warning(message) {
        this.show(message, 'warning');
    }

    static info(message) {
        this.show(message, 'info');
    }
}

// Загрузка и экспорт данных
class DataExport {
    static exportTableToCSV(table, filename = 'export.csv') {
        const rows = table.querySelectorAll('tr');
        const csv = [];
        
        rows.forEach(row => {
            const cells = row.querySelectorAll('th, td');
            const rowData = Array.from(cells).map(cell => 
                `"${cell.textContent.trim().replace(/"/g, '""')}"`
            );
            csv.push(rowData.join(','));
        });
        
        const csvContent = csv.join('\n');
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = filename;
        link.click();
    }

    static printTable(table) {
        const printWindow = window.open('', '_blank');
        printWindow.document.write(`
            <html>
                <head>
                    <title>Печать таблицы</title>
                    <style>
                        table { border-collapse: collapse; width: 100%; }
                        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                        th { background-color: #f2f2f2; }
                        @media print { 
                            body { margin: 0; }
                            table { page-break-inside: auto; }
                            tr { page-break-inside: avoid; page-break-after: auto; }
                        }
                    </style>
                </head>
                <body>
                    ${table.outerHTML}
                </body>
            </html>
        `);
        printWindow.document.close();
        printWindow.print();
    }
}

// Функции для работы с датами
class DateUtils {
    static formatDate(date, format = 'dd.mm.yyyy') {
        if (!(date instanceof Date)) {
            date = new Date(date);
        }
        
        const day = date.getDate().toString().padStart(2, '0');
        const month = (date.getMonth() + 1).toString().padStart(2, '0');
        const year = date.getFullYear();
        
        return format
            .replace('dd', day)
            .replace('mm', month)
            .replace('yyyy', year);
    }

    static isOverdue(date) {
        if (!(date instanceof Date)) {
            date = new Date(date);
        }
        return date < new Date();
    }

    static daysBetween(date1, date2) {
        const oneDay = 24 * 60 * 60 * 1000;
        return Math.round(Math.abs((date1 - date2) / oneDay));
    }
}

// Автосохранение форм
class AutoSave {
    static init(form, interval = 30000) {
        const formData = new FormData(form);
        const initialData = {};
        
        for (let [key, value] of formData.entries()) {
            initialData[key] = value;
        }
        
        setInterval(() => {
            const currentData = new FormData(form);
            let hasChanges = false;
            
            for (let [key, value] of currentData.entries()) {
                if (initialData[key] !== value) {
                    hasChanges = true;
                    break;
                }
            }
            
            if (hasChanges) {
                this.saveToLocalStorage(form);
            }
        }, interval);
    }

    static saveToLocalStorage(form) {
        const formData = new FormData(form);
        const data = {};
        
        for (let [key, value] of formData.entries()) {
            data[key] = value;
        }
        
        localStorage.setItem(`autosave_${form.id}`, JSON.stringify(data));
        Notifications.info('Данные автоматически сохранены');
    }

    static restoreFromLocalStorage(form) {
        const saved = localStorage.getItem(`autosave_${form.id}`);
        if (saved) {
            const data = JSON.parse(saved);
            
            for (let [key, value] of Object.entries(data)) {
                const field = form.querySelector(`[name="${key}"]`);
                if (field) {
                    field.value = value;
                }
            }
            
            Notifications.warning('Восстановлены несохраненные данные');
        }
    }
}

// Глобальные переменные для использования в других скриптах
window.ContractAPI = ContractAPI;
window.FormUtils = FormUtils;
window.TableUtils = TableUtils;
window.Notifications = Notifications;
window.DataExport = DataExport;
window.DateUtils = DateUtils;
window.AutoSave = AutoSave;