/* ═══ ADMIN VIEWS ═══ */

function buildAdminSidebar() {
    $('sidebar').innerHTML = `
        <div class="sidebar-section">Main</div>
        <ul class="sidebar-nav">
            <li class="sidebar-item"><a class="sidebar-link active" onclick="loadAdminDashboard()" id="sb-dash"><span class="icon">📊</span> Dashboard</a></li>
            <li class="sidebar-item"><a class="sidebar-link" onclick="loadAdminReports()" id="sb-reports"><span class="icon">📋</span> All Reports</a></li>
            <li class="sidebar-item"><a class="sidebar-link" onclick="loadAdminWorkers()" id="sb-workers"><span class="icon">👷</span> Workers</a></li>
        </ul>
        <div class="sidebar-section">Analytics</div>
        <ul class="sidebar-nav">
            <li class="sidebar-item"><a class="sidebar-link" onclick="loadAdminTrends()" id="sb-trends"><span class="icon">📈</span> Trend Analytics</a></li>
            <li class="sidebar-item"><a class="sidebar-link" onclick="loadAdminWater()" id="sb-water"><span class="icon">💧</span> Water Sources</a></li>
            <li class="sidebar-item"><a class="sidebar-link" onclick="loadAdminPredictions()" id="sb-pred"><span class="icon">🤖</span> AI Predictions</a></li>
        </ul>
        <div class="sidebar-section">Management</div>
        <ul class="sidebar-nav">
            <li class="sidebar-item"><a class="sidebar-link" onclick="loadAdminFlagged()" id="sb-flagged"><span class="icon">🚩</span> Flagged Reports</a></li>
            <li class="sidebar-item"><a class="sidebar-link" onclick="loadAdminPerformance()" id="sb-perf"><span class="icon">⭐</span> Worker Stats</a></li>
            <li class="sidebar-item"><a class="sidebar-link" onclick="loadAdminAlerts()" id="sb-alerts"><span class="icon">🔔</span> Send Alerts</a></li>
            <li class="sidebar-item"><a class="sidebar-link" onclick="loadAdminNotices()" id="sb-notices"><span class="icon">📢</span> Notices</a></li>
            <li class="sidebar-item"><a class="sidebar-link" onclick="loadAdminExport()" id="sb-export"><span class="icon">📥</span> Export Data</a></li>
            <li class="sidebar-item"><a class="sidebar-link" onclick="loadAdminDataManagement()" id="sb-data"><span class="icon">🗑️</span> Data Management</a></li>
        </ul>`;
}

function setActiveSidebar(id) {
    document.querySelectorAll('.sidebar-link').forEach(l => l.classList.remove('active'));
    $(id)?.classList.add('active');
}

async function refreshGroqStatus(probe = true) {
    const badge = $('groq-status-badge');
    if (!badge) return;

    badge.className = 'badge badge-blue';
    badge.textContent = 'Checking...';

    try {
        const q = probe ? '?probe=1' : '';
        const data = await api('/api/admin/integrations/groq-status' + q);

        if (data.configured && data.reachable === true) {
            badge.className = 'badge badge-green';
            badge.textContent = 'Groq: Connected';
            return;
        }

        if (!data.configured) {
            badge.className = 'badge badge-red';
            badge.textContent = 'Groq: Not Configured';
            return;
        }

        const msg = (data.probe_message || '').toLowerCase();
        if (msg.includes('401') || msg.includes('403') || msg.includes('invalid')) {
            badge.className = 'badge badge-red';
            badge.textContent = 'Groq: Invalid Key';
            return;
        }

        badge.className = 'badge badge-red';
        badge.textContent = 'Groq: Unreachable';
    } catch (_) {
        badge.className = 'badge badge-red';
        badge.textContent = 'Groq: Error';
    }
}

