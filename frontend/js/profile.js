/* ═══ USER PROFILE PAGE ═══ */

async function loadProfilePage() {
    try {
        const userData = await api('/api/profile');
        
        let profileHTML = `
            <div class="profile-container">
                <!-- Header Section with Gradient -->
                <div class="profile-header">
                    <!-- Top Right Actions -->
                    <div class="profile-header-actions">
                        <button class="btn btn-outline" onclick="switchProfileTab('security')" style="color:white;border-color:rgba(255,255,255,0.5)">
                            🔐 Change Password
                        </button>
                        <button class="btn btn-danger" onclick="logout()">
                            🚪 Logout
                        </button>
                    </div>
                    
                    <!-- Main Content -->
                    <div class="profile-content">
                        <!-- Photo Section -->
                        <div class="profile-photo-section">
                            <div class="profile-photo-container">
                                ${userData.photo_path ? `
                                    <img src="/uploads/${userData.photo_path}" alt="Profile">
                                ` : `
                                    <div style="font-size:3rem">👤</div>
                                `}
                            </div>
                            <button class="profile-photo-btn" onclick="showPhotoUpload()">
                                📷 Change Photo
                            </button>
                        </div>
                        
                        <!-- User Info Section -->
                        <div class="profile-info-section">
                            <h1 class="profile-name">${userData.full_name}</h1>
                            
                            <div class="profile-badges">
                                <span class="profile-badge">
                                    <span>🏷️</span>
                                    <span>${userData.role.toUpperCase()}</span>
                                </span>
                                <span class="profile-badge">
                                    <span>📅</span>
                                    <span>Member for ${userData.days_active} days</span>
                                </span>
                            </div>
                            
                            <div class="profile-details">
                                <p>
                                    <span class="profile-detail-icon">✉️</span>
                                    <span>${userData.email}</span>
                                </p>
                                ${userData.phone ? `
                                    <p>
                                        <span class="profile-detail-icon">📞</span>
                                        <span>${userData.phone}</span>
                                    </p>
                                ` : ''}
                                ${userData.village ? `
                                    <p>
                                        <span class="profile-detail-icon">📍</span>
                                        <span>${userData.village}, ${userData.district}</span>
                                    </p>
                                ` : ''}
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Tabs Section -->
                <div style="max-width:1200px;margin:0 auto">
                    <div class="profile-tabs" id="profile-tabs-button-group">
                        <button class="profile-tab active" onclick="switchProfileTab('info')" id="tab-info-btn">
                            📋 Profile Info
                        </button>
                        <button class="profile-tab" onclick="switchProfileTab('security')" id="tab-security-btn">
                            🔐 Security
                        </button>
                        ${userData.role === 'worker' ? `
                            <button class="profile-tab" onclick="switchProfileTab('messages')" id="tab-messages-btn">
                                💬 Contact Admin
                            </button>
                        ` : ''}
                        ${userData.role === 'admin' ? `
                            <button class="profile-tab" onclick="switchProfileTab('admin-messages')" id="tab-admin-messages-btn">
                                📬 Worker Messages
                            </button>
                        ` : ''}
                    </div>

                    <!-- Tab Contents -->
                    <div id="profile-tabs">
                        <!-- Profile Info Tab -->
                        <div id="tab-info" class="profile-section active">
                            <div class="grid-2">
                                <div class="card">
                                    <h3 class="card-title mb-12">👤 Personal Information</h3>
                                    <form style="display:flex;flex-direction:column;gap:12px">
                                        <div>
                                            <label class="label">Full Name</label>
                                            <input type="text" value="${userData.full_name}" disabled style="width:100%;padding:8px;border:1px solid var(--border);border-radius:4px;background:var(--bg-tertiary);color:#6b9bff">
                                        </div>
                                        <div>
                                            <label class="label">Phone Number</label>
                                            <input type="text" value="${userData.phone || 'N/A'}" disabled style="width:100%;padding:8px;border:1px solid var(--border);border-radius:4px;background:var(--bg-tertiary);color:#6b9bff">
                                        </div>
                                        <div>
                                            <label class="label">Email</label>
                                            <input type="email" value="${userData.email}" disabled style="width:100%;padding:8px;border:1px solid var(--border);border-radius:4px;background:var(--bg-tertiary);color:#6b9bff">
                                        </div>
                                        ${userData.village ? `
                                            <div>
                                                <label class="label">Location</label>
                                                <input type="text" value="${userData.village}, ${userData.district}, ${userData.state}" disabled style="width:100%;padding:8px;border:1px solid var(--border);border-radius:4px;background:var(--bg-tertiary);color:#6b9bff">
                                            </div>
                                        ` : ''}
                                    </form>
                                </div>

                                <div class="card">
                                    <h3 class="card-title mb-12">ℹ️ Account Details</h3>
                                    <div style="display:flex;flex-direction:column;gap:12px">
                                        <div style="padding:12px;background:var(--bg-secondary);border-radius:6px">
                                            <p style="margin:0;color:#6b9bff;font-size:0.9rem">Account Type</p>
                                            <p style="margin:0;font-size:1.1rem;font-weight:bold;text-transform:capitalize">${userData.role}</p>
                                        </div>
                                        <div style="padding:12px;background:var(--bg-secondary);border-radius:6px">
                                            <p style="margin:0;color:#6b9bff;font-size:0.9rem">Member Since</p>
                                            <p style="margin:0;font-size:1.1rem;font-weight:bold">${new Date(userData.created_at).toLocaleDateString()}</p>
                                        </div>
                                        <div style="padding:12px;background:var(--bg-secondary);border-radius:6px">
                                            <p style="margin:0;color:#6b9bff;font-size:0.9rem">Last Login</p>
                                            <p style="margin:0;font-size:1.1rem;font-weight:bold">${userData.last_login ? new Date(userData.last_login).toLocaleString() : 'Never'}</p>
                                        </div>
                                        <div style="padding:12px;background:var(--bg-secondary);border-radius:6px">
                                            <p style="margin:0;color:#6b9bff;font-size:0.9rem">Account Status</p>
                                            <p style="margin:0;font-size:1.1rem;font-weight:bold">
                                                ${userData.is_active ? '✅ Active' : '❌ Inactive'}
                                            </p>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- Security Tab -->
                        <div id="tab-security" class="profile-section">
                            <div class="card" style="max-width:600px">
                                <h3 class="card-title mb-12">🔐 Change Password</h3>
                                <form onsubmit="changePassword(event)" style="display:flex;flex-direction:column;gap:12px">
                                    <div>
                                        <label class="label">Current Password</label>
                                        <input type="password" id="current-password" placeholder="Enter current password" style="width:100%;padding:10px;border:1px solid var(--border);border-radius:4px;background:var(--bg-secondary);color:var(--text-primary)" required>
                                    </div>
                                    <div>
                                        <label class="label">New Password</label>
                                        <input type="password" id="new-password" placeholder="Enter new password" style="width:100%;padding:10px;border:1px solid var(--border);border-radius:4px;background:var(--bg-secondary);color:var(--text-primary)" required>
                                    </div>
                                    <div>
                                        <label class="label">Confirm Password</label>
                                        <input type="password" id="confirm-password" placeholder="Confirm new password" style="width:100%;padding:10px;border:1px solid var(--border);border-radius:4px;background:var(--bg-secondary);color:var(--text-primary)" required>
                                    </div>
                                    <div style="padding:12px;background:#fef3c7;border-radius:6px;border-left:4px solid #f59e0b">
                                        <p style="margin:0;color:#92400e;font-size:0.9rem">
                                            <strong>⚠️ Security Note:</strong> Keep your password strong and unique. Never share it with anyone.
                                        </p>
                                    </div>
                                    <button type="submit" class="btn btn-primary" style="margin-top:12px">🔐 Change Password</button>
                                </form>
                            </div>
                        </div>

                        ${userData.role === 'worker' ? `
                            <!-- Worker Messages Tab -->
                            <div id="tab-messages" class="profile-section">
                                <div class="card" style="max-width:800px">
                                    <h3 class="card-title mb-12">💬 Send Message to Admin</h3>
                                    <form onsubmit="sendMessageToAdmin(event)" style="display:flex;flex-direction:column;gap:12px;margin-bottom:24px">
                                        <div>
                                            <label class="label">Your Message</label>
                                            <textarea id="worker-message" placeholder="Type your message here..." style="width:100%;height:120px;padding:10px;border:1px solid var(--border);border-radius:4px;background:var(--bg-secondary);color:var(--text-primary);font-family:inherit;resize:vertical" required></textarea>
                                        </div>
                                        <button type="submit" class="btn btn-primary">📤 Send Message</button>
                                    </form>

                                    <h3 class="card-title mb-12">📬 Your Messages</h3>
                                    <div id="worker-messages-list">
                                        <p style="color:#6b9bff;text-align:center;padding:20px">⏳ Loading messages...</p>
                                    </div>
                                </div>
                            </div>
                        ` : ''}

                        ${userData.role === 'admin' ? `
                            <!-- Admin Messages Tab -->
                            <div id="tab-admin-messages" class="profile-section">
                                <div class="card">
                                    <h3 class="card-title mb-12">📬 Worker Messages</h3>
                                    <div id="admin-messages-list">
                                        <p style="color:#6b9bff;text-align:center;padding:20px">⏳ Loading messages...</p>
                                    </div>
                                </div>
                            </div>
                        ` : ''}
                    </div>
                </div>
            </div>

            <!-- Photo Upload Modal -->
            <div id="photo-upload-modal" class="modal hidden" style="position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.7);display:flex;align-items:center;justify-content:center;z-index:1000">
                <div class="card" style="width:90%;max-width:500px;padding:30px">
                    <h3 style="margin-top:0">📷 Upload Profile Photo</h3>
                    <form onsubmit="uploadProfilePhoto(event)" style="display:flex;flex-direction:column;gap:12px">
                        <div style="border:2px dashed var(--border);border-radius:8px;padding:30px;text-align:center;cursor:pointer" id="photo-drop-zone" onclick="$('file-input').click()">
                            <p style="margin:0;color:#6b9bff">📁 Drop image here or click to select</p>
                            <input type="file" id="file-input" accept="image/*" style="display:none" onchange="handlePhotoSelect(event)" required>
                        </div>
                        <div id="photo-preview" style="display:none;text-align:center">
                            <img id="preview-img" style="max-width:100%;max-height:300px;border-radius:8px;margin-bottom:12px">
                            <p id="file-name-display" style="font-size:0.9rem;color:#6b9bff"></p>
                        </div>
                        <div style="display:flex;gap:12px;margin-top:12px">
                            <button type="submit" class="btn btn-primary" style="flex:1">✅ Upload</button>
                            <button type="button" class="btn btn-outline" style="flex:1" onclick="closePhotoModal()">❌ Cancel</button>
                        </div>
                    </form>
                </div>
            </div>
        `;
        
        $('main-content').innerHTML = profileHTML;
        
        // Load worker messages if needed
        if (userData.role === 'worker') {
            await loadWorkerMessages();
        }
        
        // Load admin messages if needed
        if (userData.role === 'admin') {
            await loadAdminMessages();
        }
        
    } catch (e) {
        toast('Error loading profile: ' + e.message, 'error');
        $('main-content').innerHTML = `<div class="card" style="padding:40px;text-align:center"><p style="color:var(--text-danger)">❌ Error loading profile</p></div>`;
    }
}

