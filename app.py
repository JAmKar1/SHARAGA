from flask import Flask, render_template, redirect, url_for, session, request, jsonify, flash
from star import StarostaModule
from rasp import ScheduleModule
from prepod import TeachersModule
from repe import TutoringModule
from mero import EventsModule
from praktika import PracticeModule
from vxod import AuthModule
from macro import get_month_name, format_date, get_status_color, truncate_text, get_initials

app = Flask(__name__)
app.secret_key = 'your_secret_key_here_change_this_in_production'
app.config['SESSION_TYPE'] = 'filesystem'

# Регистрация фильтров для шаблонов
app.jinja_env.filters['month_name'] = get_month_name
app.jinja_env.filters['format_date'] = format_date
app.jinja_env.filters['status_color'] = get_status_color
app.jinja_env.filters['truncate'] = truncate_text
app.jinja_env.filters['initials'] = get_initials

# Инициализация модулей
starosta_module = StarostaModule()
schedule_module = ScheduleModule()
teachers_module = TeachersModule()
tutoring_module = TutoringModule()
events_module = EventsModule()
practice_module = PracticeModule()
auth_module = AuthModule()


# Добавляем функцию get_month_name в глобальный контекст шаблонов
@app.context_processor
def utility_processor():
    return dict(get_month_name=get_month_name)


# Главная страница - выбор типа входа
@app.route('/')
def index():
    return render_template('index.html')


# Вход для студентов
@app.route('/login/student', methods=['GET', 'POST'])
def student_login():
    if 'user_id' in session and session.get('user_type') == 'student':
        return redirect(url_for('student_dashboard'))

    if request.method == 'POST':
        identifier = request.form.get('identifier')
        password = request.form.get('password')

        auth_result = auth_module.authenticate(identifier, password, 'student')
        if auth_result['success']:
            user = auth_result['user']
            # Создаем сессию
        session_id = auth_module.create_session(user['id'])
        session['user_id'] = user['id']
        session['session_id'] = session_id
        session['username'] = user['username']
        session['user_type'] = user['user_type']
        session['name'] = user['name']

        flash(f'Добро пожаловать, {user["name"]}!', 'success')
        return redirect(url_for('student_dashboard'))
    else:
            return render_template('login_student.html', error=auth_result['message'])

            return render_template('login_student.html')


# Вход для преподавателей
@app.route('/login/teacher', methods=['GET', 'POST'])
def teacher_login():
    if 'user_id' in session and session.get('user_type') == 'teacher':
        return redirect(url_for('teacher_dashboard'))

    if request.method == 'POST':
        identifier = request.form.get('identifier')
        password = request.form.get('password')

        auth_result = auth_module.authenticate(identifier, password, 'teacher')
    if auth_result['success']:
            user = auth_result['user']
            # Создаем сессию
            session_id = auth_module.create_session(user['id'])
            session['user_id'] = user['id']
            session['session_id'] = session_id
            session['username'] = user['username']
            session['user_type'] = user['user_type']
            session['name'] = user['name']

            flash(f'Добро пожаловать, {user["name"]}!', 'success')
            return redirect(url_for('teacher_dashboard'))

    else:
            return render_template('login_teacher.html', error=auth_result['message'])

            return render_template('login_teacher.html')
@app.route('/login/admin', methods=['GET', 'POST'])
def admin_login():
            if 'user_id' in session and session.get('user_type') == 'admin':
                return redirect(url_for('admin_dashboard'))

            if request.method == 'POST':
                identifier = request.form.get('identifier')
                password = request.form.get('password')

                auth_result = auth_module.authenticate(identifier, password, 'admin')
                if auth_result['success']:
                    user = auth_result['user']
                    # Создаем сессию
                    session_id = auth_module.create_session(user['id'])
                    session['user_id'] = user['id']
                    session['session_id'] = session_id
                    session['username'] = user['username']
                    session['user_type'] = user['user_type']
                    session['name'] = user['name']

                    flash(f'Добро пожаловать, {user["name"]}!', 'success')
                    return redirect(url_for('admin_dashboard'))
                else:
                    return render_template('login_admin.html', error=auth_result['message'])

            return render_template('login_admin.html')

        # Регистрация студентов
