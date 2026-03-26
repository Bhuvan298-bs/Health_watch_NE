/* ═══ UTILITIES & API ═══ */
const API = '';
let TOKEN = localStorage.getItem('token');
let USER = JSON.parse(localStorage.getItem('user') || 'null');

function api(url, opts = {}) {
    const headers = opts.headers || {};
    if (TOKEN) headers['Authorization'] = 'Bearer ' + TOKEN;
    if (opts.body && !(opts.body instanceof FormData)) {
        headers['Content-Type'] = 'application/json';
        opts.body = JSON.stringify(opts.body);
    }
    return fetch(API + url, { ...opts, headers }).then(async r => {
        if (!r.ok) {
            const err = await r.json().catch(() => ({ detail: 'Request failed' }));
            throw new Error(err.detail || 'Error');
        }
        const ct = r.headers.get('content-type') || '';
        if (ct.includes('json')) return r.json();
        return r;
    });
}

function apiForm(url, formData) {
    return fetch(API + url, {
        method: 'POST',
        headers: TOKEN ? { 'Authorization': 'Bearer ' + TOKEN } : {},
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