async function loadAdminDashboard() {
    setActiveSidebar('sb-dash');
    $('main-content').innerHTML = '<div class="text-center mt-24"><div class="loading-spinner"></div></div>';
    try {
        const d = await api('/api/admin/dashboard');
        $('main-content').innerHTML = `
            <div class="flex items-center justify-between mb-20">
                <h2 class="heading-lg">📊 <span class="heading-text">Outbreak Dashboard</span></h2>
                <div class="flex items-center gap-8">
                    <span id="groq-status-badge" class="badge badge-blue">Checking...</span>
                    <button class="btn btn-outline btn-sm" onclick="refreshGroqStatus(true)">Check AI</button>
                </div>
            </div>
            <div class="grid-4 mb-24">
                <div class="stat-card blue"><div class="stat-icon">📋</div><div class="stat-number">${d.total_reports}</div><div class="stat-label">Total Reports</div></div>
                <div class="stat-card emerald"><div class="stat-icon">👷</div><div class="stat-number">${d.total_workers}</div><div class="stat-label">Health Workers</div></div>
                <div class="stat-card amber"><div class="stat-icon">⏳</div><div class="stat-number">${d.pending_workers}</div><div class="stat-label">Pending Approval</div></div>
                <div class="stat-card rose"><div class="stat-icon">🚩</div><div class="stat-number">${d.flagged_reports}</div><div class="stat-label">Flagged Reports</div></div>
            </div>
            <div class="grid-2 mb-24">
                <div class="card">
                    <div class="card-header"><h3 class="card-title">🏘️ Village Risk Map</h3></div>
                    <div id="village-risks">${d.village_risks.length === 0 ? '<div class="empty-state"><div class="empty-icon">🏘️</div><p class="empty-title">No data yet</p></div>' :
                        d.village_risks.map(v => `
                            <div class="feed-item" style="border-left:3px solid var(--risk-${v.risk_level})">
                                <div class="flex items-center justify-between mb-8">
                                    <strong>${v.village}</strong> ${riskBadge(v.risk_level)}
                                </div>
                                <div style="font-size:0.78rem;color:var(--text-muted)">${v.district} • ${v.report_count} cases • Score: ${v.risk_score}</div>
                                <div class="progress-bar mt-8"><div class="progress-fill ${v.risk_level}" style="width:${v.risk_score}%"></div></div>
                            </div>`).join('')}</div>
                </div>
                <div class="card">
                    <div class="card-header"><h3 class="card-title">📊 Severity Distribution</h3></div>
                    <div class="chart-container"><canvas id="severity-chart"></canvas></div>
                </div>
            </div>
            <div class="card mb-24">
                <div class="card-header"><h3 class="card-title">🕐 Recent Reports</h3></div>
                <div class="table-container"><table><thead><tr>
                    <th>Patient</th><th>Village</th><th>District</th><th>Symptoms</th><th>Severity</th><th>Worker</th><th>Time</th>
                </tr></thead><tbody>${d.recent_reports.map(r => `<tr>
                    <td>${r.patient_name}</td><td>${r.village}</td><td>${r.district}</td>
                    <td class="truncate" style="max-width:200px">${r.symptoms}</td>
                    <td>${severityBadge(r.severity)}</td><td>${r.worker_name || '-'}</td>
                    <td style="font-size:0.75rem;color:var(--text-muted)">${timeAgo(r.created_at)}</td>
                </tr>`).join('')}</tbody></table></div>
            </div>`;
        // Severity chart
        const sev = d.severity_stats || {};
        new Chart($('severity-chart'), {
            type: 'doughnut',
            data: {
                labels: ['Low', 'Medium', 'High', 'Critical'],
                datasets: [{ data: [sev.low||0, sev.medium||0, sev.high||0, sev.critical||0],
                    backgroundColor: ['#22c55e', '#eab308', '#f97316', '#ef4444'],
                    borderWidth: 0 }]
            },
            options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { labels: { color: '#94a3b8' } } } }
        });

        refreshGroqStatus(true);
    } catch (err) { toast('❌ ' + err.message, 'error'); }
}

