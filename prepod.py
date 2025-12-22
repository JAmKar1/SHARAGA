"""
Модуль для работы со списком преподавателей
"""


class TeachersModule:
    def __init__(self):
        self.teachers = []
        self.load_teachers()



    def get_all_teachers(self):
        """Получить всех преподавателей"""
        return self.teachers

    def get_teacher_by_id(self, teacher_id):
        """Получить преподавателя по ID"""
        for teacher in self.teachers:
            if teacher['id'] == teacher_id:
                return teacher
        return None

    def get_teachers_by_department(self, department):
        """Получить преподавателей по кафедре"""
        return [t for t in self.teachers if t['department'] == department]

    def get_teachers_by_subject(self, subject):
        """Получить преподавателей по предмету"""
        return [t for t in self.teachers if subject in t['subjects']]

    def get_departments(self):
        """Получить список кафедр"""
        departments = set()
        for teacher in self.teachers:
            departments.add(teacher['department'])
        return list(departments)

    def search_teachers(self, query):
        """Поиск преподавателей"""
        query = query.lower()
        results = []
        for teacher in self.teachers:
            if (query in teacher['name'].lower() or
                    query in teacher['department'].lower() or
                    any(query in subject.lower() for subject in teacher['subjects'])):
                results.append(teacher)
        return results