/* ═══ DEVELOPER PORTAL ═══ */

const DEVELOPER_SECRET_KEY = "2026"; // Secret key for developers

async function handleDevLogin(e) {
    e.preventDefault();
    
    const email = $('dev-email').value;
    const password = $('dev-password').value;
    const secretKey = $('dev-secret').value;
    
    // Validate inputs
    if (!email || !password || !secretKey) {
        toast('❌ All fields are required', 'error');
        return;
    }
    
    // Verify secret key
    if (secretKey !== DEVELOPER_SECRET_KEY) {
        toast('❌ Invalid developer secret key', 'error');
        $('dev-secret').value = '';
        $('dev-secret').focus();
        return;
    }
    
    const fd = new FormData();
    fd.append('email', email);
    fd.append('password', password);
    fd.append('secret_key', secretKey);
    
    try {
        $('dev-login-btn').textContent = '⏳ Authenticating...';
        
        // Use apiFormNoAuth since we're not authenticated yet
        const data = await apiFormNoAuth('/api/auth/dev-login', fd);
        
        if (!data.access_token) {
            throw new Error('Login failed: No token received');
        }
        
        TOKEN = data.access_token;
        USER = data.user;
        localStorage.setItem('token', TOKEN);
        localStorage.setItem('dev-token', TOKEN);
        localStorage.setItem('user', JSON.stringify(USER));
        
        toast('✅ Welcome to Developer Portal!', 'success');
        hide('dev-login-page');
        show('dev-dashboard');
        initDevDashboard(USER);
    } catch (err) {
        const msg = err.message.toLowerCase();
        if (msg.includes('secret')) {
            toast('❌ Invalid secret key', 'error');
        } else if (msg.includes('credential')) {
            toast('❌ Invalid email or password', 'error');
        } else {
            toast('❌ Login failed: ' + err.message, 'error');
        }
    } finally {
        $('dev-login-btn').textContent = '🔐 Access Developer Portal';
    }
}

function initDevDashboard(user) {
    // Hide other pages
    hide('auth-page');
    hide('secret-key-page');
    hide('dev-login-page');
    hide('main-app');
    show('dev-dashboard');
    
    // Set developer name
    $('dev-name').textContent = user.full_name || 'Developer';
    
    // Build menu
    buildDevMenu();
    
    // Load default page
    loadDevDashboard();
}

function buildDevMenu() {
    const menu = $('dev-menu');
    
    const items = [
        { id: 'dev-dashboard', label: '📊 Dashboard', onclick: 'loadDevDashboard()' },
        { id: 'dev-errors', label: '❌ Error Logs', onclick: 'loadDevErrorLogs()' },
        { id: 'dev-activity', label: '👥 User Activity', onclick: 'loadDevActivity()' },
        { id: 'dev-feedback', label: '💬 Feedback', onclick: 'loadDevFeedback()' },
        { id: 'dev-notices', label: '📢 Send Notice', onclick: 'loadDevNotices()' },
        { id: 'dev-logs', label: '📝 App Logs', onclick: 'loadDevLogs()' },
        { id: 'dev-admins', label: '👨‍💼 Manage Admins', onclick: 'loadManageAdmins()' },
        { id: 'dev-devs', label: '⚙️ Manage Developers', onclick: 'loadManageDevelopers()' },
        { id: 'dev-delete-logs', label: '🗑️ Delete Logs', onclick: 'loadDeleteLogsPage()' },
        { id: 'dev-blocked', label: '🔒 Blocked Users', onclick: 'loadBlockedUsersPage()' },
        { id: 'dev-health', label: '💓 Health Check', onclick: 'loadHealthCheckPage()' },
    ];
    
    menu.innerHTML = items.map(item => `
        <button onclick="${item.onclick}" 
                style="padding:12px 16px;background:transparent;border:none;color:#4B5563;text-align:left;cursor:pointer;border-radius:6px;font-size:0.9rem;transition:all 0.3s"
                onmouseover="this.style.background='#E9ECEF';this.style.color='#1F2937'"
                onmouseout="this.style.background='transparent';this.style.color='#4B5563'"
                id="${item.id}-btn">
            ${item.label}
        </button>
    `).join('');
}

