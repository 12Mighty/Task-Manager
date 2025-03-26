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

            cursor.execute(
                "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
            )

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
