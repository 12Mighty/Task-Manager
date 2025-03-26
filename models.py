from database import get_db

class User:
    @staticmethod
    def get_by_id(user_id):
        db = get_db()
        return db.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()

    @staticmethod
    def get_all():
        db = get_db()
        return db.execute('SELECT * FROM users').fetchall()

class Project:
    @staticmethod
    def create(name, description, created_by):
        db = get_db()
        db.execute('INSERT INTO projects (name, description, created_by) VALUES (?, ?, ?)',
                  (name, description, created_by))
        db.commit()
        return db.execute('SELECT last_insert_rowid()').fetchone()[0]

    @staticmethod
    def get_all():
        db = get_db()
        return db.execute('SELECT * FROM projects').fetchall()

class Task:
    @staticmethod
    def create(title, description, project_id, assigned_to, assigned_by):
        db = get_db()
        db.execute('''
            INSERT INTO tasks (title, description, project_id, assigned_to, assigned_by, status)
            VALUES (?, ?, ?, ?, ?, "pending")
        ''', (title, description, project_id, assigned_to, assigned_by))
        db.commit()
        return db.execute('SELECT last_insert_rowid()').fetchone()[0]

    @staticmethod
    def get_by_user(user_id):
        db = get_db()
        return db.execute('''
            SELECT t.*, p.name as project_name
            FROM tasks t
            JOIN projects p ON t.project_id = p.id
            WHERE t.assigned_to = ?
        ''', (user_id,)).fetchall()

    @staticmethod
    def complete(task_id):
        db = get_db()
        db.execute('UPDATE tasks SET status = "completed" WHERE id = ?', (task_id,))
        db.commit()

class Subtask:
    @staticmethod
    def create(title, description, task_id, assigned_to):
        db = get_db()
        db.execute('''
            INSERT INTO subtasks (title, description, task_id, assigned_to, status)
            VALUES (?, ?, ?, ?, "pending")
        ''', (title, description, task_id, assigned_to))
        db.commit()
        return db.execute('SELECT last_insert_rowid()').fetchone()[0]

    @staticmethod
    def get_by_user(user_id):
        db = get_db()
        return db.execute('''
            SELECT s.*, t.title as task_title
            FROM subtasks s
            JOIN tasks t ON s.task_id = t.id
            WHERE s.assigned_to = ?
        ''', (user_id,)).fetchall()

    @staticmethod
    def complete(subtask_id):
        db = get_db()
        db.execute('UPDATE subtasks SET status = "completed" WHERE id = ?', (subtask_id,))
        db.commit()

class LogEntry:
    @staticmethod
    def create(user_id, action, details):
        db = get_db()
        db.execute('INSERT INTO logs (user_id, action, details) VALUES (?, ?, ?)',
                  (user_id, action, details))
        db.commit()

    @staticmethod
    def get_recent(limit=10):
        db = get_db()
        return db.execute('''
            SELECT l.*, u.username
            FROM logs l
            JOIN users u ON l.user_id = u.id
            ORDER BY l.timestamp DESC
            LIMIT ?
        ''', (limit,)).fetchall()

class Notification:
    @staticmethod
    def create(user_id, message, link=None):
        db = get_db()
        db.execute('INSERT INTO notifications (user_id, message, link) VALUES (?, ?, ?)',
                  (user_id, message, link))
        db.commit()

    @staticmethod
    def get_for_user(user_id, unread_only=False):
        db = get_db()
        query = 'SELECT * FROM notifications WHERE user_id = ?'
        if unread_only:
            query += ' AND is_read = 0'
        query += ' ORDER BY created_at DESC'
        return db.execute(query, (user_id,)).fetchall()

    @staticmethod
    def mark_as_read(notification_id, user_id):
        db = get_db()
        db.execute('UPDATE notifications SET is_read = 1 WHERE id = ? AND user_id = ?',
                   (notification_id, user_id))
        db.commit()