function loadDevDashboard() {
    setActiveDev('dev-dashboard-btn');
    
    api('/api/dev/dashboard').then(data => {
        $('dev-content').innerHTML = `
            <h2 class="heading-lg mb-20">⚙️ Developer Dashboard</h2>
            
            <div class="grid-4 mb-24">
                <div class="stat-card blue"><div class="stat-icon">👥</div><div class="stat-number">${data.total_users}</div><div class="stat-label">Total Users</div></div>
                <div class="stat-card emerald"><div class="stat-icon">⚙️</div><div class="stat-number">${data.total_errors}</div><div class="stat-label">Total Errors</div></div>
                <div class="stat-card amber"><div class="stat-icon">❌</div><div class="stat-number">${data.unresolved_errors}</div><div class="stat-label">Unresolved</div></div>
                <div class="stat-card rose"><div class="stat-icon">💬</div><div class="stat-number">${data.unresponded_feedback}</div><div class="stat-label">Feedback</div></div>
            </div>
            
            <div class="grid-2 mb-24">
                <div class="card">
                    <h3 class="card-title mb-12">System Status</h3>
                    <div class="feed-item" style="border-left:3px solid #22c55e">
                        <strong style="color:#22c55e">✅ Database</strong>
                        <p style="font-size:0.8rem;color:#6B7280">Connected and operational</p>
                    </div>
                    <div class="feed-item" style="border-left:3px solid #22c55e">
                        <strong style="color:#22c55e">✅ API Server</strong>
                        <p style="font-size:0.8rem;color:#6B7280">All endpoints responding</p>
                    </div>
                    <div class="feed-item" style="border-left:3px solid #22c55e">
                        <strong style="color:#22c55e">✅ Active Sessions</strong>
                        <p style="font-size:0.8rem;color:#6B7280">${data.active_sessions} users online</p>
                    </div>
                </div>
                
                <div class="card">
                    <h3 class="card-title mb-12">Quick Stats</h3>
                    <div class="feed-item">
                        <strong>Total Admins</strong>
                        <p style="font-size:1.2rem;font-weight:bold;color:var(--primary)">${data.total_admins}</p>
                    </div>
                    <div class="feed-item">
                        <strong>Total Developers</strong>
                        <p style="font-size:1.2rem;font-weight:bold;color:var(--primary)">${data.total_developers}</p>
                    </div>
                    <div class="feed-item">
                        <strong>Feedback by Type</strong>
                        <p style="font-size:0.85rem;color:#6B7280">${
                            Object.entries(data.feedback_types).map(([type, count]) => `${type}: ${count}`).join(' • ')
                        }</p>
                    </div>
                </div>
            </div>
        `;
    }).catch(e => toast('Error loading dashboard: ' + e.message, 'error'));
}

function loadDevErrorLogs() {
    setActiveDev('dev-errors-btn');
    
    api('/api/dev/error-logs').then(logs => {
        $('dev-content').innerHTML = `
            <div class="flex items-center justify-between mb-20">
                <h2 class="heading-lg">❌ Error Logs</h2>
                <button class="btn btn-outline btn-sm" onclick="clearErrorLogs()">Clear Resolved</button>
            </div>
            
            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Type</th>
                            <th>Message</th>
                            <th>Severity</th>
                            <th>Endpoint</th>
                            <th>Time</th>
                            <th>Status</th>
                            <th>Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${logs.map(log => `
                            <tr>
                                <td>${log.id}</td>
                                <td>${log.error_type}</td>
                                <td style="max-width:200px;overflow:hidden;text-overflow:ellipsis">${log.error_message}</td>
                                <td><span class="badge badge-${log.severity === 'critical' ? 'danger' : log.severity === 'high' ? 'warning' : 'info'}">${log.severity}</span></td>
                                <td style="font-size:0.8rem">${log.endpoint}</td>
                                <td style="font-size:0.8rem">${new Date(log.created_at).toLocaleString()}</td>
                                <td>${log.is_resolved ? '✅ Resolved' : '⏳ Open'}</td>
                                <td>
                                    ${!log.is_resolved ? `<button class="btn btn-outline btn-xs" onclick="markErrorResolved(${log.id})">Mark Done</button>` : '-'}
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;
    }).catch(e => toast('Error loading logs: ' + e.message, 'error'));
}

function loadDevActivity() {
    setActiveDev('dev-activity-btn');
    
    api('/api/dev/user-activity').then(data => {
        // Calculate average session duration
        const totalDuration = data.all_sessions.reduce((sum, s) => sum + (s.duration_minutes || 0), 0);
        const avgDuration = data.all_sessions.length > 0 ? Math.round(totalDuration / data.all_sessions.length) : 0;
        
        $('dev-content').innerHTML = `
            <h2 class="heading-lg mb-20">👥 User Activity Monitor</h2>
            
            <div class="grid-3 mb-20">
                <div class="card">
                    <h4>👤 Online Now</h4>
                    <div style="font-size:2rem;font-weight:bold;color:var(--primary)">${data.active_count}</div>
                </div>
                <div class="card">
                    <h4>📊 Total Sessions</h4>
                    <div style="font-size:2rem;font-weight:bold;color:var(--primary)">${data.all_sessions.length}</div>
                </div>
                <div class="card">
                    <h4>⏱️ Avg Session</h4>
                    <div style="font-size:2rem;font-weight:bold;color:var(--primary)">${avgDuration}m</div>
                </div>
            </div>

            <div class="card mb-20" style="border-left:4px solid var(--danger)">
                <h3 style="margin-bottom:16px;color:var(--danger)">🗑️ Activity Management</h3>
                <p style="font-size:0.9rem;color:#6B7280;margin-bottom:16px">Delete user session records to manage storage. This action cannot be undone.</p>
                <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px">
                    <button onclick="deleteSessionsByAge(24)" class="btn btn-danger btn-sm" style="width:100%">🗑️ Last 24 Hours</button>
                    <button onclick="deleteSessionsByAge(168)" class="btn btn-danger btn-sm" style="width:100%">🗑️ Last 7 Days</button>
                    <button onclick="deleteSessionsByAge(720)" class="btn btn-danger btn-sm" style="width:100%">🗑️ Last 30 Days</button>
                    <button onclick="deleteSessionsByAge(0)" class="btn btn-danger btn-sm" style="width:100%;background:var(--accent-rose)">🗑️ Delete ALL</button>
                </div>
            </div>
            
            <h3 class="mb-12">Active Sessions (${data.active_sessions.length})</h3>
            <div class="table-container mb-20">
                <table>
                    <thead>
                        <tr>
                            <th>User</th>
                            <th>Role</th>
                            <th>Login Time</th>
                            <th>Duration</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${data.active_sessions.length > 0 ? data.active_sessions.map(s => `
                            <tr>
                                <td>${s.username || s.user_id}</td>
                                <td><span class="badge badge-blue">${s.role}</span></td>
                                <td>${new Date(s.login_time).toLocaleString()}</td>
                                <td>-</td>
                            </tr>
                        `).join('') : '<tr><td colspan="4" style="text-align:center;color:#6B7280">No active sessions</td></tr>'}
                    </tbody>
                </table>
            </div>
            
            <h3 class="mb-12">Recent Sessions (Last 20)</h3>
            <div class="card">
                ${data.all_sessions.length > 0 ? data.all_sessions.slice(0, 20).map(s => `
                    <div class="feed-item">
                        <div style="display:flex;justify-content:space-between">
                            <strong>${s.username || 'User ' + s.user_id}</strong> (${s.role})
                            <span style="font-size:0.8rem;color:#6B7280">${s.duration_minutes || 0} minutes</span>
                        </div>
                        <div style="font-size:0.75rem;color:#6B7280">
                            ${new Date(s.login_time).toLocaleString()} → ${s.logout_time ? new Date(s.logout_time).toLocaleString() : 'Still active'}
                        </div>
                    </div>
                `).join('') : '<div style="color:#6B7280">No sessions recorded</div>'}
            </div>
        `;
    }).catch(e => toast('Error loading activity: ' + e.message, 'error'));
}