function switchProfileTab(tabName) {
    // Hide all tabs and reset buttons
    document.querySelectorAll('.profile-section').forEach(tab => tab.classList.remove('active'));
    document.querySelectorAll('.profile-tab').forEach(btn => btn.classList.remove('active'));
    
    // Show selected tab and activate button
    const tabId = `tab-${tabName}`;
    const btnId = `tab-${tabName}-btn`;
    
    const tab = document.getElementById(tabId);
    const btn = document.getElementById(btnId);
    
    if (tab) {
        tab.classList.add('active');
    }
    if (btn) {
        btn.classList.add('active');
    }
}

// Profile info update disabled - name and phone are fixed by admin
// updateProfileInfo() function removed

async function changePassword(e) {
    e.preventDefault();
    
    const oldPassword = $('current-password').value;
    const newPassword = $('new-password').value;
    const confirmPassword = $('confirm-password').value;
    
    if (newPassword !== confirmPassword) {
        toast('❌ Passwords do not match', 'error');
        return;
    }
    
    if (newPassword.length < 6) {
        toast('❌ Password must be at least 6 characters', 'error');
        return;
    }
    
    try {
        const formData = new FormData();
        formData.append('old_password', oldPassword);
        formData.append('new_password', newPassword);
        formData.append('confirm_password', confirmPassword);
        
        const response = await fetch(API + '/api/profile/change-password', {
            method: 'POST',
            headers: {
                'Authorization': 'Bearer ' + getToken()
            },
            body: formData
        });
        
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Failed to change password');
        }
        
        toast('✅ Password changed successfully!', 'success');
        $('current-password').value = '';
        $('new-password').value = '';
        $('confirm-password').value = '';
    } catch (e) {
        toast('❌ Error: ' + e.message, 'error');
    }
}

