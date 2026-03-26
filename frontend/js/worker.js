/* ═══ WORKER VIEWS ═══ */

function buildWorkerSidebar() {
    $('sidebar').innerHTML = `
        <div class="sidebar-section">Main</div>
        <ul class="sidebar-nav">
            <li class="sidebar-item"><a class="sidebar-link active" onclick="loadWorkerDashboard()" id="sw-dash"><span class="icon">🏠</span> Dashboard</a></li>
            <li class="sidebar-item"><a class="sidebar-link" onclick="loadWorkerSubmit()" id="sw-submit"><span class="icon">📝</span> Submit Report</a></li>
            <li class="sidebar-item"><a class="sidebar-link" onclick="loadWorkerBulk()" id="sw-bulk"><span class="icon">📦</span> Bulk Entry</a></li>
            <li class="sidebar-item"><a class="sidebar-link" onclick="loadWorkerMyReports()" id="sw-reports"><span class="icon">📋</span> My Reports</a></li>
            <li class="sidebar-item"><a class="sidebar-link" onclick="loadWorkerAlerts()" id="sw-alerts"><span class="icon">🔔</span> Alerts</a></li>
        </ul>`;
}

function setWorkerSidebar(id) {
    document.querySelectorAll('.sidebar-link').forEach(l => l.classList.remove('active'));
    $(id)?.classList.add('active');
}

async function loadWorkerDashboard() {
    setWorkerSidebar('sw-dash');
    try {
        const [reports, alerts] = await Promise.all([
            api('/api/worker/my-reports'),
            api('/api/alerts')
        ]);
        const today = new Date().toISOString().slice(0,10);
        const todayCount = reports.filter(r => (r.created_at||'').slice(0,10) === today).length;
        const weekCount = reports.filter(r => {
            const d = new Date(r.created_at);
            return (Date.now() - d.getTime()) < 7*86400000;
        }).length;
        
        $('main-content').innerHTML = `
            <h2 class="heading-lg mb-20">👷 <span class="heading-text">Worker Dashboard</span></h2>
            <p style="color:var(--text-muted);margin-bottom:20px">Welcome, <strong>${USER.full_name}</strong> • ${USER.village || ''}, ${USER.district || ''}</p>
            <div class="grid-3 mb-24">
                <div class="stat-card blue"><div class="stat-icon">📋</div><div class="stat-number">${reports.length}</div><div class="stat-label">Total Reports</div></div>
                <div class="stat-card emerald"><div class="stat-icon">📅</div><div class="stat-number">${todayCount}</div><div class="stat-label">Today's Reports</div></div>
                <div class="stat-card purple"><div class="stat-icon">📊</div><div class="stat-number">${weekCount}</div><div class="stat-label">This Week</div></div>
            </div>
            ${alerts.filter(a=>a.alert_level==='red').slice(0,3).map(a=>`
                <div class="risk-banner red mb-12"><div class="risk-icon">🚨</div><div class="risk-text"><h3>${a.title}</h3><p>${a.message}</p></div></div>
            `).join('')}
            <div class="card">
                <div class="card-header"><h3 class="card-title">Recent Submissions</h3>
                    <button class="btn btn-primary btn-sm" onclick="loadWorkerSubmit()">+ New Report</button></div>
                ${reports.slice(0,5).map(r=>`
                    <div class="feed-item"><div class="flex items-center justify-between">
                        <strong>${r.patient_name}</strong> ${severityBadge(r.severity)}
                    </div><div style="font-size:0.8rem;color:var(--text-muted)">${r.village} • ${r.symptoms.slice(0,60)}... • ${timeAgo(r.created_at)}</div></div>
                `).join('')}
            </div>`;
    } catch(e) { toast('❌ '+e.message,'error'); }
}

