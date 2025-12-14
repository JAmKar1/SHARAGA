import sqlite3
import hashlib
import secrets
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, redirect, url_for, session, request, flash

app = Flask(__name__)
app.secret_key = 'your_secret_key_change_in_production'
app.config['DATABASE'] = 'university.db'


# ==================== ПРОСТЫЕ ФУНКЦИИ ДЛЯ ПАРОЛЕЙ ====================

def generate_password_hash(password):
    """Простая функция хэширования пароля"""
    salt = secrets.token_hex(8)
    hash_obj = hashlib.sha256((password + salt).encode())
    password_hash = hash_obj.hexdigest()
    return f"sha256${salt}${password_hash}"


def check_password_hash(stored_hash, password):
    """Проверка пароля"""
    try:
        algorithm, salt, stored_password_hash = stored_hash.split('$')
        hash_obj = hashlib.sha256((password + salt).encode())
        entered_hash = hash_obj.hexdigest()
        return stored_password_hash == entered_hash
    except:
        return False


# ==================== ФУНКЦИИ БАЗЫ ДАННЫХ ====================

def get_db_connection():
    """Соединение с базой данных"""
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row  # Возвращать строки как словари
    return conn


def init_database():
    """Инициализация базы данных"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Таблица пользователей
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        full_name TEXT NOT NULL,
        user_type TEXT NOT NULL CHECK(user_type IN ('student', 'teacher', 'starosta', 'admin')),
        email TEXT UNIQUE,
        phone TEXT,
        group_name TEXT,
        course INTEGER,
        department TEXT,
        position TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Проверяем, есть ли администратор
    cursor.execute("SELECT COUNT(*) as count FROM users WHERE user_type = 'admin'")
    admin_count = cursor.fetchone()['count']

    if admin_count == 0:
        # Создаем администратора по умолчанию
        admin_hash = generate_password_hash('admin123')
        cursor.execute('''
        INSERT INTO users (username, password_hash, full_name, user_type, email)
        VALUES (?, ?, ?, ?, ?)
        ''', ('admin', admin_hash, 'Администратор системы', 'admin', 'admin@university.ru'))
        print("Создан администратор: admin / admin123")

    conn.commit()
    conn.close()


# Инициализируем базу данных при старте
init_database()


# ==================== ФУНКЦИИ АВТОРИЗАЦИИ ====================

class AuthSystem:
    """Простая система аутентификации"""

    @staticmethod
    def register_user(username, password, full_name, user_type, **kwargs):
        """Регистрация нового пользователя"""
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            # Проверяем, существует ли пользователь
            cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
            if cursor.fetchone():
                return {'success': False, 'message': 'Пользователь с таким логином уже существует'}

            # Хэшируем пароль
            password_hash = generate_password_hash(password)

            # Сохраняем пользователя
            cursor.execute('''
            INSERT INTO users (username, password_hash, full_name, user_type, 
                             email, phone, group_name, course, department, position)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (username, password_hash, full_name, user_type,
                  kwargs.get('email'), kwargs.get('phone'),
                  kwargs.get('group'), kwargs.get('course'),
                  kwargs.get('department'), kwargs.get('position')))

            user_id = cursor.lastrowid
            conn.commit()

            return {'success': True, 'user_id': user_id}

        except sqlite3.IntegrityError as e:
            return {'success': False, 'message': f'Ошибка базы данных: {str(e)}'}
        finally:
            conn.close()

    @staticmethod
    def authenticate(username, password):
        """Аутентификация пользователя"""
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('''
        SELECT id, username, password_hash, full_name, user_type 
        FROM users WHERE username = ?
        ''', (username,))

        user = cursor.fetchone()
        conn.close()

        if not user:
            return {'success': False, 'message': 'Пользователь не найден'}

        # Проверяем пароль
        if not check_password_hash(user['password_hash'], password):
            return {'success': False, 'message': 'Неверный пароль'}

        # Возвращаем данные пользователя
        return {
            'success': True,
            'user': {
                'id': user['id'],
                'username': user['username'],
                'full_name': user['full_name'],
                'user_type': user['user_type']
            }
        }

    @staticmethod
    def get_user_by_id(user_id):
        """Получение пользователя по ID"""
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('''
        SELECT id, username, full_name, user_type, email, phone, 
               group_name, course, department, position 
        FROM users WHERE id = ?
        ''', (user_id,))

        user = cursor.fetchone()
        conn.close()

        if user:
            return dict(user)  # Преобразуем в словарь
        return None

    @staticmethod
    def get_all_users():
        """Получение всех пользователей"""
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('''
        SELECT id, username, full_name, user_type, email, phone, 
               group_name, course, department, position, created_at 
        FROM users ORDER BY user_type, full_name
        ''')

        users = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return users


# ==================== ДЕКОРАТОРЫ ДЛЯ ПРОВЕРКИ ДОСТУПА ====================

def login_required(f):
    """Требует авторизации"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Пожалуйста, войдите в систему', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)

    return decorated_function