@app.route('/register/student', methods=['GET', 'POST'])
def student_register():
            if request.method == 'POST':
                username = request.form.get('username')
                password = request.form.get('password')
                confirm_password = request.form.get('confirm_password')
                full_name = request.form.get('full_name')
                email = request.form.get('email')
                phone = request.form.get('phone')
                group = request.form.get('group')
                course = request.form.get('course')
                verification_method = request.form.get('verification_method', 'email')

                # Валидация
                if password != confirm_password:
                    return render_template('register_student.html', error='Пароли не совпадают')

                if len(password) < 6:
                    return render_template('register_student.html', error='Пароль должен быть не менее 6 символов')

                if auth_module.check_username_exists(username, 'student'):
                    return render_template('register_student.html', error='Студент с таким логином уже существует')

                if auth_module.check_email_exists(email, 'student'):
                    return render_template('register_student.html', error='Студент с таким email уже существует')

                if phone and auth_module.check_phone_exists(phone, 'student'):
                    return render_template('register_student.html', error='Студент с таким телефоном уже существует')

                # Создаем пользователя (но не подтверждаем)
                new_user = auth_module.create_user(
                    username=username,
                    password=password,
                    name=full_name,
                    user_type='student',
                    email=email,
                    phone=phone,
                    group=group,
                    course=course
                )

                # Сохраняем данные в сессии для подтверждения
                session['pending_user'] = {
                    'username': username,
                    'email': email,
                    'phone': phone,
                    'verification_method': verification_method,
                    'user_type': 'student'
                }

                # Отправляем код подтверждения
                if verification_method == 'email':
                    identifier = email
                else:
                    identifier = phone

                success, code = auth_module.create_verification_code(identifier, verification_method, 'student')

                if success:
                    session['verification_identifier'] = identifier
                    return redirect(url_for('verify', user_type='student'))
                else:
                    return render_template('register_student.html', error='Ошибка отправки кода подтверждения')

            return render_template('register_student.html')


@app.route('/register/teacher', methods=['GET', 'POST'])

