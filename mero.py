"""
Модуль для работы с мероприятиями
"""

import sqlite3
from datetime import datetime


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

    def register_for_event(self, event_id, user_id, user_name):
        """Зарегистрировать пользователя на мероприятие"""
        conn = self.get_db_connection()
        cursor = conn.cursor()

        try:
            # Создаем таблицу регистраций, если ее нет
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

            # Проверяем, существует ли мероприятие
            cursor.execute('SELECT id, max_participants, current_participants FROM events WHERE id = ?', (event_id,))
            event = cursor.fetchone()

            if not event:
                return False, "Мероприятие не найдено"

            # Проверяем, не зарегистрирован ли уже пользователь
            cursor.execute('''
            SELECT id FROM event_registrations 
            WHERE event_id = ? AND user_id = ?
            ''', (event_id, user_id))

            if cursor.fetchone():
                return False, "Вы уже зарегистрированы на это мероприятие"

            # Проверяем наличие свободных мест
            max_participants = event['max_participants']
            current_participants = event['current_participants'] or 0

            if max_participants and current_participants >= max_participants:
                return False, "Нет свободных мест"

            # Регистрируем пользователя
            cursor.execute('''
            INSERT INTO event_registrations (event_id, user_id, user_name)
            VALUES (?, ?, ?)
            ''', (event_id, user_id, user_name))

            # Обновляем счетчик участников
            cursor.execute('''
            UPDATE events 
            SET current_participants = current_participants + 1
            WHERE id = ?
            ''', (event_id,))

            conn.commit()
            return True, "Вы успешно зарегистрировались на мероприятие"

        except Exception as e:
            conn.rollback()
            print(f"❌ Ошибка регистрации на мероприятие: {e}")
            return False, f"Ошибка регистрации: {str(e)}"
        finally:
            conn.close()

    def get_event_registrations(self, event_id):
        """Получить список регистраций на мероприятие"""
        conn = self.get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('''
            SELECT * FROM event_registrations 
            WHERE event_id = ?
            ORDER BY registered_at DESC
            ''', (event_id,))

            registrations = []
            for row in cursor.fetchall():
                registrations.append(dict(row))

            return registrations
        except Exception as e:
            print(f"❌ Ошибка получения регистраций: {e}")
            return []
        finally:
            conn.close()

    def get_user_registrations(self, user_id):
        """Получить мероприятия, на которые зарегистрирован пользователь"""
        conn = self.get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('''
            SELECT e.*, er.registered_at, er.status as registration_status
            FROM events e
            JOIN event_registrations er ON e.id = er.event_id
            WHERE er.user_id = ?
            ORDER BY e.date, e.time
            ''', (user_id,))

            events = []
            for row in cursor.fetchall():
                events.append(dict(row))

            return events
        except Exception as e:
            print(f"❌ Ошибка получения мероприятий пользователя: {e}")
            return []
        finally:
            conn.close()

    def cancel_registration(self, event_id, user_id):
        """Отменить регистрацию на мероприятие"""
        conn = self.get_db_connection()
        cursor = conn.cursor()

        try:
            # Удаляем регистрацию
            cursor.execute('''
            DELETE FROM event_registrations 
            WHERE event_id = ? AND user_id = ?
            ''', (event_id, user_id))

            # Обновляем счетчик участников
            cursor.execute('''
            UPDATE events 
            SET current_participants = current_participants - 1
            WHERE id = ? AND current_participants > 0
            ''', (event_id,))

            conn.commit()
            return True, "Регистрация успешно отменена"
        except Exception as e:
            conn.rollback()
            print(f"❌ Ошибка отмены регистрации: {e}")
            return False, f"Ошибка отмены регистрации: {str(e)}"
        finally:
            conn.close()