function loadWorkerSubmit() {
    setWorkerSidebar('sw-submit');
    $('main-content').innerHTML = `
        <h2 class="heading-lg mb-20">📝 <span class="heading-text">Submit Health Report</span></h2>
        <div class="card" style="max-width:700px">
            <form onsubmit="submitReport(event)" enctype="multipart/form-data">
                <div class="grid-2">
                    <div class="form-group"><label class="form-label">Patient Name *</label><input class="form-control" id="rpt-name" required></div>
                    <div class="form-group"><label class="form-label">Age</label><input type="number" class="form-control" id="rpt-age" min="0" max="120"></div>
                </div>
                <div class="grid-2">
                    <div class="form-group"><label class="form-label">Gender</label><select class="form-control" id="rpt-gender"><option value="">Select</option><option value="Male">Male</option><option value="Female">Female</option><option value="Other">Other</option></select></div>
                    <div class="form-group"><label class="form-label">Severity *</label><select class="form-control" id="rpt-severity"><option value="low">🟢 Low</option><option value="medium">🟡 Medium</option><option value="high">🟠 High</option><option value="critical">🔴 Critical</option></select></div>
                </div>
                <div class="grid-2">
                    <div class="form-group"><label class="form-label">Village *</label><input class="form-control" id="rpt-village" required value="${USER.village||''}"></div>
                    <div class="form-group"><label class="form-label">District *</label><input class="form-control" id="rpt-district" required value="${USER.district||''}"></div>
                </div>
                <div class="form-group"><label class="form-label">Symptoms *</label><textarea class="form-control" id="rpt-symptoms" required placeholder="Describe symptoms: diarrhea, vomiting, fever, etc."></textarea></div>
                <div class="grid-2">
                    <div class="form-group"><label class="form-label">Water Source</label><input class="form-control" id="rpt-water" placeholder="e.g. River, Well, Pond"></div>
                    <div class="form-group"><label class="form-label">Water Source Type</label><select class="form-control" id="rpt-water-type"><option value="">Select</option><option value="river">River</option><option value="well">Well</option><option value="pond">Pond</option><option value="tap">Tap Water</option><option value="borewell">Borewell</option><option value="spring">Spring</option></select></div>
                </div>
                <div class="form-group"><label class="form-label">Notes</label><textarea class="form-control" id="rpt-notes" placeholder="Additional observations..."></textarea></div>
                <div class="form-group"><label class="form-label">📷 Photo (Water source / Environment)</label><input type="file" class="form-control" id="rpt-photo" accept="image/*">
                    <p style="font-size:0.72rem;color:var(--text-muted);margin-top:4px">Upload a photo of the water source or patient environment. AI will analyze the image for potential contamination indicators.</p></div>
                <button type="submit" class="btn btn-primary btn-lg" id="submit-btn">📤 Submit Report</button>
            </form>
            <div id="submit-result" class="mt-16 hidden"></div>
        </div>`;
}

async function submitReport(e) {
    e.preventDefault();
    const fd = new FormData();
    fd.append('patient_name', $('rpt-name').value);
    fd.append('patient_age', $('rpt-age').value || '');
    fd.append('patient_gender', $('rpt-gender').value);
    fd.append('village', $('rpt-village').value);
    fd.append('district', $('rpt-district').value);
    fd.append('symptoms', $('rpt-symptoms').value);
    fd.append('severity', $('rpt-severity').value);
    fd.append('water_source', $('rpt-water').value);
    fd.append('water_source_type', $('rpt-water-type').value);
    fd.append('notes', $('rpt-notes').value);
    if ($('rpt-photo').files[0]) fd.append('photo', $('rpt-photo').files[0]);
    
    try {
        $('submit-btn').textContent = '⏳ Submitting...';
        const d = await apiForm('/api/worker/reports', fd);
        toast('✅ Report submitted!', 'success');
        let html = `<div class="alert-box success">✅ <div><strong>Report #${d.report_id} submitted successfully!</strong></div></div>`;
        if (d.risk_assessment) {
            html += `<div class="alert-box ${d.risk_assessment.risk_level==='red'?'danger':d.risk_assessment.risk_level==='yellow'?'warning':'info'}">
                ${d.risk_assessment.risk_level==='red'?'🚨':d.risk_assessment.risk_level==='yellow'?'⚠️':'ℹ️'}
                <div><strong>Village Risk: ${d.risk_assessment.risk_level.toUpperCase()}</strong> (Score: ${d.risk_assessment.risk_score}%)</div></div>`;
        }
        if (d.disease_detection && d.disease_detection.length) {
            html += `<div class="card mt-12"><h4 style="margin-bottom:8px">🔬 AI Disease Detection</h4>` +
                d.disease_detection.map(dd => `<div class="flex items-center justify-between" style="padding:4px 0"><span>${dd.disease}</span><span class="badge badge-purple">${dd.confidence}% match</span></div>`).join('') + '</div>';
        }
        $('submit-result').innerHTML = html;
        $('submit-result').classList.remove('hidden');
        e.target.reset();
    } catch(err) {
        toast('❌ ' + err.message, 'error');
    } finally { $('submit-btn').textContent = '📤 Submit Report'; }
}

