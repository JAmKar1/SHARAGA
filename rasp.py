"""
Модуль для работы с расписанием (обновленная версия с группами)
"""
import sqlite3
import os
import re
import tempfile
import pdfplumber
from datetime import datetime
from collections import defaultdict

class ScheduleModule:
    def __init__(self):
        self.db_path = 'university.db'
        self.init_database()

    def init_database(self):
        """Инициализация базы данных"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Таблица групп
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS schedule_groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            course INTEGER NOT NULL,
            faculty TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        # Таблица расписания
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS group_schedule (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER NOT NULL,
            day_of_week TEXT NOT NULL,
            lesson_number INTEGER NOT NULL,
            time_start TEXT NOT NULL,
            time_end TEXT NOT NULL,
            subject TEXT NOT NULL,
            teacher TEXT NOT NULL,
            room TEXT NOT NULL,
            FOREIGN KEY (group_id) REFERENCES schedule_groups(id) ON DELETE CASCADE
        )
        ''')

        conn.commit()
        conn.close()

    def get_connection(self):
        """Получить соединение с БД"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def get_all_groups(self):
        """Получить список всех групп"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT name FROM schedule_groups ORDER BY course, name')
        groups = [row['name'] for row in cursor.fetchall()]

        conn.close()
        return groups

    def get_groups_by_course(self):
        """Получить группы по курсам"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT course, name FROM schedule_groups ORDER BY course, name')
        rows = cursor.fetchall()

        groups_by_course = defaultdict(list)
        for row in rows:
            groups_by_course[row['course']].append(row['name'])

        conn.close()
        return dict(groups_by_course)

    def get_schedule_for_group(self, group_name):
        """Получить расписание для группы"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            # Получаем ID группы
            cursor.execute('SELECT id FROM schedule_groups WHERE name = ?', (group_name,))
            group = cursor.fetchone()

            if not group:
                return {}

            group_id = group['id']

            # Получаем расписание
            cursor.execute('''
            SELECT * FROM group_schedule 
            WHERE group_id = ? 
            ORDER BY 
                CASE day_of_week
                    WHEN 'Понедельник' THEN 1
                    WHEN 'Вторник' THEN 2
                    WHEN 'Среда' THEN 3
                    WHEN 'Четверг' THEN 4
                    WHEN 'Пятница' THEN 5
                    WHEN 'Суббота' THEN 6
                    ELSE 7
                END,
                lesson_number
            ''', (group_id,))

            schedule_data = {}
            for row in cursor.fetchall():
                day = row['day_of_week']
                if day not in schedule_data:
                    schedule_data[day] = []

                schedule_data[day].append({
                    'time': f"{row['time_start']}-{row['time_end']}",
                    'subject': row['subject'],
                    'teacher': row['teacher'],
                    'room': row['room']
                })

            return schedule_data

        except Exception as e:
            print(f"❌ Ошибка получения расписания: {e}")
            return {}
        finally:
            conn.close()

    # Функции для обратной совместимости
    def get_schedule(self, course):
        """Старая функция для обратной совместимости"""
        groups_by_course = self.get_groups_by_course()
        if course in groups_by_course and groups_by_course[course]:
            return self.get_schedule_for_group(groups_by_course[course][0])
        return {}

    def get_course_days(self, course):
        """Старая функция для обратной совместимости"""
        schedule = self.get_schedule(course)
        return list(schedule.keys())

    def get_exams_schedule(self, course):
        """Старая функция для обратной совместимости"""
        # Возвращаем пустой список, так как экзамены хранятся в другой таблице
        return []

# Создаем глобальный экземпляр для импорта
schedule_module = ScheduleModule()