import sqlite3
from app import app
from werkzeug.security import generate_password_hash


def init_db():
    conn = None
    try:
        # Подключаемся к БД
        conn = sqlite3.connect(app.config['DATABASE'])
        cursor = conn.cursor()

        # Читаем schema.sql
        with open('schema.sql', 'r', encoding='utf-8') as f:
            schema = f.read()

        # Выполняем SQL скрипт
        cursor.executescript(schema)

        # Проверяем, существует ли уже пользователь admin
        cursor.execute("SELECT 1 FROM users WHERE username = 'admin' LIMIT 1")
        admin_exists = cursor.fetchone()

        if not admin_exists:
            # Создаем администратора только если он не существует
            cursor.execute(
                "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                ('admin', generate_password_hash('admin123'), 'admin')
            )
            print("Администратор успешно создан")
            print("Данные для входа: admin / admin123")
        else:
            print("Пользователь 'admin' уже существует в базе данных")

        conn.commit()
        print("База данных успешно инициализирована")
        print(f"Файл БД создан по пути: {app.config['DATABASE']}")
    except Exception as e:
        print(f"Ошибка при инициализации БД: {e}")
    finally:
        if conn:
            conn.close()


if __name__ == '__main__':
    init_db()