function showPhotoUpload() {
    $('photo-upload-modal').classList.remove('hidden');
    $('photo-upload-modal').style.display = 'flex';
}

function closePhotoModal() {
    $('photo-upload-modal').classList.add('hidden');
    $('photo-upload-modal').style.display = 'none';
    $('file-input').value = '';
    $('photo-preview').style.display = 'none';
}

function handlePhotoSelect(e) {
    const file = e.target.files[0];
    if (!file) return;
    
    const reader = new FileReader();
    reader.onload = (event) => {
        $('preview-img').src = event.target.result;
        $('file-name-display').textContent = file.name;
        $('photo-preview').style.display = 'block';
    };
    reader.readAsDataURL(file);
}

async function uploadProfilePhoto(e) {
    e.preventDefault();
    
    const file = $('file-input').files[0];
    if (!file) {
        toast('❌ Please select a file', 'error');
        return;
    }
    
    try {
        const formData = new FormData();
        formData.append('file', file);
        
        const response = await fetch(API + '/api/profile/upload-photo', {
            method: 'POST',
            headers: {
                'Authorization': 'Bearer ' + getToken()
            },
            body: formData
        });
        
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Failed to upload photo');
        }
        
        toast('✅ Photo uploaded successfully!', 'success');
        closePhotoModal();
        setTimeout(() => loadProfilePage(), 500);
    } catch (e) {
        toast('❌ Error: ' + e.message, 'error');
    }
}

