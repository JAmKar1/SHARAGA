"""
Модуль для работы с практикой
"""


class PracticeModule:
    def __init__(self):
        self.practice_data = []
        self.load_data()

    def load_data(self):
        """Загрузить данные по практике"""
        self.practice_data = [
            {
                'id': 1,
                'type': 'Учебная практика',
                'course': 2,
                'dates': '01.06.2024 - 30.06.2024',
                'supervisor': 'Иванов С.П.',
                'companies': ['IT-компания "Технософт"', 'Разработчик "ВебПро"'],
                'status': 'Планируется'
            },
            {
                'id': 2,
                'type': 'Производственная практика',
                'course': 3,
                'dates': '01.07.2024 - 31.08.2024',
                'supervisor': 'Петрова М.И.',
                'companies': ['Банк "Финансы"', 'Страховая компания "Гарант"'],
                'status': 'Набор'
            },
            {
                'id': 3,
                'type': 'Преддипломная практика',
                'course': 4,
                'dates': '01.02.2024 - 30.04.2024',
                'supervisor': 'Сидоров А.В.',
                'companies': ['Разработчик ПО "Софтлайн"', 'IT-интегратор "Технологии"'],
                'status': 'Идет'
            }
        ]

    def get_practice_data(self):
        """Получить данные по практике"""
        return self.practice_data

    def get_practice_by_course(self, course):
        """Получить практику по курсу"""
        return [p for p in self.practice_data if p['course'] == course]

    def get_active_practice(self):
        """Получить активную практику"""
        return [p for p in self.practice_data if p['status'] == 'Идет']