/* ═══ USER / PUBLIC VIEWS ═══ */

function buildUserSidebar() {
    $('sidebar').innerHTML = `
        <div class="sidebar-section">Main</div>
        <ul class="sidebar-nav">
            <li class="sidebar-item"><a class="sidebar-link active" onclick="loadUserDashboard()" id="su-dash"><span class="icon">🏠</span> Home</a></li>
            <li class="sidebar-item"><a class="sidebar-link" onclick="loadUserReportSymptom()" id="su-report"><span class="icon">🩺</span> Report Symptoms</a></li>
            <li class="sidebar-item"><a class="sidebar-link" onclick="loadUserRiskStatus()" id="su-risk"><span class="icon">⚠️</span> Risk Status</a></li>
            <li class="sidebar-item"><a class="sidebar-link" onclick="loadUserHealthTips()" id="su-tips"><span class="icon">💡</span> Health Tips</a></li>
            <li class="sidebar-item"><a class="sidebar-link" onclick="loadUserWaterGuide()" id="su-water"><span class="icon">💧</span> Safe Water Guide</a></li>
            <li class="sidebar-item"><a class="sidebar-link" onclick="loadUserHistory()" id="su-history"><span class="icon">📜</span> My Reports</a></li>
            <li class="sidebar-item"><a class="sidebar-link" onclick="loadCommunityFeed()" id="su-feed"><span class="icon">📢</span> Community Feed</a></li>
        </ul>`;
}

function setUserSidebar(id) {
    document.querySelectorAll('.sidebar-link').forEach(l => l.classList.remove('active'));
    $(id)?.classList.add('active');
}

async function loadUserDashboard() {
    setUserSidebar('su-dash');
    const village = USER.village || 'Unknown';
    try {
        const [risk, alerts] = await Promise.all([
            api('/api/user/risk-status?village=' + encodeURIComponent(village)),
            api('/api/alerts')
        ]);
        const riskColors = { green: '#22c55e', yellow: '#eab308', red: '#ef4444' };
        
        $('main-content').innerHTML = `
            <h2 class="heading-lg mb-8">🏠 <span class="heading-text">Welcome, ${USER.full_name}</span></h2>
            <p style="color:var(--text-muted);margin-bottom:20px">📍 ${village}, ${USER.district || ''}</p>
            
            <div class="risk-banner ${risk.risk_level} mb-20">
                <div class="risk-icon">${risk.risk_level==='red'?'🚨':risk.risk_level==='yellow'?'⚠️':'✅'}</div>
                <div class="risk-text">
                    <h3>Your village is ${risk.risk_level.toUpperCase()} RISK</h3>
                    <p>Risk Score: ${risk.risk_score}% • ${risk.report_count||0} cases in last 7 days</p>
                </div>
            </div>
            
            ${risk.weather ? `<div class="card mb-20"><div class="flex items-center gap-16">
                <div style="font-size:2.5rem">🌤️</div>
                <div><h3>Weather: ${risk.weather.description}</h3>
                <p style="font-size:0.85rem;color:var(--text-muted)">${risk.weather.temp}°C • Humidity: ${risk.weather.humidity}%${risk.weather.rainfall?' • Rain: '+risk.weather.rainfall+'mm':''}</p></div>
            </div></div>` : ''}
            
            <div class="grid-2 mb-20">
                <div class="card" style="cursor:pointer" onclick="loadUserReportSymptom()">
                    <div style="font-size:2rem;margin-bottom:8px">🩺</div>
                    <h3>Report Symptoms</h3>
                    <p style="font-size:0.8rem;color:var(--text-muted)">Help protect your community by reporting health issues</p>
                </div>
                <div class="card" style="cursor:pointer" onclick="loadUserWaterGuide()">
                    <div style="font-size:2rem;margin-bottom:8px">💧</div>
                    <h3>Safe Water Guide</h3>
                    <p style="font-size:0.8rem;color:var(--text-muted)">Learn how to make your water safe for drinking</p>
                </div>
            </div>

            ${risk.health_tips ? `<div class="card mb-20"><h3 class="mb-12">💡 Health Tips for You</h3>
                ${risk.health_tips.map(t=>`<div class="feed-item">${t}</div>`).join('')}</div>` : ''}
            
            <div class="card"><div class="card-header"><h3 class="card-title">📢 Recent Alerts</h3></div>
                ${alerts.slice(0,5).map(a => `
                    <div class="feed-item" style="border-left:3px solid var(--risk-${a.alert_level})">
                        <div class="feed-header">${alertBadge(a.alert_level)} <strong>${a.title}</strong>
                            <span class="feed-time">${timeAgo(a.created_at)}</span></div>
                        <div class="feed-body">${a.message}</div>
                    </div>`).join('')}
                ${alerts.length===0?'<p style="color:var(--text-muted)">No alerts at this time</p>':''}
            </div>`;
    } catch(e) { toast('❌ '+e.message,'error'); }
}

