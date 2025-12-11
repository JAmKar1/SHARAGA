"""
Модуль для работы с репетиторством через БД
"""
import sqlite3

class TutoringModule:
    def __init__(self):
        self.db_name = 'university.db'
    
    def get_db_connection(self):
        """Получить соединение с БД"""
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        return conn
    
    def get_tutoring_data(self):
        """Получить данные репетиторства из БД"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # Получаем все репетиторства
            cursor.execute('''
            SELECT t.*, 
                   COUNT(tr.id) as registered_count
            FROM tutoring t
            LEFT JOIN tutoring_registrations tr ON t.id = tr.tutoring_id
            GROUP BY t.id
            ORDER BY t.created_at DESC
            ''')
            
            all_tutoring = []
            for row in cursor.fetchall():
                # Получаем список записавшихся студентов
                cursor.execute('''
                SELECT u.full_name 
                FROM tutoring_registrations tr
                JOIN users u ON tr.student_id = u.id
                WHERE tr.tutoring_id = ? AND tr.status != 'отменено'
                ''', (row['id'],))
                
                students = [student[0] for student in cursor.fetchall()]
                
                all_tutoring.append({
                    'id': row['id'],
                    'subject': row['subject'],
                    'tutor': row['tutor_name'],
                    'tutor_type': row['tutor_type'],
                    'days': row['days'],
                    'time': row['time'],
                    'room': row['room'],
                    'price': row['price'],
                    'max_students': row['max_students'],
                    'registered_count': row['registered_count'],
                    'status': row['status'],
                    'students': students,
                    'description': row['description']
                })
            
            conn.close()
            
            # Разделяем на преподавателей и студентов
            teachers = []
            students = []
            
            for item in all_tutoring:
                if item['tutor_type'] == 'teacher':
                    teachers.append(item)
                else:
                    students.append(item)
            
            return {
                'teachers': teachers,
                'students': students
            }
            
        except Exception as e:
            print(f"❌ Ошибка получения данных репетиторства: {e}")
            # Возвращаем пустые данные если таблицы нет
            return {
                'teachers': [],
                'students': []
            }
    
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