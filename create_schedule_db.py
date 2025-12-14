import sqlite3


def create_schedule_database():
    """Создание базы данных расписания"""

    conn = sqlite3.connect('university.db')
    cursor = conn.cursor()

    print("🔄 Создание таблиц для расписания...")

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

    print("✅ Таблицы расписания созданы")

    conn.commit()
    conn.close()


if __name__ == '__main__':
    create_schedule_database()