async function loadAdminReports() {
    setActiveSidebar('sb-reports');
    $('main-content').innerHTML = '<div class="text-center mt-24"><div class="loading-spinner"></div></div>';
    try {
        const reports = await api('/api/admin/reports');
        $('main-content').innerHTML = `
            <div class="flex items-center justify-between mb-20">
                <h2 class="heading-lg">📋 <span class="heading-text">All Health Reports</span></h2>
                <span class="badge badge-blue">${reports.length} reports</span>
            </div>
            <div class="flex gap-12 mb-16">
                <input class="form-control" style="max-width:250px" placeholder="🔍 Filter by village..." oninput="filterReportsTable(this.value)">
            </div>
            <div class="table-container"><table id="reports-table"><thead><tr>
                <th>#</th><th>Patient</th><th>Age</th><th>Village</th><th>District</th><th>Symptoms</th><th>Disease</th><th>Severity</th><th>Worker</th><th>Flagged</th><th>Time</th>
            </tr></thead><tbody>${reports.map(r => `<tr class="report-row" data-village="${(r.village||'').toLowerCase()}">
                <td>${r.id}</td><td>${r.patient_name}</td><td>${r.patient_age||'-'}</td><td>${r.village}</td><td>${r.district}</td>
                <td class="truncate" style="max-width:180px">${r.symptoms}</td><td>${r.disease_suspected||'-'}</td>
                <td>${severityBadge(r.severity)}</td><td>${r.worker_name||'-'}</td>
                <td>${r.is_flagged ? '🚩' : '✅'}</td><td style="font-size:0.72rem">${timeAgo(r.created_at)}</td>
            </tr>`).join('')}</tbody></table></div>`;
    } catch (err) { toast('❌ ' + err.message, 'error'); }
}

function filterReportsTable(val) {
    document.querySelectorAll('.report-row').forEach(r => {
        r.style.display = r.dataset.village.includes(val.toLowerCase()) ? '' : 'none';
    });
}

async function loadAdminWorkers() {
    setActiveSidebar('sb-workers');
    try {
        const workers = await api('/api/admin/workers');
        $('main-content').innerHTML = `
            <h2 class="heading-lg mb-20">👷 <span class="heading-text">Health Workers</span></h2>
            <div class="table-container"><table><thead><tr>
                <th>Name</th><th>Username</th><th>Village</th><th>District</th><th>Status</th><th>Last Login</th><th>Actions</th>
            </tr></thead><tbody>${workers.map(w => `<tr>
                <td>${w.full_name}</td><td>${w.username}</td><td>${w.village||'-'}</td><td>${w.district||'-'}</td>
                <td>${w.is_approved ? '<span class="badge badge-green">Approved</span>' : '<span class="badge badge-yellow">Pending</span>'}</td>
                <td style="font-size:0.72rem">${w.last_login ? timeAgo(w.last_login) : 'Never'}</td>
                <td>${!w.is_approved ? `<button class="btn btn-success btn-sm" onclick="approveWorker(${w.id})">✅ Approve</button>
                    <button class="btn btn-danger btn-sm" onclick="rejectWorker(${w.id})">❌ Reject</button>` : '<span style="color:var(--text-muted);font-size:0.8rem">Active</span>'}</td>
            </tr>`).join('')}</tbody></table></div>`;
    } catch (err) { toast('❌ ' + err.message, 'error'); }
}

async function approveWorker(id) {
    try { await api('/api/admin/workers/'+id+'/approve', {method:'POST'}); toast('✅ Worker approved!','success'); loadAdminWorkers(); }
    catch(e) { toast('❌ '+e.message,'error'); }
}
async function rejectWorker(id) {
    if (!confirm('Reject this worker?')) return;
    try { await api('/api/admin/workers/'+id+'/reject', {method:'POST'}); toast('Worker rejected','warning'); loadAdminWorkers(); }
    catch(e) { toast('❌ '+e.message,'error'); }
}

