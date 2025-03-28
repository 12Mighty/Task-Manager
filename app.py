from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, g
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import click
import os
from datetime import datetime


#Формируем дату и время в нужном формате
def format_datetime(value, format='%Y-%m-%d %H:%M:%S'):
    if value is None:
        return ''
    if isinstance(value, str):
        value = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
        # Возвращается строку даты и времени
    return value.strftime(format)


# Конфигурация приложения
app = Flask(__name__)
app.secret_key = 'your-secret-key' # Устанавливаем секретный ключ
app.config['DATABASE'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'task_manager.db') # Указываем путь к базе
app.config['INSTANCE_PATH'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance') # Указываем путь к папке 'instance'
app.jinja_env.filters['datetimeformat'] = format_datetime #Регистрируем фильтр Jinja для формата дат

# Создаем папку instance если ее нет
os.makedirs(app.config['INSTANCE_PATH'], exist_ok=True)


# ================== БАЗА ДАННЫХ ==================
def get_db():
    if 'db' not in g: # Проверяем, есть ли уже соединение с базой данных в объекте g
        #Если нет
        g.db = sqlite3.connect(app.config['DATABASE'])
        g.db.row_factory = sqlite3.Row
    return g.db # Возвращаем объект соединения с базой данных


def init_db():
    """Инициализируем только структуру БД без пользователей"""
    with app.app_context():
        db = get_db()
        with app.open_resource('schema.sql') as f:
            db.executescript(f.read().decode('utf8'))

        # Проверяем наличие администратора
        admin_exists = db.execute(
            "SELECT 1 FROM users WHERE role = 'admin'"
        ).fetchone()

        if not admin_exists: # Если админа нет, то создадим его
            db.execute(
                "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                ('admin', generate_password_hash('admin123'), 'admin')
            )
            db.commit()
            print("Создан администратор по умолчанию: admin/admin123")

        # Явно закрываем соединение
        close_db()


# Маршруты для базы данных

   # Закрывает соединение с базой после каждого запроса
@app.teardown_appcontext
def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

    # Создаем команду CLI для создания базы данных
@click.command('init-db')
def init_db_command():
    """Инициализирует БД"""
    init_db() # Вызов функции для инициализации базы (создание таблиц и добавление администратора)
    click.echo('База данных инициализирована')

    # Регистрируем фильтр для форматирования дат в шаблонах
@app.template_filter('datetimeformat')
def datetimeformat_filter(value, format='%d.%m.%Y %H:%M'):
    if not value:
        return ''
    try:
        if isinstance(value, str):
            # Для SQLite строкового формата
            dt = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
        else:
            dt = value
        return dt.strftime(format)
    except ValueError:
        return value


# Модели данных

# ================== ПОЛЬЗОВАТЕЛИ ==================

    # Функция для регистрации нового пользователя
def register_user(username, password, role='worker'):
    db = get_db()
    try:
        db.execute(
            "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
            (username, generate_password_hash(password), role),
        )
        db.commit()
    except sqlite3.IntegrityError:
        return False
    return True


   # Функция для авторизации пользователя
def login_user(username, password):
    db = get_db()
    # Регистро-независимый поиск
    user = db.execute(
        'SELECT * FROM users WHERE username COLLATE NOCASE = ?', (username,)
    ).fetchone()
    if user and check_password_hash(user['password'], password):
        return dict(user)
    return None

    # Функция для получения роли пользователя по его идентификатору
def get_user_role(user_id):
    db = get_db()
    role = db.execute(
        'SELECT role FROM users WHERE id = ?', (user_id,)
    ).fetchone()
    return role['role'] if role else None


# Маршруты для юзеров

# ================== ПРОЕКТЫ ==================

    # Функция для создания нового проекта
def create_project(name, description, created_by):
    db = get_db()
    cursor = db.execute(
        "INSERT INTO projects (name, description, created_by) VALUES (?, ?, ?)",
        (name, description, created_by)
    )
    db.commit()
    return cursor.lastrowid

    # Функция для получения всех проектов
def get_projects():
    db = get_db()
    return db.execute('SELECT * FROM projects').fetchall()


# Маршруты для проектов

# ================== ЗАДАЧИ ==================

    # Функция для создания новой задачи
def create_task(title, description, project_id, assigned_to, assigned_by):
    db = get_db()
    cursor = db.execute(
        """INSERT INTO tasks
        (title, description, project_id, assigned_to, assigned_by, status)
        VALUES (?, ?, ?, ?, ?, 'pending')""",
        (title, description, project_id, assigned_to, assigned_by)
    )
    db.commit()
    return cursor.lastrowid

    # Функция для получения задач, назначенных юзеру
def get_user_tasks(user_id):
    db = get_db()
    return db.execute(
        """SELECT t.*, p.name as project_name, u.username as assigned_to_username
        FROM tasks t
        JOIN projects p ON t.project_id = p.id
        JOIN users u ON t.assigned_to = u.id
        WHERE t.assigned_to = ?""",
        (user_id,)
    ).fetchall()


# Маршруты для задач

   # Маршрут для завершения задачи
@app.route('/api/complete_task/<int:task_id>', methods=['POST'])
def complete_task(task_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    db = get_db()
    db.execute(
        'UPDATE tasks SET status = "completed" WHERE id = ? AND assigned_to = ?',
        (task_id, session['user_id']) # Передаем ID задачи и ID пользователя из сессии
    )
    db.commit()
    log_action(session['user_id'], 'task_completed', f'Task {task_id} completed') # Логируем действие: кто завершил задачу
    return jsonify({'success': True}) # Возвращаем успешный ответ


# ================== ЛОГИРОВАНИЕ ==================

def log_action(user_id, action, details=None):
    db = get_db()
    db.execute(
        "INSERT INTO logs (user_id, action, details) VALUES (?, ?, ?)",
        (user_id, action, details) # Передаем ID пользователя, действие и доп детали (если есть)
    )
    db.commit()


# ================== Маршруты ==============

# Маршруты без привязки к какой-либо модели

# Маршрут index (В нашем случае ролей пользователей)

  # Главная страница приложения
@app.route('/')
def index():
    # Проверяем роль
    if 'user_id' not in session:
        return redirect(url_for('login'))

    role = session.get('role')
    if role == 'admin':  # Если роль администратора, показываем панель администратора
        return admin_dashboard()
    elif role == 'manager':  # Если роль менеджера, показываем панель менеджера
        return manager_dashboard()
    return worker_dashboard()


# Маршруты авторизации

   #Маршрут входа
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = login_user(username, password)
        if user:
            session.clear()
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            log_action(user['id'], 'login', f"User {username} logged in")
            return redirect(url_for('index'))
        flash('Invalid username or password', 'error')
    return render_template('login.html')

   #Маршрут регистрации
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if register_user(username, password):
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        flash('Username already exists', 'error')
    return render_template('register.html')

   #Маршрут для выхода
@app.route('/logout')
def logout():
    if 'user_id' in session:
        log_action(session['user_id'], 'logout', f"User {session['username']} logged out")
        session.clear()
    return redirect(url_for('login'))


# Маршруты админа (Нужна для передачи запросов от админа в базу данных)

@app.route('/admin/get_users')
def get_users_table():
    db = get_db()
    users = db.execute('SELECT * FROM users ORDER BY id').fetchall()
    return render_template('_users_table.html', users=users)


@app.route('/admin/change_role', methods=['POST'])
def change_role():
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'Invalid JSON'}), 400

    user_id = data.get('user_id')
    new_role = data.get('new_role')

    if not user_id or not new_role or new_role not in ['admin', 'manager', 'worker']:
        return jsonify({'success': False, 'message': 'Invalid parameters'}), 400

    try:
        db = get_db()

        # Проверяем существование пользователя
        user = db.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
        if not user:
            return jsonify({'success': False, 'message': 'User not found'}), 404

        # Обновляем роль
        db.execute('UPDATE users SET role = ? WHERE id = ?', (new_role, user_id))
        db.commit()

        # Логируем действие
        log_action(
            session['user_id'],
            'role_change',
            f"Changed role for {user['username']} from {user['role']} to {new_role}"
        )

        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401

    db = get_db()
    try:
        # Проверяем, что пользователь не удаляет сам себя
        if user_id == session['user_id']:
            return jsonify({'success': False, 'error': 'Cannot delete yourself'}), 400

        # Удаляем пользователя
        db.execute('DELETE FROM users WHERE id = ?', (user_id,))
        db.commit()
        log_action(session['user_id'], 'user_deleted', f'User {user_id} deleted')
        return jsonify({'success': True})
    except sqlite3.Error as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/refresh_users')
