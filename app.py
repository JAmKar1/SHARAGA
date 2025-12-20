# app.py (исправленная версия)

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

# Создаем папки для загрузок
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['REPORT_UPLOAD_FOLDER'], exist_ok=True)


# ==================== МОДУЛИ ====================

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
            conn = self.get_db_connection()
            cursor = conn.cursor()

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
            conn = self.get_db_connection()
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
                created_at
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
                created_at
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
                created_at
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


# УПРОЩЕННЫЙ МОДУЛЬ РАСПИСАНИЯ
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
practice_module = PracticeModule()
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


# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ ФАЙЛОВ ====================

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


def starosta_or_teacher_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Пожалуйста, войдите в систему', 'warning')
            return redirect(url_for('login'))
        user_data = get_user_by_id(session['user_id'])
        if not user_data or user_data['user_type'] not in ['starosta', 'teacher', 'admin']:
            flash('Доступ только для старосты, преподавателя или администратора', 'error')
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
                session['group'] = user.get('group_name', '')
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
    if user_data['user_type'] not in ['starosta', 'teacher', 'admin']:
        flash('Доступ только для старосты, преподавателя или администратора', 'error')
        return redirect(url_for('home'))

    students = starosta_module.get_students_data(
        group_name=user_data.get('group_name'),
        user_id=session['user_id']
    )
    info = starosta_module.get_info_for_headman(
        group_name=user_data.get('group_name'),
        user_id=session['user_id']
    )
    messages = starosta_module.get_messages()

    reports = []
    if user_data.get('group_name'):
        reports = starosta_module.get_reports_for_group(user_data['group_name'])

    old_reports = []
    if user_data.get('group_name'):
        old_reports = reports_module.get_reports_for_group(user_data['group_name'])

    return render_template('starosta.html',
                           user=user_data,
                           students=students,
                           info=info,
                           messages=messages,
                           reports=reports,
                           old_reports=old_reports,
                           session=session)


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
    group_name = user_data.get('group_name', '')

    if not all([title, period, group_name]):
        flash('Заполните все обязательные поля', 'error')
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

    if report['uploaded_by'] != session['user_id'] and user_data['user_type'] != 'admin':
        flash('У вас нет прав для редактирования этого отчета', 'error')
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
    if user_data['user_type'] not in ['admin', 'teacher'] and user_data.get('group_name') != report['group_name']:
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

    if report['group_name'] != user_data.get('group_name') and user_data['user_type'] not in ['teacher', 'admin']:
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

    if report['uploaded_by'] != session['user_id'] and user_data['user_type'] != 'admin':
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

    if user_data['user_type'] == 'starosta' and user_data.get('group_name') != group_name:
        flash('Вы можете загружать отчеты только для своей группы', 'danger')
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
    if user_data['user_type'] not in ['admin', 'teacher'] and user_data.get('group_name') != report['group_name']:
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
    user_data = get_user_by_id(session['user_id'])
    return render_template('profile.html', user=user_data)


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
            'position': position
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


# ==================== ЗАПУСК ПРИЛОЖЕНИЯ ====================

if __name__ == '__main__':
    print("=" * 50)
    print("🚀 Запуск University Management System")
    print("=" * 50)

    if check_and_fix_db():
        print("✅ База данных готова к работе")
        print("✅ Модуль расписания инициализирован")
        print("✅ Модуль отчетов инициализирован")
        print("✅ Функция загрузки PDF файлов доступна")
        print("✅ Функция загрузки отчетов доступна")
        print("🌐 Приложение доступно по адресам:")
        print("   • На компьютере: http://localhost:5000")
        print("   • На телефоне в той же Wi-Fi сети: http://ВАШ_IP:5000")
        print("🔑 Администратор: admin / admin123")
        print("📚 Репетиторство работает через БД")
        print("📅 Расписание: администраторы загружают PDF файлы")
        print("📊 Отчеты: старосты и преподаватели загружают отчеты")
        print("💬 Чат с преподавателями работает")
        print("=" * 50)

        app.run(
            debug=True,
            host='0.0.0.0',
            port=5000,
            threaded=True
        )
    else:
        print("❌ Не удалось инициализировать базу данных")