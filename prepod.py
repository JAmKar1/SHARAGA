"""
Модуль для работы со списком преподавателей
"""


class TeachersModule:
    def __init__(self):
        self.teachers = []
        self.load_teachers()

    def load_teachers(self):
        """Загрузить данные преподавателей"""
        self.teachers = [
            {
                'id': 1,
                'name': 'Иванов Сергей Петрович',
                'position': 'Старший преподаватель',
                'department': 'Программная инженерия',
                'subjects': ['Программирование', 'Операционные системы', 'Дипломное проектирование'],
                'email': 'i.s.petrovich@tech.edu',
                'phone': 'вн. 101',
                'room': '301',
                'consultation': 'Пн 15:00-17:00, Ср 10:00-12:00'
            },
            {
                'id': 2,
                'name': 'Петрова Мария Ивановна',
                'position': 'Доцент',
                'department': 'Математика и информатика',
                'subjects': ['Математика', 'Математический анализ', 'Тестирование ПО'],
                'email': 'm.i.petrova@tech.edu',
                'phone': 'вн. 102',
                'room': '302',
                'consultation': 'Вт 14:00-16:00, Чт 11:00-13:00'
            },
            {
                'id': 3,
                'name': 'Сидоров Александр Васильевич',
                'position': 'Профессор',
                'department': 'Базы данных',
                'subjects': ['Базы данных', 'Физика', 'Сети и коммуникации'],
                'email': 'a.v.sidorov@tech.edu',
                'phone': 'вн. 103',
                'room': '303',
                'consultation': 'Пн 10:00-12:00, Пт 14:00-16:00'
            },
            {
                'id': 4,
                'name': 'Козлова Елена Николаевна',
                'position': 'Преподаватель',
                'department': 'Веб-технологии',
                'subjects': ['Веб-дизайн', 'Веб-разработка', 'История', 'Проектный менеджмент'],
                'email': 'e.n.kozlova@tech.edu',
                'phone': 'вн. 104',
                'room': '304',
                'consultation': 'Ср 13:00-15:00, Чт 15:00-17:00'
            },
            {
                'id': 5,
                'name': 'Кузнецов Дмитрий Николаевич',
                'position': 'Доцент',
                'department': 'Алгоритмы и структуры данных',
                'subjects': ['Основы алгоритмов', 'Алгоритмы', 'Мобильная разработка'],
                'email': 'd.n.kuznetsov@tech.edu',
                'phone': 'вн. 105',
                'room': '305',
                'consultation': 'Вт 10:00-12:00, Пт 10:00-12:00'
            },
            {
                'id': 6,
                'name': 'Смирнова Ольга Леонидовна',
                'position': 'Преподаватель',
                'department': 'Иностранные языки',
                'subjects': ['Иностранный язык'],
                'email': 'o.l.smirnova@tech.edu',
                'phone': 'вн. 106',
                'room': '306',
                'consultation': 'Пн 13:00-15:00, Ср 16:00-18:00'
            },
            {
                'id': 7,
                'name': 'Петров Владимир Игоревич',
                'position': 'Старший преподаватель',
                'department': 'Сетевые технологии',
                'subjects': ['Сети и коммуникации'],
                'email': 'v.i.petrov@tech.edu',
                'phone': 'вн. 107',
                'room': '307',
                'consultation': 'Вт 16:00-18:00, Чт 09:00-11:00'
            },
            {
                'id': 8,
                'name': 'Николаев Василий Сергеевич',
                'position': 'Преподаватель',
                'department': 'Физическая культура',
                'subjects': ['Физкультура'],
                'email': 'v.s.nikolaev@tech.edu',
                'phone': 'вн. 108',
                'room': 'Спортзал',
                'consultation': 'Пн 08:00-10:00, Пт 08:00-10:00'
            }
        ]

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