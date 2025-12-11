from flask import Flask, render_template, redirect, url_for, session, request, flash
import sqlite3  # Этот импорт должен быть в самом верху!
import os
import time

app = Flask(__name__)
app.secret_key = 'your_secret_key_here_change_this'  # Важно изменить на свой ключ!

# ==================== МОДУЛИ ====================

# Модуль репетиторства (встроенный, работает с БД)
class TutoringModule:
    def __init__(self):
        self.db_name = 'university.db'
    
    def get_db_connection(self):
        """Получить соединение с БД"""
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        return conn
    
    # Исправленный метод - должен быть внутри класса с правильным отступом
    def get_tutoring_data(self):
        """Получить все репетиторства для отображения на странице"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # Получаем все репетиторства с информацией о записях
            cursor.execute('''
            SELECT t.*, 
                   COUNT(tr.id) as registered_count
            FROM tutoring t
            LEFT JOIN tutoring_registrations tr ON t.id = tr.tutoring_id AND tr.status != 'отменено'
            GROUP BY t.id
            ORDER BY t.created_at DESC
            ''')
            
            result = []
            for row in cursor.fetchall():
                # Получаем список записавшихся студентов
                cursor.execute('''
                SELECT tr.student_id, u.full_name as name, tr.status
                FROM tutoring_registrations tr
                JOIN users u ON tr.student_id = u.id
                WHERE tr.tutoring_id = ? AND tr.status != 'отменено'
                ''', (row['id'],))
                
                students = []
                for student_row in cursor.fetchall():
                    students.append({
                        'student_id': student_row[0],
                        'name': student_row[1],
                        'status': student_row[2]
                    })
                
                result.append({
                    'id': row['id'],
                    'subject': row['subject'],
                    'tutor_name': row['tutor_name'],
                    'tutor_id': row['tutor_id'],
                    'tutor_type': row['tutor_type'],
                    'description': row['description'],
                    'days': row['days'],
                    'time': row['time'],
                    'room': row['room'],
                    'price': row['price'],
                    'max_students': row['max_students'],
                    'registered_count': row['registered_count'] or 0,
                    'status': row['status'],
                    'students': students,
                    'created_at': row['created_at']
                })
            
            conn.close()
            
            # Разделяем на преподавателей и студентов
            return {
                'teachers': [t for t in result if t['tutor_type'] == 'teacher'],
                'students': [t for t in result if t['tutor_type'] == 'student']
            }
            
        except Exception as e:
            print(f"❌ Ошибка получения данных репетиторства: {e}")
            return {'teachers': [], 'students': []}
    
    def register_student_for_tutoring(self, tutoring_id, student_id, student_name):
        """Записать студента на репетиторство"""
        conn = None
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # 1. Проверяем, существует ли репетиторство
            cursor.execute('SELECT * FROM tutoring WHERE id = ?', (tutoring_id,))
            tutoring = cursor.fetchone()
            if not tutoring:
                return False, "Репетиторство не найдено"
            
            # 2. Проверяем, не записан ли уже студент
            cursor.execute('''
                SELECT id FROM tutoring_registrations 
                WHERE tutoring_id = ? AND student_id = ?
            ''', (tutoring_id, student_id))
            
            if cursor.fetchone():
                return False, "Вы уже записаны на это репетиторство"
            
            # 3. Проверяем количество свободных мест
            cursor.execute('''
                SELECT COUNT(*) FROM tutoring_registrations 
                WHERE tutoring_id = ? AND status != 'отменено'
            ''', (tutoring_id,))
            
            registered_count = cursor.fetchone()[0]
            max_students = tutoring['max_students']
            
            if registered_count >= max_students:
                return False, "Нет свободных мест"
            
            # 4. Проверяем, не пытается ли репетитор записаться на свое же занятие
            if tutoring['tutor_id'] == student_id:
                return False, "Вы не можете записаться на своё же репетиторство"
            
            # 5. Записываем студента
            cursor.execute('''
                INSERT INTO tutoring_registrations (tutoring_id, student_id, status)
                VALUES (?, ?, 'ожидает')
            ''', (tutoring_id, student_id))
            
            conn.commit()
            return True, "Вы успешно записались на репетиторство!"
            
        except Exception as e:
            print(f"❌ Ошибка записи на репетиторство: {e}")
            return False, f"Ошибка: {str(e)}"
        finally:
            if conn:
                conn.close()
    
    def add_tutoring(self, subject, tutor_name, tutor_id, tutor_type, 
                    days, time, room, price, description='', max_students=10):
        """Добавить новое репетиторство в БД"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
            INSERT INTO tutoring 
            (subject, tutor_name, tutor_id, tutor_type, description, 
             days, time, room, price, max_students, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Идет набор')
            ''', (subject, tutor_name, tutor_id, tutor_type, description,
                  days, time, room, price, max_students))
            
            conn.commit()
            return True, "Репетиторство успешно добавлено"
        except Exception as e:
            return False, f"Ошибка: {str(e)}"
        finally:
            conn.close()
    
    def register_student(self, tutoring_id, student_id):
        """Записать студента на репетиторство"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Проверяем, не записан ли уже
            cursor.execute('''
            SELECT id FROM tutoring_registrations 
            WHERE tutoring_id = ? AND student_id = ?
            ''', (tutoring_id, student_id))
            
            if cursor.fetchone():
                return False, "Вы уже записаны на это репетиторство"
            
            # Проверяем количество мест
            cursor.execute('''
            SELECT COUNT(id) as count FROM tutoring_registrations 
            WHERE tutoring_id = ? AND status != 'отменено'
            ''', (tutoring_id,))
            
            registered_count = cursor.fetchone()[0]
            
            cursor.execute('SELECT max_students FROM tutoring WHERE id = ?', (tutoring_id,))
            max_students = cursor.fetchone()[0]
            
            if registered_count >= max_students:
                return False, "На это репетиторство нет свободных мест"
            
            # Записываем студента
            cursor.execute('''
            INSERT INTO tutoring_registrations (tutoring_id, student_id, status)
            VALUES (?, ?, 'ожидает')
            ''', (tutoring_id, student_id))
            
            conn.commit()
            return True, "Вы успешно записались на репетиторство"
            
        except Exception as e:
            return False, f"Ошибка: {str(e)}"
        finally:
            conn.close()
    
    def get_my_tutoring(self, tutor_id):
        """Получить репетиторства, созданные мной"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT t.*, 
               COUNT(tr.id) as registered_count
        FROM tutoring t
        LEFT JOIN tutoring_registrations tr ON t.id = tr.tutoring_id
        WHERE t.tutor_id = ?
        GROUP BY t.id
        ORDER BY t.created_at DESC
        ''', (tutor_id,))
        
        result = []
        for row in cursor.fetchall():
            result.append(dict(row))
        
        conn.close()
        return result
    
    def delete_tutoring(self, tutoring_id, tutor_id):
        """Удалить репетиторство (только создатель)"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Проверяем, что удаляет создатель
            cursor.execute('SELECT tutor_id FROM tutoring WHERE id = ?', (tutoring_id,))
            result = cursor.fetchone()
            
            if not result or result[0] != tutor_id:
                return False, "Вы не можете удалить это репетиторство"
            
            # Удаляем записи на репетиторство
            cursor.execute('DELETE FROM tutoring_registrations WHERE tutoring_id = ?', (tutoring_id,))
            # Удаляем репетиторство
            cursor.execute('DELETE FROM tutoring WHERE id = ?', (tutoring_id,))
            
            conn.commit()
            return True, "Репетиторство успешно удалено"
        except Exception as e:
            return False, f"Ошибка: {str(e)}"
        finally:
            conn.close()

# Простые заглушки для других модулей (для обратной совместимости)
class StarostaModule:
    def get_students_data(self, *args): 
        return [
            {'name': 'Иванов И.И.', 'group': 'ПИ-21', 'attendance': '95%', 'grades': '4.5'},
            {'name': 'Петров П.П.', 'group': 'ПИ-21', 'attendance': '88%', 'grades': '4.2'},
            {'name': 'Сидорова А.С.', 'group': 'ПИ-21', 'attendance': '92%', 'grades': '4.7'}
        ]
    
    def get_reports_data(self): 
        return [
            {'title': 'Отчет за сентябрь', 'date': '2024-09-30', 'status': 'Сдан'},
            {'title': 'Отчет за октябрь', 'date': '2024-10-31', 'status': 'В работе'}
        ]
    
    def get_info_for_headman(self): 
        return {
            'group': 'ПИ-21',
            'total_students': 25,
            'excellent': 8,
            'good': 12,
            'satisfactory': 5
        }
    
    def get_messages(self): 
        return [
            {'from': 'Деканат', 'message': 'Собрание старост 15.11 в 14:00', 'date': '2024-11-10'},
            {'from': 'Преподаватель', 'message': 'Принести отчеты до пятницы', 'date': '2024-11-08'}
        ]

class ScheduleModule:
    def get_schedule(self, course): 
        return {
            'Понедельник': ['Математика 9:00-10:30', 'Программирование 11:00-12:30'],
            'Вторник': ['Физика 9:00-10:30', 'Базы данных 11:00-12:30'],
            'Среда': ['Английский 9:00-10:30', 'Web-разработка 11:00-12:30'],
            'Четверг': ['Математика 9:00-10:30', 'Алгоритмы 11:00-12:30'],
            'Пятница': ['Физкультура 9:00-10:30', 'Проектирование 11:00-12:30']
        }
    
    def get_course_days(self, course):
        return ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница']
    
    def get_exams_schedule(self, course):
        return [
            {'subject': 'Математика', 'date': '2024-12-20', 'time': '9:00', 'room': '301'},
            {'subject': 'Программирование', 'date': '2024-12-22', 'time': '9:00', 'room': '305'}
        ]

class TeachersModule:
    def get_all_teachers(self):
        return [
            {'name': 'Иванов И.И.', 'department': 'Программная инженерия', 'subjects': ['Математика', 'Алгоритмы']},
            {'name': 'Петрова М.С.', 'department': 'Информационные системы', 'subjects': ['Базы данных', 'Web-разработка']},
            {'name': 'Сидоров А.В.', 'department': 'Программная инженерия', 'subjects': ['Программирование', 'ООП']}
        ]
    
    def get_departments(self):
        return ['Программная инженерия', 'Информационные системы', 'Компьютерные науки']

class EventsModule:
    def get_events(self):
        return [
            {'title': 'День открытых дверей', 'date': '2024-11-15', 'location': 'Актовый зал'},
            {'title': 'Научная конференция', 'date': '2024-11-20', 'location': 'Конференц-зал'},
            {'title': 'Спортивные соревнования', 'date': '2024-11-25', 'location': 'Спортзал'}
        ]

class PracticeModule:
    def get_practice_data(self):
        return {
            'current': [
                {'company': 'ООО "Технологии"', 'students': 5, 'period': '01.09.2024 - 30.11.2024'},
                {'company': 'ПАО "Банк"', 'students': 3, 'period': '15.09.2024 - 15.12.2024'}
            ],
            'completed': [
                {'company': 'ООО "Софт"', 'students': 8, 'period': '01.06.2024 - 31.08.2024'},
                {'company': 'АО "Телеком"', 'students': 6, 'period': '01.03.2024 - 31.05.2024'}
            ]
        }

# Инициализация модулей
starosta_module = StarostaModule()
schedule_module = ScheduleModule()
teachers_module = TeachersModule()
events_module = EventsModule()
practice_module = PracticeModule()
tutoring_module = TutoringModule()

print("✅ Все модули инициализированы")

# ==================== БАЗА ДАННЫХ ====================

def init_db():
    """Создание базы данных и таблиц"""
    print("🔄 Инициализация базы данных...")
    conn = None
    try:
        conn = sqlite3.connect('university.db')
        cursor = conn.cursor()

        cursor.execute('DROP TABLE IF EXISTS users')

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

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS tutoring (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT NOT NULL,
            tutor_name TEXT NOT NULL,
            tutor_id INTEGER NOT NULL,
            tutor_type TEXT NOT NULL CHECK(tutor_type IN ('teacher', 'student')),
            description TEXT,
            days TEXT NOT NULL,
            time TEXT NOT NULL,
            room TEXT NOT NULL,
            price TEXT NOT NULL,
            max_students INTEGER DEFAULT 10,
            status TEXT DEFAULT 'Идет набор',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (tutor_id) REFERENCES users(id)
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS tutoring_registrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tutoring_id INTEGER NOT NULL,
            student_id INTEGER NOT NULL,
            status TEXT DEFAULT 'ожидает',
            registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (tutoring_id) REFERENCES tutoring(id),
            FOREIGN KEY (student_id) REFERENCES users(id)
        )
        ''')

        cursor.execute("SELECT COUNT(*) FROM users WHERE user_type = 'admin'")
        if cursor.fetchone()[0] == 0:
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
    
    conn = None
    try:
        conn = sqlite3.connect('university.db')
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        if not cursor.fetchone():
            print("⚠️  Таблица users не найдена, создаю заново...")
            conn.close()
            init_db()
            return True
        
        cursor.execute("SELECT * FROM users LIMIT 1")
        columns = [description[0] for description in cursor.description]
        
        required_columns = ['id', 'username', 'password', 'full_name', 'user_type']
        missing_columns = [col for col in required_columns if col not in columns]
        
        if missing_columns:
            print(f"⚠️  Отсутствуют столбцы: {missing_columns}. Пересоздаю таблицу...")
            conn.close()
            init_db()
            return True
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tutoring'")
        if not cursor.fetchone():
            print("⚠️  Таблица tutoring не найдена, создаю...")
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS tutoring (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject TEXT NOT NULL,
                tutor_name TEXT NOT NULL,
                tutor_id INTEGER NOT NULL,
                tutor_type TEXT NOT NULL CHECK(tutor_type IN ('teacher', 'student')),
                description TEXT,
                days TEXT NOT NULL,
                time TEXT NOT NULL,
                room TEXT NOT NULL,
                price TEXT NOT NULL,
                max_students INTEGER DEFAULT 10,
                status TEXT DEFAULT 'Идет набор',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (tutor_id) REFERENCES users(id)
            )
            ''')
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tutoring_registrations'")
        if not cursor.fetchone():
            print("⚠️  Таблица tutoring_registrations не найдена, создаю...")
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS tutoring_registrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tutoring_id INTEGER NOT NULL,
                student_id INTEGER NOT NULL,
                status TEXT DEFAULT 'ожидает',
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (tutoring_id) REFERENCES tutoring(id),
                FOREIGN KEY (student_id) REFERENCES users(id)
            )
            ''')
        
        conn.commit()
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
        conn.execute('PRAGMA journal_mode=WAL')
        return conn
    except sqlite3.OperationalError as e:
        if "locked" in str(e):
            time.sleep(0.1)
            return get_db_connection()
        raise

def update_user_data(user_id, **kwargs):
    """Обновить данные пользователя в БД"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT id FROM users WHERE id = ?', (user_id,))
        if not cursor.fetchone():
            return False, "Пользователь не найден"
        
        if 'username' in kwargs:
            cursor.execute('SELECT id FROM users WHERE username = ? AND id != ?', 
                          (kwargs['username'], user_id))
            if cursor.fetchone():
                return False, "Пользователь с таким логином уже существует"
        
        update_fields = []
        update_values = []
        
        field_mapping = {
            'username': 'username',
            'password': 'password',
            'full_name': 'full_name',
            'user_type': 'user_type',
            'email': 'email',
            'phone': 'phone',
            'group': 'group_name',
            'course': 'course',
            'department': 'department',
            'position': 'position'
        }
        
        for key, value in kwargs.items():
            if key in field_mapping and value is not None:
                if key == 'password' and value == '':
                    continue
                update_fields.append(f"{field_mapping[key]} = ?")
                update_values.append(value)
        
        if not update_fields:
            return False, "Нет данных для обновления"
        
        update_values.append(user_id)
        
        sql = f"UPDATE users SET {', '.join(update_fields)} WHERE id = ?"
        cursor.execute(sql, update_values)
        
        conn.commit()
        return True, "Данные успешно обновлены"
        
    except Exception as e:
        print(f"❌ Ошибка обновления пользователя {user_id}: {e}")
        return False, f"Ошибка: {str(e)}"
    finally:
        if conn:
            conn.close()