async function deleteSessionsByAge(ageHours) {
    const ageLabels = {
        24: 'Last 24 Hours',
        168: 'Last 7 Days',
        720: 'Last 30 Days',
        0: 'ALL Sessions'
    };
    
    const label = ageLabels[ageHours] || `${ageHours} hours`;
    const msg = `Delete all user sessions from ${label}? This action cannot be undone.`;
    
    if (!confirm(msg)) return;
    
    if (ageHours === 0) {
        const confirmText = prompt('To delete ALL sessions, type: DELETE ALL');
        if (confirmText !== 'DELETE ALL') {
            toast('⚠️ Cancelled', 'warning');
            return;
        }
    }
    
    try {
        const result = await api(`/api/dev/delete-sessions?age_hours=${ageHours}`, { method: 'POST' });
        toast(`✅ Deleted ${result.deleted_count} sessions`, 'success');
        setTimeout(() => loadDevActivity(), 500);
    } catch (err) {
        toast('❌ ' + err.message, 'error');
    }
}

function loadDevFeedback() {
    setActiveDev('dev-feedback-btn');
    
    api('/api/dev/feedback').then(feedback => {
        $('dev-content').innerHTML = `
            <h2 class="heading-lg mb-20">💬 Feedback from Users</h2>
            
            ${feedback.map(f => `
                <div class="card mb-16" style="border-left:4px solid ${f.feedback_type === 'bug' ? '#ef4444' : f.feedback_type === 'feature' ? '#3b82f6' : '#8b5cf6'}">
                    <div style="display:flex;justify-content:space-between;align-items:start;margin-bottom:12px">
                        <div>
                            <h4 style="margin:0;color:#1F2937">${f.from_role.toUpperCase()} - ${f.from_user_name}</h4>
                            <p style="margin:4px 0 0 0;font-size:0.8rem;color:#6B7280">${new Date(f.created_at).toLocaleString()}</p>
                        </div>
                        <span class="badge badge-${f.feedback_type === 'bug' ? 'danger' : 'primary'}">${f.feedback_type}</span>
                    </div>
                    <p style="margin:12px 0">${f.feedback_text}</p>
                    ${f.page_or_feature ? `<p style="margin:8px 0;font-size:0.85rem;color:var(--primary)">Page: ${f.page_or_feature}</p>` : ''}
                    
                    ${!f.is_resolved ? `
                        <textarea id="dev-response-${f.id}" class="form-control" placeholder="Write your response..." style="margin-bottom:8px"></textarea>
                        <button onclick="respondToFeedback(${f.id})" class="btn btn-primary btn-sm">Send Response</button>
                    ` : `
                        <p style="margin:8px 0;padding:12px;background:var(--bg-secondary);border-radius:6px;font-size:0.9rem">
                            <strong>✅ Response:</strong> ${f.dev_response}
                        </p>
                    `}
                </div>
            `).join('')}
        `;
    }).catch(e => toast('Error loading feedback: ' + e.message, 'error'));
}

