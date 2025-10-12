from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import os
import json
from decimal import Decimal
import sqlite3

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///contract_management.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'

# Создаем папки если их нет
for folder in ['uploads', 'scans', 'documents', 'templates']:
    if not os.path.exists(folder):
        os.makedirs(folder)

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Модели базы данных
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    full_name = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(50), default='manager')

class Contract(db.Model):
    __tablename__ = 'contracts'
    
    id = db.Column(db.Integer, primary_key=True)
    contract_number = db.Column(db.String(100), unique=True, nullable=False)
    contract_name = db.Column(db.String(500), nullable=False)
    customer = db.Column(db.String(300), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date)
    total_amount = db.Column(db.Numeric(15, 2))
    advance_amount = db.Column(db.Numeric(15, 2))
    final_amount = db.Column(db.Numeric(15, 2))
    status = db.Column(db.String(50), default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Связи
    orders = db.relationship('Order', backref='contract', lazy=True)
    payments = db.relationship('Payment', backref='contract', lazy=True)
    subaccounts = db.relationship('ContractSubaccount', backref='contract', lazy=True)

class ContractSubaccount(db.Model):
    __tablename__ = 'contract_subaccounts'
    
    id = db.Column(db.Integer, primary_key=True)
    contract_id = db.Column(db.Integer, db.ForeignKey('contracts.id'), nullable=False)
    account_code = db.Column(db.String(100), nullable=False)
    balance = db.Column(db.Numeric(15, 2), default=0)
    reserved_amount = db.Column(db.Numeric(15, 2), default=0)
    available_amount = db.Column(db.Numeric(15, 2), default=0)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

class Order(db.Model):
    __tablename__ = 'orders'
    
    id = db.Column(db.Integer, primary_key=True)
    contract_id = db.Column(db.Integer, db.ForeignKey('contracts.id'), nullable=False)
    order_number = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    location = db.Column(db.String(300))
    region = db.Column(db.String(100))
    device_type = db.Column(db.String(200))
    device_serial = db.Column(db.String(200))
    defect_report_date = db.Column(db.Date)
    planned_start_date = db.Column(db.Date)
    planned_end_date = db.Column(db.Date)
    actual_start_date = db.Column(db.Date)
    actual_end_date = db.Column(db.Date)
    status = db.Column(db.String(50), default='created')
    priority = db.Column(db.String(20), default='normal')
    estimated_cost = db.Column(db.Numeric(15, 2))
    actual_cost = db.Column(db.Numeric(15, 2))
    is_business_trip = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Связи
    materials = db.relationship('OrderMaterial', backref='order', lazy=True)
    business_trips = db.relationship('BusinessTrip', backref='order', lazy=True)

class Material(db.Model):
    __tablename__ = 'materials'
    
    id = db.Column(db.Integer, primary_key=True)
    part_number = db.Column(db.String(100), unique=True, nullable=False)
    name = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text)
    unit = db.Column(db.String(50))
    current_stock = db.Column(db.Integer, default=0)
    min_stock = db.Column(db.Integer, default=0)
    price = db.Column(db.Numeric(10, 2))
    supplier = db.Column(db.String(300))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class OrderMaterial(db.Model):
    __tablename__ = 'order_materials'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    material_id = db.Column(db.Integer, db.ForeignKey('materials.id'), nullable=False)
    required_quantity = db.Column(db.Integer, nullable=False)
    allocated_quantity = db.Column(db.Integer, default=0)
    source = db.Column(db.String(50))
    status = db.Column(db.String(50), default='required')
    notes = db.Column(db.Text)
    
    material = db.relationship('Material', backref='order_materials')

class Employee(db.Model):
    __tablename__ = 'employees'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_number = db.Column(db.String(50), unique=True)
    full_name = db.Column(db.String(200), nullable=False)
    position = db.Column(db.String(100))
    department = db.Column(db.String(100))
    phone = db.Column(db.String(50))
    email = db.Column(db.String(100))
    passport_data = db.Column(db.String(200))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    business_trips = db.relationship('BusinessTrip', backref='employee', lazy=True)

