/* ═══ AUTH FUNCTIONS ═══ */

// Generate 4-digit code based on current time (changes every 30 seconds)
function generateVerificationCode() {
    const now = new Date();
    const seconds = Math.floor(now.getTime() / 1000);
    const block = Math.floor(seconds / 30); // 30-second blocks
    const seed = block * 9973; // Prime number for better distribution
    const code = Math.abs(seed) % 10000;
    return String(code).padStart(4, '0');
}

// Update the code display and refresh every 30 seconds
let authCodeInterval = null;

function initVerificationCode() {
    // Clear any existing interval
    if (authCodeInterval) clearInterval(authCodeInterval);
    
    const display = $('auth-code-display');
    const countdown = $('auth-code-countdown');
    if (!display) return; // Element not found
    
    const updateCode = () => {
        const now = new Date();
        const seconds = Math.floor(now.getTime() / 1000);
        const block = Math.floor(seconds / 30);
        const seed = block * 9973;
        const code = Math.abs(seed) % 10000;
        const codeStr = String(code).padStart(4, '0');
        
        // Calculate remaining time in current block
        const blockStart = block * 30;
        const blockEnd = (block + 1) * 30;
        const remaining = blockEnd - seconds;
        
        display.textContent = codeStr.split('').join(' ');
        
        // Update countdown if element exists
        if (countdown) {
            countdown.textContent = `Expires in ${remaining}s`;
            if (remaining <= 6) {
                countdown.style.color = '#ef4444'; // Red warning
            } else if (remaining <= 14) {
                countdown.style.color = '#eab308'; // Yellow warning
            } else {
                countdown.style.color = 'var(--text-muted)';
            }
        }
        
        // Add visual feedback on code change
        display.style.opacity = '0.7';
        setTimeout(() => { display.style.opacity = '1'; }, 200);
    };
    
    // Update immediately
    updateCode();
    
    // Update every second
    authCodeInterval = setInterval(updateCode, 1000);
}

function showLogin() { 
    show('login-form'); 
    hide('register-form');
    // Ensure code is initialized
    setTimeout(initVerificationCode, 100);
}

function showRegister() { 
    hide('login-form');
    show('register-form');
    if (authCodeInterval) clearInterval(authCodeInterval);
}

function showSuccessPage(message, redirectCallback) {
    hide('auth-page');
    hide('secret-key-page');
    show('success-page');
    
    // Set the success message
    const msgEl = $('success-message');
    if (msgEl) msgEl.textContent = message;
    
    // Start countdown
    let countdown = 3;
    const countdownEl = $('countdown-timer');
    
    const interval = setInterval(() => {
        countdown--;
        if (countdownEl) countdownEl.textContent = countdown;
        
        if (countdown <= 0) {
            clearInterval(interval);
            hide('success-page');
            if (redirectCallback) redirectCallback();
        }
    }, 1000);
}

async function handleLogin(e) {
    e.preventDefault();
    
    const username = $('login-username').value;
    const password = $('login-password').value;
    const code = $('login-code').value;
    
    // Validate code format
    if (!code || code.length !== 4 || !/^\d{4}$/.test(code)) {
        toast('❌ Verification code must be exactly 4 digits', 'error');
        return;
    }
    
    const fd = new FormData();
    fd.append('username', username);
    fd.append('password', password);
    fd.append('verification_code', code);
    
    try {
        $('login-btn').textContent = '⏳ Signing in...';
        const data = await apiForm('/api/auth/login', fd);
        TOKEN = data.access_token;
        USER = data.user;
        localStorage.setItem('token', TOKEN);
        localStorage.setItem('user', JSON.stringify(USER));
        
        // If admin, show secret key page instead of success page
        if (USER.role === 'admin') {
            toast('✅ Credentials verified! Now enter admin secret key.', 'success');
            hide('auth-page');
            show('secret-key-page');
            $('secret-key-input').focus();
            $('secret-key-input').value = '';
            $('login-btn').textContent = '🔐 Sign In';
        } else {
            // Show success page for regular users, workers, developers
            const message = `Successfully logged into HealthGuard NE as ${USER.role === 'developer' ? 'Developer' : USER.role === 'worker' ? 'Health Worker' : 'Community Member'}`;
            showSuccessPage(message, () => {
                initApp();
            });
        }
    } catch (err) {
        const msg = err.message.toLowerCase();
        if (msg.includes('verification') || msg.includes('code') || msg.includes('expired')) {
            toast('❌ Invalid or expired code. Check the code on the left and try again.', 'error');
            $('login-code').value = '';
            $('login-code').focus();
        } else if (msg.includes('credential')) {
            toast('❌ Invalid username or password', 'error');
        } else {
            toast('❌ ' + err.message, 'error');
        }
    } finally {
        $('login-btn').textContent = '🔐 Sign In';
    }
}