function loadDevNotices() {
    setActiveDev('dev-notices-btn');
    
    $('dev-content').innerHTML = `
        <h2 class="heading-lg mb-20">📢 Send Notice to All Users</h2>
        
        <div class="card" style="max-width:800px">
            <form onsubmit="sendDevNotice(event)">
                <div class="form-group">
                    <label class="form-label">Notice Type</label>
                    <select class="form-control" id="notice-type" required>
                        <option value="info">ℹ️ Information</option>
                        <option value="warning">⚠️ Warning</option>
                        <option value="maintenance">🔧 Maintenance</option>
                        <option value="urgent">🚨 Urgent</option>
                    </select>
                </div>
                
                <div class="form-group">
                    <label class="form-label">Title</label>
                    <input class="form-control" id="notice-title" placeholder="Notice title" required>
                </div>
                
                <div class="form-group">
                    <label class="form-label">Message</label>
                    <textarea class="form-control" id="notice-message" placeholder="Write your notice..." required style="min-height:150px"></textarea>
                </div>
                
                <div class="form-group">
                    <label class="form-label">Send to (leave empty for everyone)</label>
                    <select class="form-control" id="notice-target">
                        <option value="all">👥 All Users</option>
                        <option value="admin">👨‍💼 Admins Only</option>
                        <option value="worker">👷 Workers Only</option>
                        <option value="user">👤 Community Members Only</option>
                    </select>
                </div>
                
                <button type="submit" class="btn btn-primary btn-lg" id="notice-submit-btn">📤 Send Notice</button>
            </form>
        </div>
        
        <h3 class="heading-md mt-24 mb-12">Recent Notices Sent</h3>
        <div id="recent-notices"></div>
    `;
    
    // Load recent notices
    api('/api/dev/notices').then(notices => {
        $('recent-notices').innerHTML = notices.length > 0 ? notices.map(n => `
            <div class="feed-item" style="display:flex;justify-content:space-between;align-items:start;padding:12px 16px;background:var(--bg-secondary);border-radius:8px;margin-bottom:12px;border-left:4px solid ${n.notice_type === 'urgent' ? '#ef4444' : n.notice_type === 'warning' ? '#f59e0b' : '#3b82f6'}">
                <div style="flex:1">
                    <strong style="color:#1F2937">${n.title}</strong>
                    <p style="margin:4px 0 0 0;font-size:0.8rem;color:#6B7280">${n.message.substring(0, 80)}${n.message.length > 80 ? '...' : ''}</p>
                    <p style="font-size:0.7rem;color:#6B7280;margin-top:4px">${new Date(n.created_at).toLocaleString()} • ${n.notice_type}</p>
                </div>
                <button onclick="deleteNotice(${n.id})" class="btn btn-danger btn-xs" style="margin-left:12px;white-space:nowrap">🗑️ Delete</button>
            </div>
        `).join('') : '<p style="color:#6B7280;font-style:italic">No notices sent yet</p>';
    });
}

async function loadDevLogs() {
    setActiveDev('dev-logs-btn');
    
    try {
        const data = await api('/api/dev/logs?lines=200');
        
        $('dev-content').innerHTML = `
            <h2 style="margin-bottom:20px">📝 Application Logs</h2>
            <div class="card mb-20">
                <div style="font-size:0.85rem;color:#6B7280;margin-bottom:16px">
                    <span>📄 Total log entries: <strong>${data.total_lines}</strong></span><br>
                    <span>📋 Showing last ${data.returned_lines} entries</span>
                </div>
                <div style="background:var(--bg-secondary);border-radius:8px;padding:16px;font-family:monospace;font-size:0.75rem;max-height:600px;overflow-y:auto;line-height:1.6">
                    ${data.logs && data.logs.length > 0 ? data.logs.map(log => `
                        <div style="padding:4px 0;color:${
                            log.raw.includes('ERROR') ? '#ef4444' : 
                            log.raw.includes('WARNING') ? '#f59e0b' : 
                            log.raw.includes('INFO') ? '#3b82f6' :
                            log.raw.includes('DEBUG') ? '#10b981' :
                            'var(--text-secondary)'
                        };border-bottom:1px solid var(--border-color)">
                            ${log.raw}
                        </div>
                    `).join('') : '<p style="color:#6B7280">No logs available</p>'}
                </div>
            </div>
        `;
    } catch (err) {
        toast('❌ ' + err.message, 'error');
    }
}

