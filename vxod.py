import secrets
import time
from datetime import datetime
import hashlib


class AuthModule:
    def __init__(self):
        self.users = []
        self.verification_codes = {}  # {identifier: {'code': '123456', 'expires': timestamp, 'user_type': 'student'}}
        self.sessions = {}  # {session_id: user_id}
        self.load_users()

    def load_users(self):
        """Загрузить тестовых пользователей разных типов"""
        self.users = [
            # Студенты
            {
                'id': 1,
                'username': 'student1',
                'password': self.hash_password('password123'),
                'name': 'Иванов Иван Иванович',
                'user_type': 'student',
                'group': 'ПИ-21',
                'email': 'student1@edu.tech',
                'phone': '+79001234567',
                'verified': True,
                'created_at': '2023-01-15'
            },
            {
                'id': 2,
                'username': 'starosta',
                'password': self.hash_password('starosta123'),
                'name': 'Петров Петр Петрович',
                'user_type': 'student',
                'group': 'ПИ-21',
                'email': 'starosta@edu.tech',
                'phone': '+79002345678',
                'verified': True,
                'created_at': '2023-01-10'
            },
            # Преподаватели
            {
                'id': 3,
                'username': 'teacher1',
                'password': self.hash_password('teacher123'),
                'name': 'Иванов Сергей Петрович',
                'user_type': 'teacher',
                'department': 'Программирование',
                'email': 'i.s.petrovich@tech.edu',
                'phone': '+79003456789',
                'verified': True,
                'created_at': '2022-09-01'
            },
            {
                'id': 4,
                'username': 'teacher2',
                'password': self.hash_password('teacher456'),
                'name': 'Петрова Мария Ивановна',
                'user_type': 'teacher',
                'department': 'Математика',
                'email': 'm.i.petrova@tech.edu',
                'phone': '+79004567890',
                'verified': True,
                'created_at': '2022-09-01'
            },
            # Администраторы
            {
                'id': 5,
                'username': 'admin',
                'password': self.hash_password('admin123'),
                'name': 'Администратор Системы',
                'user_type': 'admin',
                'email': 'admin@techportal.edu',
                'phone': '+79005678901',
                'verified': True,
                'created_at': '2022-08-01'
            },
            {
                'id': 6,
                'username': 'admin2',
                'password': self.hash_password('admin456'),
                'name': 'Завуч Петрова Е.В.',
                'user_type': 'admin',
                'email': 'zavuch@techportal.edu',
                'phone': '+79006789012',
                'verified': True,
                'created_at': '2022-08-01'
            }
        ]

    def hash_password(self, password):
        """Хеширование пароля"""
        return hashlib.sha256(password.encode()).hexdigest()

    def verify_password(self, password, hashed_password):
        """Проверка пароля"""
        return self.hash_password(password) == hashed_password

    def authenticate(self, identifier, password, user_type=None):
        """Аутентификация пользователя по логину, email или телефону"""
        user = None

        # Ищем пользователя по разным идентификаторам
        for u in self.users:
            if (u['username'] == identifier or
                u['email'] == identifier or
                u.get('phone') == identifier):
                user = u
                break

        if not user:
            return {'success': False, 'message': 'Пользователь не найден'}

        # Проверяем тип пользователя, если указан
        if user_type and user['user_type'] != user_type:
            return {'success': False, 'message': f'Доступ только для {user_type}s'}

        # Проверяем пароль
        if not self.verify_password(password, user['password']):
            return {'success': False, 'message': 'Неверный пароль'}

        # Проверяем верификацию
        if not user.get('verified', True):
            return {'success': False, 'message': 'Аккаунт не подтвержден', 'user': user}

        return {'success': True, 'user': user}

    def get_user_by_id(self, user_id):
        """Получить пользователя по ID"""
        for user in self.users:
            if user['id'] == user_id:
                return user
        return None

    def get_user_by_email(self, email):
        """Получить пользователя по email"""
        for user in self.users:
            if user['email'] == email:
                return user
        return None

    def get_user_by_phone(self, phone):
        """Получить пользователя по телефону"""
        for user in self.users:
            if user.get('phone') == phone:
                return user
        return None

    def check_username_exists(self, username, user_type=None):
        """Проверить существует ли пользователь с таким логином"""
        if user_type:
            return any(u['username'] == username and u['user_type'] == user_type for u in self.users)
        return any(u['username'] == username for u in self.users)

    def check_email_exists(self, email, user_type=None):
        """Проверить существует ли пользователь с таким email"""
        if user_type:
            return any(u['email'] == email and u['user_type'] == user_type for u in self.users)
        return any(u['email'] == email for u in self.users)

    def check_phone_exists(self, phone, user_type=None):
        """Проверить существует ли пользователь с таким телефоном"""
        if user_type:
            return any(u.get('phone') == phone and u['user_type'] == user_type for u in self.users)
        return any(u.get('phone') == phone for u in self.users)

    def generate_verification_code(self):
        """Сгенерировать код подтверждения (6 цифр)"""
        return ''.join([str(secrets.randbelow(10)) for _ in range(6)])

    def send_email_verification(self, email, code, user_type):
        """Отправить код подтверждения на email"""
        # Демо-версия - вывод в консоль
        print(f"=== ДЕМО: Отправка email на {email} ===")
        print(f"Тип пользователя: {user_type}")
        print(f"Код подтверждения: {code}")
        print("=== КОНЕЦ ДЕМО ===")
        return True

    def send_sms_verification(self, phone, code, user_type):
        """Отправить код подтверждения по SMS"""
        # Демо-версия - вывод в консоль
        print(f"=== ДЕМО: Отправка SMS на {phone} ===")
        print(f"Тип пользователя: {user_type}")
        print(f"Код подтверждения: {code}")
        print("=== КОНЕЦ ДЕМО ===")
        return True

    def create_verification_code(self, identifier, method='email', user_type='student'):
        """Создать и отправить код подтверждения"""
        code = self.generate_verification_code()
        expires_at = time.time() + 600  # 10 минут

        self.verification_codes[identifier] = {
            'code': code,
            'expires': expires_at,
            'method': method,
            'user_type': user_type,
            'attempts': 0
        }

        if method == 'email':
            success = self.send_email_verification(identifier, code, user_type)
        else:  # sms
            success = self.send_sms_verification(identifier, code, user_type)

        return success, code