async function handleSecretKey(e) {
    e.preventDefault();
    
    const key = $('secret-key-input').value;
    
    if (!key) {
        toast('❌ Please enter the secret key', 'error');
        return;
    }
    
    // Verify token is available before proceeding
    const token = getToken();
    if (!token) {
        toast('❌ Session lost. Please log in again.', 'error');
        setTimeout(() => {
            logout();
        }, 1000);
        return;
    }
    
    try {
        $('secret-key-btn').textContent = '⏳ Verifying...';
        console.log('[SecretKey] Token available:', token.substring(0, 20) + '...');
        
        // Verify the secret key with backend
        const response = await api('/api/auth/verify-secret-key', {
            method: 'POST',
            body: { secret_key: key }
        });
        
        if (response.verified) {
            console.log('[SecretKey] Secret key verified successfully');
            toast('✅ Secret key verified! Welcome Admin.', 'success');
            hide('secret-key-page');
            
            // Ensure localStorage is updated
            localStorage.setItem('token', token);
            localStorage.setItem('user', JSON.stringify(USER));
            
            // Small delay to ensure DOM is ready
            setTimeout(() => {
                initApp();
            }, 300);
        } else {
            toast('❌ Invalid secret key', 'error');
            $('secret-key-input').value = '';
            $('secret-key-input').focus();
        }
    } catch (err) {
        console.error('[SecretKey] Error:', err.message);
        
        // Check if it's a 401 error (token issue)
        if (err.message.includes('Unauthorized') || err.message.includes('Session expired')) {
            toast('❌ Session expired. Please log in again.', 'error');
            setTimeout(() => {
                logout();
            }, 1500);
        } else {
            toast('❌ ' + err.message, 'error');
            $('secret-key-input').value = '';
            $('secret-key-input').focus();
        }
    } finally {
        $('secret-key-btn').textContent = '🔓 Verify & Access';
    }
}

function handleAdminLogout() {
    TOKEN = null;
    USER = null;
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    hide('secret-key-page');
    show('auth-page');
    showLogin();
    toast('Logged out', 'info');
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
        const registerBtn = document.querySelector('#register-form button[type="submit"]');
        if (registerBtn) registerBtn.textContent = '⏳ Creating account...';
        
        const data = await apiForm('/api/auth/register', fd);
        
        // Show success page before switching to login
        const role = $('reg-role').value;
        const roleLabel = role === 'worker' ? 'Health Worker' : 'Community Member';
        const message = `Account created successfully! You are now registered as a ${roleLabel}. Taking you to login...`;
        
        showSuccessPage(message, () => {
            // Clear form fields
            document.getElementById('register-form').reset();
            
            // Switch to login form
            show('auth-page');
            showLogin();
        });
    } catch (err) {
        toast('❌ ' + err.message, 'error');
        const registerBtn = document.querySelector('#register-form button[type="submit"]');
        if (registerBtn) registerBtn.textContent = '✨ Create Account';
    }
}

function logout() {
    TOKEN = null; USER = null;
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    destroyWorkerTrainingChatbot?.();
    hide('main-app');
    hide('secret-key-page');
    show('auth-page');
    initVerificationCode();
    toast('👋 Logged out', 'info');
}

function goHome() {
    if (USER) {
        if (USER.role === 'admin') loadAdminDashboard();
        else if (USER.role === 'worker') loadWorkerDashboard();
        else loadUserDashboard();
    }
}
