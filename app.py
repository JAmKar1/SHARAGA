from flask import Flask, render_template, redirect, url_for, session, request, flash
import sqlite3
import os
import time

app = Flask(__name__)
app.secret_key = 'your_secret_key_here_change_this'  # Важно изменить на свой ключ!

# Импорт ваших модулей
try:
    from star import StarostaModule
    from rasp import ScheduleModule
    from prepod import TeachersModule
    from mero import EventsModule
    from praktika import PracticeModule
    from repe import TutoringModule

    # Инициализация модулей
    starosta_module = StarostaModule()
    schedule_module = ScheduleModule()
    teachers_module = TeachersModule()
    events_module = EventsModule()
    practice_module = PracticeModule()
    tutoring_module = TutoringModule()
except ImportError as e:
    print(f"⚠️  Предупреждение: не удалось загрузить модули: {e}")


    # Создаем заглушки
    class DummyModule:
        def get_students_data(self, *args): return []

        def get_reports_data(self): return []

        def get_info_for_headman(self): return {}

        def get_messages(self): return []

        def get_schedule(self, *args): return []

        def get_course_days(self, *args): return []

        def get_exams_schedule(self, *args): return []

        def get_tutoring_data(self): return {}

        def get_events(self): return []

        def get_all_teachers(self): return []

        def get_departments(self): return []

        def get_practice_data(self): return {}


    starosta_module = schedule_module = teachers_module = events_module = practice_module = tutoring_module = DummyModule()


# ==================== БАЗА ДАННЫХ ====================

def init_db():
    """Создание базы данных и таблиц"""
    print("🔄 Инициализация базы данных...")
    conn = None
    try:
        conn = sqlite3.connect('university.db')
        cursor = conn.cursor()

        # Удаляем старую таблицу если существует (для пересоздания)
        cursor.execute('DROP TABLE IF EXISTS users')

        # Таблица пользователей
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            full_name TEXT NOT NULL,
            user_type TEXT NOT NULL CHECK(user_type IN ('student', 'teacher', 'starosta', 'admin')),
            email TEXT,
            phone TEXT,
            group_name TEXT,
            course INTEGER,
            department TEXT,
            position TEXT,
            created_by TEXT DEFAULT 'system',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        # Проверяем, есть ли администратор
        cursor.execute("SELECT COUNT(*) FROM users WHERE user_type = 'admin'")
        if cursor.fetchone()[0] == 0:
            # Создаем администратора по умолчанию
            cursor.execute('''
            INSERT INTO users (username, password, full_name, user_type, email, created_by)
            VALUES (?, ?, ?, ?, ?, ?)
            ''', ('admin', 'admin123', 'Администратор системы', 'admin', 'admin@university.ru', 'system'))
            print("✅ Создан администратор: admin / admin123")

        conn.commit()
        print("✅ База данных успешно инициализирована")
    except Exception as e:
        print(f"❌ Ошибка при создании БД: {e}")
        raise
    finally:
        if conn:
            conn.close()


def check_and_fix_db():
    """Проверка и исправление базы данных"""
    db_exists = os.path.exists('university.db')
    print(f"📁 Файл БД существует: {db_exists}")

    if not db_exists:
        print("📝 Создаю новую базу данных...")
        init_db()
        return True

    # Проверяем структуру существующей БД
    conn = None
    try:
        conn = sqlite3.connect('university.db')
        cursor = conn.cursor()

        # Проверяем существование таблицы users
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        if not cursor.fetchone():
            print("⚠️  Таблица users не найдена, создаю заново...")
            conn.close()
            init_db()
            return True

        # Проверяем структуру таблицы
        cursor.execute("SELECT * FROM users LIMIT 1")
        columns = [description[0] for description in cursor.description]

        required_columns = ['id', 'username', 'password', 'full_name', 'user_type']
        missing_columns = [col for col in required_columns if col not in columns]

        if missing_columns:
            print(f"⚠️  Отсутствуют столбцы: {missing_columns}. Пересоздаю таблицу...")
            conn.close()
            init_db()
            return True

        print("✅ Структура базы данных в порядке")
        return True
    except Exception as e:
        print(f"❌ Ошибка при проверке БД: {e}")
        print("🔄 Пытаюсь восстановить базу данных...")
        try:
            if conn:
                conn.close()
            init_db()
            return True
        except Exception as e2:
            print(f"❌ Не удалось восстановить БД: {e2}")
            return False
    finally:
        if conn:
            conn.close()