def register_user(username, password, full_name, user_type, created_by='system', **kwargs):
    """Регистрация нового пользователя"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
        if cursor.fetchone():
            return False, "Пользователь с таким логином уже существует"

        email = kwargs.get('email')
        phone = kwargs.get('phone')
        group = kwargs.get('group')
        course = kwargs.get('course')
        department = kwargs.get('department')
        position = kwargs.get('position')

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
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Пожалуйста, войдите в систему', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
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
    if 'user_id' in session:
        user_data = get_user_by_id(session['user_id'])
        return render_template('index.html', user=user_data)
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('home'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username and password:
            user = login_user(username, password)
            if user:
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
    if 'user_id' in session:
        return redirect(url_for('home'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        full_name = request.form.get('full_name')
        user_type = 'student'
        email = request.form.get('email')
        phone = request.form.get('phone')
        group = request.form.get('group')
        course = request.form.get('course')
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
    user_data = get_user_by_id(session['user_id'])
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        full_name = request.form.get('full_name')
        user_type = request.form.get('user_type')
        email = request.form.get('email')
        phone = request.form.get('phone')
        group = request.form.get('group')
        course = request.form.get('course')
        department = request.form.get('department')
        position = request.form.get('position')
        created_by = request.form.get('created_by', session.get('username', 'admin'))
        if not all([username, password, full_name, user_type]):
            flash('Заполните все обязательные поля', 'error')
            return render_template('admin_create_user.html', user=user_data, session=session)
        if len(password) < 6:
            flash('Пароль должен быть не менее 6 символов', 'error')
            return render_template('admin_create_user.html', user=user_data, session=session)
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
    session.clear()
    flash('Вы успешно вышли из системы', 'info')
    return redirect(url_for('login'))

@app.route('/starosta')
@login_required
def starosta():
    user_data = get_user_by_id(session['user_id'])
    if user_data['user_type'] not in ['starosta', 'admin']:
        flash('Доступ только для старосты или администратора', 'error')
        return redirect(url_for('home'))
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
    user_data = get_user_by_id(session['user_id'])
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
    user_data = get_user_by_id(session['user_id'])
    try:
        tutoring_data = tutoring_module.get_tutoring_data()
        return render_template('repetitorstvo.html',
                             user=user_data,
                             teachers=tutoring_data['teachers'],
                             students=tutoring_data['students'])
    except Exception as e:
        print(f"❌ Ошибка в маршруте repetitorstvo: {e}")
        return render_template('repetitorstvo.html',
                             user=user_data,
                             teachers=[],
                             students=[])

@app.route('/meropriyatiya')
@login_required
def meropriyatiya():
    user_data = get_user_by_id(session['user_id'])
    events_data = events_module.get_events()
    return render_template('meropriyatiya.html',
                           user=user_data,
                           events=events_data)

@app.route('/prepodavateli')
@login_required
def prepodavateli():
    user_data = get_user_by_id(session['user_id'])
    teachers = teachers_module.get_all_teachers()
    departments = teachers_module.get_departments()
    return render_template('prepodavateli.html',
                           user=user_data,
                           teachers=teachers,
                           departments=departments)

@app.route('/praktika')
@login_required
def praktika():
    user_data = get_user_by_id(session['user_id'])
    practice_data = practice_module.get_practice_data()
    return render_template('praktika.html',
                           user=user_data,
                           practice=practice_data)

@app.route('/podderzhka')
@login_required
def podderzhka():
    user_data = get_user_by_id(session['user_id'])
    return render_template('podderzhka.html', user=user_data)

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


# ==================== РЕПЕТИТОРСТВО (ДОПОЛНИТЕЛЬНЫЕ МАРШРУТЫ) ====================

@app.route('/repetitorstvo/add', methods=['GET', 'POST'])
@login_required
def add_tutoring():
    """Добавить репетиторство"""
    user_data = get_user_by_id(session['user_id'])
    
    # Только преподаватели и студенты могут создавать репетиторство
    if user_data['user_type'] not in ['teacher', 'student']:
        flash('Только преподаватели и студенты могут создавать репетиторство', 'error')
        return redirect(url_for('repetitorstvo'))
    
    if request.method == 'POST':
        subject = request.form.get('subject')
        description = request.form.get('description')
        days = request.form.get('days')
        time = request.form.get('time')
        room = request.form.get('room')
        price = request.form.get('price')
        max_students = request.form.get('max_students', 10)
        
        if not all([subject, days, time, room, price]):
            flash('Заполните все обязательные поля', 'error')
            return render_template('add_tutoring.html', user=user_data)
        
        # Определяем тип репетитора
        tutor_type = 'teacher' if user_data['user_type'] == 'teacher' else 'student'
        
        # Добавляем в БД
        success, message = tutoring_module.add_tutoring(
            subject=subject,
            tutor_name=user_data['full_name'],
            tutor_id=user_data['id'],
            tutor_type=tutor_type,
            description=description,
            days=days,
            time=time,
            room=room,
            price=price,
            max_students=int(max_students)
        )
        
        if success:
            flash('✅ ' + message, 'success')
            return redirect(url_for('repetitorstvo'))
        else:
            flash('❌ ' + message, 'error')
    
    return render_template('add_tutoring.html', user=user_data)

# ==================== МАРШРУТЫ ДЛЯ РЕДАКТИРОВАНИЯ ====================

@app.route('/admin/edit_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    """Редактирование пользователя"""
    user_data = get_user_by_id(session['user_id'])
    
    # Получаем редактируемого пользователя
    target_user = get_user_by_id(user_id)
    if not target_user:
        flash('Пользователь не найден', 'error')
        return redirect(url_for('users_list'))
    
    if request.method == 'POST':
        # Получаем данные из формы
        username = request.form.get('username')
        full_name = request.form.get('full_name')
        user_type = request.form.get('user_type')
        email = request.form.get('email')
        phone = request.form.get('phone')
        group = request.form.get('group')
        course = request.form.get('course')
        department = request.form.get('department')
        position = request.form.get('position')
        
        # Получаем пароль (может быть пустым)
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Проверяем пароль, если он указан
        if password or confirm_password:
            if password != confirm_password:
                flash('Пароли не совпадают', 'error')
                return render_template('edit_user.html', 
                                     user=user_data,
                                     target_user=target_user)
            
            if password and len(password) < 6:
                flash('Пароль должен быть не менее 6 символов', 'error')
                return render_template('edit_user.html', 
                                     user=user_data,
                                     target_user=target_user)
        
        # Обновляем данные в БД
        update_data = {
            'username': username,
            'full_name': full_name,
            'user_type': user_type,
            'email': email,
            'phone': phone,
            'group': group,
            'course': course,
            'department': department,
            'position': position
        }
        
        # Добавляем пароль только если он указан
        if password:
            update_data['password'] = password
        
        success, message = update_user_data(user_id=user_id, **update_data)
        
        if success:
            flash(f'Данные пользователя {full_name} успешно обновлены!', 'success')
            return redirect(url_for('users_list'))
        else:
            flash(message, 'error')
    
    return render_template('edit_user.html', 
                         user=user_data,
                         target_user=target_user)

@app.route('/repetitorstvo/register/<int:tutoring_id>', methods=['POST'])
@login_required
def register_for_tutoring(tutoring_id):
    """Записаться на репетиторство"""
    user_data = get_user_by_id(session['user_id'])
    
    # Только студенты могут записываться
    if user_data['user_type'] != 'student':
        flash('Только студенты могут записываться на репетиторство', 'error')
        return redirect(url_for('repetitorstvo'))
    
    # Записываем студента
    success, message = tutoring_module.register_student_for_tutoring(
        tutoring_id, 
        user_data['id'],
        user_data['full_name']
    )
    
    if success:
        flash('✅ ' + message, 'success')
    else:
        flash('❌ ' + message, 'error')
    
    return redirect(url_for('repetitorstvo'))


@app.route('/repetitorstvo/my')
@login_required
def my_tutoring():
    """Мои репетиторства"""
    user_data = get_user_by_id(session['user_id'])
    
    # Получаем репетиторства, созданные пользователем
    my_tutoring_list = tutoring_module.get_my_tutoring(user_data['id'])
    
    print(f"🔍 DEBUG: Получено {len(my_tutoring_list)} репетиторств для пользователя {user_data['id']}")
    
    return render_template('my_tutoring.html', 
                         user=user_data,
                         my_tutoring=my_tutoring_list)


@app.route('/repetitorstvo/delete/<int:tutoring_id>')
@login_required
def delete_tutoring(tutoring_id):
    """Удалить репетиторство"""
    user_data = get_user_by_id(session['user_id'])
    
    success, message = tutoring_module.delete_tutoring(tutoring_id, user_data['id'])
    flash(message, 'success' if success else 'error')
    
    return redirect(url_for('my_tutoring'))


# ==================== ЗАПУСК ПРИЛОЖЕНИЯ ====================

if __name__ == '__main__':
    print("=" * 50)
    print("🚀 Запуск University Management System")
    print("=" * 50)
    
    # Проверяем и инициализируем БД
    if check_and_fix_db():
        print("✅ База данных готова к работе")
        print("🌐 Приложение доступно по адресам:")
        print("   • На компьютере: http://localhost:5000")
        print("   • На телефоне в той же Wi-Fi сети: http://ВАШ_IP:5000")
        print("🔑 Администратор: admin / admin123")
        print("📚 Репетиторство работает через БД")
        print("=" * 50)
        
        # ЗАПУСКАЕМ С ДОСТУПОМ ИЗ СЕТИ
        app.run(
            debug=True, 
            host='0.0.0.0',  # Принимает подключения со всех интерфейсов
            port=5000,
            threaded=True  # Для лучшей производительности
        )
    else:
        print("❌ Не удалось инициализировать базу данных")
        print("Проверьте права доступа к файлам в папке проекта")