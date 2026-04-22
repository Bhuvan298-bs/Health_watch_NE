/* ═══ MAIN APP ORCHESTRATION ═══ */

// Mobile sidebar toggle
let sidebarOpen = false;

function toggleSidebar() {
    sidebarOpen = !sidebarOpen;
    const sidebar = $('sidebar');
    const toggle = $('menu-toggle');
    
    if (sidebarOpen) {
        sidebar.classList.add('open');
        toggle.classList.add('open');
    } else {
        sidebar.classList.remove('open');
        toggle.classList.remove('open');
    }
}

// Close sidebar when clicking outside
document.addEventListener('click', (e) => {
    const sidebar = $('sidebar');
    const toggle = $('menu-toggle');
    
    if (sidebarOpen && !sidebar.contains(e.target) && !toggle.contains(e.target)) {
        sidebarOpen = false;
        sidebar.classList.remove('open');
        toggle.classList.remove('open');
    }
});

// Close sidebar on link click
function closeSidebar() {
    if (window.innerWidth <= 768) {
        sidebarOpen = false;
        $('sidebar').classList.remove('open');
        $('menu-toggle').classList.remove('open');
    }
}

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
        // Skip if no token - user not authenticated (use getToken to get fresh token)
        if (!getToken()) {
            return;
        }
        
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
    } catch (e) { 
        // Silently fail if not authenticated or endpoint error
        if (e.message && (e.message.includes('401') || e.message.includes('Unauthorized'))) {
            console.warn('[Notifications] 401 error - session might be expired');
            return;
        }
        console.error('[Notifications] Error loading:', e.message);
    }
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
    const token = getToken();
    const user = JSON.parse(localStorage.getItem('user') || 'null');
    
    // Always initialize verification code if login page is showing
    setTimeout(() => {
        initVerificationCode();
    }, 100);
    
    if (token && user) {
        // User is logged in, restore the session
        USER = user;
        
        // Show appropriate dashboard based on role
        if (user.role === 'developer') {
            // Developer user - show developer dashboard
            hide('auth-page');
            show('dev-dashboard');
            // Initialize developer dashboard
            setTimeout(() => {
                initDevDashboard(user);
            }, 50);
        } else {
            // Regular user, admin, worker, etc. - show main app
            hide('auth-page');
            show('main-app');
            initApp();
        }
    } else {
        // Not logged in - show login page
        show('auth-page');
        hide('main-app');
        hide('dev-dashboard');
        // Also initialize on form switch
        const loginForm = document.getElementById('login-form');
        const regForm = document.getElementById('register-form');
        if (loginForm) loginForm.addEventListener('shown', initVerificationCode);
    }
});
