/* ═══ AUTH FUNCTIONS ═══ */
function showLogin() { show('login-form'); hide('register-form'); }
function showRegister() { hide('login-form'); show('register-form'); }

async function handleLogin(e) {
    e.preventDefault();
    const fd = new FormData();
    fd.append('username', $('login-username').value);
    fd.append('password', $('login-password').value);
    try {
        $('login-btn').textContent = '⏳ Signing in...';
        const data = await apiForm('/api/auth/login', fd);
        TOKEN = data.access_token;
        USER = data.user;
        localStorage.setItem('token', TOKEN);
        localStorage.setItem('user', JSON.stringify(USER));
        toast('✅ Welcome back, ' + USER.full_name + '!', 'success');
        initApp();
    } catch (err) {
        toast('❌ ' + err.message, 'error');
    } finally {
        $('login-btn').textContent = '🔐 Sign In';
    }
}

async function handleRegister(e) {
    e.preventDefault();
    const fd = new FormData();
    fd.append('username', $('reg-username').value);
    fd.append('email', $('reg-email').value);
    fd.append('password', $('reg-password').value);
    fd.append('full_name', $('reg-fullname').value);
    fd.append('role', $('reg-role').value);
    fd.append('phone', $('reg-phone').value);
    fd.append('village', $('reg-village').value);
    fd.append('district', $('reg-district').value);
    try {
        const data = await apiForm('/api/auth/register', fd);
        toast('✅ ' + data.message, 'success');
        showLogin();
    } catch (err) {
        toast('❌ ' + err.message, 'error');
    }
}

function logout() {
    TOKEN = null; USER = null;
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    destroyWorkerTrainingChatbot?.();
    hide('main-app'); show('auth-page');
    toast('👋 Logged out', 'info');
}

function goHome() {
    if (USER) {
        if (USER.role === 'admin') loadAdminDashboard();
        else if (USER.role === 'worker') loadWorkerDashboard();
        else loadUserDashboard();
    }
}
