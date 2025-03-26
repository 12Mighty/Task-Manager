from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, g
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import click
import os
from datetime import datetime

# Конфигурация приложения
app = Flask(__name__)
app.secret_key = 'your-secret-key'
app.config['DATABASE'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'task_manager.db')
app.config['INSTANCE_PATH'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance')

# Создаем папку instance если ее нет
os.makedirs(app.config['INSTANCE_PATH'], exist_ok=True)

# ================== БАЗА ДАННЫХ ==================
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(app.config['DATABASE'])
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    """Инициализирует только структуру БД без тестовых пользователей"""
    with app.app_context():
        db = get_db()
        with app.open_resource('schema.sql') as f:
            db.executescript(f.read().decode('utf8'))

        # Проверяем, есть ли хотя бы один админ
        admin_exists = db.execute(
            "SELECT 1 FROM users WHERE role = 'admin'"
        ).fetchone()

        # Если админов нет, создаем первого
        if not admin_exists:
            db.execute(
                "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                ('admin', generate_password_hash('admin123'), 'admin')
            )
            db.commit()
            print("Создан администратор по умолчанию: admin/admin123")

@click.command('init-db')
def init_db_command():
    """Инициализирует БД"""
    init_db()
    click.echo('База данных инициализирована')

# ================== ПОЛЬЗОВАТЕЛИ ==================
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

def login_user(username, password):
    db = get_db()
    user = db.execute(
        'SELECT * FROM users WHERE username = ?', (username,)
    ).fetchone()
    if user and check_password_hash(user['password'], password):
        return dict(user)
    return None

def get_user_role(user_id):
    db = get_db()
    role = db.execute(
        'SELECT role FROM users WHERE id = ?', (user_id,)
    ).fetchone()
    return role['role'] if role else None

# ================== ПРОЕКТЫ ==================
def create_project(name, description, created_by):
    db = get_db()
    cursor = db.execute(
        "INSERT INTO projects (name, description, created_by) VALUES (?, ?, ?)",
        (name, description, created_by)
    )
    db.commit()
    return cursor.lastrowid

def get_projects():
    db = get_db()
    return db.execute('SELECT * FROM projects').fetchall()

# ================== ЗАДАЧИ ==================
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

# ================== ПОДЗАДАЧИ ==================
def create_subtask(title, description, task_id, assigned_to):
    db = get_db()
    cursor = db.execute(
        """INSERT INTO subtasks
        (title, description, task_id, assigned_to, status)
        VALUES (?, ?, ?, ?, 'pending')""",
        (title, description, task_id, assigned_to)
    )
    db.commit()
    return cursor.lastrowid

# ================== ЛОГИРОВАНИЕ ==================
def log_action(user_id, action, details=None):
    db = get_db()
    db.execute(
        "INSERT INTO logs (user_id, action, details) VALUES (?, ?, ?)",
        (user_id, action, details)
    )
    db.commit()

# ================== МАРШРУТЫ ==================
@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    role = session.get('role')
    if role == 'admin':
        return admin_dashboard()
    elif role == 'manager':
        return manager_dashboard()
    return worker_dashboard()

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

@app.route('/logout')
def logout():
    if 'user_id' in session:
        log_action(session['user_id'], 'logout', f"User {session['username']} logged out")
        session.clear()
    return redirect(url_for('login'))

# ================== ПАНЕЛИ ==================
def admin_dashboard():
    db = get_db()
    users = db.execute('SELECT id, username, role FROM users').fetchall()
    logs = db.execute('SELECT * FROM logs ORDER BY timestamp DESC LIMIT 10').fetchall()
    return render_template('admin.html', users=users, logs=logs)

def manager_dashboard():
    db = get_db()
    projects = get_projects()
    workers = db.execute('SELECT id, username FROM users WHERE role = "worker"').fetchall()
    return render_template('manager.html', projects=projects, workers=workers)

def worker_dashboard():
    tasks = get_user_tasks(session['user_id'])
    return render_template('worker.html', tasks=tasks)

# ================== API ==================
@app.route('/api/complete_task/<int:task_id>', methods=['POST'])
def complete_task(task_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    db = get_db()
    db.execute(
        'UPDATE tasks SET status = "completed" WHERE id = ? AND assigned_to = ?',
        (task_id, session['user_id'])
    )
    db.commit()
    log_action(session['user_id'], 'task_completed', f'Task {task_id} completed')
    return jsonify({'success': True})

# Инициализация приложения
if __name__ == '__main__':
    os.makedirs(app.instance_path, exist_ok=True)
    app.cli.add_command(init_db_command)
    app.run(debug=True)