async function loadAdminTrends() {
    setActiveSidebar('sb-trends');
    try {
        const d = await api('/api/admin/trends?days=30');
        $('main-content').innerHTML = `
            <h2 class="heading-lg mb-20">📈 <span class="heading-text">Trend Analytics</span></h2>
            <div class="card mb-24"><div class="card-header"><h3 class="card-title">Daily Cases (Last 30 Days)</h3></div>
                <div class="chart-container"><canvas id="trend-chart"></canvas></div></div>
            <div class="card"><div class="card-header"><h3 class="card-title">Disease Breakdown</h3></div>
                <div class="chart-container"><canvas id="disease-chart"></canvas></div></div>`;
        new Chart($('trend-chart'), { type: 'line', data: {
            labels: d.daily_cases.map(c => c.date.slice(5)),
            datasets: [{ label: 'Cases', data: d.daily_cases.map(c => c.cases), borderColor: '#3b82f6',
                backgroundColor: 'rgba(59,130,246,0.1)', fill: true, tension: 0.4 }]
        }, options: { responsive: true, maintainAspectRatio: false, plugins:{legend:{labels:{color:'#94a3b8'}}},
            scales:{x:{ticks:{color:'#64748b'}},y:{ticks:{color:'#64748b'},beginAtZero:true}} }});
        if (d.disease_breakdown.length) {
            new Chart($('disease-chart'), { type: 'bar', data: {
                labels: d.disease_breakdown.map(x => x.disease_suspected),
                datasets: [{ label: 'Cases', data: d.disease_breakdown.map(x => x.c),
                    backgroundColor: ['#3b82f6','#8b5cf6','#06b6d4','#10b981','#f59e0b','#ef4444','#ec4899'] }]
            }, options: { responsive: true, maintainAspectRatio: false, indexAxis:'y',
                plugins:{legend:{display:false}}, scales:{x:{ticks:{color:'#64748b'}},y:{ticks:{color:'#94a3b8'}}} }});
        }
    } catch(e) { toast('❌ '+e.message,'error'); }
}

async function loadAdminWater() {
    setActiveSidebar('sb-water');
    try {
        const sources = await api('/api/admin/water-sources');
        $('main-content').innerHTML = `
            <h2 class="heading-lg mb-20">💧 <span class="heading-text">Water Source Analysis</span></h2>
            ${sources.length===0?'<div class="empty-state"><div class="empty-icon">💧</div><p class="empty-title">No water source data yet</p></div>':
            `<div class="grid-3">${sources.map(s => `
                <div class="card" style="border-left:3px solid var(--risk-${s.status==='contaminated'?'red':s.status==='warning'?'yellow':'green'})">
                    <h3 style="font-size:1rem;margin-bottom:8px">${s.water_source||'Unknown'}</h3>
                    <p style="font-size:0.8rem;color:var(--text-muted);margin-bottom:8px">${s.village} — ${s.district}</p>
                    <div class="flex items-center gap-8 mb-8">${riskBadge(s.status==='contaminated'?'red':s.status==='warning'?'yellow':'green')}</div>
                    <div style="font-size:0.8rem">Linked cases: <strong>${s.linked_cases}</strong></div>
                    <div style="font-size:0.8rem">Contamination Score: <strong>${s.contamination_score}%</strong></div>
                    <div class="progress-bar mt-8"><div class="progress-fill ${s.status==='contaminated'?'red':s.status==='warning'?'yellow':'green'}" style="width:${s.contamination_score}%"></div></div>
                </div>`).join('')}</div>`}`;
    } catch(e) { toast('❌ '+e.message,'error'); }
}

async function loadAdminPredictions() {
    setActiveSidebar('sb-pred');
    try {
        const preds = await api('/api/predictions');
        $('main-content').innerHTML = `
            <h2 class="heading-lg mb-20">🤖 <span class="heading-text">AI Outbreak Predictions</span></h2>
            ${preds.length===0?'<div class="empty-state"><div class="empty-icon">🤖</div><p class="empty-title">No predictions yet. Predictions are generated when workers submit reports.</p></div>':
            `<div class="grid-3">${preds.map(p => {
                let factors = []; try { factors = JSON.parse(p.factors||'[]'); } catch(e){}
                return `<div class="card" style="border-top:3px solid var(--risk-${p.risk_level})">
                    <div class="flex items-center justify-between mb-12">${riskBadge(p.risk_level)}<span style="font-size:0.75rem;color:var(--text-muted)">${p.prediction_date}</span></div>
                    <h3 style="font-size:1rem">${p.village}</h3>
                    <p style="font-size:0.8rem;color:var(--text-muted)">${p.district}</p>
                    <div style="font-size:1.5rem;font-weight:800;margin:8px 0">${p.risk_score}%</div>
                    <div class="progress-bar mb-8"><div class="progress-fill ${p.risk_level}" style="width:${p.risk_score}%"></div></div>
                    ${factors.map(f => `<div style="font-size:0.75rem;color:var(--text-secondary);padding:2px 0">• ${f}</div>`).join('')}
                </div>`;}).join('')}</div>`}`;
    } catch(e) { toast('❌ '+e.message,'error'); }
}