function loadManageAdmins() {
    setActiveDev('dev-admins-btn');
    
    api('/api/dev/admins').then(admins => {
        $('dev-content').innerHTML = `
            <div class="flex items-center justify-between mb-20">
                <h2 class="heading-lg">👨‍💼 Manage Admins</h2>
                <button class="btn btn-primary btn-sm" onclick="showAddAdminForm()">+ Add New Admin</button>
            </div>
            
            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Username</th>
                            <th>Email</th>
                            <th>Status</th>
                            <th>Joined</th>
                            <th>Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${admins.map(a => `
                            <tr>
                                <td>${a.full_name}</td>
                                <td>${a.username}</td>
                                <td>${a.email}</td>
                                <td><span class="badge badge-${a.is_active ? 'green' : 'red'}">${a.is_active ? 'Active' : 'Inactive'}</span></td>
                                <td>${new Date(a.created_at).toLocaleDateString()}</td>
                                <td>
                                    <button class="btn btn-outline btn-xs" onclick="toggleAdminStatus(${a.id}, ${a.is_active})">
                                        ${a.is_active ? 'Deactivate' : 'Activate'}
                                    </button>
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
            
            <div id="add-admin-form" class="hidden" style="margin-top:30px">
                <div class="card" style="max-width:500px">
                    <h3 class="mb-16">Add New Admin</h3>
                    <form onsubmit="createNewAdmin(event)">
                        <div class="form-group">
                            <label class="form-label">Full Name</label>
                            <input class="form-control" id="admin-fullname" placeholder="Enter full name" required>
                        </div>
                        <div class="form-group">
                            <label class="form-label">Username</label>
                            <input class="form-control" id="admin-username" placeholder="Enter username" required>
                        </div>
                        <div class="form-group">
                            <label class="form-label">Email</label>
                            <input type="email" class="form-control" id="admin-email" placeholder="Enter email address" required>
                        </div>
                        <div class="form-group">
                            <label class="form-label">Password</label>
                            <input type="password" class="form-control" id="admin-password" placeholder="Enter password" required>
                        </div>
                        <div class="form-group">
                            <label class="form-label">Secret Key (4 digits)</label>
                            <input type="password" class="form-control" id="admin-secret" maxlength="4" placeholder="Enter 4-digit key" required>
                        </div>
                        <button type="submit" class="btn btn-primary btn-lg">Create Admin</button>
                        <button type="button" class="btn btn-outline btn-lg" onclick="hide('add-admin-form')" style="margin-left:8px">Cancel</button>
                    </form>
                </div>
            </div>
        `;
    }).catch(e => toast('Error loading admins: ' + e.message, 'error'));
}

function loadManageDevelopers() {
    setActiveDev('dev-devs-btn');
    
    api('/api/dev/developers').then(devs => {
        $('dev-content').innerHTML = `
            <div class="flex items-center justify-between mb-20">
                <h2 class="heading-lg">⚙️ Manage Developers</h2>
                <button class="btn btn-primary btn-sm" onclick="showAddDevForm()">+ Add New Developer</button>
            </div>
            
            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Email</th>
                            <th>Status</th>
                            <th>Joined</th>
                            <th>Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${devs.map(d => `
                            <tr>
                                <td>${d.full_name}</td>
                                <td>${d.email}</td>
                                <td><span class="badge badge-${d.is_active ? 'green' : 'red'}">${d.is_active ? 'Active' : 'Inactive'}</span></td>
                                <td>${new Date(d.created_at).toLocaleDateString()}</td>
                                <td>
                                    <button class="btn btn-outline btn-xs" onclick="toggleDevStatus(${d.id}, ${d.is_active})">
                                        ${d.is_active ? 'Deactivate' : 'Activate'}
                                    </button>
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
            
            <div id="add-dev-form" class="hidden" style="margin-top:30px">
                <div class="card" style="max-width:500px">
                    <h3 class="mb-16">Add New Developer</h3>
                    <form onsubmit="createNewDeveloper(event)">
                        <div class="form-group">
                            <label class="form-label">Full Name</label>
                            <input class="form-control" id="dev-fullname" placeholder="Enter full name" required>
                        </div>
                        <div class="form-group">
                            <label class="form-label">Email</label>
                            <input type="email" class="form-control" id="dev-email-input" placeholder="Enter email address" required>
                        </div>
                        <div class="form-group">
                            <label class="form-label">Password</label>
                            <input type="password" class="form-control" id="dev-password-input" placeholder="Enter password" required>
                        </div>
                        <button type="submit" class="btn btn-primary btn-lg">Create Developer</button>
                        <button type="button" class="btn btn-outline btn-lg" onclick="hide('add-dev-form')" style="margin-left:8px">Cancel</button>
                    </form>
                </div>
            </div>
        `;
    }).catch(e => toast('Error loading developers: ' + e.message, 'error'));
}

function setActiveDev(id) {
    document.querySelectorAll('#dev-menu button').forEach(b => b.style.background = 'transparent');
    if ($(id)) $(id).style.background = 'var(--bg-tertiary)';
}

async function respondToFeedback(id) {
    const response = $(`dev-response-${id}`).value;
    if (!response) {
        toast('Please write a response', 'warning');
        return;
    }
    
    try {
        await api('/api/dev/feedback-response', {
            method: 'POST',
            body: { feedback_id: id, response }
        });
        toast('✅ Response sent!', 'success');
        loadDevFeedback();
    } catch (e) {
        toast('Error: ' + e.message, 'error');
    }
}

async function sendDevNotice(e) {
    e.preventDefault();
    
    const type = $('notice-type').value;
    const title = $('notice-title').value;
    const message = $('notice-message').value;
    let target = $('notice-target').value;
    
    // Map target values to role names
    const roleMap = {
        'all': 'user,worker,admin,developer',
        'admin': 'admin',
        'worker': 'worker',
        'user': 'user'
    };
    const targetRoles = roleMap[target] || 'user,worker,admin';
    
    const fd = new FormData();
    fd.append('title', title);
    fd.append('message', message);
    fd.append('notice_type', type);
    fd.append('target_roles', targetRoles);
    
    try {
        $('notice-submit-btn').textContent = '⏳ Sending...';
        await apiForm('/api/dev/send-notice', fd);
        toast('✅ Notice sent successfully!', 'success');
        
        // Reset form
        document.querySelector('form').reset();
        $('notice-submit-btn').textContent = '📤 Send Notice';
        
        // Reload notices to show the new one
        setTimeout(() => loadDevNotices(), 500);
    } catch (e) {
        toast('❌ Error: ' + e.message, 'error');
        $('notice-submit-btn').textContent = '📤 Send Notice';
    }
}

async function deleteNotice(noticeId) {
    if (!confirm('Are you sure you want to delete this notice?')) {
        return;
    }
    
    try {
        // Note: The backend may not have a delete endpoint for notices
        // This is prepared for when that feature is added
        const response = await fetch(API + '/api/dev/notices/' + noticeId, {
            method: 'DELETE',
            headers: {
                'Authorization': 'Bearer ' + getToken()
            }
        });
        
        if (!response.ok) {
            const err = await response.json().catch(() => ({ detail: 'Failed to delete' }));
            throw new Error(err.detail || 'Failed to delete notice');
        }
        
        toast('✅ Notice deleted successfully!', 'success');
        loadDevNotices(); // Reload the notices list
    } catch (e) {
        toast('❌ Error: ' + e.message, 'error');
    }
}

function showAddAdminForm() {
    show('add-admin-form');
    $('admin-fullname').focus();
}

function showAddDevForm() {
    show('add-dev-form');
    $('dev-fullname').focus();
}

async function createNewAdmin(e) {
    e.preventDefault();
    
    const adminData = {
        full_name: $('admin-fullname').value,
        username: $('admin-username').value,
        email: $('admin-email').value,
        password: $('admin-password').value,
        secret_key: $('admin-secret').value
    };
    
    // Validate inputs
    if (!adminData.full_name || !adminData.username || !adminData.email || !adminData.password || !adminData.secret_key) {
        toast('❌ All fields are required', 'error');
        return;
    }
    
    if (adminData.secret_key !== '2026') {
        toast('❌ Invalid secret key (must be 2026)', 'error');
        return;
    }
    
    try {
        $('admin-fullname').disabled = true;
        $('admin-username').disabled = true;
        $('admin-email').disabled = true;
        $('admin-password').disabled = true;
        $('admin-secret').disabled = true;
        
        console.log('[CreateAdmin] Sending data:', adminData);
        
        const result = await api('/api/dev/create-admin', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: adminData
        });
        
        console.log('[CreateAdmin] Success:', result);
        toast('✅ Admin created successfully!', 'success');
        hide('add-admin-form');
        loadManageAdmins();
    } catch (e) {
        console.error('[CreateAdmin] Error:', e);
        toast('❌ ' + (e.message || 'Failed to create admin'), 'error');
    } finally {
        $('admin-fullname').disabled = false;
        $('admin-username').disabled = false;
        $('admin-email').disabled = false;
        $('admin-password').disabled = false;
        $('admin-secret').disabled = false;
    }
}

async function createNewDeveloper(e) {
    e.preventDefault();
    
    const devData = {
        full_name: $('dev-fullname').value,
        email: $('dev-email-input').value,
        password: $('dev-password-input').value,
        secret_key: '2026'
    };
    
    // Validate inputs
    if (!devData.full_name || !devData.email || !devData.password) {
        toast('❌ All fields are required', 'error');
        return;
    }
    
    try {
        $('dev-fullname').disabled = true;
        $('dev-email-input').disabled = true;
        $('dev-password-input').disabled = true;
        
        console.log('[CreateDeveloper] Sending data:', devData);
        
        const result = await api('/api/dev/create-developer', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: devData
        });
        
        console.log('[CreateDeveloper] Success:', result);
        toast('✅ Developer created successfully!', 'success');
        hide('add-dev-form');
        loadManageDevelopers();
    } catch (e) {
        console.error('[CreateDeveloper] Error:', e);
        toast('❌ ' + (e.message || 'Failed to create developer'), 'error');
    } finally {
        $('dev-fullname').disabled = false;
        $('dev-email-input').disabled = false;
        $('dev-password-input').disabled = false;
    }
}

