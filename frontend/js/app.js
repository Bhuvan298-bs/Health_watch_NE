/* ═══ MAIN APP ORCHESTRATION ═══ */

// Notification system
let notifPanelOpen = false;

function toggleNotifications() {
    notifPanelOpen = !notifPanelOpen;
    const panel = $('notification-panel');
    if (notifPanelOpen) {
        panel.classList.add('open');
        loadNotifications();
    } else {
        panel.classList.remove('open');
    }
}

async function loadNotifications() {
    try {
        const d = await api('/api/notifications');
        const badge = $('notif-badge');
        if (d.unread_count > 0) {
            badge.textContent = d.unread_count > 9 ? '9+' : d.unread_count;
            badge.classList.remove('hidden');
        } else {
            badge.classList.add('hidden');
        }
        $('notification-list').innerHTML = d.notifications.length === 0
            ? '<div class="empty-state" style="padding:20px"><p>No notifications</p></div>'
            : d.notifications.map(n => `
                <div class="notification-item ${n.is_read ? '' : 'unread'}">
                    <div class="notif-title">${n.title}</div>
                    <div class="notif-msg">${n.message}</div>
                    <div class="notif-time">${timeAgo(n.created_at)}</div>
                </div>`).join('');
    } catch (e) { console.error(e); }
}

async function markAllRead() {
    try {
        await api('/api/notifications/read-all', { method: 'POST' });
        $('notif-badge').classList.add('hidden');
        loadNotifications();
        toast('All notifications marked as read', 'info');
    } catch (e) { console.error(e); }
}

function initApp() {
    hide('auth-page');
    show('main-app');

    if (!USER) return;

    const roleBadges = {
        admin: '🛡️ Admin Dashboard',
        worker: '👷 Health Worker',
        user: '👤 Community Member'
    };
    $('nav-role-badge').textContent = roleBadges[USER.role] || USER.role;

    // Build navigation
    if (USER.role === 'admin') {
        destroyWorkerTrainingChatbot?.();
        buildAdminSidebar();
        loadAdminDashboard();
    } else if (USER.role === 'worker') {
        buildWorkerSidebar();
        loadWorkerDashboard();
        initWorkerTrainingChatbot?.();
    } else {
        destroyWorkerTrainingChatbot?.();
        buildUserSidebar();
        loadUserDashboard();
    }

    // Poll notifications every 30 seconds
    loadNotifications();
    setInterval(loadNotifications, 30000);
}

// Auto-login if token exists
document.addEventListener('DOMContentLoaded', () => {
    if (TOKEN && USER) {
        initApp();
    } else {
        show('auth-page');
        hide('main-app');
    }
});