function loadWorkerBulk() {
    setWorkerSidebar('sw-bulk');
    $('main-content').innerHTML = `
        <h2 class="heading-lg mb-20">📦 <span class="heading-text">Bulk Data Entry</span></h2>
        <div class="card" style="max-width:800px">
            <p style="color:var(--text-muted);margin-bottom:16px">Enter multiple patient records quickly. Add rows and submit all at once.</p>
            <div id="bulk-entries"><div class="bulk-row grid-4 gap-8 mb-8" style="grid-template-columns:1fr 1fr 2fr 1fr">
                <input class="form-control bulk-name" placeholder="Patient Name">
                <input class="form-control bulk-village" placeholder="Village" value="${USER.village||''}">
                <input class="form-control bulk-symptoms" placeholder="Symptoms">
                <select class="form-control bulk-severity"><option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option><option value="critical">Critical</option></select>
            </div></div>
            <button class="btn btn-outline btn-sm mb-16" onclick="addBulkRow()">+ Add Row</button>
            <br><button class="btn btn-primary btn-lg" onclick="submitBulk()">📤 Submit All</button>
            <div id="bulk-result" class="mt-12"></div>
        </div>`;
}

function addBulkRow() {
    const row = document.createElement('div');
    row.className = 'bulk-row grid-4 gap-8 mb-8';
    row.style.gridTemplateColumns = '1fr 1fr 2fr 1fr';
    row.innerHTML = `<input class="form-control bulk-name" placeholder="Patient Name">
        <input class="form-control bulk-village" placeholder="Village" value="${USER.village||''}">
        <input class="form-control bulk-symptoms" placeholder="Symptoms">
        <select class="form-control bulk-severity"><option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option><option value="critical">Critical</option></select>`;
    $('bulk-entries').appendChild(row);
}

async function submitBulk() {
    const rows = document.querySelectorAll('.bulk-row');
    const reports = [];
    rows.forEach(r => {
        const name = r.querySelector('.bulk-name').value;
        if (!name) return;
        reports.push({
            patient_name: name,
            village: r.querySelector('.bulk-village').value || USER.village || '',
            district: USER.district || '',
            symptoms: r.querySelector('.bulk-symptoms').value,
            severity: r.querySelector('.bulk-severity').value
        });
    });
    if (!reports.length) return toast('No data to submit', 'warning');
    const fd = new FormData();
    fd.append('reports_json', JSON.stringify(reports));
    try {
        const d = await apiForm('/api/worker/reports/bulk', fd);
        toast('✅ ' + d.message, 'success');
        $('bulk-result').innerHTML = `<div class="alert-box success">✅ ${d.count} reports submitted!</div>`;
    } catch(e) { toast('❌ '+e.message,'error'); }
}

async function loadWorkerMyReports() {
    setWorkerSidebar('sw-reports');
    try {
        const reports = await api('/api/worker/my-reports');
        $('main-content').innerHTML = `
            <h2 class="heading-lg mb-20">📋 <span class="heading-text">My Reports</span></h2>
            <div class="table-container"><table><thead><tr><th>#</th><th>Patient</th><th>Village</th><th>Symptoms</th><th>Disease</th><th>Severity</th><th>Flagged</th><th>Time</th><th>Edit</th></tr></thead><tbody>
            ${reports.map(r => {
                const created = new Date(r.created_at);
                const canEdit = (Date.now()-created.getTime()) < 24*3600000;
                return `<tr><td>${r.id}</td><td>${r.patient_name}</td><td>${r.village}</td>
                <td class="truncate" style="max-width:150px">${r.symptoms}</td><td>${r.disease_suspected||'-'}</td>
                <td>${severityBadge(r.severity)}</td><td>${r.is_flagged?'🚩':'✅'}</td>
                <td style="font-size:0.72rem">${timeAgo(r.created_at)}</td>
                <td>${canEdit?`<button class="btn btn-outline btn-sm" onclick="editReport(${r.id})">✏️</button>`:'-'}</td></tr>`;
            }).join('')}</tbody></table></div>`;
    } catch(e) { toast('❌ '+e.message,'error'); }
}

