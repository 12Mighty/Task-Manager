from database import get_db

def create_notification(user_id, message, link=None):
    db = get_db()
    db.execute('INSERT INTO notifications (user_id, message, link) VALUES (?, ?, ?)',
              (user_id, message, link))
    db.commit()

def get_user_notifications(user_id, unread_only=False):
    db = get_db()
    query = 'SELECT * FROM notifications WHERE user_id = ?'
    if unread_only:
        query += ' AND is_read = 0'
    query += ' ORDER BY created_at DESC'
    return db.execute(query, (user_id,)).fetchall()