function devLogout() {
    TOKEN = null;
    USER = null;
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    localStorage.removeItem('dev-token');
    hide('dev-dashboard');
    show('auth-page');
    toast('✅ Logged out from Developer Portal', 'info');
}

function showLoginOptions() {
    hide('dev-login-page');
    show('auth-page');
}

function showLogin() {
    hide('dev-login-page');
    show('auth-page');
}

function showDevLogin() {
    hide('auth-page');
    show('dev-login-page');
}

// ═══ DELETE LOGS PAGE ═══
function loadDeleteLogsPage() {
    setActiveDev('dev-delete-logs-btn');
    
    $('dev-content').innerHTML = `
        <div class="flex items-center justify-between mb-20">
            <h2 class="heading-lg">🗑️ Delete Application Logs</h2>
        </div>
        
        <div class="card" style="max-width:600px">
            <h3 class="card-title mb-12">Delete Logs with Secret Code</h3>
            
            <form onsubmit="deleteLogs(event)" style="display:flex;flex-direction:column;gap:12px">
                <div>
                    <label class="label">Log Type</label>
                    <select id="log-type-select" style="width:100%;padding:8px;border:1px solid var(--border);border-radius:4px;background:var(--bg-secondary);color:#1F2937" required>
                        <option value="all">All Logs</option>
                        <option value="error">Error Logs Only</option>
                        <option value="app">Application Logs Only</option>
                        <option value="system">System/Backup Logs Only</option>
                    </select>
                </div>
                
                <div>
                    <label class="label">Secret Code</label>
                    <input type="password" id="log-delete-secret" placeholder="Enter secret code" 
                           style="width:100%;padding:8px;border:1px solid var(--border);border-radius:4px;background:var(--bg-secondary);color:#1F2937" required>
                </div>
                
                <div style="padding:12px;background:var(--bg-tertiary);border-radius:4px;margin:8px 0">
                    <strong style="color:#f59e0b">⚠️ Warning:</strong>
                    <p style="font-size:0.85rem;color:#6B7280;margin-top:4px">This action will permanently delete selected logs and cannot be undone. Make sure you have backups if needed.</p>
                </div>
                
                <button type="submit" class="btn btn-danger" style="margin-top:12px">🗑️ Delete Logs</button>
            </form>
        </div>
    `;
}