async function editReport(id) {
    const newSymptoms = prompt('Update symptoms:');
    if (!newSymptoms) return;
    const fd = new FormData();
    fd.append('symptoms', newSymptoms);
    try {
        await fetch('/api/worker/reports/'+id, {
            method: 'PUT',
            headers: { 'Authorization': 'Bearer '+TOKEN },
            body: fd
        }).then(r=>r.json());
        toast('✅ Report updated','success');
        loadWorkerMyReports();
    } catch(e) { toast('❌ '+e.message,'error'); }
}

async function loadWorkerAlerts() {
    setWorkerSidebar('sw-alerts');
    try {
        const alerts = await api('/api/alerts');
        $('main-content').innerHTML = `
            <h2 class="heading-lg mb-20">🔔 <span class="heading-text">Alert Feed</span></h2>
            ${alerts.map(a => `
                <div class="feed-item" style="border-left:3px solid var(--risk-${a.alert_level})">
                    <div class="feed-header">${alertBadge(a.alert_level)} <strong>${a.title}</strong>
                        <span class="feed-time">${timeAgo(a.created_at)}</span></div>
                    <div class="feed-body">${a.message}</div>
                    ${a.target_village?`<div style="font-size:0.72rem;color:var(--text-muted);margin-top:6px">📍 ${a.target_village}${a.target_district?' — '+a.target_district:''}</div>`:''}
                </div>`).join('')}
            ${alerts.length===0?'<div class="empty-state"><div class="empty-icon">🔔</div><p class="empty-title">No alerts</p></div>':''}`;
    } catch(e) { toast('❌ '+e.message,'error'); }
}

/* ═══ WORKER TRAINING CHATBOT ═══ */
const WORKER_TRAINING_QA = [
    {
        q: 'How do I submit a new health report?',
        a: 'Open Submit Report from the sidebar, fill patient details, symptoms, village and district, choose severity, then click Submit Report.'
    },
    {
        q: 'Which fields are mandatory in Submit Report?',
        a: 'Patient Name, Village, District, Symptoms, and Severity are the key required fields for correct submission.'
    },
    {
        q: 'How do I upload a photo in a report?',
        a: 'In Submit Report, use the Photo field and choose an image file. It helps with environmental analysis in the system.'
    },
    {
        q: 'How can I submit many reports quickly?',
        a: 'Use Bulk Entry. Add multiple rows, complete each row, then click Submit All to upload everything together.'
    },
    {
        q: 'Where can I see my submitted reports?',
        a: 'Go to My Reports in the worker sidebar. You can review all your submissions with time, severity, and status.'
    },
    {
        q: 'Can I edit an old report?',
        a: 'Yes, recent reports can be edited from My Reports using the edit button. Older reports may become read-only for data integrity.'
    },
    {
        q: 'How do I decide severity level?',
        a: 'Use Low for mild symptoms, Medium for moderate impact, High for severe symptoms, and Critical for emergency-level cases.'
    },
    {
        q: 'Where do I check important alerts?',
        a: 'Open Alerts in the worker sidebar. Red alerts should be handled first because they indicate urgent risk.'
    },
    {
        q: 'What should I do if I entered wrong data?',
        a: 'If the report is editable, update it from My Reports. If not editable, submit a corrected report with notes mentioning the correction.'
    },
    {
        q: 'How do I improve data quality?',
        a: 'Use clear symptom descriptions, correct village and district, realistic age, accurate severity, and add useful notes/photos.'
    },
    {
        q: 'What does flagged mean in reports?',
        a: 'Flagged means the report looks suspicious or inconsistent and may need review by admins. Provide complete and accurate details to avoid this.'
    },
    {
        q: 'How often should I submit reports?',
        a: 'Submit as soon as cases are identified. Daily updates are ideal during active outbreaks or rising risk periods.'
    },
    {
        q: 'What is the difference between Submit Report and Bulk Entry?',
        a: 'Submit Report is for one detailed case (with optional photo). Bulk Entry is for quickly adding many basic records at once.'
    },
    {
        q: 'What should I write in symptoms for better accuracy?',
        a: 'Write specific symptoms and duration, for example: fever for 2 days, vomiting 3 times, loose stool since morning.'
    },
    {
        q: 'When should I mark a case as critical?',
        a: 'Mark Critical for emergency signs such as severe dehydration, blood in stool, persistent high fever, confusion, or breathing distress.'
    },
    {
        q: 'How do I use water source information correctly?',
        a: 'Enter the actual source used by the patient (well, river, pond, tap, etc.). This helps cluster contamination patterns.'
    },
    {
        q: 'Can I submit reports if internet is slow?',
        a: 'Yes. Fill fields carefully and submit one by one if bulk fails. If a request fails, retry after checking connection.'
    },
    {
        q: 'How do I verify that my report was saved?',
        a: 'After submit, you get a success message and report ID. You can also confirm it in My Reports list.'
    },
    {
        q: 'What should I do when red alerts appear?',
        a: 'Prioritize field verification, monitor similar symptoms nearby, and submit timely updates with accurate severity and notes.'
    },
    {
        q: 'How do I avoid duplicate reports?',
        a: 'Before submitting, check My Reports for same patient and date. If duplicate happened, update notes in the latest editable record.'
    },
    {
        q: 'What is the best daily workflow for a worker?',
        a: 'Check Alerts first, submit new cases, update corrections in My Reports, then review village trends before ending the day.'
    }
];