class BusinessTrip(db.Model):
    __tablename__ = 'business_trips'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'))
    destination = db.Column(db.String(300), nullable=False)
    purpose = db.Column(db.Text)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    extension_date = db.Column(db.Date)
    status = db.Column(db.String(50), default='planned')
    travel_order_number = db.Column(db.String(100))
    accommodation = db.Column(db.String(300))
    transport_info = db.Column(db.Text)
    daily_allowance = db.Column(db.Numeric(10, 2))
    total_cost = db.Column(db.Numeric(15, 2))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Payment(db.Model):
    __tablename__ = 'payments'
    
    id = db.Column(db.Integer, primary_key=True)
    contract_id = db.Column(db.Integer, db.ForeignKey('contracts.id'), nullable=False)
    payment_type = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Numeric(15, 2), nullable=False)
    payment_date = db.Column(db.Date)
    expected_date = db.Column(db.Date)
    status = db.Column(db.String(50), default='pending')
    invoice_number = db.Column(db.String(100))
    payment_document = db.Column(db.String(200))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Document(db.Model):
    __tablename__ = 'documents'
    
    id = db.Column(db.Integer, primary_key=True)
    document_type = db.Column(db.String(100), nullable=False)
    document_number = db.Column(db.String(100))
    title = db.Column(db.String(500), nullable=False)
    file_path = db.Column(db.String(1000))
    scan_path = db.Column(db.String(1000))
    physical_location = db.Column(db.String(500))
    contract_id = db.Column(db.Integer, db.ForeignKey('contracts.id'))
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'))
    business_trip_id = db.Column(db.Integer, db.ForeignKey('business_trips.id'))
    created_date = db.Column(db.Date)
    signed_date = db.Column(db.Date)
    status = db.Column(db.String(50), default='draft')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Маршруты
@app.route('/')
@login_required
def dashboard():
    # Собираем данные для дашборда
    contracts = Contract.query.filter_by(status='active').all()
    urgent_orders = Order.query.filter_by(priority='urgent', status='in_progress').all()
    active_trips = BusinessTrip.query.filter(BusinessTrip.status.in_(['planned', 'in_progress'])).all()
    
    # Дефицит материалов
    materials_deficit = db.session.execute("""
        SELECT m.part_number, m.name, m.current_stock, m.min_stock,
               COALESCE(SUM(om.required_quantity - om.allocated_quantity), 0) as deficit
        FROM materials m
        LEFT JOIN order_materials om ON m.id = om.material_id 
        WHERE m.current_stock < m.min_stock OR om.status != 'allocated'
        GROUP BY m.id
        HAVING deficit > 0
    """).fetchall()
    
    return render_template('dashboard.html', 
                         contracts=contracts,
                         urgent_orders=urgent_orders,
                         active_trips=active_trips,
                         materials_deficit=materials_deficit)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Неверное имя пользователя или пароль')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/contracts')
@login_required
def contracts():
    contracts = Contract.query.all()
    return render_template('contracts.html', contracts=contracts)

@app.route('/contracts/new', methods=['GET', 'POST'])
@login_required
def new_contract():
    if request.method == 'POST':
        contract = Contract(
            contract_number=request.form['contract_number'],
            contract_name=request.form['contract_name'],
            customer=request.form['customer'],
            start_date=datetime.strptime(request.form['start_date'], '%Y-%m-%d').date(),
            end_date=datetime.strptime(request.form['end_date'], '%Y-%m-%d').date() if request.form['end_date'] else None,
            total_amount=Decimal(request.form['total_amount']) if request.form['total_amount'] else None,
            advance_amount=Decimal(request.form['advance_amount']) if request.form['advance_amount'] else None
        )
        
        db.session.add(contract)
        db.session.commit()
        
        # Создаем субсчет
        subaccount = ContractSubaccount(
            contract_id=contract.id,
            account_code=request.form['account_code'],
            balance=contract.advance_amount or 0
        )
        db.session.add(subaccount)
        db.session.commit()
        
        flash('Контракт успешно создан')
        return redirect(url_for('contracts'))
    
    return render_template('new_contract.html')