def verify_code(self, identifier, code):

    if identifier not in self.verification_codes:
        return {'success': False, 'message': 'Код не найден или устарел'}
        verification = self.verification_codes[identifier]

    if time.time() > verification['expires']:
            del self.verification_codes[identifier]
            return {'success': False, 'message': 'Код устарел'}

        # Проверка попыток
    if verification['attempts'] >= 3:
            del self.verification_codes[identifier]
            return {'success': False, 'message': 'Превышено количество попыток'}

         verification['attempts'] += 1

    if verification['code'] == code:
            # Код верный
            user_type = verification['user_type']
            del self.verification_codes[identifier]
            return {'success': True, 'message': 'Код подтвержден', 'user_type': user_type}
    else:
            return {'success': False, 'message': 'Неверный код'}

    def create_user(self, username, password, name, user_type, email, phone=None, **kwargs):
        new_user = {
            'id': len(self.users) + 1,
            'username': username,
            'password': self.hash_password(password),
            'name': name,
            'user_type': user_type,
            'email': email,
            'phone': phone,
            'verified': False,
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        # Добавляем дополнительные поля в зависимости от типа пользователя
        if user_type == 'student':
            new_user['group'] = kwargs.get('group', 'ПИ-21')
            new_user['course'] = kwargs.get('course', 1)
        elif user_type == 'teacher':
            new_user['department'] = kwargs.get('department', '')
            new_user['position'] = kwargs.get('position', 'Преподаватель')
        elif user_type == 'admin':
            new_user['position'] = kwargs.get('position', 'Администратор')

        self.users.append(new_user)
        return new_user

    def verify_user(self, identifier):
        """Подтвердить пользователя по email или телефону"""
        user = None

        # Ищем пользователя по email или телефону
        for u in self.users:
            if u['email'] == identifier or u.get('phone') == identifier:
                user = u
                break

        if user:
            user['verified'] = True
            return {'success': True, 'user': user}

        return {'success': False, 'message': 'Пользователь не найден'}

    def update_password(self, identifier, new_password):
        """Обновить пароль пользователя"""
        user = None

        # Ищем пользователя по email или телефону
        for u in self.users:
            if u['email'] == identifier or u.get('phone') == identifier:
                user = u
                break

        if user:
            user['password'] = self.hash_password(new_password)
            return {'success': True, 'user': user}

        return {'success': False, 'message': 'Пользователь не найден'}

    def create_session(self, user_id):
        """Создать сессию для пользователя"""
        session_id = secrets.token_hex(32)
        self.sessions[session_id] = {
            'user_id': user_id,
            'created_at': time.time(),
            'last_activity': time.time()
        }
        return session_id

    def validate_session(self, session_id):
        """Проверить валидность сессии"""
        if session_id in self.sessions:
            session = self.sessions[session_id]
            # Проверяем время бездействия (30 минут)
            if time.time() - session['last_activity'] < 1800:
                session['last_activity'] = time.time()

                return session['user_id']
            else:
                # Сессия истекла
                del self.sessions[session_id]
        return None

        def delete_session(self, session_id):
            """Удалить сессию"""
            if session_id in self.sessions:
                del self.sessions[session_id]

        def get_users_by_type(self, user_type):
            """Получить всех пользователей определенного типа"""
            return [u for u in self.users if u['user_type'] == user_type]