def teacher_register():
    # Только администраторы могут создавать учетные записи преподавателей
    if 'user_id' not in session or session.get('user_type') != 'admin':
        flash('Доступ запрещен. Только администраторы могут регистрировать преподавателей.', 'error')
        return redirect(url_for('admin_login'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        department = request.form.get('department')
        position = request.form.get('position')
        verification_method = request.form.get('verification_method', 'email')

        # Валидация
        if password != confirm_password:
            return render_template('register_teacher.html', error='Пароли не совпадают')

        if auth_module.check_username_exists(username, 'teacher'):
            return render_template('register_teacher.html', error='Преподаватель с таким логином уже существует')

        if auth_module.check_email_exists(email, 'teacher'):
            return render_template('register_teacher.html', error='Преподаватель с таким email уже существует')

        # Создаем пользователя
        new_user = auth_module.create_user(
            username=username,
            password=password,
            name=full_name,
            user_type='teacher',
            email=email,
            phone=phone,
            department=department,
            position=position
        )

        # Отправляем приглашение
        if verification_method == 'email':
            identifier = email
        else:
            identifier = phone

        success, code = auth_module.create_verification_code(identifier, verification_method, 'teacher')

        if success:
            flash(f'Учетная запись преподавателя {full_name} создана. Код подтверждения отправлен.', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            return render_template('register_teacher.html', error='Ошибка отправки кода подтверждения')

    return render_template('register_teacher.html')

# Страница подтверждения
@app.route('/verify/<user_type>', methods=['GET', 'POST'])
def verify(user_type):
    if 'verification_identifier' not in session:
        return redirect(url_for(f'{user_type}_register'))

    identifier = session['verification_identifier']
    pending_user = session.get('pending_user', {})

    if request.method == 'POST':
        code = request.form.get('code')
        resend = request.form.get('resend')

        if resend:
            # Повторная отправка кода
            if pending_user['verification_method'] == 'email':
                identifier = pending_user['email']
            else:
                identifier = pending_user['phone']

            success, new_code = auth_module.create_verification_code(
                identifier,
                pending_user['verification_method'],
                user_type
            )

            if success:
                return render_template('verify.html',
                                     success='Новый код отправлен',
                                     method=pending_user['verification_method'],
                                     user_type=user_type)
            else:
                return render_template('verify.html',
                                     error='Ошибка отправки кода',
                                     method=pending_user['verification_method'],
                                     user_type=user_type)

        # Проверка кода
        result = auth_module.verify_code(identifier, code)

        if result['success']:
            # Подтверждаем пользователя
            verify_result = auth_module.verify_user(identifier)

            if verify_result['success']:
                user = verify_result['user']

                # Создаем сессию
                session_id = auth_module.create_session(user['id'])
                session['user_id'] = user['id']
                session['session_id'] = session_id
                session['username'] = user['username']
                session['user_type'] = user['user_type']
                session['name'] = user['name']

                # Очищаем временные данные
                session.pop('verification_identifier', None)
                session.pop('pending_user', None)

                flash('Регистрация успешно завершена!', 'success')

                # Перенаправляем в зависимости от типа пользователя
                if user_type == 'student':
                    return redirect(url_for('student_dashboard'))
                elif user_type == 'teacher':
                    return redirect(url_for('teacher_dashboard'))
                else:
                    return redirect(url_for('index'))
            else:
                return render_template('verify.html',
                                       error='Ошибка подтверждения пользователя',
                                       method=pending_user['verification_method'],
                                       user_type=user_type)
        else:
            return render_template('verify.html',
            error=result['message'],
            method=pending_user['verification_method'],
            user_type=user_type)

    return render_template('verify.html',
method=pending_user.get('verification_method', 'email'),
user_type=user_type)

        # Восстановление пароля
@app.route('/forgot_password/<user_type>', methods=['GET', 'POST'])
def forgot_password(user_type):
            if request.method == 'POST':
                identifier = request.form.get('identifier')
                verification_method = request.form.get('verification_method', 'email')

                # Проверяем существование пользователя
                user = None
                if '@' in identifier:  # Это email
                    user = auth_module.get_user_by_email(identifier)
                else:  # Это телефон
                    user = auth_module.get_user_by_phone(identifier)

                if not user or user.get('user_type') != user_type:
                    return render_template('forgot_password.html',
                                           error='Пользователь не найден',
                                           user_type=user_type)

                # Отправляем код подтверждения
                success, code = auth_module.create_verification_code(identifier, verification_method, user_type)

                if success:
                    session['reset_password_identifier'] = identifier
                    session['reset_password_method'] = verification_method
                    session['reset_password_user_type'] = user_type
                    return redirect(url_for('reset_password', user_type=user_type))
                else:
                    return render_template('forgot_password.html',
                                           error='Ошибка отправки кода подтверждения',
                                           user_type=user_type)

            return render_template('forgot_password.html', user_type=user_type)

        # Сброс пароля
@app.route('/reset_password/<user_type>', methods=['GET', 'POST'])
def reset_password(user_type):
            if 'reset_password_identifier' not in session:
                return redirect(url_for('forgot_password', user_type=user_type))

            identifier = session['reset_password_identifier']
            method = session.get('reset_password_method', 'email')

            if request.method == 'POST':
                code = request.form.get('code')
                new_password = request.form.get('new_password')
                confirm_password = request.form.get('confirm_password')
                resend = request.form.get('resend')

            if resend:
            # Повторная отправка кода
                 success, new_code = auth_module.create_verification_code(identifier, method, user_type)

            if success:
                return render_template('reset_password.html',
                                       success='Новый код отправлен',
                                       method=method,
                                       user_type=user_type)
            else:
                return render_template('reset_password.html',
                                       error='Ошибка отправки кода',
                                       method=method,
                                       user_type=user_type)

                # Проверяем, что пароли совпадают
            if new_password != confirm_password:
                return render_template('reset_password.html',
                                           error='Пароли не совпадают',
                                           method=method,
                                           user_type=user_type)

            if len(new_password) < 6:
                    return render_template('reset_password.html',
                                           error='Пароль должен быть не менее 6 символов',
                                           method=method,
                                           user_type=user_type)

                    # Проверяем код
            result = auth_module.verify_code(identifier, code)

            if not result['success']:
                    return render_template('reset_password.html',
                                       error=result['message'],
                                       method=method,
                                       user_type=user_type)
            else:
                        # Меняем пароль
                        update_result = auth_module.update_password(identifier, new_password)

                        if update_result['success']:
                            # Очищаем сессию
                            session.pop('reset_password_identifier', None)
                            session.pop('reset_password_method', None)
                            session.pop('reset_password_user_type', None)

                            flash('Пароль успешно изменен! Теперь вы можете войти в систему.', 'success')
                            return redirect(url_for(f'{user_type}_login'))
                        else:
                            return render_template('reset_password.html',
                                                   error=update_result['message'],
                                                   method=method,
                                                   user_type=user_type)

            return render_template('reset_password.html', method=method, user_type=user_type)

            # Выход из системы
            @app.route('/logout')
            def logout():
                if 'session_id' in session:
                    auth_module.delete_session(session['session_id'])

                session.clear()
                flash('Вы успешно вышли из системы', 'info')
                return redirect(url_for('index'))

            # Дашборды для разных типов пользователей
            @app.route('/dashboard/student')
            def student_dashboard():
                if 'user_id' not in session or session.get('user_type') != 'student':
                    return redirect(url_for('student_login'))

                user_data = auth_module.get_user_by_id(session['user_id'])
                return render_template('dashboard_student.html', user=user_data)

            @app.route('/dashboard/teacher')
            def teacher_dashboard():
                if 'user_id' not in session or session.get('user_type') != 'teacher':
                    return redirect(url_for('teacher_login'))

                user_data = auth_module.get_user_by_id(session['user_id'])
                return render_template('dashboard_teacher.html', user=user_data)

            @app.route('/dashboard/admin')
            def admin_dashboard():
                if 'user_id' not in session or session.get('user_type') != 'admin':
                    return redirect(url_for('admin_login'))

                user_data = auth_module.get_user_by_id(session['user_id'])
                students = auth_module.get_users_by_type('student')
                teachers = auth_module.get_users_by_type('teacher')
                admins = auth_module.get_users_by_type('admin')

                return render_template('dashboard_admin.html',
                                       user=user_data,
                                       students=students,
                                       teachers=teachers,
                                       admins=admins)

            # API для проверки доступности
            @app.route('/api/check_availability/<user_type>', methods=['POST'])
            def check_availability(user_type):
                data = request.json
                field = data.get('field')
                value = data.get('value')

                if field == 'username':
                    exists = auth_module.check_username_exists(value, user_type)
                    return jsonify({'available': not exists})
                elif field == 'email':
                    exists = auth_module.check_email_exists(value, user_type)
                    return jsonify({'available': not exists})
                elif field == 'phone':
                    exists = auth_module.check_phone_exists(value, user_type)
                    return jsonify({'available': not exists})

                return jsonify({'error': 'Invalid field'})

            # Middleware для проверки авторизации
            @app.before_request
            def check_auth():
                # Разрешаем доступ к публичным страницам
                public_paths = [
                    '/', '/login/student', '/login/teacher', '/login/admin',
                    '/register/student', '/register/teacher', '/verify/student',
                    '/verify/teacher', '/forgot_password/student', '/forgot_password/teacher',
                    '/forgot_password/admin', '/reset_password/student', '/reset_password/teacher',
                    '/reset_password/admin', '/api/check_availability/student',
                    '/api/check_availability/teacher', '/api/check_availability/admin',
                    '/static'
                ]

                if request.path not in public_paths and not request.path.startswith('/static'):
                    if 'user_id' not in session:
                        return redirect(url_for('index'))

                    # Проверяем валидность сессии
                    if 'session_id' in session:
                        user_id = auth_module.validate_session(session['session_id'])
                        if not user_id or user_id != session['user_id']:
                            session.clear()
                            return redirect(url_for('index'))

            # Маршруты для студента (из предыдущей версии, с проверкой прав)
            @app.route('/student/starosta')
            def student_starosta():
                if 'user_id' not in session or session.get('user_type') != 'student':
                    return redirect(url_for('student_login'))

                user_data = auth_module.get_user_by_id(session['user_id'])
                # Проверяем, является ли студент старостой
                if user_data['username'] != 'starosta':
                    flash('Доступ только для старосты группы', 'error')
                    return redirect(url_for('student_dashboard'))

                students = starosta_module.get_students_data('ПИ-21')
                reports = starosta_module.get_reports_data()
                info = starosta_module.get_info_for_headman()
                messages = starosta_module.get_messages()

                return render_template('starosta.html',
                                       user=user_data['name'],
                                       role='student',
                                       students=students,
                                       reports=reports,
                                       info=info,
                                       messages=messages)

            @app.route('/student/raspisanie')
            def student_raspisanie():
                if 'user_id' not in session or session.get('user_type') != 'student':
                    return redirect(url_for('student_login'))

                user_data = auth_module.get_user_by_id(session['user_id'])
                course = request.args.get('course', default=1, type=int)
                schedule = schedule_module.get_schedule(course)
                days = schedule_module.get_course_days(course)
                exams = schedule_module.get_exams_schedule(course)

                return render_template('raspisanie.html',
                                       user=user_data['name'],
                                       role='student',
                                       schedule=schedule,
                                       days=days,
                                       exams=exams,
                                       current_course=course,
                                       courses=[1, 2, 3, 4])

            # Добавьте остальные маршруты для студента...

            # Маршруты для преподавателя
            @app.route('/teacher/prepodavateli')
            def teacher_prepodavateli():
                if 'user_id' not in session or session.get('user_type') != 'teacher':
                    return redirect(url_for('teacher_login'))

                user_data = auth_module.get_user_by_id(session['user_id'])
                teachers = teachers_module.get_all_teachers()
                departments = teachers_module.get_departments()

                return render_template('prepodavateli.html',
                                       user=user_data['name'],
                                       role='teacher',
                                       teachers=teachers,
                                       departments=departments)

            # Добавьте остальные маршруты для преподавателя...

            # Маршруты для администратора
            @app.route('/admin/manage_users')
            def admin_manage_users():
                if 'user_id' not in session or session.get('user_type') != 'admin':
                    return redirect(url_for('admin_login'))

                user_data = auth_module.get_user_by_id(session['user_id'])
                students = auth_module.get_users_by_type('student')
                teachers = auth_module.get_users_by_type('teacher')
                admins = auth_module.get_users_by_type('admin')

                return render_template('manage_users.html',
                                       user=user_data,
                                       students=students,
                                       teachers=teachers,
                                       admins=admins)

            # Добавьте остальные маршруты для администратора...

            if __name__ == '__main__':
                app.run(debug=True, host='0.0.0.0', port=5000)