async function sendMessageToAdmin(e) {
    e.preventDefault();
    
    const message = $('worker-message').value;
    if (!message.trim()) {
        toast('❌ Please enter a message', 'error');
        return;
    }
    
    try {
        const formData = new FormData();
        formData.append('message_text', message);
        
        const response = await fetch(API + '/api/worker/send-message', {
            method: 'POST',
            headers: {
                'Authorization': 'Bearer ' + getToken()
            },
            body: formData
        });
        
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Failed to send message');
        }
        
        toast('✅ Message sent successfully!', 'success');
        $('worker-message').value = '';
        await loadWorkerMessages();
    } catch (e) {
        toast('❌ Error: ' + e.message, 'error');
    }
}

async function loadWorkerMessages() {
    try {
        const messages = await api('/api/messages');
        
        if (messages.length === 0) {
            $('worker-messages-list').innerHTML = `
                <div style="text-align:center;padding:40px;color:#6b9bff">
                    <p style="font-size:1.1rem">📭 No messages yet</p>
                </div>
            `;
            return;
        }
        
        let html = '';
        messages.forEach(msg => {
            html += `
                <div class="card" style="margin-bottom:12px">
                    <div style="display:flex;justify-content:space-between;align-items:start;margin-bottom:12px">
                        <div>
                            <p style="margin:0;font-weight:bold">Your Message</p>
                            <p style="margin:0;font-size:0.9rem;color:#6b9bff">${new Date(msg.created_at).toLocaleString()}</p>
                        </div>
                        ${msg.replied_at ? `<span class="badge badge-success">✅ Replied</span>` : `<span class="badge badge-warning">⏳ Awaiting Reply</span>`}
                    </div>
                    <div style="padding:12px;background:var(--bg-secondary);border-radius:6px;margin-bottom:12px">
                        <p style="margin:0;word-wrap:break-word">${msg.message_text}</p>
                    </div>
                    ${msg.reply_text ? `
                        <div style="padding:12px;background:var(--bg-tertiary);border-left:4px solid var(--primary);border-radius:6px">
                            <p style="margin:0;font-weight:bold;color:var(--primary)">📨 Admin's Reply</p>
                            <p style="margin:8px 0 0 0;word-wrap:break-word">${msg.reply_text}</p>
                            <p style="margin:8px 0 0 0;font-size:0.85rem;color:#6b9bff">${new Date(msg.replied_at).toLocaleString()}</p>
                        </div>
                    ` : `
                        <p style="margin:0;color:#6b9bff;font-size:0.9rem">⏳ Waiting for admin reply...</p>
                    `}
                </div>
            `;
        });
        
        $('worker-messages-list').innerHTML = html;
    } catch (e) {
        $('worker-messages-list').innerHTML = `<p style="color:var(--text-danger)">Error loading messages: ${e.message}</p>`;
    }
}