async function loadAdminFlagged() {
    setActiveSidebar('sb-flagged');
    try {
        const reports = await api('/api/admin/flagged-reports');
        $('main-content').innerHTML = `
            <h2 class="heading-lg mb-20">🚩 <span class="heading-text">Flagged / Suspicious Reports</span></h2>
            ${reports.length===0?'<div class="empty-state"><div class="empty-icon">✅</div><p class="empty-title">No flagged reports</p></div>':
            `<div class="table-container"><table><thead><tr><th>ID</th><th>Patient</th><th>Village</th><th>Worker</th><th>Flag Reason</th><th>Severity</th><th>Time</th></tr></thead><tbody>
            ${reports.map(r=>`<tr style="background:rgba(239,68,68,0.05)"><td>${r.id}</td><td>${r.patient_name}</td><td>${r.village}</td><td>${r.worker_name||'-'}</td>
            <td style="color:var(--accent-rose);font-size:0.8rem">${r.flag_reason||'Suspicious'}</td><td>${severityBadge(r.severity)}</td><td style="font-size:0.72rem">${timeAgo(r.created_at)}</td></tr>`).join('')}
            </tbody></table></div>`}`;
    } catch(e) { toast('❌ '+e.message,'error'); }
}

async function loadAdminPerformance() {
    setActiveSidebar('sb-perf');
    try {
        const workers = await api('/api/admin/worker-performance');
        $('main-content').innerHTML = `
            <h2 class="heading-lg mb-20">⭐ <span class="heading-text">Worker Performance</span></h2>
            <div class="table-container"><table><thead><tr><th>Worker</th><th>Village</th><th>District</th><th>Total Reports</th><th>This Week</th><th>This Month</th><th>Flagged</th><th>Last Active</th></tr></thead><tbody>
            ${workers.map(w=>`<tr><td><strong>${w.full_name}</strong><br><span style="font-size:0.72rem;color:var(--text-muted)">@${w.username}</span></td>
            <td>${w.village||'-'}</td><td>${w.district||'-'}</td><td><strong>${w.total_reports}</strong></td>
            <td>${w.weekly_reports}</td><td>${w.monthly_reports}</td>
            <td>${w.flagged_reports>0?`<span class="badge badge-red">${w.flagged_reports}</span>`:'0'}</td>
            <td style="font-size:0.72rem">${w.last_login?timeAgo(w.last_login):'Never'}</td></tr>`).join('')}
            </tbody></table></div>`;
    } catch(e) { toast('❌ '+e.message,'error'); }
}

function loadAdminAlerts() {
    setActiveSidebar('sb-alerts');
    $('main-content').innerHTML = `
        <h2 class="heading-lg mb-20">🔔 <span class="heading-text">Send Alert</span></h2>
        <div class="card" style="max-width:600px">
            <form onsubmit="sendAlert(event)">
                <div class="form-group"><label class="form-label">Alert Title</label><input class="form-control" id="alert-title" required placeholder="e.g. Water contamination warning"></div>
                <div class="form-group"><label class="form-label">Message</label><textarea class="form-control" id="alert-message" required placeholder="Describe the situation..."></textarea></div>
                <div class="grid-2">
                    <div class="form-group"><label class="form-label">Alert Level</label><select class="form-control" id="alert-level"><option value="green">🟢 Green (Info)</option><option value="yellow" selected>🟡 Yellow (Warning)</option><option value="red">🔴 Red (Critical)</option></select></div>
                    <div class="form-group"><label class="form-label">Target Village</label><input class="form-control" id="alert-village" placeholder="Leave blank for all"></div>
                </div>
                <div class="form-group"><label class="form-label">Target District</label><input class="form-control" id="alert-district" placeholder="Leave blank for all"></div>
                <div class="form-group"><label style="display:flex;align-items:center;gap:8px;cursor:pointer"><input type="checkbox" id="alert-global"> Send to ALL users (Global Alert)</label></div>
                <button type="submit" class="btn btn-primary btn-lg">📤 Send Alert</button>
            </form>
        </div>`;
}