function getWorkerBotReplyLocal(input) {
    const text = (input || '').trim();
    const lower = text.toLowerCase();

    if (!text) return 'Please type your question. I can help with report submission, bulk entry, alerts, and best practices.';

    if (/^(hi|hello|hey|hii|hola)\b/.test(lower)) {
        return 'Hello! I am your Worker Training Assistant. Ask me anything about using this dashboard.';
    }
    if (/good\s*morning/.test(lower)) return 'Good morning! Ready to submit and manage reports today?';
    if (/good\s*afternoon/.test(lower)) return 'Good afternoon! I can guide you through any worker task.';
    if (/good\s*evening/.test(lower)) return 'Good evening! Need help with reports, alerts, or bulk entry?';
    if (/how are you/.test(lower)) return 'I am doing great. I am here to support your health worker tasks.';
    if (/^(yes|yeah|yep|sure|ok|okay|done)\b/.test(lower)) {
        return 'Great. You can ask me about Submit Report, Bulk Entry, severity selection, alerts, data quality, or click any suggested question above.';
    }
    if (/^(no|nah|not now)\b/.test(lower)) {
        return 'No problem. Whenever you need help, type a question or click one of the training chips.';
    }
    if (/\b(who is|what is cricket|virat|movie|song|news|politics)\b/.test(lower)) {
        return 'I am a training assistant for this worker dashboard. I can help only with using this website and report workflow.';
    }
    if (/thanks|thank you/.test(lower)) return 'You are welcome. Keep up the important field work.';

    const exact = WORKER_TRAINING_QA.find(item => item.q.toLowerCase() === lower);
    if (exact) return exact.a;

    const keywordMap = [
        { keys: ['submit', 'report', 'new report'], idx: 0 },
        { keys: ['mandatory', 'required', 'fields'], idx: 1 },
        { keys: ['photo', 'image', 'upload'], idx: 2 },
        { keys: ['bulk', 'many', 'multiple'], idx: 3 },
        { keys: ['my reports', 'history', 'submitted'], idx: 4 },
        { keys: ['edit', 'update', 'wrong'], idx: 5 },
        { keys: ['severity', 'low', 'medium', 'high', 'critical'], idx: 6 },
        { keys: ['alert', 'alerts', 'urgent'], idx: 7 },
        { keys: ['quality', 'accurate', 'data'], idx: 9 },
        { keys: ['flagged', 'suspicious'], idx: 10 },
        { keys: ['difference', 'submit report and bulk', 'single vs bulk'], idx: 12 },
        { keys: ['symptom', 'write symptoms', 'description'], idx: 13 },
        { keys: ['internet', 'network', 'slow'], idx: 16 },
        { keys: ['saved', 'report id', 'confirm'], idx: 17 },
        { keys: ['duplicate', 'same patient'], idx: 19 },
        { keys: ['workflow', 'daily workflow'], idx: 20 }
    ];

    for (const rule of keywordMap) {
        if (rule.keys.some(k => lower.includes(k))) {
            return WORKER_TRAINING_QA[rule.idx].a;
        }
    }

    return 'I can help with Submit Report, Bulk Entry, My Reports, Alerts, severity guidance, and data quality. Try a clear worker question or click any suggested training question.';
}