function loadUserReportSymptom() {
    setUserSidebar('su-report');
    $('main-content').innerHTML = `
        <h2 class="heading-lg mb-20">🩺 <span class="heading-text">Report Your Symptoms</span></h2>
        <div class="card" style="max-width:600px">
            <form onsubmit="submitSymptom(event)">
                <div class="grid-2">
                    <div class="form-group"><label class="form-label">Village *</label><input class="form-control" id="sym-village" required value="${USER.village||''}"></div>
                    <div class="form-group"><label class="form-label">District *</label><input class="form-control" id="sym-district" required value="${USER.district||''}"></div>
                </div>
                <div class="form-group"><label class="form-label">Symptoms *</label><textarea class="form-control" id="sym-symptoms" required placeholder="Describe what you are feeling: fever, stomach pain, vomiting, diarrhea..."></textarea></div>
                <div class="grid-2">
                    <div class="form-group"><label class="form-label">Duration (days)</label><input type="number" class="form-control" id="sym-duration" min="1" placeholder="How many days"></div>
                    <div class="form-group"><label class="form-label">Water Source</label><input class="form-control" id="sym-water" placeholder="What water do you drink?"></div>
                </div>
                <div class="form-group"><label style="display:flex;align-items:center;gap:8px;cursor:pointer"><input type="checkbox" id="sym-anon"> Submit anonymously</label></div>
                <button type="submit" class="btn btn-primary btn-lg">📤 Submit Report</button>
            </form>
            <div id="sym-result" class="mt-16 hidden"></div>
        </div>`;
}

async function submitSymptom(e) {
    e.preventDefault();
    const fd = new FormData();
    fd.append('village', $('sym-village').value);
    fd.append('district', $('sym-district').value);
    fd.append('symptoms', $('sym-symptoms').value);
    fd.append('duration_days', $('sym-duration').value || '');
    fd.append('water_source', $('sym-water').value);
    fd.append('is_anonymous', $('sym-anon').checked ? 1 : 0);
    try {
        const d = await apiForm('/api/user/symptom-report', fd);
        let html = `<div class="alert-box success">✅ ${d.message}</div>`;
        if (d.possible_diseases && d.possible_diseases.length) {
            html += `<div class="card mt-12"><h4 style="margin-bottom:8px">🔬 Possible Conditions</h4>
                <p style="font-size:0.75rem;color:var(--text-muted);margin-bottom:8px">Based on AI analysis of your symptoms:</p>` +
                d.possible_diseases.map(dd=>`<div class="flex items-center justify-between" style="padding:4px 0"><span>${dd.disease}</span><span class="badge badge-purple">${dd.confidence}%</span></div>`).join('') +
                `<p style="font-size:0.72rem;color:var(--accent-rose);margin-top:12px">⚕️ Please consult a doctor for proper diagnosis.</p></div>`;
        }
        if (d.health_tips) {
            html += `<div class="card mt-12"><h4 style="margin-bottom:8px">💡 Recommended Actions</h4>` +
                d.health_tips.map(t=>`<div style="padding:4px 0;font-size:0.85rem">• ${t}</div>`).join('') + '</div>';
        }
        $('sym-result').innerHTML = html;
        show('sym-result');
    } catch(err) { toast('❌ '+err.message,'error'); }
}