def refresh_users():
    if 'user_id' not in session or session.get('role') != 'admin':
        return '', 403

    db = get_db()
    users = db.execute('SELECT id, username, role FROM users').fetchall()
    return render_template('_users_table.html', users=users, current_user=session['user_id'])


# Маршруты Менеджера

@app.route('/manager/get_projects')
def get_projects():
    if session.get('role') not in ['admin', 'manager']:
        return redirect(url_for('login'))

    db = get_db()
    try:
        projects = db.execute('''
            SELECT id, name, description,
                   strftime('%Y-%m-%d %H:%M:%S', created_at) as created_at
            FROM projects
            WHERE created_by = ?
            ORDER BY created_at DESC
        ''', (session['user_id'],)).fetchall()

        # Конвертируем Row объекты в словари
        projects = [dict(project) for project in projects]
        return render_template('_projects_list.html', projects=projects)
    except Exception as e:
        print(f"Error fetching projects: {e}")
        return render_template('_projects_list.html', projects=[])


@app.route('/manager/create_project', methods=['POST'])
def create_project():
    if session.get('role') not in ['admin', 'manager']:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403

    name = request.form.get('name')
    description = request.form.get('description')

    if not name:
        return jsonify({'success': False, 'message': 'Project name is required'}), 400

    try:
        db = get_db()
        db.execute(
            "INSERT INTO projects (name, description, created_by) VALUES (?, ?, ?)",
            (name, description, session['user_id'])
        )
        db.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/manager/get_projects_select')