async function getWorkerBotReply(input) {
    const fd = new FormData();
    fd.append('message', input || '');
    try {
        const res = await apiForm('/api/worker/training-chat', fd);
        if (res && res.reply) return res.reply;
    } catch (_) {
        // Fall back to local trainer responses when API is unavailable.
    }
    return getWorkerBotReplyLocal(input);
}

function appendWorkerChatMessage(sender, text) {
    const messages = $('worker-chat-messages');
    if (!messages) return;

    const row = document.createElement('div');
    row.className = `worker-chat-row ${sender}`;
    row.innerHTML = `<div class="worker-chat-bubble">${text}</div>`;
    messages.appendChild(row);
    messages.scrollTop = messages.scrollHeight;
}

async function askWorkerTrainingQuestion(questionText) {
    appendWorkerChatMessage('user', questionText);
    const reply = await getWorkerBotReply(questionText);
    setTimeout(() => appendWorkerChatMessage('bot', reply), 180);
}

function sendWorkerChatMessage() {
    const input = $('worker-chat-input');
    if (!input) return;
    const text = input.value.trim();
    if (!text) return;
    input.value = '';
    askWorkerTrainingQuestion(text);
}

function toggleWorkerTrainingChat() {
    const panel = $('worker-chat-panel');
    const fab = $('worker-chat-fab');
    if (!panel || !fab) return;

    panel.classList.toggle('open');
    fab.classList.toggle('active');
}

function initWorkerTrainingChatbot() {
    if (USER?.role !== 'worker') return;
    if ($('worker-chat-widget')) return;

    const widget = document.createElement('div');
    widget.id = 'worker-chat-widget';
    widget.className = 'worker-chat-widget';
    widget.innerHTML = `
        <button id="worker-chat-fab" class="worker-chat-fab" onclick="toggleWorkerTrainingChat()" title="Worker Training Assistant">💬 Training AI</button>
        <div id="worker-chat-panel" class="worker-chat-panel">
            <div class="worker-chat-header">
                <div>
                    <strong>Worker Training AI</strong>
                    <p>Ask how to use this website</p>
                </div>
                <button class="worker-chat-close" onclick="toggleWorkerTrainingChat()">×</button>
            </div>
            <div class="worker-chat-questions" id="worker-chat-questions"></div>
            <div class="worker-chat-messages" id="worker-chat-messages"></div>
            <div class="worker-chat-input-wrap">
                <input id="worker-chat-input" class="worker-chat-input" placeholder="Type your message..." onkeydown="if(event.key==='Enter'){sendWorkerChatMessage();}">
                <button class="worker-chat-send" onclick="sendWorkerChatMessage()">Send</button>
            </div>
        </div>
    `;

    const host = $('main-app') || document.body;
    host.appendChild(widget);

    const qWrap = $('worker-chat-questions');
    if (qWrap) {
        WORKER_TRAINING_QA.forEach(item => {
            const btn = document.createElement('button');
            btn.className = 'worker-chat-qchip';
            btn.textContent = item.q;
            btn.onclick = () => askWorkerTrainingQuestion(item.q);
            qWrap.appendChild(btn);
        });
    }

    appendWorkerChatMessage('bot', 'Hello! I am your Worker Training Assistant. Click any question or type a message like hi, hello, good morning, or ask about reports.');
}

function destroyWorkerTrainingChatbot() {
    const node = $('worker-chat-widget');
    if (node) node.remove();
}
