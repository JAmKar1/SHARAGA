"""
Модуль для работы с практикой
"""

import sqlite3
from datetime import datetime


class PracticeModule:
    def __init__(self, db_name='university.db'):
        self.db_name = db_name
        self.init_practice_table()
        self.load_default_data()

    def get_db_connection(self):
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        return conn

    def init_practice_table(self):
        """Инициализация таблицы практик в базе данных"""
        conn = self.get_db_connection()
        cursor = conn.cursor()

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS practices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            course INTEGER NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            supervisor TEXT NOT NULL,
            companies TEXT NOT NULL,
            status TEXT DEFAULT 'Планируется',
            description TEXT,
            requirements TEXT,
            max_students INTEGER,
            current_students INTEGER DEFAULT 0,
            location TEXT,
            contact_person TEXT,
            contact_phone TEXT,
            contact_email TEXT,
            created_by INTEGER NOT NULL,
            created_by_name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (created_by) REFERENCES users(id)
        )
        ''')

        conn.commit()
        conn.close()

    def load_default_data(self):
        """Загрузить демо-данные, если таблица пуста"""
        conn = self.get_db_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT COUNT(*) FROM practices')
        count = cursor.fetchone()[0]

        if count == 0:
            default_practices = [
                {
                    'type': 'Учебная практика',
                    'course': 2,
                    'start_date': '01.06.2024',
                    'end_date': '30.06.2024',
                    'supervisor': 'Иванов С.П.',
                    'companies': 'IT-компания "Технософт",Разработчик "ВебПро"',
                    'status': 'Планируется',
                    'description': 'Практика по основам программирования',
                    'requirements': 'Знание Python, Базовые знания SQL',
                    'max_students': 15,
                    'location': 'ул. Ленина, 15',
                    'contact_person': 'Иванов Иван',
                    'contact_phone': '+7 912 345-67-89',
                    'contact_email': 'ivanov@company.ru',
                    'created_by': 1,
                    'created_by_name': 'Администратор'
                },
                {
                    'type': 'Производственная практика',
                    'course': 3,
                    'start_date': '01.07.2024',
                    'end_date': '31.08.2024',
                    'supervisor': 'Петрова М.И.',
                    'companies': 'Банк "Финансы",Страховая компания "Гарант"',
                    'status': 'Набор',
                    'description': 'Практика в финансовых организациях',
                    'requirements': 'Знание Excel, Аналитические навыки',
                    'max_students': 10,
                    'location': 'пр. Мира, 25',
                    'contact_person': 'Петрова Мария',
                    'contact_phone': '+7 912 987-65-43',
                    'contact_email': 'petrova@bank.ru',
                    'created_by': 1,
                    'created_by_name': 'Администратор'
                },
                {
                    'type': 'Преддипломная практика',
                    'course': 4,
                    'start_date': '01.02.2024',
                    'end_date': '30.04.2024',
                    'supervisor': 'Сидоров А.В.',
                    'companies': 'Разработчик ПО "Софтлайн",IT-интегратор "Технологии"',
                    'status': 'Идет',
                    'description': 'Преддипломная практика для выпускников',
                    'requirements': 'Знание Java, Опыт работы с Git, Базовые знания Spring',
                    'max_students': 8,
                    'location': 'ул. Техническая, 8',
                    'contact_person': 'Сидоров Алексей',
                    'contact_phone': '+7 912 555-12-34',
                    'contact_email': 'sidorov@softline.ru',
                    'created_by': 1,
                    'created_by_name': 'Администратор'
                }
            ]

            for practice in default_practices:
                cursor.execute('''
                INSERT INTO practices 
                (type, course, start_date, end_date, supervisor, companies, status,
                 description, requirements, max_students, location, contact_person,
                 contact_phone, contact_email, created_by, created_by_name)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    practice['type'],
                    practice['course'],
                    practice['start_date'],
                    practice['end_date'],
                    practice['supervisor'],
                    practice['companies'],
                    practice['status'],
                    practice['description'],
                    practice['requirements'],
                    practice['max_students'],
                    practice['location'],
                    practice['contact_person'],
                    practice['contact_phone'],
                    practice['contact_email'],
                    practice['created_by'],
                    practice['created_by_name']
                ))

            conn.commit()
            print("✅ Демо-данные практик загружены")

        conn.close()

    def get_practice_data(self):
        """Получить все данные по практике"""
        conn = self.get_db_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM practices ORDER BY start_date DESC')
        practices = []

        for row in cursor.fetchall():
            practice = dict(row)
            practice['dates'] = f"{practice['start_date']} - {practice['end_date']}"
            practice['companies_list'] = practice['companies'].split(',')
            practices.append(practice)

        conn.close()
        return practices

    def get_practice_by_course(self, course):
        """Получить практику по курсу"""
        conn = self.get_db_connection()
        cursor = conn.cursor()

        cursor.execute('''
        SELECT * FROM practices 
        WHERE course = ? 
        ORDER BY start_date DESC
        ''', (course,))

        practices = []
        for row in cursor.fetchall():
            practice = dict(row)
            practice['dates'] = f"{practice['start_date']} - {practice['end_date']}"
            practice['companies_list'] = practice['companies'].split(',')
            practices.append(practice)

        conn.close()
        return practices

    def get_active_practice(self):
        """Получить активную практику"""
        conn = self.get_db_connection()
        cursor = conn.cursor()

        cursor.execute('''
        SELECT * FROM practices 
        WHERE status = 'Идет' 
        ORDER BY start_date DESC
        ''')

        practices = []
        for row in cursor.fetchall():
            practice = dict(row)
            practice['dates'] = f"{practice['start_date']} - {practice['end_date']}"
            practice['companies_list'] = practice['companies'].split(',')
            practices.append(practice)

        conn.close()
        return practices

    def get_practice_by_id(self, practice_id):
        """Получить практику по ID"""
        conn = self.get_db_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM practices WHERE id = ?', (practice_id,))
        row = cursor.fetchone()

        if row:
            practice = dict(row)
            practice['dates'] = f"{practice['start_date']} - {practice['end_date']}"
            practice['companies_list'] = practice['companies'].split(',')
            conn.close()
            return practice

        conn.close()
        return None

    def add_practice(self, practice_data):
        """Добавить новую практику в базу данных"""
        conn = self.get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('''
            INSERT INTO practices 
            (type, course, start_date, end_date, supervisor, companies, status,
             description, requirements, max_students, current_students, location,
             contact_person, contact_phone, contact_email, created_by, created_by_name)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                practice_data['type'],
                practice_data['course'],
                practice_data['start_date'],
                practice_data['end_date'],
                practice_data['supervisor'],
                practice_data['companies'],
                practice_data.get('status', 'Планируется'),
                practice_data.get('description', ''),
                practice_data.get('requirements', ''),
                practice_data.get('max_students', 0),
                practice_data.get('current_students', 0),
                practice_data.get('location', ''),
                practice_data.get('contact_person', ''),
                practice_data.get('contact_phone', ''),
                practice_data.get('contact_email', ''),
                practice_data['created_by'],
                practice_data['created_by_name']
            ))

            practice_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return True, "Практика успешно добавлена", practice_id
        except Exception as e:
            conn.rollback()
            conn.close()
            return False, f"Ошибка при добавлении практики: {str(e)}", None

    def update_practice(self, practice_id, practice_data):
        """Обновить данные практики"""
        conn = self.get_db_connection()
        cursor = conn.cursor()

        try:
            # Проверяем существование практики
            cursor.execute('SELECT id FROM practices WHERE id = ?', (practice_id,))
            if not cursor.fetchone():
                conn.close()
                return False, "Практика не найдена"

            updates = []
            params = []

            fields = [
                'type', 'course', 'start_date', 'end_date', 'supervisor',
                'companies', 'status', 'description', 'requirements',
                'max_students', 'current_students', 'location',
                'contact_person', 'contact_phone', 'contact_email'
            ]

            for field in fields:
                if field in practice_data:
                    updates.append(f"{field} = ?")
                    params.append(practice_data[field])

            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(practice_id)

            sql = f"UPDATE practices SET {', '.join(updates)} WHERE id = ?"
            cursor.execute(sql, params)
            conn.commit()

            conn.close()
            return True, "Практика успешно обновлена"
        except Exception as e:
            conn.rollback()
            conn.close()
            return False, f"Ошибка при обновлении практики: {str(e)}"

    def delete_practice(self, practice_id, user_id=None, user_type=None):
        """Удалить практику"""
        conn = self.get_db_connection()
        cursor = conn.cursor()

        try:
            # Проверяем права доступа
            if user_id and user_type:
                cursor.execute('SELECT created_by FROM practices WHERE id = ?', (practice_id,))
                row = cursor.fetchone()

                if row:
                    practice_creator = row['created_by']
                    # Разрешаем удаление только администраторам и создателям практики
                    if user_type != 'admin' and int(user_id) != int(practice_creator):
                        conn.close()
                        return False, "Вы не можете удалить эту практику"

            cursor.execute('DELETE FROM practices WHERE id = ?', (practice_id,))
            conn.commit()

            conn.close()
            return True, "Практика успешно удалена"
        except Exception as e:
            conn.rollback()
            conn.close()
            return False, f"Ошибка при удалении практики: {str(e)}"

    def search_practices(self, search_term=None, course=None, status=None):
        """Поиск практик по параметрам"""
        conn = self.get_db_connection()
        cursor = conn.cursor()

        query = 'SELECT * FROM practices WHERE 1=1'
        params = []

        if search_term:
            query += ''' AND (
                type LIKE ? OR 
                supervisor LIKE ? OR 
                companies LIKE ? OR 
                description LIKE ? OR
                location LIKE ?
            )'''
            search_pattern = f'%{search_term}%'
            params.extend([search_pattern] * 5)

        if course:
            query += ' AND course = ?'
            params.append(course)

        if status:
            query += ' AND status = ?'
            params.append(status)

        query += ' ORDER BY start_date DESC'
        cursor.execute(query, params)

        practices = []
        for row in cursor.fetchall():
            practice = dict(row)
            practice['dates'] = f"{practice['start_date']} - {practice['end_date']}"
            practice['companies_list'] = practice['companies'].split(',')
            practices.append(practice)

        conn.close()
        return practices

    def get_statistics(self):
        """Получить статистику по практикам"""
        conn = self.get_db_connection()
        cursor = conn.cursor()

        cursor.execute('''
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN status = 'Идет' THEN 1 ELSE 0 END) as active,
            SUM(CASE WHEN status = 'Планируется' THEN 1 ELSE 0 END) as planned,
            SUM(CASE WHEN status = 'Набор' THEN 1 ELSE 0 END) as recruiting,
            SUM(CASE WHEN status = 'Завершено' THEN 1 ELSE 0 END) as completed,
            SUM(current_students) as total_students,
            SUM(max_students) as max_students_total
        FROM practices
        ''')

        result = cursor.fetchone()
        conn.close()

        if result:
            return dict(result)
        return {
            'total': 0,
            'active': 0,
            'planned': 0,
            'recruiting': 0,
            'completed': 0,
            'total_students': 0,
            'max_students_total': 0
        }