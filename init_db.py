import sqlite3
from app import app

def init_db():
    try:
        # Подключаемся к БД
        conn = sqlite3.connect(app.config['DATABASE'])
        cursor = conn.cursor()

        # Читаем schema.sql
        with open('schema.sql', 'r', encoding='utf-8') as f:
            schema = f.read()

        # Выполняем SQL скрипт
        cursor.executescript(schema)

        # Создаем администратора
        cursor.execute(
            "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
            ('admin', 'pbkdf2:sha256:260000$...', 'admin')  # Пароль: admin123
        )

        conn.commit()
        print("База данных успешно инициализирована")
        print(f"Файл БД создан по пути: {app.config['DATABASE']}")
        print("Данные для входа: admin / admin123")
    except Exception as e:
        print(f"Ошибка при инициализации БД: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    init_db()
