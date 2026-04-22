/* ═══ UTILITIES & API ═══ */
const API = '';
let TOKEN = localStorage.getItem('token');
let USER = JSON.parse(localStorage.getItem('user') || 'null');

function getToken() {
    // Always get fresh token from localStorage
    return localStorage.getItem('token');
}

function api(url, opts = {}) {
    const headers = opts.headers || {};
    const token = getToken();
    if (token) headers['Authorization'] = 'Bearer ' + token;
    if (opts.body && !(opts.body instanceof FormData)) {
        headers['Content-Type'] = 'application/json';
        opts.body = JSON.stringify(opts.body);
    }
    return fetch(API + url, { ...opts, headers }).then(async r => {
        if (!r.ok) {
            // Handle 401 Unauthorized - auto logout
            if (r.status === 401) {
                console.error('[API 401] Unauthorized access to', url);
                console.error('[API 401] Token present:', !!token);
                console.error('[API 401] Token value:', token ? token.substring(0, 20) + '...' : 'none');
                
                // Only auto-logout if we have a token (it might be invalid)
                if (token) {
                    localStorage.removeItem('token');
                    localStorage.removeItem('user');
                    TOKEN = null;
                    USER = null;
                    
                    // Redirect to login if not already there
                    if (!window.location.pathname.includes('/index.html') && !window.location.pathname === '/') {
                        toast('❌ Session expired. Please log in again.', 'error');
                        setTimeout(() => {
                            window.location.href = '/index.html';
                        }, 2000);
                    }
                }
                throw new Error('Unauthorized: Session expired or invalid');
            }
            
            let errorMsg = 'Error';
            try {
                const err = await r.json();
                console.error('[API Error Response]', err);
                errorMsg = err.detail || err.message || JSON.stringify(err);
            } catch (e) {
                errorMsg = `Request failed with status ${r.status}`;
            }
            throw new Error(errorMsg);
        }
        const ct = r.headers.get('content-type') || '';
        if (ct.includes('json')) return r.json();
        return r;
    });
}

function apiForm(url, formData) {
    const token = getToken();
    return fetch(API + url, {
        method: 'POST',
        headers: token ? { 'Authorization': 'Bearer ' + token } : {},
        body: formData
    }).then(async r => {
        if (!r.ok) {
            // Handle 401 Unauthorized
            if (r.status === 401) {
                console.error('[apiForm 401] Unauthorized access to', url);
                if (token) {
                    localStorage.removeItem('token');
                    localStorage.removeItem('user');
                    TOKEN = null;
                    USER = null;
                    toast('❌ Session expired. Please log in again.', 'error');
                    setTimeout(() => {
                        window.location.href = '/index.html';
                    }, 2000);
                }
                throw new Error('Unauthorized: Session expired or invalid');
            }
            
            const err = await r.json().catch(() => ({ detail: 'Request failed' }));
            throw new Error(err.detail || 'Error');
        }
        return r.json();
    });
}

// API call without authentication (for login endpoints)
function apiFormNoAuth(url, formData) {
    return fetch(API + url, {
        method: 'POST',
        body: formData
    }).then(async r => {
        if (!r.ok) {
            const err = await r.json().catch(() => ({ detail: 'Request failed' }));
            throw new Error(err.detail || 'Error');
        }
        return r.json();
    });
}

function toast(msg, type = 'info') {
    const c = document.getElementById('toast-container');
    const t = document.createElement('div');
    t.className = 'toast ' + type;
    t.innerHTML = msg;
    c.appendChild(t);
    setTimeout(() => { t.style.opacity = '0'; setTimeout(() => t.remove(), 300); }, 4000);
}

function timeAgo(dateStr) {
    if (!dateStr) return '';
    const d = new Date(dateStr.replace(' ', 'T') + 'Z');
    const s = Math.floor((Date.now() - d.getTime()) / 1000);
    if (s < 60) return 'Just now';
    if (s < 3600) return Math.floor(s / 60) + 'm ago';
    if (s < 86400) return Math.floor(s / 3600) + 'h ago';
    return Math.floor(s / 86400) + 'd ago';
}

function severityBadge(s) {
    return `<span class="badge badge-${s || 'low'}">${(s || 'low').toUpperCase()}</span>`;
}

function riskBadge(level) {
    const icons = { green: '🟢', yellow: '🟡', red: '🔴' };
    return `<span class="risk-indicator ${level}">${icons[level] || '⚪'} ${level.toUpperCase()}</span>`;
}

function alertBadge(level) {
    const cls = { green: 'badge-green', yellow: 'badge-yellow', red: 'badge-red' };
    return `<span class="badge ${cls[level] || 'badge-blue'}">${level.toUpperCase()}</span>`;
}

function $(id) { return document.getElementById(id); }
function show(id) { $(id)?.classList.remove('hidden'); }
function hide(id) { $(id)?.classList.add('hidden'); }
