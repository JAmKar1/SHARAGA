"""
Модуль для работы с мероприятиями
"""


class EventsModule:
    def __init__(self):
        self.events = []
        self.load_events()

    def load_events(self):
        """Загрузить мероприятия"""
        self.events = [
            {
                'id': 1,
                'title': 'День открытых дверей',
                'date': '15.11.2023',
                'time': '10:00',
                'location': 'Актовый зал',
                'description': 'Приглашаем абитуриентов и их родителей',
                'organizer': 'Администрация',
                'status': 'Запланировано'
            },
            {
                'id': 2,
                'title': 'Студенческая конференция',
                'date': '20.11.2023',
                'time': '14:00',
                'location': 'Аудитория 301',
                'description': 'Доклады студентов по научным работам',
                'organizer': 'Научный отдел',
                'status': 'Подготовка'
            },
            {
                'id': 3,
                'title': 'Спортивные соревнования',
                'date': '25.11.2023',
                'time': '09:00',
                'location': 'Спортзал',
                'description': 'Соревнования между группами',
                'organizer': 'Кафедра физкультуры',
                'status': 'Запланировано'
            },
            {
                'id': 4,
                'title': 'Новогодний вечер',
                'date': '28.12.2023',
                'time': '18:00',
                'location': 'Актовый зал',
                'description': 'Новогодний концерт и дискотека',
                'organizer': 'Студенческий совет',
                'status': 'Планируется'
            }
        ]

    def get_events(self):
        """Получить все мероприятия"""
        return self.events

    def get_event_by_id(self, event_id):
        """Получить мероприятие по ID"""
        for event in self.events:
            if event['id'] == event_id:
                return event
        return None

    def add_event(self, event_data):
        """Добавить новое мероприятие"""
        event_data['id'] = len(self.events) + 1
        self.events.append(event_data)
        return True

    def get_upcoming_events(self):
        """Получить предстоящие мероприятия"""
        return [e for e in self.events if e['status'] in ['Запланировано', 'Подготовка', 'Планируется']]