def role_required(*allowed_roles):
    """Требует определенной роли"""

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_type' not in session:
                flash('Доступ запрещен', 'error')
                return redirect(url_for('login'))

            if session['user_type'] not in allowed_roles:
                flash(f'Доступ только для: {", ".join(allowed_roles)}', 'error')
                return redirect(url_for('dashboard'))

            return f(*args, **kwargs)

        return decorated_function

    return decorator


# ==================== МАРШРУТЫ ====================

@app.route('/')
def index():
    """Главная страница"""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Страница входа для всех"""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
            flash('Заполните все поля', 'error')
            return render_template('login.html')

        auth_result = AuthSystem.authenticate(username, password)

        if auth_result['success']:
            user = auth_result['user']

            # Сохраняем в сессии
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['user_type'] = user['user_type']
            session['name'] = user['full_name']

            flash(f'Добро пожаловать, {user["full_name"]}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash(auth_result['message'], 'error')

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    """Регистрация для всех типов пользователей"""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        # Основные данные
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        full_name = request.form.get('full_name')
        user_type = request.form.get('user_type', 'student')

        # Дополнительные данные в зависимости от типа
        email = request.form.get('email')
        phone = request.form.get('phone')

        # Данные для студентов и старост
        group = request.form.get('group')
        course = request.form.get('course')

        # Данные для преподавателей
        department = request.form.get('department')
        position = request.form.get('position')

        # Валидация
        if not all([username, password, confirm_password, full_name]):
            flash('Заполните все обязательные поля', 'error')
            return render_template('register.html')

        if password != confirm_password:
            flash('Пароли не совпадают', 'error')
            return render_template('register.html')

        if len(password) < 6:
            flash('Пароль должен быть не менее 6 символов', 'error')
            return render_template('register.html')

        # Регистрируем пользователя
        result = AuthSystem.register_user(
            username=username,
            password=password,
            full_name=full_name,
            user_type=user_type,
            email=email,
            phone=phone,
            group=group,
            course=course,
            department=department,
            position=position
        )

        if result['success']:
            flash('Регистрация успешна! Теперь войдите в систему.', 'success')
            return redirect(url_for('login'))
        else:
            flash(result['message'], 'error')

    return render_template('register.html')


@app.route('/dashboard')
@login_required
def dashboard():
    """Общая панель управления для всех"""
    user_data = AuthSystem.get_user_by_id(session['user_id'])

    # В зависимости от роли показываем разную информацию
    if session['user_type'] == 'admin':
        users = AuthSystem.get_all_users()
        return render_template('dashboard.html', user=user_data, users=users)
    else:
        return render_template('dashboard.html', user=user_data)


@app.route('/profile')
@login_required
def profile():
    """Профиль пользователя"""
    user_data = AuthSystem.get_user_by_id(session['user_id'])
    return render_template('profile.html', user=user_data)


@app.route('/users')
@login_required
@role_required('admin')
def users_list():
    """Список всех пользователей (только для админа)"""
    users = AuthSystem.get_all_users()
    return render_template('users.html', users=users)


@app.route('/logout')
def logout():
    """Выход из системы"""
    session.clear()
    flash('Вы успешно вышли из системы', 'info')
    return redirect(url_for('index'))


# ==================== ОБЩИЕ ФУНКЦИИ ====================

@app.route('/schedule')
@login_required
def schedule():
    """Расписание (доступно всем)"""
    return render_template('schedule.html',
                           user_type=session['user_type'],
                           name=session['name'])


@app.route('/events')
@login_required
def events():
    """Мероприятия (доступно всем)"""
    return render_template('events.html',
                           user_type=session['user_type'],
                           name=session['name'])


@app.route('/messages')
@login_required
def messages():
    """Сообщения (доступно всем)"""
    return render_template('messages.html',
                           user_type=session['user_type'],
                           name=session['name'])


@app.route('/tasks')
@login_required
def tasks():
    """Задачи (доступно всем)"""
    return render_template('tasks.html',
                           user_type=session['user_type'],
                           name=session['name'])


# ==================== ЗАПУСК ПРИЛОЖЕНИЯ ====================

if __name__ == '__main__':
    print("=" * 50)
    print("СИСТЕМА УЧЕБНОГО ПОРТАЛА")
    print("=" * 50)
    print("Доступные учетные записи для тестирования:")
    print("1. Администратор: admin / admin123")
    print("2. Можете зарегистрироваться с любым типом пользователя")
    print("=" * 50)
    print("База данных: university.db")
    print("=" * 50)

    app.run(debug=True, host='0.0.0.0', port=5000)