document.addEventListener('DOMContentLoaded', function() {
    // Управление уведомлениями
    const notificationsBtn = document.getElementById('notifications-btn');
    const notificationsPanel = document.getElementById('notifications-panel');

    if (notificationsBtn) {
        notificationsBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            notificationsPanel.style.display = notificationsPanel.style.display === 'block' ? 'none' : 'block';
            loadNotifications();
        });

        // Закрытие панели при клике вне ее
        document.addEventListener('click', function(e) {
            if (!notificationsPanel.contains(e.target)) {
                notificationsPanel.style.display = 'none';
            }
        });
    }

    // Загрузка уведомлений
    function loadNotifications() {
        fetch('/api/notifications')
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    const notificationsList = document.getElementById('notifications-list');
                    const notificationCount = document.getElementById('notification-count');

                    // Обновляем счетчик непрочитанных уведомлений
                    const unreadCount = data.notifications.filter(n => !n.is_read).length;
                    notificationCount.textContent = unreadCount;
                    notificationCount.style.display = unreadCount > 0 ? 'flex' : 'none';

                    // Очищаем список и добавляем новые уведомления
                    notificationsList.innerHTML = '';

                    if (data.notifications.length === 0) {
                        notificationsList.innerHTML = '<p>No notifications</p>';
                        return;
                    }

                    data.notifications.forEach(notification => {
                        const notificationItem = document.createElement('div');
                        notificationItem.className = `notification-item ${notification.is_read ? '' : 'unread'}`;
                        notificationItem.innerHTML = `
                            <p>${notification.message}</p>
                            <div class="notification-time">${new Date(notification.created_at).toLocaleString()}</div>
                        `;

                        notificationItem.addEventListener('click', function() {
                            if (!notification.is_read) {
                                fetch(`/api/mark_notification_read/${notification.id}`, {
                                    method: 'POST'
                                });
                            }

                            if (notification.link) {
                                window.location.href = notification.link;
                            }
                        });

                        notificationsList.appendChild(notificationItem);
                    });
                }
            });
    }

    // Периодическая проверка новых уведомлений (каждые 30 секунд)
    setInterval(loadNotifications, 30000);

    // Инициализация при загрузке страницы
    loadNotifications();
});