@app.route('/orders')
@login_required
def orders():
    contract_id = request.args.get('contract_id')
    if contract_id:
        orders = Order.query.filter_by(contract_id=contract_id).all()
    else:
        orders = Order.query.all()
    
    contracts = Contract.query.filter_by(status='active').all()
    return render_template('orders.html', orders=orders, contracts=contracts)

@app.route('/orders/new', methods=['GET', 'POST'])
@login_required
def new_order():
    if request.method == 'POST':
        order = Order(
            contract_id=request.form['contract_id'],
            order_number=request.form['order_number'],
            description=request.form['description'],
            location=request.form['location'],
            region=request.form['region'],
            device_type=request.form['device_type'],
            device_serial=request.form['device_serial'],
            planned_start_date=datetime.strptime(request.form['planned_start_date'], '%Y-%m-%d').date() if request.form['planned_start_date'] else None,
            planned_end_date=datetime.strptime(request.form['planned_end_date'], '%Y-%m-%d').date() if request.form['planned_end_date'] else None,
            priority=request.form['priority'],
            estimated_cost=Decimal(request.form['estimated_cost']) if request.form['estimated_cost'] else None,
            is_business_trip=bool(request.form.get('is_business_trip'))
        )
        
        db.session.add(order)
        db.session.commit()
        flash('Заказ успешно создан')
        return redirect(url_for('orders'))
    
    contracts = Contract.query.filter_by(status='active').all()
    return render_template('new_order.html', contracts=contracts)

@app.route('/materials')
@login_required
def materials():
    materials = Material.query.all()
    return render_template('materials.html', materials=materials)

@app.route('/business_trips')
@login_required
def business_trips():
    trips = BusinessTrip.query.all()
    return render_template('business_trips.html', trips=trips)

@app.route('/analytics')
@login_required
def analytics():
    # Финансовая аналитика
    contract_summary = db.session.execute("""
        SELECT c.contract_number, c.contract_name, c.total_amount,
               COALESCE(cs.balance, 0) as balance,
               COUNT(o.id) as total_orders,
               SUM(CASE WHEN o.status = 'completed' THEN 1 ELSE 0 END) as completed_orders,
               SUM(CASE WHEN p.status = 'received' THEN p.amount ELSE 0 END) as received_payments
        FROM contracts c
        LEFT JOIN contract_subaccounts cs ON c.id = cs.contract_id
        LEFT JOIN orders o ON c.id = o.contract_id
        LEFT JOIN payments p ON c.id = p.contract_id
        WHERE c.status = 'active'
        GROUP BY c.id
    """).fetchall()
    
    return render_template('analytics.html', contract_summary=contract_summary)

@app.route('/api/contract_balance/<int:contract_id>')
@login_required
def get_contract_balance(contract_id):
    subaccount = ContractSubaccount.query.filter_by(contract_id=contract_id).first()
    if subaccount:
        return jsonify({
            'balance': float(subaccount.balance),
            'available': float(subaccount.available_amount),
            'reserved': float(subaccount.reserved_amount)
        })
    return jsonify({'error': 'Субсчет не найден'}), 404

def init_db():
    """Инициализация базы данных"""
    with app.app_context():
        db.create_all()
        
        # Создаем пользователя по умолчанию
        if not User.query.filter_by(username='admin').first():
            admin = User(
                username='admin',
                password_hash=generate_password_hash('admin123'),
                full_name='Администратор',
                role='admin'
            )
            db.session.add(admin)
            db.session.commit()

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)