async function sendAlert(e) {
    e.preventDefault();
    const fd = new FormData();
    fd.append('title', $('alert-title').value);
    fd.append('message', $('alert-message').value);
    fd.append('alert_level', $('alert-level').value);
    fd.append('target_village', $('alert-village').value);
    fd.append('target_district', $('alert-district').value);
    fd.append('is_global', $('alert-global').checked ? 1 : 0);
    try {
        const d = await apiForm('/api/admin/alerts', fd);
        toast('✅ ' + d.message, 'success');
    } catch(e) { toast('❌ '+e.message,'error'); }
}

function loadAdminNotices() {
    setActiveSidebar('sb-notices');
    $('main-content').innerHTML = `
        <h2 class="heading-lg mb-20">📢 <span class="heading-text">Publish Notice</span></h2>
        <div class="card" style="max-width:600px">
            <form onsubmit="publishNotice(event)">
                <div class="form-group"><label class="form-label">Title</label><input class="form-control" id="notice-title" required placeholder="Notice title"></div>
                <div class="form-group"><label class="form-label">Content</label><textarea class="form-control" id="notice-content" required placeholder="Notice content..." style="min-height:120px"></textarea></div>
                <div class="form-group"><label class="form-label">Type</label><select class="form-control" id="notice-type"><option value="general">General</option><option value="health_advisory">Health Advisory</option><option value="water_safety">Water Safety</option><option value="emergency">Emergency</option></select></div>
                <button type="submit" class="btn btn-primary btn-lg">📢 Publish Notice</button>
            </form>
        </div>`;
}

async function publishNotice(e) {
    e.preventDefault();
    const fd = new FormData();
    fd.append('title', $('notice-title').value);
    fd.append('content', $('notice-content').value);
    fd.append('notice_type', $('notice-type').value);
    fd.append('is_global', 1);
    try {
        await apiForm('/api/admin/notices', fd);
        toast('✅ Notice published!', 'success');
    } catch(e) { toast('❌ '+e.message,'error'); }
}

function loadAdminExport() {
    setActiveSidebar('sb-export');
    $('main-content').innerHTML = `
        <h2 class="heading-lg mb-20">📥 <span class="heading-text">Export Data</span></h2>
        <div class="grid-2">
            <div class="card text-center" style="padding:40px">
                <div style="font-size:3rem;margin-bottom:12px">📊</div>
                <h3 class="mb-8">Export as CSV</h3>
                <p style="font-size:0.85rem;color:var(--text-muted);margin-bottom:20px">Download all health reports in CSV format for analysis in Excel or other tools.</p>
                <a href="/api/admin/export/csv" class="btn btn-primary btn-lg" target="_blank" onclick="addAuthToExport(this)">⬇️ Download CSV</a>
            </div>
            <div class="card text-center" style="padding:40px">
                <div style="font-size:3rem;margin-bottom:12px">🖨️</div>
                <h3 class="mb-8">Print Report</h3>
                <p style="font-size:0.85rem;color:var(--text-muted);margin-bottom:20px">Print all current data including charts for government submissions.</p>
                <button class="btn btn-outline btn-lg" onclick="window.print()">🖨️ Print Page</button>
            </div>
        </div>`;
}

function addAuthToExport(el) {
    el.href = '/api/admin/export/csv';
    // For authenticated download, open in new tab with token
    fetch('/api/admin/export/csv', { headers: { 'Authorization': 'Bearer ' + TOKEN } })
        .then(r => r.blob())
        .then(b => {
            const url = URL.createObjectURL(b);
            const a = document.createElement('a');
            a.href = url; a.download = 'health_reports.csv'; a.click();
        });
    return false;
}