async function loadUserRiskStatus() {
    setUserSidebar('su-risk');
    const village = USER.village || 'Unknown';
    try {
        const risk = await api('/api/user/risk-status?village=' + encodeURIComponent(village));
        $('main-content').innerHTML = `
            <h2 class="heading-lg mb-20">⚠️ <span class="heading-text">Village Risk Status</span></h2>
            <div class="risk-banner ${risk.risk_level} mb-20">
                <div class="risk-icon" style="font-size:3rem">${risk.risk_level==='red'?'🚨':risk.risk_level==='yellow'?'⚠️':'✅'}</div>
                <div class="risk-text">
                    <h3 style="font-size:1.3rem">${village} is ${risk.risk_level.toUpperCase()} RISK</h3>
                    <p>Risk Score: ${risk.risk_score}% • ${risk.report_count||0} reported cases this week</p>
                </div>
            </div>
            <div class="card mb-20"><h3 class="mb-12">📊 Risk Factors</h3>
                ${(risk.factors||[]).map(f=>`<div style="padding:4px 0;font-size:0.85rem">• ${f}</div>`).join('')}
                ${(!risk.factors||!risk.factors.length)?'<p style="color:var(--text-muted)">No specific risk factors identified.</p>':''}
            </div>
            ${risk.diseases_detected && risk.diseases_detected.length ? `
                <div class="card mb-20"><h3 class="mb-12">🦠 Diseases Detected in Area</h3>
                ${risk.diseases_detected.map(d=>`<div class="flex items-center justify-between mb-8"><span>${d.disease}</span><span class="badge badge-purple">${d.confidence}% confidence</span></div>`).join('')}</div>` : ''}
            <div class="card"><h3 class="mb-12">💡 Health Advice</h3>
                ${(risk.health_tips||[]).map(t=>`<div class="feed-item">${t}</div>`).join('')}</div>`;
    } catch(e) { toast('❌ '+e.message,'error'); }
}

function loadUserHealthTips() {
    setUserSidebar('su-tips');
    $('main-content').innerHTML = `
        <h2 class="heading-lg mb-20">💡 <span class="heading-text">Health Tips & Prevention</span></h2>
        <div class="grid-2">
            <div class="card"><div style="font-size:2rem;margin-bottom:8px">🧼</div><h3 class="mb-8">Hand Hygiene</h3>
                <p style="font-size:0.85rem;color:var(--text-secondary)">Wash hands with soap for 20 seconds before eating, after using toilet, and after handling animals. This prevents 40% of waterborne diseases.</p></div>
            <div class="card"><div style="font-size:2rem;margin-bottom:8px">🥗</div><h3 class="mb-8">Food Safety</h3>
                <p style="font-size:0.85rem;color:var(--text-secondary)">Always wash fruits and vegetables with clean water. Cook food thoroughly, especially during monsoon season.</p></div>
            <div class="card"><div style="font-size:2rem;margin-bottom:8px">🚽</div><h3 class="mb-8">Sanitation</h3>
                <p style="font-size:0.85rem;color:var(--text-secondary)">Use toilets / latrines. Never defecate near water sources. Dispose of waste properly to prevent contamination.</p></div>
            <div class="card"><div style="font-size:2rem;margin-bottom:8px">🏥</div><h3 class="mb-8">Seek Medical Help</h3>
                <p style="font-size:0.85rem;color:var(--text-secondary)">If you have diarrhea lasting more than 2 days, blood in stool, high fever, or severe dehydration — seek medical help immediately.</p></div>
            <div class="card"><div style="font-size:2rem;margin-bottom:8px">💊</div><h3 class="mb-8">ORS Solution</h3>
                <p style="font-size:0.85rem;color:var(--text-secondary)">For dehydration: Mix 6 teaspoons of sugar + ½ teaspoon of salt in 1 liter of clean water. Drink frequently in small sips.</p></div>
            <div class="card"><div style="font-size:2rem;margin-bottom:8px">🦟</div><h3 class="mb-8">Mosquito Prevention</h3>
                <p style="font-size:0.85rem;color:var(--text-secondary)">Remove stagnant water. Use mosquito nets while sleeping. Wear long sleeves in evenings.</p></div>
        </div>`;
}

