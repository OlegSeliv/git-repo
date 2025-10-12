# Система хранения документов и интеграция сканирования
from flask import Flask, request, jsonify, send_file
import os
import uuid
from datetime import datetime
from PIL import Image
import pytesseract
import cv2
import numpy as np
from werkzeug.utils import secure_filename
import shutil
import sqlite3
import hashlib
from pathlib import Path

class DocumentStorageSystem:
    def __init__(self, base_path="documents"):
        self.base_path = Path(base_path)
        self.scans_path = self.base_path / "scans"
        self.originals_path = self.base_path / "originals"
        self.processed_path = self.base_path / "processed"
        
        # Создаем необходимые папки
        for path in [self.base_path, self.scans_path, self.originals_path, self.processed_path]:
            path.mkdir(parents=True, exist_ok=True)
        
        # Создаем структуру папок по типам документов
        self.create_folder_structure()
        
        # Инициализируем базу метаданных
        self.init_metadata_db()
    
    def create_folder_structure(self):
        """Создание структуры папок для хранения документов"""
        folder_structure = {
            "contracts": "Контракты",
            "orders": "Заказы",
            "acts": {
                "work_acts": "Акты выполненных работ",
                "acceptance_acts": "Акты сдачи-приемки",
                "defect_acts": "Акты дефектации"
            },
            "certificates": "Удостоверения военпреда",
            "travel_documents": {
                "travel_orders": "Служебные задания",
                "trip_reports": "Отчеты о командировках"
            },
            "communications": {
                "meetings": "Протоколы совещаний",
                "letters": "Переписка",
                "emails": "Электронная переписка"
            },
            "financial": {
                "invoices": "Счета",
                "payments": "Платежные документы",
                "reports": "Финансовые отчеты"
            },
            "technical": {
                "specifications": "Технические задания",
                "manuals": "Руководства",
                "drawings": "Чертежи"
            }
        }
        
        def create_folders(structure, parent_path=""):
            for key, value in structure.items():
                if isinstance(value, dict):
                    folder_path = parent_path / key if parent_path else self.base_path / key
                    folder_path.mkdir(exist_ok=True)
                    create_folders(value, folder_path)
                else:
                    folder_path = parent_path / key if parent_path else self.base_path / key
                    folder_path.mkdir(exist_ok=True)
        
        create_folders(folder_structure)
    
    def init_metadata_db(self):
        """Инициализация базы данных метаданных документов"""
        self.metadata_db_path = self.base_path / "metadata.db"
        conn = sqlite3.connect(str(self.metadata_db_path))
        cursor = conn.cursor()
        
        # Таблица метаданных файлов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS file_metadata (
                id TEXT PRIMARY KEY,
                original_filename TEXT NOT NULL,
                stored_filename TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_type TEXT NOT NULL,
                file_size INTEGER,
                mime_type TEXT,
                hash_md5 TEXT,
                upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                contract_id INTEGER,
                order_id INTEGER,
                document_type TEXT,
                tags TEXT,
                ocr_text TEXT,
                physical_location TEXT,
                notes TEXT
            )
        ''')
        
        # Таблица версий документов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS document_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id TEXT NOT NULL,
                version_number INTEGER NOT NULL,
                file_id TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by TEXT,
                changes_description TEXT,
                FOREIGN KEY (file_id) REFERENCES file_metadata(id)
            )
        ''')
        
        # Таблица связей документов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS document_relationships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                parent_document_id TEXT NOT NULL,
                child_document_id TEXT NOT NULL,
                relationship_type TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Индексы для быстрого поиска
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_file_type ON file_metadata(file_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_document_type ON file_metadata(document_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_contract_id ON file_metadata(contract_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_upload_date ON file_metadata(upload_date)')
        
        conn.commit()
        conn.close()
    
    def upload_file(self, file, document_type=None, contract_id=None, order_id=None, 
                   physical_location=None, notes=None, tags=None):
        """Загрузка и сохранение файла"""
        if not file or not file.filename:
            return None
        
        # Генерируем уникальный ID
        file_id = str(uuid.uuid4())
        
        # Безопасное имя файла
        original_filename = secure_filename(file.filename)
        file_extension = os.path.splitext(original_filename)[1].lower()
        
        # Определяем папку назначения по типу документа
        target_folder = self.get_target_folder(document_type, contract_id)
        
        # Генерируем имя для хранения
        stored_filename = f"{file_id}{file_extension}"
        file_path = target_folder / stored_filename
        
        # Сохраняем файл
        file.save(str(file_path))
        
        # Вычисляем хеш файла
        file_hash = self.calculate_file_hash(file_path)
        
        # Получаем размер файла
        file_size = file_path.stat().st_size
        
        # Определяем MIME тип
        mime_type = self.get_mime_type(file_extension)
        
        # Сохраняем метаданные
        metadata = {
            'id': file_id,
            'original_filename': original_filename,
            'stored_filename': stored_filename,
            'file_path': str(file_path.relative_to(self.base_path)),
            'file_type': file_extension,
            'file_size': file_size,
            'mime_type': mime_type,
            'hash_md5': file_hash,
            'contract_id': contract_id,
            'order_id': order_id,
            'document_type': document_type,
            'tags': tags,
            'physical_location': physical_location,
            'notes': notes
        }
        
        self.save_file_metadata(metadata)
        
        # Если это изображение, пытаемся распознать текст
        if mime_type.startswith('image/'):
            ocr_text = self.perform_ocr(file_path)
            if ocr_text:
                self.update_ocr_text(file_id, ocr_text)
        
        return file_id
    
    def get_target_folder(self, document_type, contract_id=None):
        """Определение папки назначения для файла"""
        type_mapping = {
            'contract': 'contracts',
            'order': 'orders',
            'work_act': 'acts/work_acts',
            'acceptance_act': 'acts/acceptance_acts',
            'defect_act': 'acts/defect_acts',
            'military_certificate': 'certificates',
            'travel_order': 'travel_documents/travel_orders',
            'trip_report': 'travel_documents/trip_reports',
            'meeting_protocol': 'communications/meetings',
            'letter': 'communications/letters',
            'email': 'communications/emails',
            'invoice': 'financial/invoices',
            'payment': 'financial/payments'
        }
        
        folder_path = type_mapping.get(document_type, 'other')
        
        # Если есть ID контракта, создаем подпапку
        if contract_id:
            folder_path = f"{folder_path}/contract_{contract_id}"
        
        target_path = self.base_path / folder_path
        target_path.mkdir(parents=True, exist_ok=True)
        
        return target_path
    
    def calculate_file_hash(self, file_path):
        """Вычисление MD5 хеша файла"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def get_mime_type(self, file_extension):
        """Определение MIME типа по расширению файла"""
        mime_types = {
            '.pdf': 'application/pdf',
            '.doc': 'application/msword',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.xls': 'application/vnd.ms-excel',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.tiff': 'image/tiff',
            '.tif': 'image/tiff',
            '.txt': 'text/plain',
            '.rtf': 'application/rtf',
            '.zip': 'application/zip',
            '.rar': 'application/x-rar-compressed'
        }
        
        return mime_types.get(file_extension, 'application/octet-stream')
    
    def save_file_metadata(self, metadata):
        """Сохранение метаданных файла в БД"""
        conn = sqlite3.connect(str(self.metadata_db_path))
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO file_metadata 
            (id, original_filename, stored_filename, file_path, file_type, file_size, 
             mime_type, hash_md5, contract_id, order_id, document_type, tags, 
             physical_location, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            metadata['id'], metadata['original_filename'], metadata['stored_filename'],
            metadata['file_path'], metadata['file_type'], metadata['file_size'],
            metadata['mime_type'], metadata['hash_md5'], metadata['contract_id'],
            metadata['order_id'], metadata['document_type'], metadata['tags'],
            metadata['physical_location'], metadata['notes']
        ))
        
        conn.commit()
        conn.close()
    
    def perform_ocr(self, image_path):
        """Оптическое распознавание символов"""
        try:
            # Предобработка изображения для лучшего OCR
            image = cv2.imread(str(image_path))
            if image is None:
                return None
            
            # Преобразуем в оттенки серого
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Улучшаем контрастность
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            gray = clahe.apply(gray)
            
            # Устраняем шум
            gray = cv2.medianBlur(gray, 3)
            
            # Бинаризация
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Конфигурация для русского языка
            custom_config = r'--oem 3 --psm 6 -l rus+eng'
            
            # Распознаем текст
            text = pytesseract.image_to_string(binary, config=custom_config)
            
            return text.strip() if text.strip() else None
            
        except Exception as e:
            print(f"Ошибка OCR: {e}")
            return None
    
    def update_ocr_text(self, file_id, ocr_text):
        """Обновление OCR текста для файла"""
        conn = sqlite3.connect(str(self.metadata_db_path))
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE file_metadata SET ocr_text = ? WHERE id = ?
        ''', (ocr_text, file_id))
        
        conn.commit()
        conn.close()
    
    def search_documents(self, query=None, document_type=None, contract_id=None, 
                        order_id=None, date_from=None, date_to=None, tags=None):
        """Поиск документов по различным критериям"""
        conn = sqlite3.connect(str(self.metadata_db_path))
        cursor = conn.cursor()
        
        # Базовый запрос
        sql = "SELECT * FROM file_metadata WHERE 1=1"
        params = []
        
        # Добавляем условия поиска
        if query:
            sql += " AND (original_filename LIKE ? OR ocr_text LIKE ? OR notes LIKE ?)"
            params.extend([f"%{query}%", f"%{query}%", f"%{query}%"])
        
        if document_type:
            sql += " AND document_type = ?"
            params.append(document_type)
        
        if contract_id:
            sql += " AND contract_id = ?"
            params.append(contract_id)
        
        if order_id:
            sql += " AND order_id = ?"
            params.append(order_id)
        
        if date_from:
            sql += " AND upload_date >= ?"
            params.append(date_from)
        
        if date_to:
            sql += " AND upload_date <= ?"
            params.append(date_to)
        
        if tags:
            sql += " AND tags LIKE ?"
            params.append(f"%{tags}%")
        
        sql += " ORDER BY upload_date DESC"
        
        cursor.execute(sql, params)
        results = cursor.fetchall()
        
        # Преобразуем в список словарей
        columns = [description[0] for description in cursor.description]
        documents = [dict(zip(columns, row)) for row in results]
        
        conn.close()
        return documents
    
    def get_document_by_id(self, file_id):
        """Получение документа по ID"""
        conn = sqlite3.connect(str(self.metadata_db_path))
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM file_metadata WHERE id = ?", (file_id,))
        result = cursor.fetchone()
        
        if result:
            columns = [description[0] for description in cursor.description]
            document = dict(zip(columns, result))
        else:
            document = None
        
        conn.close()
        return document
    
    def delete_document(self, file_id):
        """Удаление документа"""
        document = self.get_document_by_id(file_id)
        if not document:
            return False
        
        # Удаляем файл
        file_path = self.base_path / document['file_path']
        if file_path.exists():
            file_path.unlink()
        
        # Удаляем из БД
        conn = sqlite3.connect(str(self.metadata_db_path))
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM file_metadata WHERE id = ?", (file_id,))
        cursor.execute("DELETE FROM document_versions WHERE file_id = ?", (file_id,))
        cursor.execute("DELETE FROM document_relationships WHERE parent_document_id = ? OR child_document_id = ?", 
                      (file_id, file_id))
        
        conn.commit()
        conn.close()
        
        return True
    
    def create_document_version(self, document_id, new_file_id, created_by=None, changes_description=None):
        """Создание новой версии документа"""
        conn = sqlite3.connect(str(self.metadata_db_path))
        cursor = conn.cursor()
        
        # Получаем следующий номер версии
        cursor.execute("""
            SELECT COALESCE(MAX(version_number), 0) + 1 
            FROM document_versions 
            WHERE document_id = ?
        """, (document_id,))
        
        version_number = cursor.fetchone()[0]
        
        # Создаем новую версию
        cursor.execute("""
            INSERT INTO document_versions 
            (document_id, version_number, file_id, created_by, changes_description)
            VALUES (?, ?, ?, ?, ?)
        """, (document_id, version_number, new_file_id, created_by, changes_description))
        
        conn.commit()
        conn.close()
        
        return version_number
    
    def get_document_versions(self, document_id):
        """Получение всех версий документа"""
        conn = sqlite3.connect(str(self.metadata_db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT dv.*, fm.original_filename, fm.file_size, fm.upload_date
            FROM document_versions dv
            JOIN file_metadata fm ON dv.file_id = fm.id
            WHERE dv.document_id = ?
            ORDER BY dv.version_number DESC
        """, (document_id,))
        
        results = cursor.fetchall()
        columns = [description[0] for description in cursor.description]
        versions = [dict(zip(columns, row)) for row in results]
        
        conn.close()
        return versions
    
    def create_document_relationship(self, parent_id, child_id, relationship_type):
        """Создание связи между документами"""
        conn = sqlite3.connect(str(self.metadata_db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO document_relationships 
            (parent_document_id, child_document_id, relationship_type)
            VALUES (?, ?, ?)
        """, (parent_id, child_id, relationship_type))
        
        conn.commit()
        conn.close()
    
    def get_related_documents(self, document_id):
        """Получение связанных документов"""
        conn = sqlite3.connect(str(self.metadata_db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT dr.*, fm.original_filename, fm.document_type, fm.upload_date
            FROM document_relationships dr
            JOIN file_metadata fm ON (dr.parent_document_id = fm.id OR dr.child_document_id = fm.id)
            WHERE (dr.parent_document_id = ? OR dr.child_document_id = ?) 
            AND fm.id != ?
        """, (document_id, document_id, document_id))
        
        results = cursor.fetchall()
        columns = [description[0] for description in cursor.description]
        related = [dict(zip(columns, row)) for row in results]
        
        conn.close()
        return related
    
    def backup_documents(self, backup_path):
        """Создание резервной копии всех документов"""
        backup_path = Path(backup_path)
        backup_path.mkdir(parents=True, exist_ok=True)
        
        # Копируем файлы
        shutil.copytree(self.base_path, backup_path / "documents", dirs_exist_ok=True)
        
        # Копируем базу метаданных
        shutil.copy2(self.metadata_db_path, backup_path / "metadata.db")
        
        return True
    
    def get_storage_statistics(self):
        """Получение статистики хранилища"""
        conn = sqlite3.connect(str(self.metadata_db_path))
        cursor = conn.cursor()
        
        stats = {}
        
        # Общее количество файлов
        cursor.execute("SELECT COUNT(*) FROM file_metadata")
        stats['total_files'] = cursor.fetchone()[0]
        
        # Общий размер
        cursor.execute("SELECT SUM(file_size) FROM file_metadata")
        stats['total_size'] = cursor.fetchone()[0] or 0
        
        # По типам документов
        cursor.execute("""
            SELECT document_type, COUNT(*), SUM(file_size)
            FROM file_metadata 
            WHERE document_type IS NOT NULL
            GROUP BY document_type
        """)
        
        stats['by_type'] = {}
        for row in cursor.fetchall():
            stats['by_type'][row[0]] = {
                'count': row[1],
                'size': row[2] or 0
            }
        
        # По месяцам
        cursor.execute("""
            SELECT strftime('%Y-%m', upload_date) as month, COUNT(*), SUM(file_size)
            FROM file_metadata 
            GROUP BY strftime('%Y-%m', upload_date)
            ORDER BY month DESC
            LIMIT 12
        """)
        
        stats['by_month'] = {}
        for row in cursor.fetchall():
            stats['by_month'][row[0]] = {
                'count': row[1],
                'size': row[2] or 0
            }
        
        conn.close()
        return stats

# Интеграция сканирования документов
class DocumentScanner:
    def __init__(self, storage_system):
        self.storage = storage_system
        self.scan_settings = {
            'resolution': 300,  # DPI
            'color_mode': 'color',  # color, grayscale, black_white
            'format': 'pdf',  # pdf, jpg, png, tiff
            'quality': 95,  # для JPEG
            'auto_crop': True,
            'auto_rotate': True,
            'auto_enhance': True
        }
    
    def scan_document(self, document_type=None, contract_id=None, order_id=None,
                     physical_location=None, notes=None):
        """Сканирование документа (заглушка - требует интеграции с реальным сканером)"""
        # В реальной реализации здесь будет код для работы со сканером
        # Например, через TWAIN или WIA интерфейсы
        
        # Пример использования библиотеки python-twain:
        # import twain
        # 
        # sm = twain.SourceManager()
        # scanner = sm.open_source()
        # 
        # scanner.request_acquire(show_ui=False, modal_ui=True)
        # rv = scanner.xfer_image_natively()
        # 
        # if rv:
        #     (handle, more_to_come) = rv
        #     # Сохраняем изображение
        #     image = twain.dib_to_bm_file(handle)
        
        # Для демонстрации возвращаем путь к тестовому файлу
        return None
    
    def process_scanned_image(self, image_path, auto_enhance=True):
        """Постобработка отсканированного изображения"""
        if not os.path.exists(image_path):
            return None
        
        try:
            # Загружаем изображение
            image = cv2.imread(image_path)
            if image is None:
                return None
            
            processed_image = image.copy()
            
            if auto_enhance:
                # Автоматическое улучшение качества
                processed_image = self.enhance_image_quality(processed_image)
            
            # Автоматический поворот
            if self.scan_settings['auto_rotate']:
                processed_image = self.auto_rotate_image(processed_image)
            
            # Автоматическая обрезка
            if self.scan_settings['auto_crop']:
                processed_image = self.auto_crop_image(processed_image)
            
            # Сохраняем обработанное изображение
            processed_path = image_path.replace('.', '_processed.')
            cv2.imwrite(processed_path, processed_image)
            
            return processed_path
            
        except Exception as e:
            print(f"Ошибка обработки изображения: {e}")
            return image_path  # Возвращаем оригинал в случае ошибки
    
    def enhance_image_quality(self, image):
        """Улучшение качества изображения"""
        # Преобразуем в оттенки серого для некоторых операций
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Улучшаем контрастность
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        enhanced_gray = clahe.apply(gray)
        
        # Устраняем шум
        denoised = cv2.fastNlMeansDenoising(enhanced_gray)
        
        # Повышаем резкость
        kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
        sharpened = cv2.filter2D(denoised, -1, kernel)
        
        # Преобразуем обратно в цветное изображение
        enhanced = cv2.cvtColor(sharpened, cv2.COLOR_GRAY2BGR)
        
        return enhanced
    
    def auto_rotate_image(self, image):
        """Автоматический поворот изображения"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Используем преобразование Хафа для детекции линий
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        lines = cv2.HoughLines(edges, 1, np.pi/180, threshold=100)
        
        if lines is not None:
            angles = []
            for rho, theta in lines[:10]:  # Берем первые 10 линий
                angle = theta * 180 / np.pi
                angles.append(angle)
            
            # Находим медианный угол
            if angles:
                median_angle = np.median(angles)
                
                # Поворачиваем изображение
                if abs(median_angle - 90) < 45:
                    rotation_angle = median_angle - 90
                else:
                    rotation_angle = median_angle
                
                if abs(rotation_angle) > 1:  # Поворачиваем только если угол значительный
                    center = tuple(np.array(image.shape[1::-1]) / 2)
                    rot_mat = cv2.getRotationMatrix2D(center, rotation_angle, 1.0)
                    return cv2.warpAffine(image, rot_mat, image.shape[1::-1], flags=cv2.INTER_LINEAR)
        
        return image
    
    def auto_crop_image(self, image):
        """Автоматическая обрезка изображения"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Находим контуры
        _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if contours:
            # Находим самый большой прямоугольный контур
            largest_contour = max(contours, key=cv2.contourArea)
            
            # Аппроксимируем контур
            epsilon = 0.02 * cv2.arcLength(largest_contour, True)
            approx = cv2.approxPolyDP(largest_contour, epsilon, True)
            
            if len(approx) == 4:  # Если контур прямоугольный
                # Получаем координаты углов
                pts = approx.reshape(4, 2)
                
                # Сортируем точки: top-left, top-right, bottom-right, bottom-left
                rect = np.zeros((4, 2), dtype="float32")
                s = pts.sum(axis=1)
                rect[0] = pts[np.argmin(s)]
                rect[2] = pts[np.argmax(s)]
                
                diff = np.diff(pts, axis=1)
                rect[1] = pts[np.argmin(diff)]
                rect[3] = pts[np.argmax(diff)]
                
                # Вычисляем размеры нового изображения
                (tl, tr, br, bl) = rect
                widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
                widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
                maxWidth = max(int(widthA), int(widthB))
                
                heightA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
                heightB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
                maxHeight = max(int(heightA), int(heightB))
                
                # Определяем целевые точки
                dst = np.array([
                    [0, 0],
                    [maxWidth - 1, 0],
                    [maxWidth - 1, maxHeight - 1],
                    [0, maxHeight - 1]], dtype="float32")
                
                # Применяем перспективное преобразование
                M = cv2.getPerspectiveTransform(rect, dst)
                warped = cv2.warpPerspective(image, M, (maxWidth, maxHeight))
                
                return warped
        
        return image

# Flask маршруты для работы с документами
def create_document_routes(app, storage_system):
    """Создание маршрутов Flask для работы с документами"""
    
    @app.route('/api/documents/upload', methods=['POST'])
    def upload_document():
        if 'file' not in request.files:
            return jsonify({'error': 'Файл не найден'}), 400
        
        file = request.files['file']
        document_type = request.form.get('document_type')
        contract_id = request.form.get('contract_id')
        order_id = request.form.get('order_id')
        physical_location = request.form.get('physical_location')
        notes = request.form.get('notes')
        tags = request.form.get('tags')
        
        file_id = storage_system.upload_file(
            file=file,
            document_type=document_type,
            contract_id=contract_id,
            order_id=order_id,
            physical_location=physical_location,
            notes=notes,
            tags=tags
        )
        
        if file_id:
            return jsonify({'file_id': file_id, 'status': 'success'})
        else:
            return jsonify({'error': 'Ошибка загрузки файла'}), 500
    
    @app.route('/api/documents/search', methods=['GET'])
    def search_documents():
        query = request.args.get('query')
        document_type = request.args.get('document_type')
        contract_id = request.args.get('contract_id')
        order_id = request.args.get('order_id')
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        tags = request.args.get('tags')
        
        documents = storage_system.search_documents(
            query=query,
            document_type=document_type,
            contract_id=contract_id,
            order_id=order_id,
            date_from=date_from,
            date_to=date_to,
            tags=tags
        )
        
        return jsonify(documents)
    
    @app.route('/api/documents/<file_id>', methods=['GET'])
    def get_document(file_id):
        document = storage_system.get_document_by_id(file_id)
        
        if not document:
            return jsonify({'error': 'Документ не найден'}), 404
        
        return jsonify(document)
    
    @app.route('/api/documents/<file_id>/download', methods=['GET'])
    def download_document(file_id):
        document = storage_system.get_document_by_id(file_id)
        
        if not document:
            return jsonify({'error': 'Документ не найден'}), 404
        
        file_path = storage_system.base_path / document['file_path']
        
        if not file_path.exists():
            return jsonify({'error': 'Файл не найден на диске'}), 404
        
        return send_file(
            str(file_path),
            as_attachment=True,
            download_name=document['original_filename']
        )
    
    @app.route('/api/documents/<file_id>', methods=['DELETE'])
    def delete_document(file_id):
        success = storage_system.delete_document(file_id)
        
        if success:
            return jsonify({'status': 'success'})
        else:
            return jsonify({'error': 'Не удалось удалить документ'}), 500
    
    @app.route('/api/documents/statistics', methods=['GET'])
    def get_storage_statistics():
        stats = storage_system.get_storage_statistics()
        return jsonify(stats)