async function loadAdminDataManagement() {
    setActiveSidebar('sb-data');
    $('main-content').innerHTML = '<div class="text-center mt-24"><div class="loading-spinner"></div></div>';
    try {
        const stats = await api('/api/admin/data-stats');
        $('main-content').innerHTML = `
            <h2 class="heading-lg mb-20">🗑️ <span class="heading-text">Data Management</span></h2>
            
            <div class="grid-2 mb-24">
                <div class="card">
                    <div style="font-size:2rem;margin-bottom:12px">👥</div>
                    <div style="font-size:0.85rem;color:var(--text-muted);margin-bottom:4px">Total Users</div>
                    <div style="font-size:2rem;font-weight:800">${stats.total_users}</div>
                    <div style="font-size:0.75rem;color:var(--text-muted);margin-top:8px">Admins: ${stats.admin_count} | Workers: ${stats.worker_count} | Users: ${stats.user_count}</div>
                </div>
                <div class="card">
                    <div style="font-size:2rem;margin-bottom:12px">📋</div>
                    <div style="font-size:0.85rem;color:var(--text-muted);margin-bottom:4px">Total Reports</div>
                    <div style="font-size:2rem;font-weight:800">${stats.total_reports}</div>
                    <div style="font-size:0.75rem;color:var(--text-muted);margin-top:8px">Health: ${stats.health_reports} | Symptom: ${stats.symptom_reports}</div>
                </div>
            </div>

            <div class="grid-2 mb-24">
                <div class="card" style="border-left:3px solid var(--accent-rose);">
                    <div style="font-size:0.9rem;font-weight:600;margin-bottom:12px">⚠️ Delete All Non-Admin Users</div>
                    <p style="font-size:0.8rem;color:var(--text-muted);margin-bottom:16px">Remove all workers and public users, keeping only admin account. This action is irreversible.</p>
                    <button class="btn btn-danger btn-lg w-full" onclick="deleteAllNonAdminUsers()">🗑️ Delete All Non-Admin Users</button>
                </div>
                <div class="card" style="border-left:3px solid var(--accent-orange);">
                    <div style="font-size:0.9rem;font-weight:600;margin-bottom:12px">🗑️ Delete All Reports</div>
                    <p style="font-size:0.8rem;color:var(--text-muted);margin-bottom:16px">Remove all health and symptom reports from the system. This action is irreversible.</p>
                    <button class="btn btn-danger btn-lg w-full" onclick="deleteAllReports()">🗑️ Delete All Reports</button>
                </div>
            </div>

            <div class="card mb-24" style="border-left:3px solid var(--accent-yellow);">
                <div style="font-size:0.9rem;font-weight:600;margin-bottom:12px">🔄 Full System Reset</div>
                <p style="font-size:0.8rem;color:var(--text-muted);margin-bottom:16px">Delete all data (users except admin, reports, alerts, notices) and reset the system to initial state. This action is irreversible.</p>
                <button class="btn btn-warning btn-lg w-full" onclick="resetAllData()">⚠️ FULL SYSTEM RESET</button>
            </div>

            <div class="card mb-24">
                <div style="font-size:0.9rem;font-weight:600;margin-bottom:16px">👥 User Management</div>
                <div class="table-container"><table><thead><tr><th>Name</th><th>Username</th><th>Role</th><th>Village</th><th>Actions</th></tr></thead><tbody>
                ${stats.all_users.map(u => `<tr>
                    <td>${u.full_name}</td>
                    <td>${u.username}</td>
                    <td><span class="badge ${u.role === 'admin' ? 'badge-purple' : u.role === 'worker' ? 'badge-blue' : 'badge-green'}">${u.role}</span></td>
                    <td>${u.village || '-'}</td>
                    <td>${u.role === 'admin' ? '<span style="color:var(--text-muted);font-size:0.8rem">Protected</span>' : `<button class="btn btn-danger btn-sm" onclick="deleteUser(${u.id}, '${u.username}')">Delete</button>`}</td>
                </tr>`).join('')}
                </tbody></table></div>
            </div>

            <div class="card">
                <div style="font-size:0.9rem;font-weight:600;margin-bottom:16px">📋 Recent Reports Preview</div>
                <div class="table-container"><table><thead><tr><th>ID</th><th>Patient</th><th>Village</th><th>Type</th><th>Date</th><th>Actions</th></tr></thead><tbody>
                ${stats.recent_reports.slice(0, 10).map(r => `<tr>
                    <td>${r.id}</td>
                    <td>${r.patient_name || 'N/A'}</td>
                    <td>${r.village}</td>
                    <td><span class="badge badge-blue">${r.type}</span></td>
                    <td style="font-size:0.75rem">${r.created_at}</td>
                    <td><button class="btn btn-danger btn-sm" onclick="deleteReport(${r.id})">Delete</button></td>
                </tr>`).join('')}
                </tbody></table></div>
            </div>
        `;
    } catch (err) { toast('❌ ' + err.message, 'error'); }
}