# ==================== ФУНКЦИИ ДЛЯ РАБОТЫ С БД ====================

def get_db_connection():
    """Получить соединение с базой данных"""
    try:
        conn = sqlite3.connect('university.db', timeout=10.0)
        conn.row_factory = sqlite3.Row
        # Включаем WAL режим для лучшей производительности
        conn.execute('PRAGMA journal_mode=WAL')
        return conn
    except sqlite3.OperationalError as e:
        if "locked" in str(e):
            # Ждем и пробуем снова
            time.sleep(0.1)
            return get_db_connection()
        raise


def register_user(username, password, full_name, user_type, created_by='system', **kwargs):
    """Регистрация нового пользователя"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Проверяем, не существует ли уже пользователь
        cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
        if cursor.fetchone():
            return False, "Пользователь с таким логином уже существует"

        # Подготавливаем данные для вставки
        email = kwargs.get('email')
        phone = kwargs.get('phone')
        group = kwargs.get('group')
        course = kwargs.get('course')
        department = kwargs.get('department')
        position = kwargs.get('position')

        # Для числовых полей проверяем корректность
        if course and not str(course).isdigit():
            course = None

        cursor.execute('''
        INSERT INTO users (username, password, full_name, user_type, created_by,
                          email, phone, group_name, course, department, position)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (username, password, full_name, user_type, created_by,
              email, phone, group, course, department, position))

        conn.commit()
        return True, "Пользователь успешно создан"
    except sqlite3.IntegrityError as e:
        return False, f"Ошибка базы данных: {str(e)}"
    except Exception as e:
        print(f"❌ Ошибка регистрации: {e}")
        return False, f"Ошибка при регистрации: {str(e)}"
    finally:
        if conn:
            conn.close()


def login_user(username, password):
    """Вход пользователя"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('''
        SELECT id, username, password, full_name, user_type, email, phone, 
               group_name, course, department, position, created_by, created_at
        FROM users WHERE username = ? AND password = ?
        ''', (username, password))

        user = cursor.fetchone()
        return dict(user) if user else None
    except Exception as e:
        print(f"❌ Ошибка входа: {e}")
        return None
    finally:
        if conn:
            conn.close()


def get_user_by_id(user_id):
    """Получить пользователя по ID"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('''
        SELECT id, username, full_name, user_type, email, phone, 
               group_name, course, department, position, created_by, created_at
        FROM users WHERE id = ?
        ''', (user_id,))

        user = cursor.fetchone()
        return dict(user) if user else None
    except Exception as e:
        print(f"❌ Ошибка получения пользователя: {e}")
        return None
    finally:
        if conn:
            conn.close()


def get_all_users():
    """Получить всех пользователей"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM users ORDER BY user_type, full_name')
        users = [dict(row) for row in cursor.fetchall()]
        return users
    except Exception as e:
        print(f"❌ Ошибка получения списка пользователей: {e}")
        return []
    finally:
        if conn:
            conn.close()


def delete_user(user_id):
    """Удалить пользователя"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        print(f"❌ Ошибка удаления пользователя: {e}")
        return False
    finally:
        if conn:
            conn.close()


# ==================== ДЕКОРАТОРЫ ДЛЯ ПРОВЕРКИ АВТОРИЗАЦИИ ====================

def login_required(f):
    """Декоратор для проверки авторизации"""
    from functools import wraps

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Пожалуйста, войдите в систему', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)

    return decorated_function


def admin_required(f):
    """Декоратор для проверки прав администратора"""
    from functools import wraps

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Пожалуйста, войдите в систему', 'warning')
            return redirect(url_for('login'))

        user_data = get_user_by_id(session['user_id'])
        if not user_data or user_data['user_type'] != 'admin':
            flash('Доступ только для администратора', 'error')
            return redirect(url_for('home'))

        return f(*args, **kwargs)

    return decorated_function


# ==================== МАРШРУТЫ ====================

@app.route('/')
def home():
    """Главная страница"""
    if 'user_id' in session:
        user_data = get_user_by_id(session['user_id'])
        return render_template('index.html', user=user_data)
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Страница входа"""
    if 'user_id' in session:
        return redirect(url_for('home'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if username and password:
            user = login_user(username, password)

            if user:
                # Сохраняем данные в сессии
                session['user_id'] = user['id']
                session['username'] = user['username']
                session['user_type'] = user['user_type']
                session['name'] = user['full_name']

                flash(f'Добро пожаловать, {user["full_name"]}!', 'success')
                return redirect(url_for('home'))
            else:
                flash('Неверный логин или пароль', 'error')
        else:
            flash('Заполните все поля', 'error')

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    """Регистрация ТОЛЬКО для студентов"""
    if 'user_id' in session:
        return redirect(url_for('home'))

    if request.method == 'POST':
        # Основные данные
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        full_name = request.form.get('full_name')
        user_type = 'student'  # Всегда студент

        # Дополнительные данные
        email = request.form.get('email')
        phone = request.form.get('phone')
        group = request.form.get('group')
        course = request.form.get('course')

        # Валидация
        if not all([username, password, confirm_password, full_name, group, course]):
            flash('Заполните все обязательные поля', 'error')
            return render_template('register.html')

        if password != confirm_password:
            flash('Пароли не совпадают', 'error')
            return render_template('register.html')

        if len(password) < 6:
            flash('Пароль должен быть не менее 6 символов', 'error')
            return render_template('register.html')

        if not course.isdigit() or not (1 <= int(course) <= 6):
            flash('Укажите корректный курс (1-6)', 'error')
            return render_template('register.html')

        # Регистрируем пользователя (только студент)
        success, message = register_user(
            username=username,
            password=password,
            full_name=full_name,
            user_type=user_type,
            created_by='self',
            email=email,
            phone=phone,
            group=group,
            course=int(course)
        )

        if success:
            flash('Регистрация успешна! Теперь войдите в систему.', 'success')
            return redirect(url_for('login'))
        else:
            flash(message, 'error')

    return render_template('register.html')


@app.route('/admin/create_user', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_create_user():
    """Создание пользователя администратором"""
    user_data = get_user_by_id(session['user_id'])

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        full_name = request.form.get('full_name')
        user_type = request.form.get('user_type')

        # Дополнительные данные в зависимости от типа
        email = request.form.get('email')
        phone = request.form.get('phone')

        # Данные для студентов и старост
        group = request.form.get('group')
        course = request.form.get('course')

        # Данные для преподавателей
        department = request.form.get('department')
        position = request.form.get('position')

        # Получаем created_by из скрытого поля или из сессии
        created_by = request.form.get('created_by', session.get('username', 'admin'))

        # Валидация
        if not all([username, password, full_name, user_type]):
            flash('Заполните все обязательные поля', 'error')
            return render_template('admin_create_user.html', user=user_data, session=session)

        if len(password) < 6:
            flash('Пароль должен быть не менее 6 символов', 'error')
            return render_template('admin_create_user.html', user=user_data, session=session)

        # Создаем пользователя
        success, message = register_user(
            username=username,
            password=password,
            full_name=full_name,
            user_type=user_type,
            created_by=created_by,
            email=email,
            phone=phone,
            group=group,
            course=course,
            department=department,
            position=position
        )

        if success:
            flash(f'Пользователь {full_name} успешно создан!', 'success')
            return redirect(url_for('users_list'))
        else:
            flash(message, 'error')

    return render_template('admin_create_user.html', user=user_data, session=session)


@app.route('/logout')
def logout():
    """Выход из системы"""
    session.clear()
    flash('Вы успешно вышли из системы', 'info')
    return redirect(url_for('login'))


# ==================== ОСНОВНЫЕ СТРАНИЦЫ ====================

@app.route('/starosta')
@login_required
def starosta():
    """Страница старосты"""
    user_data = get_user_by_id(session['user_id'])

    # Проверяем, что пользователь - староста
    if user_data['user_type'] not in ['starosta', 'admin']:
        flash('Доступ только для старосты', 'error')
        return redirect(url_for('home'))

    # Получаем данные из модуля
    students = starosta_module.get_students_data('ПИ-21')
    reports = starosta_module.get_reports_data()
    info = starosta_module.get_info_for_headman()
    messages = starosta_module.get_messages()

    return render_template('starosta.html',
                           user=user_data,
                           students=students,
                           reports=reports,
                           info=info,
                           messages=messages)


@app.route('/raspisanie')
@login_required
def raspisanie():
    """Расписание"""
    user_data = get_user_by_id(session['user_id'])

    # Получаем данные из модуля
    course = request.args.get('course', default=1, type=int)
    schedule = schedule_module.get_schedule(course)
    days = schedule_module.get_course_days(course)
    exams = schedule_module.get_exams_schedule(course)

    return render_template('raspisanie.html',
                           user=user_data,
                           schedule=schedule,
                           days=days,
                           exams=exams,
                           current_course=course,
                           courses=[1, 2, 3, 4])


@app.route('/repetitorstvo')
@login_required
def repetitorstvo():
    """Репетиторство"""
    user_data = get_user_by_id(session['user_id'])
    tutoring_data = tutoring_module.get_tutoring_data()

    return render_template('repetitorstvo.html',
                           user=user_data,
                           tutoring=tutoring_data)


@app.route('/meropriyatiya')
@login_required
def meropriyatiya():
    """Мероприятия"""
    user_data = get_user_by_id(session['user_id'])
    events_data = events_module.get_events()

    return render_template('meropriyatiya.html',
                           user=user_data,
                           events=events_data)


@app.route('/prepodavateli')
@login_required
def prepodavateli():
    """Преподаватели"""
    user_data = get_user_by_id(session['user_id'])

    # Получаем данные из модуля
    teachers = teachers_module.get_all_teachers()
    departments = teachers_module.get_departments()

    return render_template('prepodavateli.html',
                           user=user_data,
                           teachers=teachers,
                           departments=departments)


@app.route('/praktika')
@login_required
def praktika():
    """Практика"""
    user_data = get_user_by_id(session['user_id'])
    practice_data = practice_module.get_practice_data()

    return render_template('praktika.html',
                           user=user_data,
                           practice=practice_data)


@app.route('/podderzhka')
@login_required
def podderzhka():
    """Поддержка"""
    user_data = get_user_by_id(session['user_id'])
    return render_template('podderzhka.html', user=user_data)


# ==================== АДМИН-ПАНЕЛЬ ====================

@app.route('/profile')
@login_required
def profile():
    """Профиль пользователя"""
    user_data = get_user_by_id(session['user_id'])
    return render_template('profile.html', user=user_data)


@app.route('/users')
@login_required
@admin_required
def users_list():
    """Список всех пользователей (только для админа)"""
    user_data = get_user_by_id(session['user_id'])
    users = get_all_users()
    return render_template('users.html', user=user_data, users=users)


@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def delete_user_route(user_id):
    """Удалить пользователя"""
    if delete_user(user_id):
        flash('Пользователь успешно удален', 'success')
    else:
        flash('Пользователь не найден', 'error')

    return redirect(url_for('users_list'))


# ==================== ЗАПУСК ПРИЛОЖЕНИЯ ====================

if __name__ == '__main__':
    print("=" * 50)
    print("🚀 Запуск University Management System")
    print("=" * 50)

    # Проверяем и инициализируем БД
    if check_and_fix_db():
        print("✅ База данных готова к работе")
        print("🌐 Приложение доступно по адресу: http://localhost:5000")
        print("🔑 Администратор: admin / admin123")
        print("=" * 50)

        # Запускаем приложение
        app.run(debug=True, host='0.0.0.0', port=5000)
    else:
        print("❌ Не удалось инициализировать базу данных")
        print("Проверьте права доступа к файлам в папке проекта")