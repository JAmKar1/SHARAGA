"""
Модуль для работы с общими PDF расписаниями
Администратор загружает PDF файл, который доступен всем студентам
"""

import sqlite3
import os
import time
from werkzeug.utils import secure_filename
from datetime import datetime


class ScheduleModule:
    def __init__(self):
        self.db_name = 'university.db'
        self.upload_folder = 'uploads/schedules'

        # Создаем папку для загрузок
        os.makedirs(self.upload_folder, exist_ok=True)

        # Инициализируем базу данных
        self.init_database()

    def init_database(self):
        """Инициализация таблиц базы данных"""
        conn = self.get_db_connection()
        cursor = conn.cursor()

        # Таблица для хранения загруженных PDF файлов расписания
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS schedule_pdfs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            original_filename TEXT NOT NULL,
            file_path TEXT NOT NULL,
            description TEXT,
            upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            uploaded_by INTEGER,
            is_active BOOLEAN DEFAULT 1,
            FOREIGN KEY (uploaded_by) REFERENCES users(id)
        )
        ''')

        conn.commit()
        conn.close()

        print("✅ Таблицы расписания инициализированы")

    def get_db_connection(self):
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        return conn

    def save_schedule_file(self, file, uploaded_by, description=''):
        """Сохранить PDF файл расписания"""
        try:
            # Создаем уникальное имя файла
            original_filename = secure_filename(file.filename)
            timestamp = int(time.time())
            filename = f"schedule_{timestamp}_{original_filename}"

            # Сохраняем файл
            file_path = os.path.join(self.upload_folder, filename)
            file.save(file_path)

            print(f"📁 PDF файл сохранен: {file_path}")
            print(f"📊 Оригинальное имя: {original_filename}")

            # Сохраняем информацию о файле в БД
            conn = self.get_db_connection()
            cursor = conn.cursor()

            # Деактивируем все предыдущие расписания
            cursor.execute('UPDATE schedule_pdfs SET is_active = 0')

            # Добавляем новое расписание
            cursor.execute('''
            INSERT INTO schedule_pdfs 
            (filename, original_filename, file_path, description, uploaded_by, is_active)
            VALUES (?, ?, ?, ?, ?, 1)
            ''', (filename, original_filename, file_path, description, uploaded_by))

            conn.commit()
            conn.close()

            return True, "Расписание успешно загружено и активировано"

        except Exception as e:
            print(f"❌ Ошибка сохранения файла: {e}")
            return False, f"Ошибка: {str(e)}"

    def get_latest_schedule(self):
        """Получить последнее активное расписание"""
        conn = self.get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('''
            SELECT sp.*, u.full_name as uploaded_by_name
            FROM schedule_pdfs sp
            LEFT JOIN users u ON sp.uploaded_by = u.id
            WHERE sp.is_active = 1
            ORDER BY sp.upload_date DESC
            LIMIT 1
            ''')

            result = cursor.fetchone()
            return dict(result) if result else None

        except Exception as e:
            print(f"❌ Ошибка получения расписания: {e}")
            return None
        finally:
            conn.close()

    def get_schedule_by_id(self, schedule_id):
        """Получить расписание по ID"""
        conn = self.get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('''
            SELECT sp.*, u.full_name as uploaded_by_name
            FROM schedule_pdfs sp
            LEFT JOIN users u ON sp.uploaded_by = u.id
            WHERE sp.id = ?
            ''', (schedule_id,))

            result = cursor.fetchone()
            return dict(result) if result else None

        except Exception as e:
            print(f"❌ Ошибка получения расписания по ID: {e}")
            return None
        finally:
            conn.close()

    def get_all_schedules(self):
        """Получить все загруженные расписания"""
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
            print(f"❌ Ошибка получения списка расписаний: {e}")
            return []
        finally:
            conn.close()

    def delete_schedule(self, schedule_id):
        """Удалить расписание"""
        conn = self.get_db_connection()
        cursor = conn.cursor()

        try:
            # Получаем информацию о файле
            cursor.execute('SELECT file_path FROM schedule_pdfs WHERE id = ?', (schedule_id,))
            result = cursor.fetchone()

            if not result:
                return False, "Расписание не найдено"

            file_path = result['file_path']

            # Удаляем запись из БД
            cursor.execute('DELETE FROM schedule_pdfs WHERE id = ?', (schedule_id,))

            # Удаляем файл с диска
            if os.path.exists(file_path):
                os.remove(file_path)

            conn.commit()
            return True, "Расписание успешно удалено"

        except Exception as e:
            conn.rollback()
            return False, f"Ошибка при удалении: {str(e)}"
        finally:
            conn.close()

    def activate_schedule(self, schedule_id):
        """Активировать расписание"""
        conn = self.get_db_connection()
        cursor = conn.cursor()

        try:
            # Проверяем, существует ли расписание
            cursor.execute('SELECT id FROM schedule_pdfs WHERE id = ?', (schedule_id,))
            if not cursor.fetchone():
                return False, "Расписание не найдено"

            # Деактивируем все расписания
            cursor.execute('UPDATE schedule_pdfs SET is_active = 0')

            # Активируем выбранное расписание
            cursor.execute('UPDATE schedule_pdfs SET is_active = 1 WHERE id = ?', (schedule_id,))

            conn.commit()
            return True, "Расписание активировано"

        except Exception as e:
            conn.rollback()
            return False, f"Ошибка при активации: {str(e)}"
        finally:
            conn.close()

    # Функции для обратной совместимости (если нужны)
    def get_all_groups(self):
        """Для обратной совместимости - возвращаем пустой список"""
        return []

    def get_groups_by_course(self):
        """Для обратной совместимости - возвращаем пустой словарь"""
        return {}

    def get_schedule_for_group(self, group_name):
        """Для обратной совместимости - возвращаем пустой словарь"""
        return {}


# Создаем глобальный экземпляр для импорта
schedule_module = ScheduleModule()