async function loadUserWaterGuide() {
    setUserSidebar('su-water');
    try {
        const risk = await api('/api/user/risk-status?village=' + encodeURIComponent(USER.village || 'Unknown'));
        const guide = risk.safe_water_guide || [];
        $('main-content').innerHTML = `
            <h2 class="heading-lg mb-20">💧 <span class="heading-text">Safe Water Guide</span></h2>
            <p style="color:var(--text-muted);margin-bottom:24px">Learn how to make your water safe for drinking and cooking</p>
            <div class="grid-3">${guide.map(g => `
                <div class="guide-card">
                    <div class="guide-icon">${g.icon}</div>
                    <div class="guide-title">${g.title}</div>
                    <div class="guide-desc">${g.description}</div>
                </div>`).join('')}</div>`;
    } catch(e) { toast('❌ '+e.message,'error'); }
}

async function loadUserHistory() {
    setUserSidebar('su-history');
    try {
        const reports = await api('/api/user/my-reports');
        $('main-content').innerHTML = `
            <h2 class="heading-lg mb-20">📜 <span class="heading-text">My Report History</span></h2>
            ${reports.length===0?'<div class="empty-state"><div class="empty-icon">📜</div><p class="empty-title">No reports submitted yet</p></div>':
            `<div class="table-container"><table><thead><tr><th>ID</th><th>Village</th><th>Symptoms</th><th>Duration</th><th>Water Source</th><th>Anonymous</th><th>Date</th></tr></thead><tbody>
            ${reports.map(r=>`<tr><td>${r.id}</td><td>${r.village}</td><td class="truncate" style="max-width:200px">${r.symptoms}</td>
            <td>${r.duration_days||'-'} days</td><td>${r.water_source||'-'}</td><td>${r.is_anonymous?'Yes':'No'}</td>
            <td style="font-size:0.72rem">${timeAgo(r.created_at)}</td></tr>`).join('')}
            </tbody></table></div>`}`;
    } catch(e) { toast('❌ '+e.message,'error'); }
}

async function loadCommunityFeed() {
    setUserSidebar('su-feed');
    try {
        const [alerts, notices] = await Promise.all([api('/api/alerts'), api('/api/notices')]);
        $('main-content').innerHTML = `
            <h2 class="heading-lg mb-20">📢 <span class="heading-text">Community Feed</span></h2>
            <div class="tabs mb-16"><button class="tab active" onclick="showFeedTab('alerts-tab',this)">🔔 Alerts</button>
                <button class="tab" onclick="showFeedTab('notices-tab',this)">📢 Notices</button></div>
            <div id="alerts-tab">${alerts.map(a=>`
                <div class="feed-item" style="border-left:3px solid var(--risk-${a.alert_level})">
                    <div class="feed-header">${alertBadge(a.alert_level)} <strong>${a.title}</strong>
                        <span class="feed-time">${timeAgo(a.created_at)}</span></div>
                    <div class="feed-body">${a.message}</div>
                </div>`).join('')}${alerts.length===0?'<p style="color:var(--text-muted)">No alerts</p>':''}</div>
            <div id="notices-tab" class="hidden">${notices.map(n=>`
                <div class="feed-item"><div class="feed-header"><span class="badge badge-blue">${n.notice_type||'general'}</span> <strong>${n.title}</strong>
                    <span class="feed-time">${timeAgo(n.created_at)}</span></div>
                    <div class="feed-body">${n.content}</div>
                    ${n.author?`<div style="font-size:0.72rem;color:var(--text-muted);margin-top:4px">— ${n.author}</div>`:''}
                </div>`).join('')}${notices.length===0?'<p style="color:var(--text-muted)">No notices</p>':''}</div>`;
    } catch(e) { toast('❌ '+e.message,'error'); }
}

function showFeedTab(tabId, btn) {
    document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
    btn.classList.add('active');
    ['alerts-tab','notices-tab'].forEach(id=> $(id)?.classList.add('hidden'));
    $(tabId)?.classList.remove('hidden');
}
