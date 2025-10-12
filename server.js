const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const rateLimit = require('express-rate-limit');
const path = require('path');
const multer = require('multer');
const { Pool } = require('pg');
const jwt = require('jsonwebtoken');
const bcrypt = require('bcryptjs');
const fs = require('fs').promises;
const sharp = require('sharp');

const app = express();
const PORT = process.env.PORT || 3000;

// Настройка подключения к базе данных
const pool = new Pool({
  user: process.env.DB_USER || 'postgres',
  host: process.env.DB_HOST || 'localhost',
  database: process.env.DB_NAME || 'service_contracts_db',
  password: process.env.DB_PASSWORD || 'password',
  port: process.env.DB_PORT || 5432,
});

// Middleware
app.use(helmet());
app.use(cors());
app.use(express.json({ limit: '50mb' }));
app.use(express.urlencoded({ extended: true, limit: '50mb' }));

// Rate limiting
const limiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 минут
  max: 100 // максимум 100 запросов с одного IP
});
app.use('/api/', limiter);

// Настройка multer для загрузки файлов
const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    const uploadPath = path.join(__dirname, 'uploads');
    cb(null, uploadPath);
  },
  filename: (req, file, cb) => {
    const uniqueSuffix = Date.now() + '-' + Math.round(Math.random() * 1E9);
    cb(null, file.fieldname + '-' + uniqueSuffix + path.extname(file.originalname));
  }
});

const upload = multer({ 
  storage: storage,
  limits: { fileSize: 50 * 1024 * 1024 }, // 50MB
  fileFilter: (req, file, cb) => {
    const allowedTypes = /jpeg|jpg|png|pdf|doc|docx|xls|xlsx/;
    const extname = allowedTypes.test(path.extname(file.originalname).toLowerCase());
    const mimetype = allowedTypes.test(file.mimetype);
    
    if (mimetype && extname) {
      return cb(null, true);
    } else {
      cb(new Error('Неподдерживаемый тип файла'));
    }
  }
});

// Middleware для проверки JWT токена
const authenticateToken = (req, res, next) => {
  const authHeader = req.headers['authorization'];
  const token = authHeader && authHeader.split(' ')[1];

  if (!token) {
    return res.status(401).json({ error: 'Токен доступа не предоставлен' });
  }

  jwt.verify(token, process.env.JWT_SECRET || 'your-secret-key', (err, user) => {
    if (err) {
      return res.status(403).json({ error: 'Недействительный токен' });
    }
    req.user = user;
    next();
  });
};

// Создание папки для загрузок
const createUploadsDir = async () => {
  try {
    await fs.mkdir(path.join(__dirname, 'uploads'), { recursive: true });
    await fs.mkdir(path.join(__dirname, 'uploads', 'documents'), { recursive: true });
    await fs.mkdir(path.join(__dirname, 'uploads', 'scans'), { recursive: true });
  } catch (error) {
    console.error('Ошибка создания папки uploads:', error);
  }
};

// API Routes

// Аутентификация
app.post('/api/auth/login', async (req, res) => {
  try {
    const { username, password } = req.body;
    
    // Простая проверка (в реальном приложении нужно использовать хеширование)
    if (username === 'admin' && password === 'admin') {
      const token = jwt.sign(
        { username: username, role: 'admin' },
        process.env.JWT_SECRET || 'your-secret-key',
        { expiresIn: '24h' }
      );
      
      res.json({ token, user: { username, role: 'admin' } });
    } else {
      res.status(401).json({ error: 'Неверные учетные данные' });
    }
  } catch (error) {
    res.status(500).json({ error: 'Ошибка сервера' });
  }
});