async function loadAdminMessages() {
    try {
        const messages = await api('/api/messages');
        
        if (messages.length === 0) {
            $('admin-messages-list').innerHTML = `
                <div style="text-align:center;padding:40px;color:#6b9bff">
                    <p style="font-size:1.1rem">📭 No messages from workers</p>
                </div>
            `;
            return;
        }
        
        let html = `<div style="display:flex;flex-direction:column;gap:12px">`;
        messages.forEach(msg => {
            html += `
                <div class="card">
                    <div style="display:flex;justify-content:space-between;align-items:start;margin-bottom:12px">
                        <div>
                            <p style="margin:0;font-weight:bold">From: ${msg.full_name}</p>
                            <p style="margin:0;font-size:0.85rem;color:#6b9bff">
                                📧 ${msg.email} | 📞 ${msg.phone || 'N/A'} | 📍 ${msg.village}, ${msg.district}
                            </p>
                            <p style="margin:0;font-size:0.85rem;color:#6b9bff">${new Date(msg.created_at).toLocaleString()}</p>
                        </div>
                        <div style="display:flex;gap:8px;align-items:center">
                            ${msg.is_read ? `<span class="badge badge-success">✅ Read</span>` : `<span class="badge badge-warning">🔴 Unread</span>`}
                            <button class="btn btn-sm" onclick="clearChat(${msg.worker_id})" style="background:#ef4444;color:white;padding:6px 12px;font-size:0.85rem;border:none;border-radius:4px;cursor:pointer">🗑️ Clear</button>
                        </div>
                    </div>
                    <div style="padding:12px;background:var(--bg-secondary);border-radius:6px;margin-bottom:12px">
                        <p style="margin:0;word-wrap:break-word">${msg.message_text}</p>
                    </div>
                    ${msg.reply_text ? `
                        <div style="padding:12px;background:var(--bg-tertiary);border-left:4px solid var(--success);border-radius:6px;margin-bottom:12px">
                            <p style="margin:0;font-weight:bold;color:var(--success)">✅ Your Reply</p>
                            <p style="margin:8px 0 0 0;word-wrap:break-word">${msg.reply_text}</p>
                            <p style="margin:8px 0 0 0;font-size:0.85rem;color:#6b9bff">${new Date(msg.replied_at).toLocaleString()}</p>
                        </div>
                    ` : `
                        <form onsubmit="replyToMessage(event, ${msg.id})" style="display:flex;gap:8px;margin-bottom:12px">
                            <textarea id="reply-${msg.id}" placeholder="Type your reply..." style="flex:1;height:80px;padding:10px;border:1px solid var(--border);border-radius:4px;background:var(--bg-secondary);color:var(--text-primary);font-family:inherit;resize:vertical" required></textarea>
                            <button type="submit" class="btn btn-primary" style="align-self:flex-end">📤 Reply</button>
                        </form>
                    `}
                </div>
            `;
        });
        html += '</div>';
        
        $('admin-messages-list').innerHTML = html;
    } catch (e) {
        $('admin-messages-list').innerHTML = `<p style="color:var(--text-danger)">Error loading messages: ${e.message}</p>`;
    }
}

async function replyToMessage(e, messageId) {
    e.preventDefault();
    
    const replyText = $(`reply-${messageId}`).value;
    if (!replyText.trim()) {
        toast('❌ Please enter a reply', 'error');
        return;
    }
    
    try {
        const formData = new FormData();
        formData.append('reply_text', replyText);
        
        const response = await fetch(API + `/api/message/${messageId}/reply`, {
            method: 'POST',
            headers: {
                'Authorization': 'Bearer ' + getToken()
            },
            body: formData
        });
        
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Failed to send reply');
        }
        
        toast('✅ Reply sent successfully!', 'success');
        await loadAdminMessages();
    } catch (e) {
        toast('❌ Error: ' + e.message, 'error');
    }
}

// Clear chat between admin and worker
async function clearChat(workerId) {
    if (!confirm('🗑️ Are you sure you want to clear this entire conversation? This action cannot be undone.')) {
        return;
    }
    
    try {
        const response = await fetch(API + `/api/message/clear-chat/${workerId}`, {
            method: 'DELETE',
            headers: {
                'Authorization': 'Bearer ' + getToken()
            }
        });
        
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Failed to clear chat');
        }
        
        toast('✅ Chat cleared successfully!', 'success');
        await loadAdminMessages();
    } catch (e) {
        toast('❌ Error: ' + e.message, 'error');
    }
}
