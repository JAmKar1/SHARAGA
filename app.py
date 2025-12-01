from flask import Flask, render_template, redirect, url_for, session, request
from star import StarostaModule
from rasp import ScheduleModule
from prepod import TeachersModule

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Измените на свой секретный ключ

# Инициализация модулей
starosta_module = StarostaModule()
schedule_module = ScheduleModule()
teachers_module = TeachersModule()


# Главная страница с авторизацией
@app.route('/', methods=['GET', 'POST'])
def index():
    if 'user' in session:
        # Если пользователь уже авторизован, показываем главную страницу
        return render_template('index.html', user=session['user'])

    if request.method == 'POST':
        # Простая проверка авторизации (в реальном приложении нужна БД)
        username = request.form.get('username')
        password = request.form.get('password')

        if username and password:  # В реальном приложении здесь проверка из БД
            session['user'] = username
            return redirect(url_for('index'))

    return render_template('login.html')


# Выход из системы
@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('index'))


# Маршруты для разных разделов
@app.route('/starosta')
def starosta():
    if 'user' not in session:
        return redirect(url_for('index'))

    # Получаем данные из модуля
    students = starosta_module.get_students_data('ПИ-21')
    reports = starosta_module.get_reports_data()
    info = starosta_module.get_info_for_headman()
    messages = starosta_module.get_messages()

    return render_template('starosta.html',
                           user=session['user'],
                           students=students,
                           reports=reports,
                           info=info,
                           messages=messages)


@app.route('/raspisanie')
def raspisanie():
    if 'user' not in session:
        return redirect(url_for('index'))

    # Получаем данные из модуля
    course = request.args.get('course', default=1, type=int)
    schedule = schedule_module.get_schedule(course)
    days = schedule_module.get_course_days(course)
    exams = schedule_module.get_exams_schedule(course)

    return render_template('raspisanie.html',
                           user=session['user'],
                           schedule=schedule,
                           days=days,
                           exams=exams,
                           current_course=course,
                           courses=[1, 2, 3, 4])


@app.route('/repetitorstvo')
def repetitorstvo():
    if 'user' not in session:
        return redirect(url_for('index'))
    return render_template('repetitorstvo.html', user=session['user'])


@app.route('/meropriyatiya')
def meropriyatiya():
    if 'user' not in session:
        return redirect(url_for('index'))
    return render_template('meropriyatiya.html', user=session['user'])


@app.route('/prepodavateli')
def prepodavateli():
    if 'user' not in session:
        return redirect(url_for('index'))

    # Получаем данные из модуля
    teachers = teachers_module.get_all_teachers()
    departments = teachers_module.get_departments()

    return render_template('prepodavateli.html',
                           user=session['user'],
                           teachers=teachers,
                           departments=departments)


@app.route('/praktika')
def praktika():
    if 'user' not in session:
        return redirect(url_for('index'))
    return render_template('praktika.html', user=session['user'])


@app.route('/podderzhka')
def podderzhka():
    if 'user' not in session:
        return redirect(url_for('index'))
    return render_template('podderzhka.html', user=session['user'])


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)