// Контракты
app.get('/api/contracts', authenticateToken, async (req, res) => {
  try {
    const result = await pool.query(`
      SELECT c.*, 
             COUNT(o.id) as orders_count,
             SUM(o.actual_cost) as total_orders_cost
      FROM contracts c
      LEFT JOIN orders o ON c.id = o.contract_id
      GROUP BY c.id
      ORDER BY c.created_at DESC
    `);
    res.json(result.rows);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/contracts', authenticateToken, async (req, res) => {
  try {
    const { contract_number, customer_name, customer_contact, start_date, end_date, total_amount, advance_amount } = req.body;
    
    const result = await pool.query(`
      INSERT INTO contracts (contract_number, customer_name, customer_contact, start_date, end_date, total_amount, advance_amount)
      VALUES ($1, $2, $3, $4, $5, $6, $7)
      RETURNING *
    `, [contract_number, customer_name, customer_contact, start_date, end_date, total_amount, advance_amount]);
    
    res.json(result.rows[0]);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Заказы
app.get('/api/orders', authenticateToken, async (req, res) => {
  try {
    const { contract_id, status } = req.query;
    let query = `
      SELECT o.*, c.contract_number, c.customer_name
      FROM orders o
      LEFT JOIN contracts c ON o.contract_id = c.id
    `;
    const params = [];
    let paramCount = 1;

    if (contract_id) {
      query += ` WHERE o.contract_id = $${paramCount}`;
      params.push(contract_id);
      paramCount++;
    }

    if (status) {
      query += contract_id ? ` AND o.status = $${paramCount}` : ` WHERE o.status = $${paramCount}`;
      params.push(status);
    }

    query += ` ORDER BY o.created_at DESC`;

    const result = await pool.query(query, params);
    res.json(result.rows);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/orders', authenticateToken, async (req, res) => {
  try {
    const { contract_id, order_number, order_date, description, location, priority, estimated_cost } = req.body;
    
    const result = await pool.query(`
      INSERT INTO orders (contract_id, order_number, order_date, description, location, priority, estimated_cost)
      VALUES ($1, $2, $3, $4, $5, $6, $7)
      RETURNING *
    `, [contract_id, order_number, order_date, description, location, priority, estimated_cost]);
    
    res.json(result.rows[0]);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Материалы
app.get('/api/materials', authenticateToken, async (req, res) => {
  try {
    const { search } = req.query;
    let query = `
      SELECT m.*, ws.quantity as stock_quantity, ws.reserved_quantity
      FROM materials m
      LEFT JOIN warehouse_stock ws ON m.id = ws.material_id
    `;
    const params = [];

    if (search) {
      query += ` WHERE m.name ILIKE $1 OR m.material_code ILIKE $1`;
      params.push(`%${search}%`);
    }

    query += ` ORDER BY m.name`;

    const result = await pool.query(query, params);
    res.json(result.rows);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Командировки
app.get('/api/business-trips', authenticateToken, async (req, res) => {
  try {
    const result = await pool.query(`
      SELECT bt.*, e.full_name as employee_name, o.order_number, c.contract_number, c.customer_name
      FROM business_trips bt
      LEFT JOIN employees e ON bt.employee_id = e.id
      LEFT JOIN orders o ON bt.order_id = o.id
      LEFT JOIN contracts c ON o.contract_id = c.id
      ORDER BY bt.start_date DESC
    `);
    res.json(result.rows);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Финансовые операции
app.get('/api/financial-operations', authenticateToken, async (req, res) => {
  try {
    const { contract_id } = req.query;
    let query = `
      SELECT fo.*, c.contract_number, c.customer_name
      FROM financial_operations fo
      LEFT JOIN contracts c ON fo.contract_id = c.id
    `;
    const params = [];

    if (contract_id) {
      query += ` WHERE fo.contract_id = $1`;
      params.push(contract_id);
    }

    query += ` ORDER BY fo.operation_date DESC`;

    const result = await pool.query(query, params);
    res.json(result.rows);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Документы
app.get('/api/documents', authenticateToken, async (req, res) => {
  try {
    const { document_type, related_contract_id } = req.query;
    let query = `
      SELECT d.*, c.contract_number, c.customer_name
      FROM documents d
      LEFT JOIN contracts c ON d.related_contract_id = c.id
    `;
    const params = [];
    let paramCount = 1;

    if (document_type) {
      query += ` WHERE d.document_type = $${paramCount}`;
      params.push(document_type);
      paramCount++;
    }

    if (related_contract_id) {
      query += document_type ? ` AND d.related_contract_id = $${paramCount}` : ` WHERE d.related_contract_id = $${paramCount}`;
      params.push(related_contract_id);
    }

    query += ` ORDER BY d.created_at DESC`;

    const result = await pool.query(query, params);
    res.json(result.rows);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Загрузка документов
app.post('/api/documents/upload', authenticateToken, upload.single('file'), async (req, res) => {
  try {
    if (!req.file) {
      return res.status(400).json({ error: 'Файл не загружен' });
    }

    const { document_type, title, description, related_contract_id, physical_location } = req.body;
    
    // Обработка изображений для уменьшения размера
    if (req.file.mimetype.startsWith('image/')) {
      const processedPath = req.file.path.replace(/\.[^/.]+$/, '_processed.jpg');
      await sharp(req.file.path)
        .jpeg({ quality: 80 })
        .toFile(processedPath);
      
      // Удаляем оригинал и переименовываем обработанный файл
      await fs.unlink(req.file.path);
      await fs.rename(processedPath, req.file.path);
    }

    const result = await pool.query(`
      INSERT INTO documents (document_type, title, description, file_path, file_size, mime_type, related_contract_id, physical_location, created_by)
      VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
      RETURNING *
    `, [document_type, title, description, req.file.path, req.file.size, req.file.mimetype, related_contract_id, physical_location, req.user.username]);
    
    res.json(result.rows[0]);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Скачивание документов
app.get('/api/documents/:id/download', authenticateToken, async (req, res) => {
  try {
    const result = await pool.query('SELECT * FROM documents WHERE id = $1', [req.params.id]);
    
    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'Документ не найден' });
    }

    const document = result.rows[0];
    const filePath = path.join(__dirname, document.file_path);
    
    res.download(filePath, document.title);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Аналитика и отчеты
app.get('/api/analytics/contracts-summary', authenticateToken, async (req, res) => {
  try {
    const result = await pool.query(`
      SELECT 
        COUNT(*) as total_contracts,
        COUNT(CASE WHEN status = 'active' THEN 1 END) as active_contracts,
        SUM(total_amount) as total_contracts_value,
        SUM(advance_amount) as total_advances,
        SUM(total_amount - advance_amount) as remaining_amount
      FROM contracts
    `);
    res.json(result.rows[0]);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.get('/api/analytics/materials-deficit', authenticateToken, async (req, res) => {
  try {
    const result = await pool.query(`
      SELECT 
        m.material_code,
        m.name,
        m.unit,
        COALESCE(ws.quantity, 0) as available_quantity,
        COALESCE(ws.reserved_quantity, 0) as reserved_quantity,
        COALESCE(ws.quantity, 0) - COALESCE(ws.reserved_quantity, 0) as free_quantity,
        SUM(om.required_quantity) as total_required
      FROM materials m
      LEFT JOIN warehouse_stock ws ON m.id = ws.material_id
      LEFT JOIN order_materials om ON m.id = om.material_id
      LEFT JOIN orders o ON om.order_id = o.id
      WHERE o.status IN ('pending', 'in_progress')
      GROUP BY m.id, m.material_code, m.name, m.unit, ws.quantity, ws.reserved_quantity
      HAVING COALESCE(ws.quantity, 0) - COALESCE(ws.reserved_quantity, 0) < SUM(om.required_quantity)
      ORDER BY (SUM(om.required_quantity) - (COALESCE(ws.quantity, 0) - COALESCE(ws.reserved_quantity, 0))) DESC
    `);
    res.json(result.rows);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Уведомления
app.get('/api/notifications', authenticateToken, async (req, res) => {
  try {
    const result = await pool.query(`
      SELECT * FROM notifications 
      WHERE user_id = $1 
      ORDER BY created_at DESC 
      LIMIT 50
    `, [req.user.username]);
    res.json(result.rows);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.put('/api/notifications/:id/read', authenticateToken, async (req, res) => {
  try {
    const result = await pool.query(`
      UPDATE notifications 
      SET is_read = true 
      WHERE id = $1 AND user_id = $2
      RETURNING *
    `, [req.params.id, req.user.username]);
    res.json(result.rows[0]);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Статические файлы
app.use(express.static(path.join(__dirname, 'public')));

// Главная страница
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

// Обработка ошибок
app.use((error, req, res, next) => {
  console.error(error);
  res.status(500).json({ error: 'Внутренняя ошибка сервера' });
});

// Инициализация сервера
const startServer = async () => {
  try {
    await createUploadsDir();
    await pool.connect();
    console.log('Подключение к базе данных установлено');
    
    app.listen(PORT, () => {
      console.log(`Сервер запущен на порту ${PORT}`);
      console.log(`Откройте http://localhost:${PORT} в браузере`);
    });
  } catch (error) {
    console.error('Ошибка запуска сервера:', error);
    process.exit(1);
  }
};

startServer();