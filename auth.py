#Данный файл использовался для тестов авторизации


from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db

def register_user(username, password, role='worker'):
    db = get_db()

    # Проверяем, существует ли пользователь с таким именем
    existing_user = db.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()
    if existing_user:
        return False

    # Хешируем пароль
    hashed_password = generate_password_hash(password)

    # Создаем нового пользователя
    db.execute('INSERT INTO users (username, password, role) VALUES (?, ?, ?)',
              (username, hashed_password, role))
    db.commit()
    return True

def login_user(username, password):
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()

    if user and check_password_hash(user['password'], password):
        return dict(user)  # Конвертируем Row в dict
    return None

def get_user_role(user_id):
    db = get_db()
    user = db.execute('SELECT role FROM users WHERE id = ?', (user_id,)).fetchone()
    return user['role'] if user else None
