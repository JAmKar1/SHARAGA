"""
Модуль для работы с репетиторством
"""


class TutoringModule:
    def __init__(self):
        self.tutoring_data = []
        self.load_data()

    def load_data(self):
        """Загрузить данные репетиторства"""
        self.tutoring_data = [
            {
                'id': 1,
                'subject': 'Математика',
                'tutor': 'Петрова М.И.',
                'days': 'Пн, Ср, Пт',
                'time': '15:00-17:00',
                'room': '302',
                'price': 'Бесплатно',
                'students': ['Иванов И.И.', 'Петров П.П.'],
                'status': 'Идет набор'
            },
            {
                'id': 2,
                'subject': 'Программирование',
                'tutor': 'Иванов С.П.',
                'days': 'Вт, Чт',
                'time': '16:00-18:00',
                'room': '305',
                'price': '500 руб/час',
                'students': ['Сидорова А.С.', 'Кузнецов Д.А.'],
                'status': 'Занятия идут'
            },
            {
                'id': 3,
                'subject': 'Английский язык',
                'tutor': 'Смирнова О.Л.',
                'days': 'Ср, Пт',
                'time': '14:00-16:00',
                'room': '208',
                'price': 'Бесплатно',
                'students': ['Иванов И.И.', 'Петров П.П.', 'Сидорова А.С.'],
                'status': 'Набор закрыт'
            },
            {
                'id': 4,
                'subject': 'Базы данных',
                'tutor': 'Сидоров А.В.',
                'days': 'Пн, Чт',
                'time': '17:00-19:00',
                'room': '411',
                'price': '600 руб/час',
                'students': ['Кузнецов Д.А.'],
                'status': 'Идет набор'
            }
        ]

    def get_tutoring_data(self):
        """Получить данные репетиторства"""
        return self.tutoring_data

    def get_tutoring_by_subject(self, subject):
        """Получить репетиторство по предмету"""
        return [t for t in self.tutoring_data if subject.lower() in t['subject'].lower()]

    def get_free_tutoring(self):
        """Получить бесплатное репетиторство"""
        return [t for t in self.tutoring_data if t['price'] == 'Бесплатно']