"""
Модуль для работы с функционалом старосты
"""
import os
import json
import sqlite3
from datetime import datetime
import uuid
from werkzeug.utils import secure_filename


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
            file_content TEXT,  # Для хранения текстового содержимого
            file_type TEXT,     # Тип файла: text, pdf, doc, etc.
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

    # ==================== ОСНОВНЫЕ МЕТОДЫ ДЛЯ РАБОТЫ С ОТЧЕТАМИ ====================

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
                # Добавляем информацию о файле
                report['has_file'] = bool(report['filename']) or bool(report['file_content'])
                report['has_uploaded_file'] = bool(report['filename'])
                report['has_text_content'] = bool(report['file_content'])

                # URL для скачивания/просмотра
                if report['filename']:
                    report['file_url'] = f"/starosta/download/{report['id']}"
                    report['view_url'] = f"/starosta/view/{report['id']}"
                elif report['file_content']:
                    report['edit_url'] = f"/starosta/edit/{report['id']}"

                # Определяем цвет статуса
                status_colors = {
                    'draft': 'secondary',
                    'pending': 'warning',
                    'completed': 'success'
                }
                report['status_color'] = status_colors.get(report['status'], 'secondary')

                # Русское название статуса
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

            # Всегда обновляем updated_at
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
            # Получаем информацию о файле
            cursor.execute('SELECT file_path FROM starosta_reports WHERE id = ?', (report_id,))
            row = cursor.fetchone()

            # Удаляем запись из БД
            cursor.execute('DELETE FROM starosta_reports WHERE id = ?', (report_id,))
            conn.commit()

            # Удаляем файл, если он существует
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

            # Проверяем расширение файла
            original_filename = secure_filename(file.filename)
            file_ext = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else ''

            allowed_extensions = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'txt', 'csv'}
            if file_ext not in allowed_extensions:
                return False, "Недопустимый формат файла", None, None, None

            # Создаем уникальное имя файла
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{group_name}_{timestamp}_{original_filename}"

            # Создаем папку для группы
            group_folder = os.path.join(self.reports_folder, group_name)
            os.makedirs(group_folder, exist_ok=True)

            # Сохраняем файл
            file_path = os.path.join(group_folder, filename)
            file.save(file_path)

            # Определяем тип файла
            file_type = 'text' if file_ext in ['txt', 'csv'] else 'document'

            return True, "Файл успешно сохранен", original_filename, file_path, file_type
        except Exception as e:
            return False, f"Ошибка при сохранении файла: {str(e)}", None, None, None

    def save_text_report(self, content, group_name, title):
        """Сохранить текстовый отчет (без файла)"""
        try:
            if not content or not content.strip():
                return False, "Контент не может быть пустым", None

            # Создаем уникальное имя файла
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

    # ==================== СУЩЕСТВУЮЩИЕ МЕТОДЫ ====================

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

            if not group_name:
                return []

            # Получаем студентов из указанной группы (исключая самого пользователя)
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
            WHERE group_name = ? AND id != ? AND user_type = 'student'
            ORDER BY full_name
            ''', (group_name, user_id))

            rows = cursor.fetchall()

            students = []
            for row in rows:
                if row['user_type'] == 'student':
                    import random
                    attendance = f"{random.randint(80, 100)}%"

                    students.append({
                        'name': row['full_name'],
                        'group': group_name,
                        'email': row['email'] or 'Не указан',
                        'phone': row['phone'] or 'Не указан',
                        'login': row['login'],
                        'course': row['course'] or 'Не указан',
                        'attendance': attendance,
                        'joined_date': row['joined_date']
                    })

            return students

        except Exception as e:
            print(f"❌ Ошибка получения студентов: {e}")
            return []
        finally:
            if conn:
                conn.close()

    def get_info_for_headman(self, group_name=None, user_id=None):
        """Получает информацию о группе для старосты/куратора"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()

            # Если группа не указана, пытаемся получить группу текущего пользователя
            if not group_name and user_id:
                cursor.execute('SELECT group_name FROM users WHERE id = ?', (user_id,))
                user_group = cursor.fetchone()
                if user_group and user_group['group_name']:
                    group_name = user_group['group_name']

            if not group_name:
                return {
                    'group': 'Группа не указана',
                    'total_students': 0,
                    'excellent': 0,
                    'good': 0,
                    'satisfactory': 0
                }

            # Получаем общее количество СТУДЕНТОВ в группе (исключая пользователя)
            cursor.execute('''
            SELECT COUNT(*) as total 
            FROM users 
            WHERE group_name = ? AND user_type = 'student' AND id != ?
            ''', (group_name, user_id))

            result = cursor.fetchone()
            total = result['total'] if result else 0

            # Если студентов нет, возвращаем нули
            if total == 0:
                return {
                    'group': group_name,
                    'total_students': 0,
                    'excellent': 0,
                    'good': 0,
                    'satisfactory': 0
                }

            # Для демонстрации генерируем статистику
            import random
            excellent = random.randint(1, max(1, total // 3)) if total > 0 else 0
            good = random.randint(1, max(1, total // 2)) if total > 0 else 0
            satisfactory = max(0, total - excellent - good) if total > 0 else 0

            # Корректируем, если сумма превышает total
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