def get_projects_select():
    if session.get('role') not in ['admin', 'manager']:
        return jsonify([])

    db = get_db()
    projects = db.execute('''
        SELECT id, name FROM projects
        WHERE created_by = ?
        ORDER BY name
    ''', (session['user_id'],)).fetchall()
    return jsonify([dict(project) for project in projects])


@app.route('/manager/get_workers')
def get_workers():
    if session.get('role') not in ['admin', 'manager']:
        return jsonify([])

    db = get_db()
    workers = db.execute('''
        SELECT id, username FROM users
        WHERE role = 'worker'
        ORDER BY username
    ''').fetchall()
    return jsonify([dict(worker) for worker in workers])


@app.route('/manager/create_task', methods=['POST'])
def create_task():
    if session.get('role') not in ['admin', 'manager']:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403

    title = request.form.get('title')
    project_id = request.form.get('project_id')
    assigned_to = request.form.get('assigned_to')
    description = request.form.get('description')

    if not all([title, project_id, assigned_to]):
        return jsonify({'success': False, 'message': 'Required fields are missing'}), 400

    try:
        db = get_db()
        db.execute(
            """INSERT INTO tasks
            (title, description, project_id, assigned_to, assigned_by, status)
            VALUES (?, ?, ?, ?, ?, 'pending')""",
            (title, description, project_id, assigned_to, session['user_id'])
        )
        db.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/delete_project/<int:project_id>', methods=['POST'])
def delete_project(project_id):
    if 'user_id' not in session or session.get('role') not in ['admin', 'manager']:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401

    db = get_db()
    try:
        # Проверяем существование проекта
        project = db.execute('SELECT * FROM projects WHERE id = ?', (project_id,)).fetchone()
        if not project:
            return jsonify({'success': False, 'error': 'Project not found'}), 404

        # Удаляем проект
        db.execute('DELETE FROM projects WHERE id = ?', (project_id,))
        db.commit()
        log_action(session['user_id'], 'project_deleted', f'Project {project_id} deleted')
        return jsonify({'success': True})
    except sqlite3.Error as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ================== Сервисы ============== (В данном случае имеется виду панели разных ролей пользователей)

def admin_dashboard():
    db = get_db()
    users = db.execute('SELECT id, username, role FROM users').fetchall()
    logs = db.execute('''
        SELECT l.*, u.username 
        FROM logs l
        LEFT JOIN users u ON l.user_id = u.id
        ORDER BY l.timestamp DESC 
        LIMIT 10
    ''').fetchall()
    return render_template('admin.html', users=users, logs=logs, current_user=session['user_id'])


def manager_dashboard():
    db = get_db()
    # Получаем все проекты, а не только созданные текущим менеджером
    projects = db.execute('''
        SELECT p.*, u.username as creator_name 
        FROM projects p
        JOIN users u ON p.created_by = u.id
        ORDER BY p.id DESC
    ''').fetchall()

    workers = db.execute('SELECT id, username FROM users WHERE role = "worker"').fetchall()
    return render_template('manager.html', projects=projects, workers=workers, current_user=session['user_id'])


def worker_dashboard():
    tasks = get_user_tasks(session['user_id'])
    return render_template('worker.html', tasks=tasks)


# Инициализация приложения
if __name__ == '__main__':
    os.makedirs(app.instance_path, exist_ok=True)
    app.cli.add_command(init_db_command)
    app.run(debug=True)
