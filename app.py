# app.py (расширенная версия с системой управления практиками)

from flask import Flask, render_template, redirect, url_for, session, request, flash, jsonify, send_file
import sqlite3
import os
import time
import re
import tempfile
from werkzeug.utils import secure_filename
from collections import defaultdict
import io
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key_here_change_this'

# Конфигурация для загрузки файлов
app.config['UPLOAD_FOLDER'] = 'uploads/schedules'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['REPORT_UPLOAD_FOLDER'] = 'uploads/reports'
app.config['EVENT_UPLOAD_FOLDER'] = 'uploads/events'

# Создаем папки для загрузок
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['REPORT_UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['EVENT_UPLOAD_FOLDER'], exist_ok=True)


# ==================== МОДУЛИ ====================

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


class TutoringModule:
    def __init__(self):
        self.db_name = 'university.db'

    def get_db_connection(self):
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        return conn

    def get_tutoring_data(self):
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()

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

            return {
                'teachers': [t for t in result if t['tutor_type'] == 'teacher'],
                'students': [t for t in result if t['tutor_type'] == 'student']
            }

        except Exception as e:
            print(f"❌ Ошибка получения данных репетиторства: {e}")
            return {'teachers': [], 'students': []}

    def register_student_for_tutoring(self, tutoring_id, student_id, student_name):
        conn = None
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()

            cursor.execute('SELECT * FROM tutoring WHERE id = ?', (tutoring_id,))
            tutoring = cursor.fetchone()
            if not tutoring:
                return False, "Репетиторство не найдено"

            cursor.execute('''
                SELECT id FROM tutoring_registrations 
                WHERE tutoring_id = ? AND student_id = ?
            ''', (tutoring_id, student_id))

            if cursor.fetchone():
                return False, "Вы уже записаны на это репетиторство"

            cursor.execute('''
                SELECT COUNT(*) FROM tutoring_registrations 
                WHERE tutoring_id = ? AND status != 'отменено'
            ''', (tutoring_id,))

            registered_count = cursor.fetchone()[0]
            max_students = tutoring['max_students']

            if registered_count >= max_students:
                return False, "Нет свободных мест"

            if tutoring['tutor_id'] == student_id:
                return False, "Вы не можете записаться на своё же репетиторство"

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

    def get_my_tutoring(self, tutor_id):
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
        conn = self.get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('SELECT tutor_id FROM tutoring WHERE id = ?', (tutoring_id,))
            result = cursor.fetchone()

            if not result or result[0] != tutor_id:
                return False, "Вы не можете удалить это репетиторство"

            cursor.execute('DELETE FROM tutoring_registrations WHERE tutoring_id = ?', (tutoring_id,))
            cursor.execute('DELETE FROM tutoring WHERE id = ?', (tutoring_id,))

            conn.commit()
            return True, "Репетиторство успешно удалено"
        except Exception as e:
            return False, f"Ошибка: {str(e)}"
        finally:
            conn.close()


class StarostaModule:
    def __init__(self):
        self.db_name = 'university.db'
        self.reports_folder = 'uploads/starosta_reports'
        os.makedirs(self.reports_folder, exist_ok=True)

    def get_db_connection(self):
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        return conn

    def init_reports_table(self):
        """Инициализация таблицы отчетов"""
        conn = self.get_db_connection()
        cursor = conn.cursor()

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS starosta_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_type TEXT NOT NULL CHECK(report_type IN ('attendance', 'performance', 'other')),
            title TEXT NOT NULL,
            description TEXT,
            period TEXT NOT NULL,
            group_name TEXT NOT NULL,
            filename TEXT,
            original_filename TEXT,
            file_path TEXT,
            file_content TEXT,
            file_type TEXT,
            status TEXT DEFAULT 'draft' CHECK(status IN ('draft', 'pending', 'completed')),
            uploaded_by INTEGER NOT NULL,
            uploaded_by_name TEXT NOT NULL,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (uploaded_by) REFERENCES users(id)
        )
        ''')

        conn.commit()
        conn.close()

    def create_report(self, report_type, title, description, period, group_name,
                      uploaded_by, uploaded_by_name, filename=None, file_path=None,
                      file_content=None, file_type=None, status='draft'):
        """Создать новый отчет"""
        conn = self.get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('''
            INSERT INTO starosta_reports 
            (report_type, title, description, period, group_name, 
             filename, file_path, file_content, file_type, status,
             uploaded_by, uploaded_by_name)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (report_type, title, description, period, group_name,
                  filename, file_path, file_content, file_type, status,
                  uploaded_by, uploaded_by_name))

            report_id = cursor.lastrowid
            conn.commit()
            return True, "Отчет успешно создан", report_id
        except Exception as e:
            conn.rollback()
            return False, f"Ошибка при создании отчета: {str(e)}", None
        finally:
            conn.close()

    def get_reports_for_group(self, group_name):
        """Получить все отчеты для группы"""
        conn = self.get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('''
            SELECT * FROM starosta_reports 
            WHERE group_name = ?
            ORDER BY updated_at DESC
            ''', (group_name,))

            reports = []
            for row in cursor.fetchall():
                report = dict(row)
                report['has_file'] = bool(report['filename']) or bool(report['file_content'])
                report['has_uploaded_file'] = bool(report['filename'])
                report['has_text_content'] = bool(report['file_content'])

                if report['filename']:
                    report['file_url'] = f"/starosta/download/{report['id']}"
                    report['view_url'] = f"/starosta/view/{report['id']}"
                elif report['file_content']:
                    report['edit_url'] = f"/starosta/edit/{report['id']}"

                status_colors = {
                    'draft': 'secondary',
                    'pending': 'warning',
                    'completed': 'success'
                }
                report['status_color'] = status_colors.get(report['status'], 'secondary')

                status_names = {
                    'draft': 'Черновик',
                    'pending': 'В работе',
                    'completed': 'Завершен'
                }
                report['status_name'] = status_names.get(report['status'], 'Черновик')

                reports.append(report)

            return reports
        except Exception as e:
            print(f"❌ Ошибка получения отчетов: {e}")
            return []
        finally:
            conn.close()

    def get_report_by_id(self, report_id):
        """Получить отчет по ID"""
        conn = self.get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('SELECT * FROM starosta_reports WHERE id = ?', (report_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
        except Exception as e:
            print(f"❌ Ошибка получения отчета: {e}")
            return None
        finally:
            conn.close()

    def update_report(self, report_id, title=None, description=None, period=None,
                      status=None, filename=None, file_path=None,
                      file_content=None, file_type=None):
        """Обновить отчет"""
        conn = self.get_db_connection()
        cursor = conn.cursor()

        try:
            updates = []
            params = []

            if title is not None:
                updates.append("title = ?")
                params.append(title)
            if description is not None:
                updates.append("description = ?")
                params.append(description)
            if period is not None:
                updates.append("period = ?")
                params.append(period)
            if status is not None:
                updates.append("status = ?")
                params.append(status)
            if filename is not None:
                updates.append("filename = ?")
                params.append(filename)
            if file_path is not None:
                updates.append("file_path = ?")
                params.append(file_path)
            if file_content is not None:
                updates.append("file_content = ?")
                params.append(file_content)
            if file_type is not None:
                updates.append("file_type = ?")
                params.append(file_type)

            updates.append("updated_at = CURRENT_TIMESTAMP")

            if not updates:
                return False, "Нет данных для обновления"

            params.append(report_id)
            sql = f"UPDATE starosta_reports SET {', '.join(updates)} WHERE id = ?"

            cursor.execute(sql, params)
            conn.commit()

            if cursor.rowcount > 0:
                return True, "Отчет успешно обновлен"
            else:
                return False, "Отчет не найден"
        except Exception as e:
            conn.rollback()
            return False, f"Ошибка при обновлении отчета: {str(e)}"
        finally:
            conn.close()

    def delete_report(self, report_id):
        """Удалить отчет"""
        conn = self.get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('SELECT file_path FROM starosta_reports WHERE id = ?', (report_id,))
            row = cursor.fetchone()

            cursor.execute('DELETE FROM starosta_reports WHERE id = ?', (report_id,))
            conn.commit()

            if row and row['file_path'] and os.path.exists(row['file_path']):
                try:
                    os.remove(row['file_path'])
                except Exception as e:
                    print(f"⚠️ Не удалось удалить файл: {e}")

            return True, "Отчет успешно удален"
        except Exception as e:
            conn.rollback()
            return False, f"Ошибка при удалении отчета: {str(e)}"
        finally:
            conn.close()

    def save_report_file(self, file, group_name):
        """Сохранить файл отчета на диск"""
        try:
            if not file or file.filename == '':
                return False, "Файл не выбран", None, None, None

            original_filename = secure_filename(file.filename)
            file_ext = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else ''

            allowed_extensions = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'txt', 'csv'}
            if file_ext not in allowed_extensions:
                return False, "Недопустимый формат файла", None, None, None

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{group_name}_{timestamp}_{original_filename}"

            group_folder = os.path.join(self.reports_folder, group_name)
            os.makedirs(group_folder, exist_ok=True)

            file_path = os.path.join(group_folder, filename)
            file.save(file_path)

            file_type = 'text' if file_ext in ['txt', 'csv'] else 'document'

            return True, "Файл успешно сохранен", original_filename, file_path, file_type
        except Exception as e:
            return False, f"Ошибка при сохранении файла: {str(e)}", None, None, None

    def save_text_report(self, content, group_name, title):
        """Сохранить текстовый отчет (без файла)"""
        try:
            if not content or not content.strip():
                return False, "Контент не может быть пустым", None

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{group_name}_{timestamp}_{title.replace(' ', '_')}.txt"

            return True, "Текстовый отчет сохранен", filename
        except Exception as e:
            return False, f"Ошибка при сохранении текстового отчета: {str(e)}", None

    def get_file_content(self, file_path):
        """Получить содержимое текстового файла"""
        try:
            if not os.path.exists(file_path):
                return None

            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"❌ Ошибка чтения файла: {e}")
            return None

    def save_file_content(self, file_path, content):
        """Сохранить содержимое в файл"""
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except Exception as e:
            print(f"❌ Ошибка сохранения файла: {e}")
            return False

    def get_students_data(self, group_name=None, user_id=None):
        """Получает список студентов по группе"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_name)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Получаем информацию о текущем пользователе
            cursor.execute('SELECT user_type, is_curator, curator_group FROM users WHERE id = ?', (user_id,))
            current_user = cursor.fetchone()

            # Если пользователь - преподаватель, проверяем, что он куратор этой группы
            if current_user and current_user['user_type'] == 'teacher':
                if not current_user['is_curator'] or current_user['curator_group'] != group_name:
                    print(f"⚠️ Преподаватель {user_id} не является куратором группы {group_name}")
                    return []

            if not group_name and user_id:
                cursor.execute('SELECT group_name FROM users WHERE id = ?', (user_id,))
                user_group = cursor.fetchone()
                if user_group:
                    group_name = user_group['group_name']

            print(f"🔍 DEBUG get_students_data: Ищем студентов группы '{group_name}'")

            if not group_name:
                print("⚠️  Группа не указана")
                return []

            cursor.execute('''
            SELECT 
                full_name,
                email,
                phone,
                username as login,
                course,
                created_at as joined_date,
                user_type
            FROM users 
            WHERE group_name = ? AND id != ?
            ORDER BY full_name
            ''', (group_name, user_id))

            rows = cursor.fetchall()
            print(f"✅ Найдено {len(rows)} пользователей в группе {group_name}")

            students = []
            for row in rows:
                if row['user_type'] == 'student':
                    import random
                    attendance = f"{random.randint(80, 100)}%"
                    grades = f"{random.uniform(3.5, 5.0):.1f}"

                    students.append({
                        'name': row['full_name'],
                        'group': group_name,
                        'email': row['email'] or 'Не указан',
                        'phone': row['phone'] or 'Не указан',
                        'login': row['login'],
                        'course': row['course'] or 'Не указан',
                        'attendance': attendance,
                        'grades': grades,
                        'joined_date': row['joined_date']
                    })
                    print(f"👤 Добавлен студент: {row['full_name']}")
                else:
                    print(f"⏭️  Пропущен (не студент): {row['full_name']} - тип: {row['user_type']}")

            print(f"📊 Итого студентов: {len(students)}")
            return students

        except Exception as e:
            print(f"❌ Ошибка получения студентов: {e}")
            import traceback
            traceback.print_exc()
            return []
        finally:
            if conn:
                conn.close()

    def get_info_for_headman(self, group_name=None, user_id=None):
        """Получает информацию о группе для старосты"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()

            if not group_name and user_id:
                cursor.execute('SELECT group_name FROM users WHERE id = ?', (user_id,))
                user_group = cursor.fetchone()
                if user_group and user_group['group_name']:
                    group_name = user_group['group_name']

            print(f"🔍 DEBUG get_info_for_headman: Группа = '{group_name}'")

            if not group_name:
                return {
                    'group': 'Группа не указана',
                    'total_students': 0,
                    'excellent': 0,
                    'good': 0,
                    'satisfactory': 0
                }

            cursor.execute('''
            SELECT COUNT(*) as total 
            FROM users 
            WHERE group_name = ? AND user_type = 'student' AND id != ?
            ''', (group_name, user_id))

            result = cursor.fetchone()
            total = result['total'] if result else 0

            print(f"📊 Всего студентов в группе {group_name}: {total}")

            if total == 0:
                return {
                    'group': group_name,
                    'total_students': 0,
                    'excellent': 0,
                    'good': 0,
                    'satisfactory': 0
                }

            import random
            excellent = random.randint(1, max(1, total // 3)) if total > 0 else 0
            good = random.randint(1, max(1, total // 2)) if total > 0 else 0
            satisfactory = max(0, total - excellent - good) if total > 0 else 0

            if excellent + good + satisfactory > total:
                excellent = int(total * 0.3)
                good = int(total * 0.5)
                satisfactory = total - excellent - good

            return {
                'group': group_name,
                'total_students': total,
                'excellent': excellent,
                'good': good,
                'satisfactory': satisfactory
            }

        except Exception as e:
            print(f"❌ Ошибка получения информации о группе: {e}")
            import traceback
            traceback.print_exc()
            return {
                'group': group_name or 'Ошибка загрузки',
                'total_students': 0,
                'excellent': 0,
                'good': 0,
                'satisfactory': 0
            }
        finally:
            if conn:
                conn.close()

    def get_messages(self):
        return [
            {'from': 'Деканат', 'message': 'Собрание старост 15.11 в 14:00', 'date': '2024-11-10'},
            {'from': 'Преподаватель', 'message': 'Принести отчеты до пятницы', 'date': '2024-11-08'}
        ]


class TeachersModule:
    def get_all_teachers(self):
        """Получает всех преподавателей из базы данных"""
        conn = None
        try:
            conn = sqlite3.connect('university.db')
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute('''
            SELECT 
                id,
                username,
                full_name as name,
                department,
                position,
                email,
                phone,
                group_name as room,
                course,
                user_type,
                created_at,
                is_curator,
                curator_group
            FROM users 
            WHERE user_type = 'teacher'
            ORDER BY full_name
            ''')

            teachers = []
            for row in cursor.fetchall():
                teacher = dict(row)
                # Получаем предметы преподавателя
                cursor.execute('''
                SELECT DISTINCT subject 
                FROM tutoring 
                WHERE tutor_id = ? AND tutor_type = 'teacher'
                ''', (teacher['id'],))

                subjects = [row['subject'] for row in cursor.fetchall()]
                if not subjects:
                    subjects = ['Математика', 'Информатика', 'Программирование']

                teacher['subjects'] = subjects
                teachers.append(teacher)

            return teachers
        except Exception as e:
            print(f"❌ Ошибка получения преподавателей: {e}")
            return []
        finally:
            if conn:
                conn.close()

    def get_teachers_by_department(self, department=None):
        """Получает преподавателей по кафедре"""
        conn = None
        try:
            conn = sqlite3.connect('university.db')
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = '''
            SELECT 
                id,
                full_name as name,
                department,
                position,
                email,
                phone,
                group_name as room,
                course,
                user_type,
                created_at,
                is_curator,
                curator_group
            FROM users 
            WHERE user_type = 'teacher'
            '''

            params = []
            if department:
                query += ' AND department = ?'
                params.append(department)

            query += ' ORDER BY full_name'

            cursor.execute(query, params)

            teachers = []
            for row in cursor.fetchall():
                teacher = dict(row)

                # Получаем предметы преподавателя
                cursor.execute('''
                SELECT DISTINCT subject 
                FROM tutoring 
                WHERE tutor_id = ? AND tutor_type = 'teacher'
                ''', (teacher['id'],))

                subjects = [row['subject'] for row in cursor.fetchall()]
                if not subjects:
                    subjects = ['Математика', 'Программирование']

                teacher['subjects'] = subjects
                teachers.append(teacher)

            return teachers

        except Exception as e:
            print(f"❌ Ошибка получения преподавателей по кафедре: {e}")
            return []
        finally:
            if conn:
                conn.close()

    def get_departments(self):
        """Получает список всех кафедр из базы данных"""
        conn = None
        try:
            conn = sqlite3.connect('university.db')
            cursor = conn.cursor()

            cursor.execute('''
            SELECT DISTINCT department 
            FROM users 
            WHERE user_type = 'teacher' AND department IS NOT NULL AND department != ''
            ORDER BY department
            ''')

            departments = [row[0] for row in cursor.fetchall()]

            # Если нет кафедр в БД, возвращаем дефолтные
            if not departments:
                departments = ['Программная инженерия', 'Информационные системы', 'Компьютерные науки']

            return departments

        except Exception as e:
            print(f"❌ Ошибка получения кафедр: {e}")
            return ['Программная инженерия', 'Информационные системы']
        finally:
            if conn:
                conn.close()

    def get_teacher_details(self, teacher_id):
        """Получает детальную информацию о преподавателе"""
        conn = None
        try:
            conn = sqlite3.connect('university.db')
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute('''
            SELECT 
                id,
                username,
                full_name as name,
                department,
                position,
                email,
                phone,
                group_name as room,
                course,
                user_type,
                created_at,
                is_curator,
                curator_group
            FROM users 
            WHERE id = ? AND user_type = 'teacher'
            ''', (teacher_id,))

            row = cursor.fetchone()
            if not row:
                return None

            teacher = dict(row)

            # Получаем предметы преподавателя
            cursor.execute('''
            SELECT DISTINCT subject 
            FROM tutoring 
            WHERE tutor_id = ? AND tutor_type = 'teacher'
            ''', (teacher_id,))

            subjects = [row['subject'] for row in cursor.fetchall()]
            teacher['subjects'] = subjects if subjects else ['Математика', 'Программирование']

            return teacher

        except Exception as e:
            print(f"❌ Ошибка получения деталей преподавателя: {e}")
            return None
        finally:
            if conn:
                conn.close()

    def get_chat_history(self, user_id, teacher_id):
        """Получить историю переписки между студентом и преподавателем"""
        conn = sqlite3.connect('university.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('''
            SELECT m.*, u.full_name as sender_name
            FROM messages m
            JOIN users u ON m.sender_id = u.id
            WHERE (m.sender_id = ? AND m.receiver_id = ?)
               OR (m.sender_id = ? AND m.receiver_id = ?)
            ORDER BY m.timestamp ASC
        ''', (user_id, teacher_id, teacher_id, user_id))
        messages = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return messages

    def send_message_to_teacher(self, sender_id, receiver_id, message):
        """Отправить сообщение преподавателю"""
        conn = sqlite3.connect('university.db')
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO messages (sender_id, receiver_id, message)
                VALUES (?, ?, ?)
            ''', (sender_id, receiver_id, message))
            conn.commit()
            return True, "Сообщение отправлено"
        except Exception as e:
            return False, str(e)
        finally:
            conn.close()


class EventsModule:
    def __init__(self):
        self.db_name = 'university.db'
        self.init_events_table()

    def init_events_table(self):
        """Инициализация таблицы мероприятий в базе данных"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            location TEXT NOT NULL,
            category TEXT NOT NULL,
            organizer TEXT NOT NULL,
            status TEXT DEFAULT 'Запланировано',
            max_participants INTEGER,
            current_participants INTEGER DEFAULT 0,
            requirements TEXT,
            duration TEXT,
            created_by INTEGER NOT NULL,
            created_by_name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (created_by) REFERENCES users(id)
        )
        ''')

        conn.commit()
        conn.close()

    def get_db_connection(self):
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        return conn

    def load_events(self):
        """Загрузить мероприятия из базы данных"""
        conn = self.get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('''
            SELECT * FROM events 
            ORDER BY 
                CASE status
                    WHEN 'Текущее' THEN 1
                    WHEN 'Предстоящее' THEN 2
                    WHEN 'Завершено' THEN 3
                    WHEN 'Отменено' THEN 4
                    ELSE 5
                END,
                date, time
            ''')

            events = []
            for row in cursor.fetchall():
                event = dict(row)
                events.append(event)

            return events
        except Exception as e:
            print(f"❌ Ошибка загрузки мероприятий: {e}")
            return []
        finally:
            conn.close()

    def get_events(self):
        """Получить все мероприятия"""
        return self.load_events()

    def get_event_by_id(self, event_id):
        """Получить мероприятие по ID"""
        conn = self.get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('SELECT * FROM events WHERE id = ?', (event_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            print(f"❌ Ошибка получения мероприятия: {e}")
            return None
        finally:
            conn.close()

    def add_event(self, event_data):
        """Добавить новое мероприятие в базу данных"""
        conn = self.get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('''
            INSERT INTO events 
            (title, description, date, time, location, category, 
             organizer, status, max_participants, requirements, 
             duration, created_by, created_by_name)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                event_data['title'],
                event_data['description'],
                event_data['date'],
                event_data['time'],
                event_data['location'],
                event_data.get('category', 'Общее'),
                event_data['organizer'],
                event_data.get('status', 'Запланировано'),
                event_data.get('max_participants'),
                event_data.get('requirements', ''),
                event_data.get('duration', '2 часа'),
                event_data['created_by'],
                event_data['created_by_name']
            ))

            conn.commit()
            return True, "Мероприятие успешно добавлено"
        except Exception as e:
            conn.rollback()
            print(f"❌ Ошибка добавления мероприятия: {e}")
            return False, f"Ошибка при добавлении мероприятия: {str(e)}"
        finally:
            conn.close()

    def update_event(self, event_id, event_data):
        """Обновить мероприятие"""
        conn = self.get_db_connection()
        cursor = conn.cursor()

        try:
            updates = []
            params = []

            fields = ['title', 'description', 'date', 'time', 'location',
                      'category', 'organizer', 'status', 'max_participants',
                      'requirements', 'duration']

            for field in fields:
                if field in event_data:
                    updates.append(f"{field} = ?")
                    params.append(event_data[field])

            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(event_id)

            sql = f"UPDATE events SET {', '.join(updates)} WHERE id = ?"
            cursor.execute(sql, params)
            conn.commit()

            return True, "Мероприятие успешно обновлено"
        except Exception as e:
            conn.rollback()
            print(f"❌ Ошибка обновления мероприятия: {e}")
            return False, f"Ошибка при обновлении мероприятия: {str(e)}"
        finally:
            conn.close()

    def delete_event(self, event_id, user_id=None, user_type=None):
        """Удалить мероприятие"""
        conn = self.get_db_connection()
        cursor = conn.cursor()

        try:
            # Проверяем права доступа
            if user_id and user_type:
                cursor.execute('''
                SELECT created_by FROM events WHERE id = ?
                ''', (event_id,))
                row = cursor.fetchone()

                if row:
                    event_creator = row['created_by']
                    # Проверяем, может ли пользователь удалить мероприятие
                    if user_type != 'admin' and int(user_id) != int(event_creator):
                        return False, "Вы не можете удалить это мероприятие"

            cursor.execute('DELETE FROM events WHERE id = ?', (event_id,))
            conn.commit()

            return True, "Мероприятие успешно удалено"
        except Exception as e:
            conn.rollback()
            print(f"❌ Ошибка удаления мероприятия: {e}")
            return False, f"Ошибка при удалении мероприятия: {str(e)}"
        finally:
            conn.close()

    def get_upcoming_events(self):
        """Получить предстоящие мероприятия"""
        conn = self.get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('''
            SELECT * FROM events 
            WHERE status IN ('Запланировано', 'Предстоящее', 'Текущее')
            ORDER BY date, time
            LIMIT 10
            ''')

            events = []
            for row in cursor.fetchall():
                events.append(dict(row))

            return events
        except Exception as e:
            print(f"❌ Ошибка получения предстоящих мероприятий: {e}")
            return []
        finally:
            conn.close()


class SimplifiedScheduleModule:
    def __init__(self):
        self.db_name = 'university.db'
        self.init_schedule_tables()

    def get_db_connection(self):
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        return conn

    def init_schedule_tables(self):
        """Инициализация таблиц для хранения PDF файлов расписания"""
        conn = self.get_db_connection()
        cursor = conn.cursor()

        # Таблица для хранения загруженных PDF файлов расписания
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS schedule_pdfs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_name TEXT NOT NULL,
            filename TEXT NOT NULL,
            original_filename TEXT NOT NULL,
            file_path TEXT NOT NULL,
            upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            uploaded_by INTEGER,
            FOREIGN KEY (uploaded_by) REFERENCES users(id)
        )
        ''')

        conn.commit()
        conn.close()

    def save_pdf_schedule(self, group_name, filename, original_filename, file_path, uploaded_by):
        """Сохранить информацию о загруженном PDF файле"""
        conn = self.get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('SELECT id FROM schedule_pdfs WHERE group_name = ?', (group_name,))
            existing = cursor.fetchone()

            if existing:
                cursor.execute('''
                UPDATE schedule_pdfs 
                SET filename = ?, original_filename = ?, file_path = ?, upload_date = CURRENT_TIMESTAMP, uploaded_by = ?
                WHERE group_name = ?
                ''', (filename, original_filename, file_path, uploaded_by, group_name))
            else:
                cursor.execute('''
                INSERT INTO schedule_pdfs (group_name, filename, original_filename, file_path, uploaded_by)
                VALUES (?, ?, ?, ?, ?)
                ''', (group_name, filename, original_filename, file_path, uploaded_by))

            conn.commit()
            return True, "PDF файл расписания успешно сохранен"

        except Exception as e:
            conn.rollback()
            return False, f"Ошибка при сохранении: {str(e)}"
        finally:
            conn.close()

    def get_pdf_schedule(self, group_name):
        """Получить информацию о PDF файле расписания для группы"""
        conn = self.get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('''
            SELECT * FROM schedule_pdfs 
            WHERE group_name = ?
            ORDER BY upload_date DESC 
            LIMIT 1
            ''', (group_name,))

            result = cursor.fetchone()
            return dict(result) if result else None

        except Exception as e:
            print(f"❌ Ошибка получения PDF расписания: {e}")
            return None
        finally:
            conn.close()

    def get_all_pdf_schedules(self):
        """Получить все загруженные PDF расписания"""
        conn = self.get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('''
            SELECT sp.*, u.full_name as uploaded_by_name
            FROM schedule_pdfs sp
            LEFT JOIN users u ON sp.uploaded_by = u.id
            ORDER BY sp.upload_date DESC
            ''')

            return [dict(row) for row in cursor.fetchall()]

        except Exception as e:
            print(f"❌ Ошибка получения списка PDF расписаний: {e}")
            return []
        finally:
            conn.close()

    def delete_pdf_schedule(self, schedule_id):
        """Удалить PDF расписание"""
        conn = self.get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('SELECT file_path FROM schedule_pdfs WHERE id = ?', (schedule_id,))
            result = cursor.fetchone()

            if not result:
                return False, "Расписание не найдено"

            file_path = result['file_path']

            cursor.execute('DELETE FROM schedule_pdfs WHERE id = ?', (schedule_id,))

            if os.path.exists(file_path):
                os.remove(file_path)

            conn.commit()
            return True, "Расписание успешно удалено"

        except Exception as e:
            conn.rollback()
            return False, f"Ошибка при удалении: {str(e)}"
        finally:
            conn.close()

    def get_all_groups(self):
        """Получить список всех групп из расписания"""
        conn = self.get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('SELECT DISTINCT group_name FROM schedule_pdfs ORDER BY group_name')
            pdf_groups = [row['group_name'] for row in cursor.fetchall()]

            if pdf_groups:
                return pdf_groups

            cursor.execute(
                'SELECT DISTINCT group_name FROM users WHERE group_name IS NOT NULL AND group_name != "" ORDER BY group_name')
            user_groups = [row['group_name'] for row in cursor.fetchall()]

            return user_groups

        except Exception as e:
            print(f"❌ Ошибка получения групп: {e}")
            return []
        finally:
            conn.close()

    def get_groups_by_course(self):
        """Получить группы, сгруппированные по курсам"""
        conn = self.get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('SELECT DISTINCT group_name FROM schedule_pdfs')
            pdf_groups = [row['group_name'] for row in cursor.fetchall()]

            groups_by_course = defaultdict(list)
            for group_name in pdf_groups:
                course = 1
                if group_name:
                    import re
                    number_match = re.search(r'\d+', group_name)
                    if number_match:
                        number = number_match.group(0)
                        if len(number) >= 2:
                            course = int(number[0]) if number[0].isdigit() else 1

                groups_by_course[course].append(group_name)

            if groups_by_course:
                return dict(groups_by_course)

            return {}

        except Exception as e:
            print(f"❌ Ошибка получения групп по курсам: {e}")
            return {}
        finally:
            conn.close()


# МОДУЛЬ ДЛЯ ОТЧЕТОВ
class ReportsModule:
    def __init__(self):
        self.db_name = 'university.db'
        self.init_reports_tables()

    def get_db_connection(self):
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        return conn

    def init_reports_tables(self):
        """Инициализация таблиц для хранения отчетов"""
        conn = self.get_db_connection()
        cursor = conn.cursor()

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS group_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_type TEXT NOT NULL CHECK(report_type IN ('attendance', 'performance')),
            group_name TEXT NOT NULL,
            filename TEXT NOT NULL,
            original_filename TEXT NOT NULL,
            file_path TEXT NOT NULL,
            uploaded_by INTEGER NOT NULL,
            uploaded_by_name TEXT NOT NULL,
            uploaded_by_type TEXT NOT NULL,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (uploaded_by) REFERENCES users(id)
        )
        ''')

        conn.commit()
        conn.close()

    def save_report(self, report_type, group_name, filename, original_filename,
                    file_path, uploaded_by, uploaded_by_name, uploaded_by_type):
        """Сохранить информацию о загруженном отчете"""
        conn = self.get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('''
            INSERT INTO group_reports (report_type, group_name, filename, original_filename, 
                                     file_path, uploaded_by, uploaded_by_name, uploaded_by_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (report_type, group_name, filename, original_filename,
                  file_path, uploaded_by, uploaded_by_name, uploaded_by_type))

            conn.commit()
            return True, "Отчет успешно загружен"
        except Exception as e:
            conn.rollback()
            return False, f"Ошибка при сохранении отчета: {str(e)}"
        finally:
            conn.close()

    def get_reports_for_group(self, group_name, report_type=None):
        """Получить отчеты для определенной группы"""
        conn = self.get_db_connection()
        cursor = conn.cursor()

        try:
            if report_type:
                cursor.execute('''
                SELECT * FROM group_reports 
                WHERE group_name = ? AND report_type = ?
                ORDER BY uploaded_at DESC
                ''', (group_name, report_type))
            else:
                cursor.execute('''
                SELECT * FROM group_reports 
                WHERE group_name = ?
                ORDER BY uploaded_at DESC
                ''', (group_name,))

            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"❌ Ошибка получения отчетов: {e}")
            return []
        finally:
            conn.close()

    def get_report_by_id(self, report_id):
        """Получить отчет по ID"""
        conn = self.get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('SELECT * FROM group_reports WHERE id = ?', (report_id,))
            result = cursor.fetchone()
            return dict(result) if result else None
        except Exception as e:
            print(f"❌ Ошибка получения отчета: {e}")
            return None
        finally:
            conn.close()

    def delete_report(self, report_id):
        """Удалить отчет"""
        conn = self.get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('SELECT file_path FROM group_reports WHERE id = ?', (report_id,))
            result = cursor.fetchone()

            if not result:
                return False, "Отчет не найден"

            file_path = result['file_path']

            cursor.execute('DELETE FROM group_reports WHERE id = ?', (report_id,))

            if os.path.exists(file_path):
                os.remove(file_path)

            conn.commit()
            return True, "Отчет успешно удален"
        except Exception as e:
            conn.rollback()
            return False, f"Ошибка при удалении отчета: {str(e)}"
        finally:
            conn.close()


# Инициализация модулей
starosta_module = StarostaModule()
teachers_module = TeachersModule()
events_module = EventsModule()
practice_module = PracticeModule()  # Новый модуль практик
tutoring_module = TutoringModule()
schedule_module = SimplifiedScheduleModule()
reports_module = ReportsModule()

print("✅ Все модули инициализированы")


# ==================== БАЗА ДАННЫХ ====================

def init_db():
    print("🔄 Инициализация базы данных...")
    conn = None
    try:
        conn = sqlite3.connect('university.db')
        cursor = conn.cursor()

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
            is_curator BOOLEAN DEFAULT 0,
            curator_group TEXT,
            created_by TEXT DEFAULT 'system',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            location TEXT NOT NULL,
            category TEXT NOT NULL,
            organizer TEXT NOT NULL,
            status TEXT DEFAULT 'Запланировано',
            max_participants INTEGER,
            current_participants INTEGER DEFAULT 0,
            requirements TEXT,
            duration TEXT,
            created_by INTEGER NOT NULL,
            created_by_name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (created_by) REFERENCES users(id)
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS event_registrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            user_name TEXT NOT NULL,
            registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'Зарегистрирован',
            FOREIGN KEY (event_id) REFERENCES events(id),
            FOREIGN KEY (user_id) REFERENCES users(id),
            UNIQUE(event_id, user_id)
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

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS group_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_type TEXT NOT NULL CHECK(report_type IN ('attendance', 'performance')),
            group_name TEXT NOT NULL,
            filename TEXT NOT NULL,
            original_filename TEXT NOT NULL,
            file_path TEXT NOT NULL,
            uploaded_by INTEGER NOT NULL,
            uploaded_by_name TEXT NOT NULL,
            uploaded_by_type TEXT NOT NULL,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (uploaded_by) REFERENCES users(id)
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS starosta_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_type TEXT NOT NULL CHECK(report_type IN ('attendance', 'performance', 'other')),
            title TEXT NOT NULL,
            description TEXT,
            period TEXT NOT NULL,
            group_name TEXT NOT NULL,
            filename TEXT,
            original_filename TEXT,
            file_path TEXT,
            file_content TEXT,
            file_type TEXT,
            status TEXT DEFAULT 'draft' CHECK(status IN ('draft', 'pending', 'completed')),
            uploaded_by INTEGER NOT NULL,
            uploaded_by_name TEXT NOT NULL,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (uploaded_by) REFERENCES users(id)
        )
        ''')

        cursor.execute("SELECT COUNT(*) FROM users WHERE user_type = 'admin'")
        if cursor.fetchone()[0] == 0:
            cursor.execute('''
            INSERT INTO users (username, password, full_name, user_type, email, created_by)
            VALUES (?, ?, ?, ?, ?, ?)
            ''', ('admin', 'admin123', 'Администратор системы', 'admin', 'admin@university.ru', 'system'))
            print("✅ Создан администратор: admin / admin123")

        # Добавляем тестовые мероприятия
        cursor.execute("SELECT COUNT(*) FROM events")
        if cursor.fetchone()[0] == 0:
            test_events = [
                ('День открытых дверей',
                 'Приглашаем абитуриентов и их родителей на день открытых дверей в нашем техникуме',
                 '15.11.2024', '10:00', 'Актовый зал', 'Общее', 'Администрация',
                 'Запланировано', 200, 0, 'Приглашаются все желающие', '3 часа', 1, 'Администратор'),
                ('Студенческая конференция',
                 'Доклады студентов по научным работам на ежегодной студенческой конференции',
                 '20.11.2024', '14:00', 'Аудитория 301', 'Учебное', 'Научный отдел',
                 'Предстоящее', 50, 0, 'Студенты 2-4 курсов', '4 часа', 1, 'Администратор'),
                ('Спортивные соревнования',
                 'Соревнования между группами по волейболу и баскетболу',
                 '25.11.2024', '09:00', 'Спортзал', 'Спортивное', 'Кафедра физкультуры',
                 'Текущее', 100, 0, 'Спортивная форма', '5 часов', 1, 'Администратор'),
                ('Новогодний вечер',
                 'Новогодний концерт и дискотека для студентов и преподавателей',
                 '28.12.2024', '18:00', 'Актовый зал', 'Культурное', 'Студенческий совет',
                 'Запланировано', 300, 0, 'Новогодние костюмы приветствуются', '6 часов', 1, 'Администратор')
            ]

            for event in test_events:
                cursor.execute('''
                INSERT INTO events 
                (title, description, date, time, location, category, organizer, 
                 status, max_participants, current_participants, requirements, 
                 duration, created_by, created_by_name)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', event)

            print("✅ Добавлены тестовые мероприятия")

        conn.commit()
        print("✅ База данных успешно инициализирована")

    except Exception as e:
        print(f"❌ Ошибка при создании БД: {e}")
        raise
    finally:
        if conn:
            conn.close()


def check_and_fix_db():
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

        # Проверяем наличие поля is_curator
        if 'is_curator' not in columns:
            print("⚠️  Поле is_curator не найдено, добавляю...")
            cursor.execute('ALTER TABLE users ADD COLUMN is_curator BOOLEAN DEFAULT 0')

        # Проверяем наличие поля curator_group
        if 'curator_group' not in columns:
            print("⚠️  Поле curator_group не найдено, добавляю...")
            cursor.execute('ALTER TABLE users ADD COLUMN curator_group TEXT')

        # Проверяем наличие таблицы events
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='events'")
        if not cursor.fetchone():
            print("⚠️  Таблица events не найдена, создаю...")
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                date TEXT NOT NULL,
                time TEXT NOT NULL,
                location TEXT NOT NULL,
                category TEXT NOT NULL,
                organizer TEXT NOT NULL,
                status TEXT DEFAULT 'Запланировано',
                max_participants INTEGER,
                current_participants INTEGER DEFAULT 0,
                requirements TEXT,
                duration TEXT,
                created_by INTEGER NOT NULL,
                created_by_name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (created_by) REFERENCES users(id)
            )
            ''')

        # Проверяем наличие таблицы event_registrations
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='event_registrations'")
        if not cursor.fetchone():
            print("⚠️  Таблица event_registrations не найдена, создаю...")
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS event_registrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                user_name TEXT NOT NULL,
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'Зарегистрирован',
                FOREIGN KEY (event_id) REFERENCES events(id),
                FOREIGN KEY (user_id) REFERENCES users(id),
                UNIQUE(event_id, user_id)
            )
            ''')

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

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='schedule_pdfs'")
        if not cursor.fetchone():
            print("⚠️  Таблицы PDF расписаний не найдены, создаю...")
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS schedule_pdfs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_name TEXT NOT NULL,
                filename TEXT NOT NULL,
                original_filename TEXT NOT NULL,
                file_path TEXT NOT NULL,
                upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                uploaded_by INTEGER,
                FOREIGN KEY (uploaded_by) REFERENCES users(id)
            )
            ''')

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='starosta_reports'")
        if not cursor.fetchone():
            print("⚠️  Таблица starosta_reports не найдена, создаю...")
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS starosta_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_type TEXT NOT NULL CHECK(report_type IN ('attendance', 'performance', 'other')),
                title TEXT NOT NULL,
                description TEXT,
                period TEXT NOT NULL,
                group_name TEXT NOT NULL,
                filename TEXT,
                original_filename TEXT,
                file_path TEXT,
                file_content TEXT,
                file_type TEXT,
                status TEXT DEFAULT 'draft' CHECK(status IN ('draft', 'pending', 'completed')),
                uploaded_by INTEGER NOT NULL,
                uploaded_by_name TEXT NOT NULL,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (uploaded_by) REFERENCES users(id)
            )
            ''')

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='messages'")
        if not cursor.fetchone():
            print("⚠️  Создаём таблицу messages...")
            cursor.execute('''
                CREATE TABLE messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sender_id INTEGER NOT NULL,
                    receiver_id INTEGER NOT NULL,
                    message TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    is_read BOOLEAN DEFAULT 0,
                    FOREIGN KEY (sender_id) REFERENCES users(id),
                    FOREIGN KEY (receiver_id) REFERENCES users(id)
                )
            ''')
            print("✅ Таблица messages создана")

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='practices'")
        if not cursor.fetchone():
            print("⚠️  Таблица practices не найдена, создаю...")
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
            print("✅ Таблица practices создана")

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
            'position': 'position',
            'is_curator': 'is_curator',
            'curator_group': 'curator_group'
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
        is_curator = kwargs.get('is_curator', 0)
        curator_group = kwargs.get('curator_group')

        if course and not str(course).isdigit():
            course = None

        cursor.execute('''
        INSERT INTO users (username, password, full_name, user_type, created_by,
                          email, phone, group_name, course, department, position,
                          is_curator, curator_group)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (username, password, full_name, user_type, created_by,
              email, phone, group, course, department, position,
              is_curator, curator_group))

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
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('''
        SELECT id, username, password, full_name, user_type, email, phone, 
               group_name, course, department, position, created_by, created_at,
               is_curator, curator_group
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
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('''
        SELECT id, username, full_name, user_type, email, phone, 
               group_name, course, department, position, created_by, created_at,
               is_curator, curator_group
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


# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

def allowed_file(filename, file_type='pdf'):
    """Проверка разрешенных расширений файлов"""
    if file_type == 'pdf':
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'pdf'}
    else:
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'txt',
                                                                          'csv'}


def validate_student_fields(user_type, group, course):
    """Валидация полей для студентов"""
    if user_type in ['student', 'starosta']:
        if not group or not group.strip():
            return False, "Группа обязательна для студентов и старост"
        if not course or not str(course).isdigit():
            return False, "Курс обязателен для студентов и старост"
        if not (1 <= int(course) <= 6):
            return False, "Курс должен быть от 1 до 6"
    return True, ""


def check_group_access(user_id, group_name):
    """Проверяет, имеет ли пользователь доступ к группе"""
    user_data = get_user_by_id(user_id)

    if not user_data:
        return False

    # Администраторы имеют доступ ко всем группам
    if user_data['user_type'] == 'admin':
        return True

    # Старосты имеют доступ только к своей группе
    if user_data['user_type'] == 'starosta' and user_data.get('group_name') == group_name:
        return True

    # Преподаватели имеют доступ, если являются кураторами этой группы
    if user_data['user_type'] == 'teacher' and user_data.get('is_curator') and user_data.get(
            'curator_group') == group_name:
        return True

    return False


def can_edit_events(user_type):
    """Проверяет, может ли пользователь редактировать мероприятия"""
    return user_type in ['teacher', 'admin']


# ==================== ДЕКОРАТОРЫ ====================

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


def teacher_or_admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Пожалуйста, войдите в систему', 'warning')
            return redirect(url_for('login'))

        user_data = get_user_by_id(session['user_id'])
        if not user_data:
            flash('Ошибка доступа', 'error')
            return redirect(url_for('login'))

        if user_data['user_type'] not in ['teacher', 'admin']:
            flash('Доступ только для преподавателей и администраторов', 'error')
            return redirect(url_for('home'))

        return f(*args, **kwargs)

    return decorated_function


def starosta_or_teacher_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Пожалуйста, войдите в систему', 'warning')
            return redirect(url_for('login'))

        user_data = get_user_by_id(session['user_id'])
        if not user_data:
            flash('Ошибка доступа', 'error')
            return redirect(url_for('login'))

        # Разрешаем доступ если:
        # 1. Пользователь староста
        # 2. Пользователь администратор
        # 3. Пользователь преподаватель И является куратором
        allowed = (
                user_data['user_type'] == 'starosta' or
                user_data['user_type'] == 'admin' or
                (user_data['user_type'] == 'teacher' and user_data.get('is_curator'))
        )

        if not allowed:
            flash('Доступ только для старосты, администратора или преподавателя-куратора', 'error')
            return redirect(url_for('home'))

        return f(*args, **kwargs)

    return decorated_function


# ==================== МАРШРУТЫ ДЛЯ ПРАКТИК ====================

@app.route('/praktika')
@login_required
def praktika():
    user_data = get_user_by_id(session['user_id'])

    # Проверяем, может ли пользователь управлять практиками
    can_manage = user_data['user_type'] in ['teacher', 'admin']

    # Получаем все практики
    all_practices = practice_module.get_practice_data()

    # Получаем статистику
    stats = practice_module.get_statistics()

    # Получаем уникальные курсы для фильтрации
    courses = sorted(set([p['course'] for p in all_practices]))

    return render_template('praktika.html',
                           user=user_data,
                           practices=all_practices,
                           can_manage=can_manage,
                           stats=stats,
                           courses=courses,
                           session=session)


@app.route('/praktika/add', methods=['GET', 'POST'])
@login_required
@teacher_or_admin_required
def add_practice():
    user_data = get_user_by_id(session['user_id'])

    if request.method == 'POST':
        # Получаем данные из формы
        practice_data = {
            'type': request.form.get('type'),
            'course': request.form.get('course'),
            'start_date': request.form.get('start_date'),
            'end_date': request.form.get('end_date'),
            'supervisor': request.form.get('supervisor'),
            'companies': request.form.get('companies'),
            'status': request.form.get('status'),
            'description': request.form.get('description'),
            'requirements': request.form.get('requirements'),
            'max_students': request.form.get('max_students'),
            'location': request.form.get('location'),
            'contact_person': request.form.get('contact_person'),
            'contact_phone': request.form.get('contact_phone'),
            'contact_email': request.form.get('contact_email'),
            'created_by': session['user_id'],
            'created_by_name': user_data['full_name']
        }

        # Валидация обязательных полей
        required_fields = ['type', 'course', 'start_date', 'end_date', 'supervisor', 'companies']
        for field in required_fields:
            if not practice_data[field]:
                flash('Заполните все обязательные поля', 'error')
                return render_template('add_practice.html', user=user_data, form_data=practice_data)

        # Добавляем практику
        success, message, practice_id = practice_module.add_practice(practice_data)

        if success:
            flash(f'✅ {message}', 'success')
            return redirect(url_for('praktika'))
        else:
            flash(f'❌ {message}', 'error')

    return render_template('add_practice.html', user=user_data)


@app.route('/praktika/edit/<int:practice_id>', methods=['GET', 'POST'])
@login_required
@teacher_or_admin_required
def edit_practice(practice_id):
    user_data = get_user_by_id(session['user_id'])
    practice = practice_module.get_practice_by_id(practice_id)

    if not practice:
        flash('Практика не найдена', 'error')
        return redirect(url_for('praktika'))

    # Проверяем права на редактирование
    if user_data['user_type'] != 'admin' and int(practice['created_by']) != session['user_id']:
        flash('У вас нет прав для редактирования этой практики', 'error')
        return redirect(url_for('praktika'))

    if request.method == 'POST':
        # Получаем данные из формы
        practice_data = {
            'type': request.form.get('type'),
            'course': request.form.get('course'),
            'start_date': request.form.get('start_date'),
            'end_date': request.form.get('end_date'),
            'supervisor': request.form.get('supervisor'),
            'companies': request.form.get('companies'),
            'status': request.form.get('status'),
            'description': request.form.get('description'),
            'requirements': request.form.get('requirements'),
            'max_students': request.form.get('max_students'),
            'current_students': request.form.get('current_students'),
            'location': request.form.get('location'),
            'contact_person': request.form.get('contact_person'),
            'contact_phone': request.form.get('contact_phone'),
            'contact_email': request.form.get('contact_email')
        }

        # Обновляем практику
        success, message = practice_module.update_practice(practice_id, practice_data)

        if success:
            flash(f'✅ {message}', 'success')
            return redirect(url_for('praktika'))
        else:
            flash(f'❌ {message}', 'error')

    return render_template('edit_practice.html', user=user_data, practice=practice)


@app.route('/praktika/delete/<int:practice_id>', methods=['POST'])
@login_required
@teacher_or_admin_required
def delete_practice(practice_id):
    user_data = get_user_by_id(session['user_id'])

    # Удаляем практику
    success, message = practice_module.delete_practice(
        practice_id=practice_id,
        user_id=session['user_id'],
        user_type=user_data['user_type']
    )

    if success:
        flash(f'✅ {message}', 'success')
    else:
        flash(f'❌ {message}', 'error')

    return redirect(url_for('praktika'))


@app.route('/praktika/view/<int:practice_id>')
@login_required
def view_practice(practice_id):
    user_data = get_user_by_id(session['user_id'])
    practice = practice_module.get_practice_by_id(practice_id)

    if not practice:
        flash('Практика не найдена', 'error')
        return redirect(url_for('praktika'))

    can_manage = user_data['user_type'] in ['teacher', 'admin']
    can_edit = (user_data['user_type'] == 'admin' or
                (can_manage and int(practice['created_by']) == session['user_id']))

    return render_template('view_practice.html',
                           user=user_data,
                           practice=practice,
                           can_edit=can_edit)


@app.route('/praktika/search', methods=['GET'])
@login_required
def search_practices():
    user_data = get_user_by_id(session['user_id'])

    search_term = request.args.get('search', '').strip()
    course = request.args.get('course', '').strip()
    status = request.args.get('status', '').strip()

    # Преобразуем параметры
    course = int(course) if course and course.isdigit() else None
    status = status if status else None

    # Выполняем поиск
    practices = practice_module.search_practices(
        search_term=search_term if search_term else None,
        course=course,
        status=status
    )

    # Получаем статистику
    stats = practice_module.get_statistics()

    can_manage = user_data['user_type'] in ['teacher', 'admin']
    courses = sorted(set([p['course'] for p in practices]))

    return render_template('praktika.html',
                           user=user_data,
                           practices=practices,
                           can_manage=can_manage,
                           stats=stats,
                           courses=courses,
                           search_term=search_term,
                           selected_course=course,
                           selected_status=status,
                           session=session)


# ==================== МАРШРУТЫ ДЛЯ МЕРОПРИЯТИЙ ====================

@app.route('/meropriyatiya')
@login_required
def meropriyatiya():
    user_data = get_user_by_id(session['user_id'])
    events = events_module.get_events()

    # Проверяем, может ли пользователь редактировать мероприятия
    can_edit = can_edit_events(user_data['user_type'])

    return render_template('meropriyatiya.html',
                           user=user_data,
                           events=events,
                           can_edit=can_edit,
                           current_user_id=session['user_id'])


@app.route('/meropriyatiya/add', methods=['GET', 'POST'])
@login_required
@teacher_or_admin_required
def add_event():
    user_data = get_user_by_id(session['user_id'])

    if request.method == 'POST':
        # Получаем данные из формы
        title = request.form.get('title')
        description = request.form.get('description')
        date = request.form.get('date')
        time = request.form.get('time')
        location = request.form.get('location')
        category = request.form.get('category')
        organizer = request.form.get('organizer')
        status = request.form.get('status')
        max_participants = request.form.get('max_participants')
        requirements = request.form.get('requirements')
        duration = request.form.get('duration')

        # Валидация обязательных полей
        if not all([title, description, date, time, location, category, organizer]):
            flash('Заполните все обязательные поля', 'error')
            return render_template('add_event.html', user=user_data)

        # Подготавливаем данные для добавления
        event_data = {
            'title': title,
            'description': description,
            'date': date,
            'time': time,
            'location': location,
            'category': category,
            'organizer': organizer,
            'status': status or 'Запланировано',
            'max_participants': int(max_participants) if max_participants and max_participants.isdigit() else None,
            'requirements': requirements or '',
            'duration': duration or '2 часа',
            'created_by': session['user_id'],
            'created_by_name': user_data['full_name']
        }

        # Добавляем мероприятие в базу данных
        success, message = events_module.add_event(event_data)

        if success:
            flash('✅ ' + message, 'success')
            return redirect(url_for('meropriyatiya'))
        else:
            flash('❌ ' + message, 'error')

    return render_template('add_event.html', user=user_data)


@app.route('/meropriyatiya/delete/<int:event_id>', methods=['POST'])
@login_required
@teacher_or_admin_required
def delete_event(event_id):
    user_data = get_user_by_id(session['user_id'])

    # Удаляем мероприятие
    success, message = events_module.delete_event(
        event_id=event_id,
        user_id=session['user_id'],
        user_type=user_data['user_type']
    )

    if success:
        flash('✅ ' + message, 'success')
    else:
        flash('❌ ' + message, 'error')

    return redirect(url_for('meropriyatiya'))


@app.route('/meropriyatiya/edit/<int:event_id>', methods=['GET', 'POST'])
@login_required
@teacher_or_admin_required
def edit_event(event_id):
    user_data = get_user_by_id(session['user_id'])
    event = events_module.get_event_by_id(event_id)

    if not event:
        flash('Мероприятие не найдено', 'error')
        return redirect(url_for('meropriyatiya'))

    # Проверяем права на редактирование
    if user_data['user_type'] != 'admin' and int(event['created_by']) != session['user_id']:
        flash('У вас нет прав для редактирования этого мероприятия', 'error')
        return redirect(url_for('meropriyatiya'))

    if request.method == 'POST':
        # Получаем данные из формы
        event_data = {
            'title': request.form.get('title'),
            'description': request.form.get('description'),
            'date': request.form.get('date'),
            'time': request.form.get('time'),
            'location': request.form.get('location'),
            'category': request.form.get('category'),
            'organizer': request.form.get('organizer'),
            'status': request.form.get('status'),
            'max_participants': request.form.get('max_participants'),
            'requirements': request.form.get('requirements'),
            'duration': request.form.get('duration')
        }

        # Обновляем мероприятие
        success, message = events_module.update_event(event_id, event_data)

        if success:
            flash('✅ ' + message, 'success')
            return redirect(url_for('meropriyatiya'))
        else:
            flash('❌ ' + message, 'error')

    return render_template('edit_event.html', user=user_data, event=event)


@app.route('/meropriyatiya/register/<int:event_id>', methods=['POST'])
@login_required
def register_for_event(event_id):
    user_data = get_user_by_id(session['user_id'])

    # Регистрируем пользователя на мероприятие
    success, message = events_module.register_for_event(
        event_id=event_id,
        user_id=session['user_id'],
        user_name=user_data['full_name']
    )

    if success:
        flash('✅ ' + message, 'success')
    else:
        flash('❌ ' + message, 'error')

    return redirect(url_for('meropriyatiya'))


@app.route('/meropriyatiya/my')
@login_required
def my_events():
    user_data = get_user_by_id(session['user_id'])

    # Получаем все мероприятия пользователя (созданные им)
    all_events = events_module.get_events()
    my_created_events = [e for e in all_events if e['created_by'] == session['user_id']]

    return render_template('my_events.html',
                           user=user_data,
                           my_events=my_created_events)


# ==================== ОСНОВНЫЕ МАРШРУТЫ ====================

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
                session['group'] = user.get('group_name', '')
                # Добавляем информацию о кураторе
                session['is_curator'] = bool(user.get('is_curator'))
                session['curator_group'] = user.get('curator_group')

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

        if not all([username, password, confirm_password, full_name]):
            flash('Заполните все обязательные поля', 'error')
            return render_template('register.html')

        valid, message = validate_student_fields(user_type, group, course)
        if not valid:
            flash(message, 'error')
            return render_template('register.html')

        if password != confirm_password:
            flash('Пароли не совпадают', 'error')
            return render_template('register.html')
        if len(password) < 6:
            flash('Пароль должен быть не менее 6 символов', 'error')
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
        is_curator = 1 if request.form.get('is_curator') == 'on' else 0
        curator_group = request.form.get('curator_group')
        created_by = request.form.get('created_by', session.get('username', 'admin'))

        if not all([username, password, full_name, user_type]):
            flash('Заполните все обязательные поля', 'error')
            return render_template('admin_create_user.html', user=user_data, session=session)

        valid, message = validate_student_fields(user_type, group, course)
        if not valid:
            flash(message, 'error')
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
            position=position,
            is_curator=is_curator,
            curator_group=curator_group
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

    # Определяем группу для отображения
    group_name = None

    # Для студентов-старост - их собственная группа
    if user_data['user_type'] == 'starosta':
        group_name = user_data.get('group_name')

    # Для преподавателей-кураторов - группа куратора
    elif user_data['user_type'] == 'teacher' and user_data.get('is_curator'):
        group_name = user_data.get('curator_group')

    # Для администраторов - можно выбрать любую группу (опционально)
    elif user_data['user_type'] == 'admin':
        # Админ может видеть все группы
        group_name = request.args.get('group', user_data.get('group_name'))

    # Проверяем доступ
    if not group_name:
        if user_data['user_type'] == 'teacher':
            flash('Вы не являетесь куратором группы. Настройте статус куратора в профиле.', 'warning')
            return redirect(url_for('profile'))
        else:
            flash('У вас нет доступа к панели старосты', 'error')
            return redirect(url_for('home'))

    # Получаем данные для группы
    students = starosta_module.get_students_data(
        group_name=group_name,
        user_id=session['user_id']
    )

    info = starosta_module.get_info_for_headman(
        group_name=group_name,
        user_id=session['user_id']
    )

    messages = starosta_module.get_messages()

    reports = []
    if group_name:
        reports = starosta_module.get_reports_for_group(group_name)

    old_reports = []
    if group_name:
        old_reports = reports_module.get_reports_for_group(group_name)

    # Определяем заголовок в зависимости от роли
    if user_data['user_type'] == 'teacher':
        page_title = f"Панель куратора группы {group_name}"
        role_badge = "Куратор"
        role_icon = "bi-person-badge"
    elif user_data['user_type'] == 'starosta':
        page_title = f"Панель старосты группы {group_name}"
        role_badge = "Староста"
        role_icon = "bi-star-fill"
    else:
        page_title = f"Панель группы {group_name}"
        role_badge = "Администратор"
        role_icon = "bi-shield-check"

    return render_template('starosta.html',
                           user=user_data,
                           students=students,
                           info=info,
                           messages=messages,
                           reports=reports,
                           old_reports=old_reports,
                           session=session,
                           page_title=page_title,
                           role_badge=role_badge,
                           role_icon=role_icon)


@app.route('/starosta/create_report', methods=['POST'])
@login_required
def create_report():
    user_data = get_user_by_id(session['user_id'])

    if user_data['user_type'] not in ['starosta', 'teacher', 'admin']:
        flash('Доступ только для старосты, преподавателя или администратора', 'error')
        return redirect(url_for('starosta'))

    report_type = request.form.get('report_type', 'other')
    title = request.form.get('title', '')
    description = request.form.get('description', '')
    period = request.form.get('period', '')

    # Определяем группу для отчета
    if user_data['user_type'] == 'teacher' and user_data.get('is_curator'):
        group_name = user_data.get('curator_group')
    else:
        group_name = user_data.get('group_name', '')

    if not all([title, period, group_name]):
        flash('Заполните все обязательные поля', 'error')
        return redirect(url_for('starosta'))

    # Проверяем доступ к группе
    if not check_group_access(session['user_id'], group_name):
        flash('У вас нет доступа к этой группе', 'error')
        return redirect(url_for('starosta'))

    file = request.files.get('report_file')

    if file and file.filename:
        success, message, original_filename, file_path, file_type = starosta_module.save_report_file(
            file, group_name
        )

        if not success:
            flash(message, 'error')
            return redirect(url_for('starosta'))

        success, message, report_id = starosta_module.create_report(
            report_type=report_type,
            title=title,
            description=description,
            period=period,
            group_name=group_name,
            uploaded_by=session['user_id'],
            uploaded_by_name=user_data['full_name'],
            filename=original_filename,
            file_path=file_path,
            file_type=file_type,
            status='draft'
        )
    else:
        success, message, report_id = starosta_module.create_report(
            report_type=report_type,
            title=title,
            description=description,
            period=period,
            group_name=group_name,
            uploaded_by=session['user_id'],
            uploaded_by_name=user_data['full_name'],
            status='draft'
        )

    if success:
        flash(f'✅ {message}', 'success')
    else:
        flash(f'❌ {message}', 'error')

    return redirect(url_for('starosta'))


@app.route('/starosta/edit/<int:report_id>', methods=['GET', 'POST'])
@login_required
def edit_report(report_id):
    user_data = get_user_by_id(session['user_id'])
    report = starosta_module.get_report_by_id(report_id)

    if not report:
        flash('Отчет не найден', 'error')
        return redirect(url_for('starosta'))

    # Проверяем доступ к группе отчета
    if not check_group_access(session['user_id'], report['group_name']):
        flash('У вас нет доступа к этому отчету', 'error')
        return redirect(url_for('starosta'))

    if request.method == 'POST':
        title = request.form.get('title', report['title'])
        description = request.form.get('description', report['description'])
        period = request.form.get('period', report['period'])
        status = request.form.get('status', report['status'])

        success, message = starosta_module.update_report(
            report_id=report_id,
            title=title,
            description=description,
            period=period,
            status=status
        )

        if report['file_content']:
            content = request.form.get('content', '')
            if content:
                success, message = starosta_module.update_report(
                    report_id=report_id,
                    file_content=content
                )

        file = request.files.get('report_file')
        if file and file.filename:
            if report['file_path'] and os.path.exists(report['file_path']):
                try:
                    os.remove(report['file_path'])
                except Exception as e:
                    print(f"⚠️ Не удалось удалить старый файл: {e}")

            success, msg, original_filename, file_path, file_type = starosta_module.save_report_file(
                file, report['group_name']
            )

            if success:
                success, message = starosta_module.update_report(
                    report_id=report_id,
                    filename=original_filename,
                    file_path=file_path,
                    file_type=file_type
                )
            else:
                flash(msg, 'error')

        if success:
            flash('✅ Отчет успешно обновлен', 'success')
        else:
            flash(f'❌ {message}', 'error')

        return redirect(url_for('starosta'))

    return render_template('edit_report.html',
                           user=user_data,
                           report=report)


@app.route('/delete_old_report/<int:report_id>', methods=['POST'])
@login_required
def delete_old_report(report_id):
    report = reports_module.get_report_by_id(report_id)

    if not report:
        flash('Отчет не найден', 'danger')
        return redirect(url_for('starosta'))

    user_data = get_user_by_id(session['user_id'])
    if user_data['user_type'] != 'admin' and session['user_id'] != report['uploaded_by']:
        flash('У вас нет прав для удаления этого отчета', 'danger')
        return redirect(url_for('starosta'))

    success, message = reports_module.delete_report(report_id)

    if success:
        flash('✅ Отчет успешно удален', 'success')
    else:
        flash(f'❌ {message}', 'danger')

    return redirect(url_for('starosta'))


@app.route('/download_old_report/<int:report_id>')
@login_required
def download_old_report(report_id):
    report = reports_module.get_report_by_id(report_id)

    if not report:
        flash('Отчет не найден', 'danger')
        return redirect(url_for('starosta'))

    user_data = get_user_by_id(session['user_id'])
    if not check_group_access(session['user_id'], report['group_name']):
        flash('У вас нет доступа к этому отчету', 'danger')
        return redirect(url_for('starosta'))

    if not os.path.exists(report['file_path']):
        flash('Файл отчета не найден', 'danger')
        return redirect(url_for('starosta'))

    try:
        return send_file(
            report['file_path'],
            as_attachment=True,
            download_name=report['original_filename']
        )
    except Exception as e:
        flash(f'Ошибка при скачивании файла: {str(e)}', 'danger')
        return redirect(url_for('starosta'))


@app.route('/starosta/view/<int:report_id>')
@login_required
def view_report(report_id):
    user_data = get_user_by_id(session['user_id'])
    report = starosta_module.get_report_by_id(report_id)

    if not report:
        flash('Отчет не найден', 'error')
        return redirect(url_for('starosta'))

    if not check_group_access(session['user_id'], report['group_name']):
        flash('У вас нет доступа к этому отчету', 'error')
        return redirect(url_for('starosta'))

    if report['file_content']:
        return render_template('view_report.html',
                               user=user_data,
                               report=report)
    elif report['file_path'] and os.path.exists(report['file_path']):
        if report['file_type'] == 'text':
            content = starosta_module.get_file_content(report['file_path'])
            return render_template('view_report.html',
                                   user=user_data,
                                   report=report,
                                   content=content)
        else:
            return send_file(
                report['file_path'],
                as_attachment=False,
                mimetype='application/octet-stream'
            )

    flash('Содержимое отчета недоступно', 'error')
    return redirect(url_for('starosta'))


@app.route('/starosta/api/report_content/<int:report_id>', methods=['GET', 'POST'])
@login_required
def report_content_api(report_id):
    user_data = get_user_by_id(session['user_id'])
    report = starosta_module.get_report_by_id(report_id)

    if not report:
        return jsonify({'error': 'Отчет не найден'}), 404

    if not check_group_access(session['user_id'], report['group_name']):
        return jsonify({'error': 'Нет прав доступа'}), 403

    if request.method == 'GET':
        if report['file_content']:
            return jsonify({
                'content': report['file_content'],
                'title': report['title'],
                'status': report['status']
            })
        elif report['file_path'] and report['file_type'] == 'text':
            content = starosta_module.get_file_content(report['file_path'])
            return jsonify({'content': content or ''})
        else:
            return jsonify({'content': ''})

    elif request.method == 'POST':
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Нет данных'}), 400

        content = data.get('content', '')

        if report['file_content']:
            success, message = starosta_module.update_report(
                report_id=report_id,
                file_content=content
            )
        elif report['file_path'] and report['file_type'] == 'text':
            success = starosta_module.save_file_content(report['file_path'], content)
            message = 'Файл обновлен' if success else 'Ошибка сохранения'
        else:
            success, message = starosta_module.update_report(
                report_id=report_id,
                file_content=content,
                file_type='text'
            )

        if success:
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'error': message}), 500


@app.route('/raspisanie', methods=['GET', 'POST'])
@login_required
def raspisanie():
    user_data = get_user_by_id(session['user_id'])

    course = request.args.get('course', type=int)
    group_name = request.args.get('group', '')

    all_groups = schedule_module.get_all_groups()

    pdf_schedule = None
    if group_name:
        pdf_schedule = schedule_module.get_pdf_schedule(group_name)
    elif course:
        groups_for_course_dict = schedule_module.get_groups_by_course()
        groups_for_course = groups_for_course_dict.get(course, [])

        if groups_for_course:
            group_name = groups_for_course[0]
            pdf_schedule = schedule_module.get_pdf_schedule(group_name)
        else:
            flash(f'Для {course} курса нет групп в расписании', 'info')

    schedule_data = {}
    days = []
    exams = []

    return render_template('raspisanie.html',
                           user=user_data,
                           groups=all_groups,
                           selected_group=group_name,
                           schedule=schedule_data,
                           days=days,
                           exams=exams,
                           current_course=course if course else 1,
                           courses=[1, 2, 3, 4],
                           pdf_schedule=pdf_schedule)


@app.route('/upload_schedule', methods=['POST'])
@login_required
@admin_required
def upload_schedule():
    user_data = get_user_by_id(session['user_id'])

    if 'schedule_file' not in request.files:
        flash('Файл не выбран', 'error')
        return redirect(url_for('raspisanie'))

    file = request.files['schedule_file']
    if file.filename == '':
        flash('Файл не выбран', 'error')
        return redirect(url_for('raspisanie'))

    group_name = request.form.get('group_name', '').strip()
    if not group_name:
        flash('Введите название группы', 'error')
        return redirect(url_for('raspisanie'))

    if file and allowed_file(file.filename):
        try:
            original_filename = secure_filename(file.filename)
            filename = f"{group_name}_{int(time.time())}_{original_filename}"

            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)

            print(f"📁 PDF файл сохранен: {file_path}")
            print(f"📊 Группа: {group_name}")

            success, message = schedule_module.save_pdf_schedule(
                group_name=group_name,
                filename=filename,
                original_filename=original_filename,
                file_path=file_path,
                uploaded_by=session['user_id']
            )

            if success:
                flash(f'✅ {message} для группы {group_name}', 'success')
            else:
                flash(f'❌ {message}', 'error')
                if os.path.exists(file_path):
                    os.remove(file_path)

        except Exception as e:
            flash(f'❌ Ошибка обработки файла: {str(e)}', 'error')
            import traceback
            traceback.print_exc()
    else:
        flash('❌ Разрешены только PDF файлы', 'error')

    return redirect(url_for('raspisanie'))


@app.route('/download_schedule/<group_name>')
@login_required
def download_schedule(group_name):
    pdf_schedule = schedule_module.get_pdf_schedule(group_name)

    if not pdf_schedule or not os.path.exists(pdf_schedule['file_path']):
        flash('Расписание не найдено', 'error')
        return redirect(url_for('raspisanie'))

    try:
        return send_file(
            pdf_schedule['file_path'],
            as_attachment=True,
            download_name=pdf_schedule['original_filename'],
            mimetype='application/pdf'
        )
    except Exception as e:
        flash(f'Ошибка при скачивании файла: {str(e)}', 'error')
        return redirect(url_for('raspisanie'))


@app.route('/view_schedule/<group_name>')
@login_required
def view_schedule(group_name):
    pdf_schedule = schedule_module.get_pdf_schedule(group_name)

    if not pdf_schedule or not os.path.exists(pdf_schedule['file_path']):
        flash('Расписание не найдено', 'error')
        return redirect(url_for('raspisanie'))

    try:
        return send_file(
            pdf_schedule['file_path'],
            as_attachment=False,
            mimetype='application/pdf'
        )
    except Exception as e:
        flash(f'Ошибка при открытии файла: {str(e)}', 'error')
        return redirect(url_for('raspisanie'))


@app.route('/upload_report/<report_type>/<group_name>', methods=['POST'])
@login_required
@starosta_or_teacher_required
def upload_report(report_type, group_name):
    user_data = get_user_by_id(session['user_id'])

    # Проверяем доступ к группе
    if not check_group_access(session['user_id'], group_name):
        flash('Вы можете загружать отчеты только для доступных вам групп', 'danger')
        return redirect(url_for('starosta'))

    if 'file' not in request.files:
        flash('Файл не выбран', 'danger')
        return redirect(url_for('starosta'))

    file = request.files['file']
    if file.filename == '':
        flash('Файл не выбран', 'danger')
        return redirect(url_for('starosta'))

    if file and allowed_file(file.filename, 'report'):
        try:
            original_filename = secure_filename(file.filename)
            filename = f"{report_type}_{group_name}_{int(time.time())}_{original_filename}"

            group_folder = os.path.join(app.config['REPORT_UPLOAD_FOLDER'], group_name)
            os.makedirs(group_folder, exist_ok=True)

            file_path = os.path.join(group_folder, filename)
            file.save(file_path)

            success, message = reports_module.save_report(
                report_type=report_type,
                group_name=group_name,
                filename=filename,
                original_filename=original_filename,
                file_path=file_path,
                uploaded_by=session['user_id'],
                uploaded_by_name=user_data['full_name'],
                uploaded_by_type=user_data['user_type']
            )

            if success:
                report_name = 'посещаемости' if report_type == 'attendance' else 'успеваемости'
                flash(f'✅ Отчет по {report_name} успешно загружен для группы {group_name}', 'success')
            else:
                flash(f'❌ {message}', 'danger')
                if os.path.exists(file_path):
                    os.remove(file_path)

        except Exception as e:
            flash(f'❌ Ошибка загрузки файла: {str(e)}', 'danger')
    else:
        flash('❌ Недопустимый формат файла. Разрешены: PDF, DOC, DOCX, XLS, XLSX, TXT, CSV', 'danger')

    return redirect(url_for('starosta'))


@app.route('/download_report/<int:report_id>')
@login_required
def download_report(report_id):
    report = reports_module.get_report_by_id(report_id)

    if not report:
        flash('Отчет не найден', 'danger')
        return redirect(url_for('starosta'))

    user_data = get_user_by_id(session['user_id'])
    if not check_group_access(session['user_id'], report['group_name']):
        flash('У вас нет доступа к этому отчету', 'danger')
        return redirect(url_for('starosta'))

    if not os.path.exists(report['file_path']):
        flash('Файл отчета не найден', 'danger')
        return redirect(url_for('starosta'))

    try:
        return send_file(
            report['file_path'],
            as_attachment=True,
            download_name=report['original_filename']
        )
    except Exception as e:
        flash(f'Ошибка при скачивании файла: {str(e)}', 'danger')
        return redirect(url_for('starosta'))


@app.route('/delete_report/<int:report_id>', methods=['POST'])
@login_required
def delete_report(report_id):
    report = reports_module.get_report_by_id(report_id)

    if not report:
        flash('Отчет не найден', 'danger')
        return redirect(url_for('starosta'))

    user_data = get_user_by_id(session['user_id'])
    if user_data['user_type'] != 'admin' and session['user_id'] != report['uploaded_by']:
        flash('У вас нет прав для удаления этого отчета', 'danger')
        return redirect(url_for('starosta'))

    success, message = reports_module.delete_report(report_id)

    if success:
        flash('✅ Отчет успешно удален', 'success')
    else:
        flash(f'❌ {message}', 'danger')

    return redirect(url_for('starosta'))


@app.route('/api/search_group')
@login_required
def search_group():
    search_term = request.args.get('q', '')

    if not search_term:
        return jsonify([])

    all_groups = schedule_module.get_all_groups()
    results = [group for group in all_groups if search_term.lower() in group.lower()]

    return jsonify(results[:10])


@app.route('/repetitorstvo')
@login_required
def repetitorstvo():
    user_data = get_user_by_id(session['user_id'])
    try:
        tutoring_data = tutoring_module.get_tutoring_data()
        return render_template('repetitorstvo.html',
                               user=user_data,
                               teachers=tutoring_data['teachers'],
                               students=tutoring_data['students'],
                               tutoring_sessions=[],
                               available_tutors=[],
                               subjects_count=5,
                               success_rate=95)
    except Exception as e:
        print(f"❌ Ошибка в маршруте repetitorstvo: {e}")
        return render_template('repetitorstvo.html',
                               user=user_data,
                               teachers=[],
                               students=[],
                               tutoring_sessions=[],
                               available_tutors=[],
                               subjects_count=0,
                               success_rate=0)


@app.route('/prepodavateli')
@login_required
def prepodavateli():
    user_data = get_user_by_id(session['user_id'])

    # Получаем параметры фильтрации
    search_query = request.args.get('search', '').strip()
    selected_department = request.args.get('department', '').strip()

    # Получаем всех преподавателей
    teachers = teachers_module.get_all_teachers()
    departments = teachers_module.get_departments()

    # Применяем фильтры
    filtered_teachers = teachers

    if search_query:
        filtered_teachers = [
            t for t in filtered_teachers
            if search_query.lower() in t['name'].lower() or
               search_query.lower() in (t.get('department') or '').lower() or
               any(search_query.lower() in subject.lower() for subject in t.get('subjects', []))
        ]

    if selected_department:
        filtered_teachers = [
            t for t in filtered_teachers
            if t.get('department') == selected_department
        ]

    print(f"🔍 Преподаватели после фильтрации: {len(filtered_teachers)} из {len(teachers)}")

    return render_template('prepodavateli.html',
                           user=user_data,
                           teachers=filtered_teachers,
                           departments=departments,
                           search_query=search_query,
                           selected_department=selected_department)


@app.route('/prepodavateli/<int:teacher_id>')
@login_required
def teacher_detail(teacher_id):
    user_data = get_user_by_id(session['user_id'])
    teacher = teachers_module.get_teacher_details(teacher_id)

    if not teacher:
        flash('Преподаватель не найден', 'error')
        return redirect(url_for('prepodavateli'))

    return render_template('teacher_detail.html',
                           user=user_data,
                           teacher=teacher)


@app.route('/api/teachers/search')
@login_required
def search_teachers_api():
    query = request.args.get('q', '')

    if not query:
        return jsonify([])

    teachers = teachers_module.get_all_teachers()

    results = []
    for teacher in teachers:
        if query.lower() in teacher['name'].lower():
            results.append({
                'id': teacher['id'],
                'name': teacher['name'],
                'department': teacher.get('department', ''),
                'position': teacher.get('position', ''),
                'subjects': teacher.get('subjects', [])
            })

    return jsonify(results[:10])


@app.route('/podderzhka')
@login_required
def podderzhka():
    user_data = get_user_by_id(session['user_id'])
    return render_template('podderzhka.html', user=user_data)


@app.route('/profile')
@login_required
def profile():
    user_data = get_user_by_id(session['user_id'])
    return render_template('profile.html', user=user_data)


@app.route('/profile/set_curator', methods=['GET', 'POST'])
@login_required
def set_curator():
    """Настройка статуса куратора для преподавателя с возможностью смены группы"""
    user_data = get_user_by_id(session['user_id'])

    if user_data['user_type'] != 'teacher':
        flash('Только преподаватели могут быть кураторами', 'error')
        return redirect(url_for('profile'))

    if request.method == 'POST':
        action = request.form.get('action')
        group_name = request.form.get('group_name', '').strip()
        new_group_name = request.form.get('new_group_name', '').strip()

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            if action == 'set':
                if group_name:
                    # Проверяем, существует ли такая группа
                    cursor.execute('SELECT COUNT(*) FROM users WHERE group_name = ? AND user_type = "student"',
                                   (group_name,))
                    if cursor.fetchone()[0] > 0:
                        # Устанавливаем преподавателя как куратора
                        cursor.execute('''
                            UPDATE users 
                            SET is_curator = 1, curator_group = ?
                            WHERE id = ?
                        ''', (group_name, session['user_id']))
                        flash(f'Вы назначены куратором группы {group_name}', 'success')
                    else:
                        flash('Группа не найдена или в ней нет студентов', 'error')
                else:
                    flash('Введите название группы', 'error')

            elif action == 'change':
                if new_group_name:
                    # Проверяем, существует ли новая группа
                    cursor.execute('SELECT COUNT(*) FROM users WHERE group_name = ? AND user_type = "student"',
                                   (new_group_name,))
                    if cursor.fetchone()[0] > 0:
                        # Меняем группу куратора
                        old_group = user_data.get('curator_group')
                        cursor.execute('''
                            UPDATE users 
                            SET curator_group = ?
                            WHERE id = ?
                        ''', (new_group_name, session['user_id']))
                        flash(f'Группа куратора изменена с {old_group} на {new_group_name}', 'success')
                    else:
                        flash('Группа не найдена или в ней нет студентов', 'error')
                else:
                    flash('Введите название новой группы', 'error')

            elif action == 'remove':
                # Снимаем статус куратора
                cursor.execute('''
                    UPDATE users 
                    SET is_curator = 0, curator_group = NULL 
                    WHERE id = ?
                ''', (session['user_id'],))
                flash('Статус куратора удален', 'info')

            conn.commit()

            # Обновляем данные в сессии
            updated_user = get_user_by_id(session['user_id'])
            if updated_user:
                session['is_curator'] = bool(updated_user.get('is_curator'))
                session['curator_group'] = updated_user.get('curator_group')

        except Exception as e:
            print(f"❌ Ошибка обновления статуса куратора: {e}")
            flash('Ошибка при сохранении', 'error')
        finally:
            conn.close()

        return redirect(url_for('profile'))

    return render_template('set_curator.html', user=user_data)


@app.route('/users')
@login_required
@admin_required
def users_list():
    user_data = get_user_by_id(session['user_id'])
    users = get_all_users()
    return render_template('users.html', user=user_data, users=users)


@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def delete_user_route(user_id):
    if delete_user(user_id):
        flash('Пользователь успешно удален', 'success')
    else:
        flash('Пользователь не найден', 'error')

    return redirect(url_for('users_list'))


@app.route('/repetitorstvo/add', methods=['GET', 'POST'])
@login_required
def add_tutoring():
    user_data = get_user_by_id(session['user_id'])

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

        tutor_type = 'teacher' if user_data['user_type'] == 'teacher' else 'student'

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


@app.route('/admin/edit_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    user_data = get_user_by_id(session['user_id'])

    target_user = get_user_by_id(user_id)
    if not target_user:
        flash('Пользователь не найден', 'error')
        return redirect(url_for('users_list'))

    if request.method == 'POST':
        username = request.form.get('username')
        full_name = request.form.get('full_name')
        user_type = request.form.get('user_type')
        email = request.form.get('email')
        phone = request.form.get('phone')
        group = request.form.get('group')
        course = request.form.get('course')
        department = request.form.get('department')
        position = request.form.get('position')
        is_curator = 1 if request.form.get('is_curator') == 'on' else 0
        curator_group = request.form.get('curator_group')

        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

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

        update_data = {
            'username': username,
            'full_name': full_name,
            'user_type': user_type,
            'email': email,
            'phone': phone,
            'group': group,
            'course': course,
            'department': department,
            'position': position,
            'is_curator': is_curator,
            'curator_group': curator_group
        }

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
    user_data = get_user_by_id(session['user_id'])

    if user_data['user_type'] != 'student':
        flash('Только студенты могут записываться на репетиторство', 'error')
        return redirect(url_for('repetitorstvo'))

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
    user_data = get_user_by_id(session['user_id'])

    my_tutoring_list = tutoring_module.get_my_tutoring(user_data['id'])

    return render_template('my_tutoring.html',
                           user=user_data,
                           my_tutoring=my_tutoring_list)


@app.route('/repetitorstvo/delete/<int:tutoring_id>')
@login_required
def delete_tutoring(tutoring_id):
    user_data = get_user_by_id(session['user_id'])

    success, message = tutoring_module.delete_tutoring(tutoring_id, user_data['id'])
    flash(message, 'success' if success else 'error')

    return redirect(url_for('my_tutoring'))


@app.route('/admin/schedule')
@login_required
@admin_required
def admin_schedule():
    user_data = get_user_by_id(session['user_id'])

    all_groups = schedule_module.get_all_groups()
    groups_by_course = schedule_module.get_groups_by_course()
    pdf_schedules = schedule_module.get_all_pdf_schedules()

    return render_template('admin_schedule.html',
                           user=user_data,
                           all_groups=all_groups,
                           groups_by_course=groups_by_course,
                           pdf_schedules=pdf_schedules,
                           total_groups=len(all_groups))


@app.route('/admin/delete_schedule/<int:schedule_id>', methods=['POST'])
@login_required
@admin_required
def delete_schedule(schedule_id):
    success, message = schedule_module.delete_pdf_schedule(schedule_id)
    flash(message, 'success' if success else 'error')
    return redirect(url_for('admin_schedule'))


# ==================== ЧАТ С ПРЕПОДАВАТЕЛЕМ ====================

@app.route('/chat/<int:teacher_id>')
@login_required
def chat(teacher_id):
    """Открыть чат со преподавателем"""
    user_data = get_user_by_id(session['user_id'])

    if user_data['user_type'] != 'student':
        flash('Только студенты могут писать преподавателям', 'error')
        return redirect(url_for('prepodavateli'))

    teacher = get_user_by_id(teacher_id)
    if not teacher or teacher['user_type'] != 'teacher':
        flash('Преподаватель не найден', 'error')
        return redirect(url_for('prepodavateli'))

    conn = sqlite3.connect('university.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('''
        SELECT m.*, u.full_name as sender_name
        FROM messages m
        JOIN users u ON m.sender_id = u.id
        WHERE 
            (m.sender_id = ? AND m.receiver_id = ?)
            OR 
            (m.sender_id = ? AND m.receiver_id = ?)
        ORDER BY m.timestamp ASC
    ''', (session['user_id'], teacher_id, teacher_id, session['user_id']))

    messages = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return render_template('chat.html',
                           user=user_data,
                           teacher=teacher,
                           messages=messages)


@app.route('/chat/<int:teacher_id>/send', methods=['POST'])
@login_required
def send_message(teacher_id):
    """Отправить сообщение преподавателю"""
    message = request.form.get('message', '').strip()
    if not message:
        flash('Сообщение не может быть пустым', 'error')
        return redirect(url_for('chat', teacher_id=teacher_id))

    conn = sqlite3.connect('university.db')
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO messages (sender_id, receiver_id, message)
            VALUES (?, ?, ?)
        ''', (session['user_id'], teacher_id, message))
        conn.commit()
    except Exception as e:
        print("❌ Ошибка отправки сообщения:", e)
        flash('Не удалось отправить сообщение', 'error')
    finally:
        conn.close()

    return redirect(url_for('chat', teacher_id=teacher_id))


@app.route('/prepodavateli/chat/<int:teacher_id>')
@login_required
def teacher_chat(teacher_id):
    user_data = get_user_by_id(session['user_id'])
    teacher = get_user_by_id(teacher_id)
    if not teacher or teacher['user_type'] != 'teacher':
        flash('Преподаватель не найден', 'error')
        return redirect(url_for('prepodavateli'))

    if user_data['user_type'] != 'student':
        flash('Только студенты могут писать преподавателям', 'error')
        return redirect(url_for('prepodavateli'))

    messages = teachers_module.get_chat_history(user_data['id'], teacher_id)
    return render_template('teacher_chat.html',
                           user=user_data,
                           teacher=teacher,
                           messages=messages)


@app.route('/prepodavateli/chat/<int:teacher_id>/send', methods=['POST'])
@login_required
def send_teacher_message(teacher_id):
    user_data = get_user_by_id(session['user_id'])
    message = request.form.get('message', '').strip()
    if not message:
        flash('Сообщение не может быть пустым', 'error')
        return redirect(url_for('teacher_chat', teacher_id=teacher_id))

    if user_data['user_type'] != 'student':
        flash('Только студенты могут писать преподавателям', 'error')
        return redirect(url_for('prepodavateli'))

    success, msg = teachers_module.send_message_to_teacher(
        user_data['id'], teacher_id, message
    )
    if not success:
        flash(f'Ошибка: {msg}', 'error')

    return redirect(url_for('teacher_chat', teacher_id=teacher_id))


@app.route('/teacher_chats')
@login_required
def teacher_chats():
    if session.get('user_type') != 'teacher':
        flash('Только преподаватели могут просматривать чаты', 'error')
        return redirect(url_for('home'))

    teacher_id = session['user_id']

    conn = sqlite3.connect('university.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Получаем список студентов, с которыми есть переписка
    cursor.execute('''
        SELECT DISTINCT u.id, u.full_name, u.group_name, MAX(m.timestamp) as last_message
        FROM messages m
        JOIN users u ON (m.sender_id = u.id OR m.receiver_id = u.id)
        WHERE (m.sender_id = ? OR m.receiver_id = ?) 
          AND u.id != ?
          AND u.user_type = 'student'
        GROUP BY u.id
        ORDER BY last_message DESC
    ''', (teacher_id, teacher_id, teacher_id))

    students_with_chat = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return render_template('teacher_chats.html', students=students_with_chat)


@app.route('/teacher_chat_with_student/<int:student_id>', methods=['GET', 'POST'])
@login_required
def teacher_chat_with_student(student_id):
    if session.get('user_type') != 'teacher':
        flash('Только преподаватели могут общаться со студентами', 'error')
        return redirect(url_for('home'))

    teacher_id = session['user_id']

    conn = sqlite3.connect('university.db')
    conn.row_factory = sqlite3.Row

    # Получаем информацию о студенте
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE id = ? AND user_type = "student"', (student_id,))
    student = cursor.fetchone()

    if not student:
        flash('Студент не найден', 'error')
        return redirect(url_for('teacher_chats'))

    # Получаем историю переписки
    cursor.execute('''
        SELECT m.*, u.full_name as sender_name
        FROM messages m
        JOIN users u ON m.sender_id = u.id
        WHERE (m.sender_id = ? AND m.receiver_id = ?)
           OR (m.sender_id = ? AND m.receiver_id = ?)
        ORDER BY m.timestamp ASC
    ''', (student_id, teacher_id, teacher_id, student_id))

    messages = [dict(row) for row in cursor.fetchall()]

    if request.method == 'POST':
        message = request.form.get('message', '').strip()
        if message:
            try:
                cursor.execute('''
                    INSERT INTO messages (sender_id, receiver_id, message)
                    VALUES (?, ?, ?)
                ''', (teacher_id, student_id, message))
                conn.commit()
                return redirect(url_for('teacher_chat_with_student', student_id=student_id))
            except Exception as e:
                print(f"❌ Ошибка отправки сообщения: {e}")
                flash('Не удалось отправить сообщение', 'error')

    conn.close()

    return render_template('teacher_chat_with_student.html',
                           student=dict(student),
                           messages=messages)


@app.route('/api/get_messages/<int:teacher_id>')
@login_required
def get_messages_api(teacher_id):
    """API для получения сообщений с преподавателем"""
    user_data = get_user_by_id(session['user_id'])

    if user_data['user_type'] != 'student':
        return jsonify({'error': 'Только студенты могут получать сообщения'}), 403

    teacher = get_user_by_id(teacher_id)
    if not teacher or teacher['user_type'] != 'teacher':
        return jsonify({'error': 'Преподаватель не найден'}), 404

    conn = sqlite3.connect('university.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute('''
        SELECT m.*, u.full_name as sender_name
        FROM messages m
        JOIN users u ON m.sender_id = u.id
        WHERE 
            (m.sender_id = ? AND m.receiver_id = ?)
            OR 
            (m.sender_id = ? AND m.receiver_id = ?)
        ORDER BY m.timestamp ASC
    ''', (session['user_id'], teacher_id, teacher_id, session['user_id']))

    messages = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return jsonify(messages)


@app.route('/api/send_message_student/<int:teacher_id>', methods=['POST'])
@login_required
def send_message_student_api(teacher_id):
    """API для отправки сообщений студентами через AJAX"""
    user_data = get_user_by_id(session['user_id'])

    if user_data['user_type'] != 'student':
        return jsonify({'success': False, 'error': 'Только студенты могут использовать этот API'})

    message = request.form.get('message', '').strip()
    if not message:
        return jsonify({'success': False, 'error': 'Сообщение не может быть пустым'})

    teacher = get_user_by_id(teacher_id)
    if not teacher or teacher['user_type'] != 'teacher':
        return jsonify({'success': False, 'error': 'Преподаватель не найден'})

    conn = sqlite3.connect('university.db')
    cursor = conn.cursor()

    try:
        cursor.execute('''
            INSERT INTO messages (sender_id, receiver_id, message)
            VALUES (?, ?, ?)
        ''', (session['user_id'], teacher_id, message))

        conn.commit()
        return jsonify({'success': True, 'message': 'Сообщение отправлено'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
    finally:
        conn.close()

# ==================== ЗАПУСК ПРИЛОЖЕНИЯ ====================

if __name__ == '__main__':
    print("=" * 50)
    print("🚀 Запуск University Management System")
    print("=" * 50)

    if check_and_fix_db():
        print("✅ База данных готова к работе")
        print("✅ Модуль практик инициализирован")
        print("✅ Модуль мероприятий инициализирован")
        print("✅ Модуль расписания инициализирован")
        print("✅ Модуль отчетов инициализирован")
        print("✅ Система управления практиками готова")
        print("🌐 Приложение доступно по адресам:")
        print("   • На компьютере: http://localhost:5000")
        print("   • На телефоне в той же Wi-Fi сети: http://ВАШ_IP:5000")
        print("🔑 Администратор: admin / admin123")
        print("📚 Репетиторство работает через БД")
        print("📅 Расписание: администраторы загружают PDF файлы")
        print("🎉 Мероприятия: преподаватели и администраторы могут добавлять/удалять")
        print("📊 Отчеты: старосты и преподаватели-кураторы загружают отчеты")
        print("👨‍🏫 Преподаватели могут стать кураторами и менять группу куратора")
        print("💬 Чат с преподавателями работает")
        print("🏢 Практики: преподаватели и администраторы могут добавлять/редактировать/удалять")
        print("🔍 Поиск практик по типу, курсу и статусу")
        print("📈 Статистика практик на главной странице")
        print("=" * 50)

        app.run(
            debug=True,
            host='0.0.0.0',
            port=5000,
            threaded=True
        )
    else:
        print("❌ Не удалось инициализировать базу данных")