async function deleteUser(userId, username) {
    const msg = `Delete user "${username}"? This action cannot be undone.`;
    if (!confirm(msg)) return;
    const msg2 = 'Type CONFIRM to delete this user:';
    const confirm_text = prompt(msg2);
    if (confirm_text !== 'CONFIRM') {
        toast('⚠️ Deletion cancelled', 'warning');
        return;
    }
    try {
        await api(`/api/admin/data/users/${userId}`, {method: 'DELETE'});
        toast('✅ User deleted successfully', 'success');
        loadAdminDataManagement();
    } catch (err) {
        toast('❌ ' + err.message, 'error');
    }
}

async function deleteReport(reportId) {
    if (!confirm('Delete this report? This action cannot be undone.')) return;
    try {
        await api(`/api/admin/data/reports/${reportId}`, {method: 'DELETE'});
        toast('✅ Report deleted successfully', 'success');
        loadAdminDataManagement();
    } catch (err) {
        toast('❌ ' + err.message, 'error');
    }
}

async function deleteAllNonAdminUsers() {
    const warning = '⚠️ WARNING: This will DELETE ALL workers and users, keeping only admin!\n\nType "DELETE ALL USERS" to confirm:';
    const confirm_text = prompt(warning);
    if (confirm_text !== 'DELETE ALL USERS') {
        toast('⚠️ Deletion cancelled', 'warning');
        return;
    }
    try {
        await api('/api/admin/data/delete-all-users', {method: 'POST'});
        toast('✅ All non-admin users deleted successfully', 'success');
        loadAdminDataManagement();
    } catch (err) {
        toast('❌ ' + err.message, 'error');
    }
}

async function deleteAllReports() {
    const warning = '⚠️ WARNING: This will DELETE ALL REPORTS!\n\nType "DELETE ALL REPORTS" to confirm:';
    const confirm_text = prompt(warning);
    if (confirm_text !== 'DELETE ALL REPORTS') {
        toast('⚠️ Deletion cancelled', 'warning');
        return;
    }
    try {
        await api('/api/admin/data/delete-all-reports', {method: 'POST'});
        toast('✅ All reports deleted successfully', 'success');
        loadAdminDataManagement();
    } catch (err) {
        toast('❌ ' + err.message, 'error');
    }
}

async function resetAllData() {
    const warning = '⚠️⚠️⚠️ CRITICAL WARNING: FULL SYSTEM RESET!\n\nThis will delete:\n- All users (except admin)\n- All reports\n- All alerts\n- All notices\n\nType "RESET EVERYTHING" to confirm (IRREVERSIBLE):';
    const confirm_text = prompt(warning);
    if (confirm_text !== 'RESET EVERYTHING') {
        toast('⚠️ Reset cancelled', 'warning');
        return;
    }
    try {
        await api('/api/admin/data/reset', {method: 'POST'});
        toast('✅ System reset successfully', 'success');
        loadAdminDataManagement();
    } catch (err) {
        toast('❌ ' + err.message, 'error');
    }
}