async function deleteLogs(e) {
    e.preventDefault();
    
    const logType = $('log-type-select').value;
    const secretCode = $('log-delete-secret').value;
    
    if (!secretCode) {
        toast('❌ Secret code is required', 'error');
        return;
    }
    
    try {
        const formData = new FormData();
        formData.append('secret_code', secretCode);
        formData.append('log_type', logType);
        
        const response = await fetch(API + '/api/dev/delete-logs', {
            method: 'POST',
            headers: {
                'Authorization': 'Bearer ' + getToken()
            },
            body: formData
        });
        
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Failed to delete logs');
        }
        
        const data = await response.json();
        toast('✅ ' + data.message + ' - ' + data.deleted_count + ' items deleted', 'success');
        
        // Reload the page after a short delay
        setTimeout(() => loadDeleteLogsPage(), 1000);
    } catch (e) {
        toast('❌ Error: ' + e.message, 'error');
    }
}


// ═══ BLOCKED USERS PAGE ═══
function loadBlockedUsersPage() {
    setActiveDev('dev-blocked-btn');
    
    api('/api/dev/blocked-users').then(blockedUsers => {
        $('dev-content').innerHTML = `
            <div class="flex items-center justify-between mb-20">
                <h2 class="heading-lg">🔒 Blocked Users & Admins</h2>
                <span class="badge badge-danger">${blockedUsers.length} Blocked</span>
            </div>
            
            ${blockedUsers.length === 0 ? `
                <div class="card" style="text-align:center;padding:40px">
                    <p style="font-size:1.1rem;color:#6B7280">✅ No blocked users or admins</p>
                </div>
            ` : `
                <div class="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>Username</th>
                                <th>Email</th>
                                <th>Full Name</th>
                                <th>Role</th>
                                <th>Blocked Reason</th>
                                <th>Blocked At</th>
                                <th>Action</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${blockedUsers.map(user => `
                                <tr>
                                    <td>${user.id}</td>
                                    <td><strong>${user.username}</strong></td>
                                    <td style="font-size:0.9rem">${user.email}</td>
                                    <td>${user.full_name}</td>
                                    <td><span class="badge badge-warning">${user.role}</span></td>
                                    <td style="font-size:0.9rem">${user.blocked_reason || 'N/A'}</td>
                                    <td style="font-size:0.85rem">${new Date(user.blocked_at).toLocaleString()}</td>
                                    <td>
                                        <button class="btn btn-outline btn-xs" 
                                                onclick="unblockUserModal(${user.id}, '${user.username}')">
                                            🔓 Unblock
                                        </button>
                                    </td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            `}
        `;
    }).catch(e => toast('Error: ' + e.message, 'error'));
}

function unblockUserModal(userId, username) {
    const secret = prompt(`\n🔓 Unblock User: ${username}\n\nEnter secret code to unblock:`, '');
    
    if (secret === null) return;
    
    if (!secret) {
        toast('❌ Secret code is required', 'error');
        return;
    }
    
    unblockUser(userId, secret);
}

async function unblockUser(userId, secretCode) {
    try {
        const formData = new FormData();
        formData.append('secret_code', secretCode);
        
        const response = await fetch(API + '/api/dev/unblock-user/' + userId, {
            method: 'POST',
            headers: {
                'Authorization': 'Bearer ' + getToken()
            },
            body: formData
        });
        
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Failed to unblock user');
        }
        
        const data = await response.json();
        toast('✅ ' + data.message, 'success');
        loadBlockedUsersPage();
    } catch (e) {
        toast('❌ Error: ' + e.message, 'error');
    }
}


// ═══ HEALTH CHECK PAGE ═══
function loadHealthCheckPage() {
    setActiveDev('dev-health-btn');
    
    $('dev-content').innerHTML = `
        <div class="flex items-center justify-between mb-20">
            <h2 class="heading-lg">💓 System Health Check</h2>
            <button class="btn btn-outline btn-sm" onclick="loadHealthCheckPage()">🔄 Refresh</button>
        </div>
        
        <div class="card" style="text-align:center;padding:40px">
            <p style="font-size:1.1rem;color:#6B7280">⏳ Running health checks...</p>
        </div>
    `;
    
    api('/api/dev/health-check').then(data => {
        const getStatusColor = (status) => {
            if (status === 'operational') return '#22c55e';
            if (status === 'warning') return '#f59e0b';
            return '#ef4444';
        };
        
        const getStatusBg = (status) => {
            if (status === 'operational') return '#dcfce7';
            if (status === 'warning') return '#fef3c7';
            return '#fee2e2';
        };
        
        let html = `
            <div class="grid-2 mb-20">
                <div class="card" style="border-left:4px solid ${getStatusColor(data.overall_status)};background:${getStatusBg(data.overall_status)}">
                    <div style="font-size:3rem;margin-bottom:10px">${
                        data.overall_status === 'healthy' ? '✅' :
                        data.overall_status === 'degraded' ? '⚠️' : '❌'
                    }</div>
                    <h3 style="font-size:1.3rem;text-transform:uppercase;font-weight:bold;margin-bottom:5px;color:${getStatusColor(data.overall_status)}">${data.overall_status}</h3>
                    <p style="color:#6B7280;font-size:0.9rem">Last checked: ${new Date(data.timestamp).toLocaleString()}</p>
                </div>
                
                <div class="card">
                    <h3 class="card-title mb-12">📊 Summary</h3>
                    <div style="display:flex;flex-direction:column;gap:8px">
                        <div style="display:flex;justify-content:space-between;padding:8px;background:var(--bg-tertiary);border-radius:4px">
                            <span style="color:#22c55e;font-weight:bold">✅ Passing:</span>
                            <span style="font-weight:bold">${data.summary.passing}</span>
                        </div>
                        <div style="display:flex;justify-content:space-between;padding:8px;background:var(--bg-tertiary);border-radius:4px">
                            <span style="color:#f59e0b;font-weight:bold">⚠️ Warning:</span>
                            <span style="font-weight:bold">${data.summary.warning}</span>
                        </div>
                        <div style="display:flex;justify-content:space-between;padding:8px;background:var(--bg-tertiary);border-radius:4px">
                            <span style="color:#ef4444;font-weight:bold">❌ Error:</span>
                            <span style="font-weight:bold">${data.summary.error}</span>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="heading-md mb-12">🔍 Component Status</div>
        `;
        
        // Add each component
        Object.entries(data.components).forEach(([key, component]) => {
            const bgColor = getStatusBg(component.status);
            const borderColor = getStatusColor(component.status);
            const componentName = key.replace(/_/g, ' ').toUpperCase();
            
            html += `
                <div class="card" style="border-left:4px solid ${borderColor};background:${bgColor};margin-bottom:12px">
                    <div style="display:flex;align-items:flex-start;gap:12px">
                        <div style="font-size:2rem">${component.icon}</div>
                        <div style="flex:1">
                            <h4 style="font-weight:bold;margin-bottom:4px;text-transform:capitalize">${key}</h4>
                            <p style="color:#6B7280;font-size:0.9rem;margin-bottom:6px">${component.message}</p>
                            <span class="badge badge-${component.status === 'operational' ? 'success' : component.status === 'warning' ? 'warning' : 'danger'}">${component.status.toUpperCase()}</span>
                            ${component.accessible_tables ? `
                                <div style="margin-top:8px;font-size:0.85rem;color:#6B7280">
                                    <strong>Tables:</strong> ${component.accessible_tables.join(', ')}
                                </div>
                            ` : ''}
                            ${component.unresolved_errors !== undefined ? `
                                <div style="margin-top:4px;font-size:0.85rem;color:#6B7280">
                                    <strong>Unresolved Errors:</strong> ${component.unresolved_errors}
                                </div>
                            ` : ''}
                            ${component.blocked_users !== undefined ? `
                                <div style="margin-top:4px;font-size:0.85rem;color:#6B7280">
                                    <strong>Blocked Users:</strong> ${component.blocked_users}
                                </div>
                            ` : ''}
                        </div>
                    </div>
                </div>
            `;
        });
        
        $('dev-content').innerHTML = `
            <div class="flex items-center justify-between mb-20">
                <h2 class="heading-lg">💓 System Health Check</h2>
                <button class="btn btn-outline btn-sm" onclick="loadHealthCheckPage()">🔄 Refresh</button>
            </div>
            
            ${html}
        `;
    }).catch(e => {
        toast('Error loading health check: ' + e.message, 'error');
        $('dev-content').innerHTML = `
            <div class="card" style="border:2px solid #ef4444;padding:20px">
                <p style="color:#ef4444;font-weight:bold">❌ Error Loading Health Check</p>
                <p style="color:#6B7280;margin-top:8px">${e.message}</p>
            </div>
        `;
    });
}

// ═══ Admin and Developer Management Functions ═══

async function toggleAdminStatus(adminId, isActive) {
    const action = isActive ? 'deactivate' : 'activate';
    
    if (!confirm(`Are you sure you want to ${action} this admin?`)) {
        return;
    }
    
    try {
        const endpoint = isActive ? 
            `/api/dev/deactivate-admin/${adminId}` : 
            `/api/dev/activate-admin/${adminId}`;
        
        console.log(`[ToggleAdmin] ${action} admin ${adminId}`);
        
        await api(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        toast(`✅ Admin ${action}d successfully!`, 'success');
        loadManageAdmins();
    } catch (e) {
        console.error(`[ToggleAdmin] Error:`, e);
        toast(`❌ Error: ${e.message}`, 'error');
    }
}

async function toggleDevStatus(devId, isActive) {
    const action = isActive ? 'deactivate' : 'activate';
    
    if (!confirm(`Are you sure you want to ${action} this developer?`)) {
        return;
    }
    
    try {
        const endpoint = isActive ? 
            `/api/dev/deactivate-developer/${devId}` : 
            `/api/dev/activate-developer/${devId}`;
        
        console.log(`[ToggleDev] ${action} developer ${devId}`);
        
        await api(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        toast(`✅ Developer ${action}d successfully!`, 'success');
        loadManageDevelopers();
    } catch (e) {
        console.error(`[ToggleDev] Error:`, e);
        toast(`❌ Error: ${e.message}`, 'error');
    }
}
