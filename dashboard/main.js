// AI-NGFW Dashboard — Traffic Monitor
const API_BASE = window.location.origin;
let socket = null;
let trafficChart = null;
let protocolChart = null;

const MAX_CHART_POINTS = 30;
const chartLabels = [];
const chartBytesData = [];
const protocolData = { TCP: 0, UDP: 0, ICMP: 0, Other: 0 };

let liveSessions = [];
let sessionIdCounter = 0;
let lastTotalBytes = 0;
let lastUpdateTime = Date.now();

function formatBytes(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function formatDuration(seconds) {
    if (seconds < 60) return `${seconds}s`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
    return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
}

function getProtocolName(protocol) {
    const map = { '6': 'TCP', '17': 'UDP', '1': 'ICMP', 'TCP': 'TCP', 'UDP': 'UDP', 'ICMP': 'ICMP' };
    return map[protocol] || 'Other';
}

// ── Charts ────────────────────────────────────────────────
function initCharts() {
    const ctxTraffic = document.getElementById('trafficChart');
    if (ctxTraffic) {
        trafficChart = new Chart(ctxTraffic.getContext('2d'), {
            type: 'line',
            data: {
                labels: chartLabels,
                datasets: [{
                    label: 'Traffic (KB/s)',
                    data: chartBytesData,
                    borderColor: '#2563eb',
                    backgroundColor: 'rgba(37,99,235,0.06)',
                    borderWidth: 1.5,
                    fill: true,
                    tension: 0.4,
                    pointRadius: 2,
                    pointHoverRadius: 4,
                    pointBackgroundColor: '#2563eb'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: '#18181b',
                        titleColor: '#f4f4f5',
                        bodyColor: '#a1a1aa',
                        borderColor: '#3f3f46',
                        borderWidth: 1,
                        padding: 10,
                        displayColors: false,
                        cornerRadius: 6
                    }
                },
                scales: {
                    x: {
                        grid: { color: '#f4f4f5', drawBorder: false },
                        ticks: { color: '#a1a1aa', font: { size: 11, family: 'DM Mono' }, maxRotation: 0 }
                    },
                    y: {
                        grid: { color: '#f4f4f5', drawBorder: false },
                        ticks: { color: '#a1a1aa', font: { size: 11, family: 'DM Mono' } },
                        beginAtZero: true
                    }
                },
                interaction: { intersect: false, mode: 'index' }
            }
        });
    }

    const ctxProto = document.getElementById('protocolChart');
    if (ctxProto) {
        protocolChart = new Chart(ctxProto.getContext('2d'), {
            type: 'doughnut',
            data: {
                labels: ['TCP', 'UDP', 'ICMP', 'Other'],
                datasets: [{
                    data: [0, 0, 0, 0],
                    backgroundColor: ['#2563eb', '#16a34a', '#d97706', '#a1a1aa'],
                    borderWidth: 0,
                    hoverOffset: 3
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            color: '#71717a',
                            font: { size: 12, family: 'DM Sans' },
                            padding: 16,
                            usePointStyle: true,
                            pointStyleWidth: 8
                        }
                    },
                    tooltip: {
                        backgroundColor: '#18181b',
                        titleColor: '#f4f4f5',
                        bodyColor: '#a1a1aa',
                        borderColor: '#3f3f46',
                        borderWidth: 1,
                        padding: 10,
                        cornerRadius: 6,
                        callbacks: {
                            label: function(ctx) {
                                const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
                                const pct = total > 0 ? ((ctx.parsed / total) * 100).toFixed(1) : 0;
                                return `${ctx.label}: ${ctx.parsed} (${pct}%)`;
                            }
                        }
                    }
                },
                cutout: '68%'
            }
        });
    }
}

// ── WebSocket ─────────────────────────────────────────────
function connectWebSocket() {
    const wsProto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProto}//${window.location.hostname}:8000/ws`;
    console.log(`  🔌 Attempting WebSocket connection to: ${wsUrl}`);
    try {
        socket = new WebSocket(wsUrl);
        socket.onopen = () => {
            console.log('  ✅ WebSocket connected!');
            updateSystemStatus(true);
        };
        socket.onmessage = (event) => {
            console.log('  📨 WebSocket message received');
            try { updateDashboard(JSON.parse(event.data)); } catch(e) { console.error('  ❌ Error parsing WebSocket data:', e); }
        };
        socket.onclose = (event) => {
            console.log(`  ⚠️ WebSocket closed (code: ${event.code}). Reconnecting in 3s...`);
            updateSystemStatus(false);
            setTimeout(connectWebSocket, 3000);
        };
        socket.onerror = (error) => {
            console.error('  ❌ WebSocket error:', error);
            updateSystemStatus(false);
        };
    } catch(e) {
        console.error('  ❌ Failed to create WebSocket:', e);
        setTimeout(connectWebSocket, 3000);
    }
}

function updateSystemStatus(online) {
    const pill = document.getElementById('system-status-pill');
    const label = document.getElementById('status-label');
    const dot = pill?.querySelector('.pulse-dot');
    if (!pill) return;
    if (online) {
        pill.style.background = 'var(--green-faint)';
        pill.style.borderColor = '#bbf7d0';
        pill.style.color = 'var(--green)';
        if (dot) dot.style.background = 'var(--green)';
        if (label) label.textContent = 'System Online';
    } else {
        pill.style.background = 'var(--red-faint)';
        pill.style.borderColor = '#fecaca';
        pill.style.color = 'var(--red)';
        if (dot) dot.style.background = 'var(--red)';
        if (label) label.textContent = 'Reconnecting…';
    }
}

// ── Dashboard update ──────────────────────────────────────
function updateDashboard(data) {
    updateMetricsCards(data);
    updateTrafficChart(data);
    updateProtocolChart(data);
    updateLiveSessions(data);
    updateThreatFeed(data);
    updateSystemResources(data);
}

function updateMetricsCards(data) {
    const activeSessions = data.latest_threats ? data.latest_threats.length : 0;
    document.getElementById('metric-sessions').textContent = activeSessions;

    const totalBytes = data.metrics?.total_bytes || 0;
    document.getElementById('metric-traffic').textContent = formatBytes(totalBytes);

    const uniqueIPs = data.latest_threats
        ? new Set(data.latest_threats.map(t => t.src_ip)).size : 0;
    document.getElementById('metric-unique-ips').textContent = uniqueIPs;

    const protocols = Object.keys(data.protocols || {}).length;
    document.getElementById('metric-apps').textContent = protocols;
}

function updateTrafficChart(data) {
    if (!trafficChart) return;
    const now = Date.now();
    const timeDiff = (now - lastUpdateTime) / 1000;
    const totalBytes = data.metrics?.total_bytes || 0;
    const kbPerSecond = timeDiff > 0 ? Math.max(0, (totalBytes - lastTotalBytes) / timeDiff / 1024) : 0;
    lastTotalBytes = totalBytes;
    lastUpdateTime = now;
    chartLabels.push(new Date().toLocaleTimeString());
    chartBytesData.push(kbPerSecond.toFixed(2));
    if (chartLabels.length > MAX_CHART_POINTS) { chartLabels.shift(); chartBytesData.shift(); }
    trafficChart.update('none');
}

function updateProtocolChart(data) {
    if (!protocolChart) return;
    const protocols = data.protocols || {};
    protocolData.TCP = protocolData.UDP = protocolData.ICMP = protocolData.Other = 0;
    Object.keys(protocols).forEach(key => {
        const name = getProtocolName(key);
        if (protocolData.hasOwnProperty(name)) protocolData[name] += protocols[key];
        else protocolData.Other += protocols[key];
    });
    protocolChart.data.datasets[0].data = [
        protocolData.TCP, protocolData.UDP, protocolData.ICMP, protocolData.Other
    ];
    protocolChart.update('none');
}

function updateLiveSessions(data) {
    const tbody = document.getElementById('sessions-table-body');
    const countBadge = document.getElementById('live-session-count');
    if (!data.latest_threats || data.latest_threats.length === 0) {
        if (tbody) tbody.innerHTML = `<tr class="empty-row"><td colspan="10"><div class="empty-state"><i class="fas fa-inbox"></i><p>No active sessions</p></div></td></tr>`;
        if (countBadge) countBadge.textContent = '0';
        return;
    }
    liveSessions = data.latest_threats.slice(0, 50).map((threat) => {
        const isMalicious = threat.verdict === 1;
        return {
            id: sessionIdCounter++,
            srcIp: threat.src_ip,
            dstIp: threat.dst_ip,
            protocol: getProtocolName(threat.protocol),
            port: threat.dst_port,
            state: isMalicious ? 'BLOCKED' : 'ESTABLISHED',
            bytes: Math.floor(Math.random() * 1000000),
            duration: Math.floor(Math.random() * 300),
            application: isMalicious ? threat.attack_type : 'HTTP/HTTPS',
            user: 'system',
            isMalicious
        };
    });
    renderSessionsTable();
    if (countBadge) countBadge.textContent = liveSessions.length;
}

function renderSessionsTable() {
    const tbody = document.getElementById('sessions-table-body');
    if (!tbody) return;
    const search = document.getElementById('search-sessions')?.value.toLowerCase() || '';
    const protoF = document.getElementById('proto-filter')?.value || '';
    const stateF = document.getElementById('state-filter')?.value || '';

    let sessions = liveSessions.filter(s => {
        const matchSearch = !search ||
            s.srcIp.toLowerCase().includes(search) ||
            s.dstIp.toLowerCase().includes(search) ||
            s.application.toLowerCase().includes(search) ||
            s.user.toLowerCase().includes(search);
        const matchProto = !protoF || s.protocol === protoF;
        const matchState = !stateF || s.state === stateF;
        const matchIP = !activeIPFilter || s.srcIp === activeIPFilter || s.dstIp === activeIPFilter;
        return matchSearch && matchProto && matchState && matchIP;
    });

    if (sessions.length === 0) {
        tbody.innerHTML = `<tr class="empty-row"><td colspan="10"><div class="empty-state"><i class="fas fa-search"></i><p>No sessions match your filters</p></div></td></tr>`;
        return;
    }

    tbody.innerHTML = '';
    sessions.forEach(s => {
        const tr = document.createElement('tr');
        const protoClass = s.protocol.toLowerCase();
        const stateClass = s.state === 'BLOCKED' ? 'blocked' : s.state === 'ESTABLISHED' ? 'established' : 'new';
        
        // Add click handler to entire row
        tr.addEventListener('click', (e) => {
            // Don't trigger if clicking on an IP address or button
            if (e.target.classList.contains('ip-cell') || e.target.closest('.row-btn')) {
                return;
            }
            showSessionModal(s);
        });
        
        tr.innerHTML = `
            <td class="ip-cell" onclick="event.stopPropagation(); filterByIP('${s.srcIp}')">${s.srcIp}</td>
            <td class="ip-cell text-secondary" style="font-family:'DM Mono',monospace;font-size:12.5px" onclick="event.stopPropagation(); filterByIP('${s.dstIp}')">${s.dstIp}</td>
            <td><span class="proto-tag ${protoClass}">${s.protocol}</span></td>
            <td style="font-family:'DM Mono',monospace;font-size:12.5px;color:var(--t3)">${s.port}</td>
            <td><span class="state-tag ${stateClass}">${s.state}</span></td>
            <td style="font-family:'DM Mono',monospace;font-size:12px">${formatBytes(s.bytes)}</td>
            <td style="font-family:'DM Mono',monospace;font-size:12px">${formatDuration(s.duration)}</td>
            <td>${s.application}</td>
            <td style="color:var(--t3)">${s.user}</td>
            <td><button class="btn-icon row-btn" title="Details" onclick="event.stopPropagation(); showSessionModal(${JSON.stringify(s).replace(/"/g, '&quot;')})"><i class="fas fa-info-circle"></i></button></td>
        `;
        tbody.appendChild(tr);
    });
}

function updateThreatFeed(data) {
    const feed = document.getElementById('threat-feed');
    const badge = document.getElementById('threat-count');
    if (!data.latest_threats || data.latest_threats.length === 0) {
        if (feed) feed.innerHTML = `<div class="empty-state"><i class="fas fa-shield-halved"></i><p>No threats detected</p></div>`;
        if (badge) badge.textContent = '0';
        return;
    }
    const threats = data.latest_threats.filter(t => t.verdict === 1);
    if (badge) badge.textContent = threats.length;
    if (threats.length === 0) {
        if (feed) feed.innerHTML = `<div class="empty-state"><i class="fas fa-shield-halved"></i><p>No threats detected</p></div>`;
        return;
    }
    if (feed) {
        feed.innerHTML = '';
        threats.slice(0, 20).forEach(threat => {
            const div = document.createElement('div');
            div.className = 'threat-item critical';
            div.innerHTML = `
                <div class="threat-header">
                    <span class="threat-name">${threat.attack_type}</span>
                    <span class="threat-conf">${(threat.confidence * 100).toFixed(1)}%</span>
                </div>
                <div class="threat-ips">${threat.src_ip} → ${threat.dst_ip}:${threat.dst_port}</div>
                <div class="threat-time">${new Date(threat.timestamp).toLocaleTimeString()}</div>
            `;
            feed.appendChild(div);
        });
    }
}

function updateSystemResources(data) {
    const m = data.metrics || {};
    const setRes = (valId, fillId, val) => {
        const el = document.getElementById(valId);
        const fill = document.getElementById(fillId);
        if (el) el.textContent = `${val}%`;
        if (fill) fill.style.width = `${val}%`;
    };
    setRes('cpu-val',  'cpu-fill',  m.cpu    || 0);
    setRes('mem-val',  'mem-fill',  m.memory || 0);
    setRes('disk-val', 'disk-fill', m.disk   || 0);
    const rules = document.getElementById('active-rules-count');
    const blocked = document.getElementById('blocked-ips-count');
    if (rules) rules.textContent = m.active_rules || 0;
    if (blocked) blocked.textContent = m.active_rules || 0;
}

// ── Event listeners ───────────────────────────────────────
function setupListeners() {
    console.log('  📌 Setting up button listeners...');
    
    const btnRefresh = document.getElementById('btn-refresh');
    if (btnRefresh) {
        btnRefresh.addEventListener('click', () => {
            console.log('🔄 Refresh button clicked!');
            const icon = btnRefresh.querySelector('i');
            if (icon) { 
                icon.style.animation = 'spin 0.5s linear'; 
                setTimeout(() => icon.style.animation = '', 500); 
            }
        });
    }

    const btnExport = document.getElementById('btn-export');
    if (btnExport) {
        btnExport.addEventListener('click', () => {
            console.log('💾 Export button clicked!');
            if (liveSessions.length === 0) return;
            const rows = [['Source IP','Destination IP','Protocol','Port','State','Bytes','Duration','Application','User']];
            liveSessions.forEach(s => rows.push([s.srcIp,s.dstIp,s.protocol,s.port,s.state,s.bytes,s.duration,s.application,s.user]));
            const csv = rows.map(r => r.join(',')).join('\n');
            const a = document.createElement('a');
            a.href = 'data:text/csv,' + encodeURIComponent(csv);
            a.download = `sessions_${Date.now()}.csv`;
            a.click();
            console.log('  ✅ CSV downloaded');
        });
    }

    const searchInput = document.getElementById('search-sessions');
    searchInput?.addEventListener('input', renderSessionsTable);

    const protoFilter = document.getElementById('proto-filter');
    const stateFilter = document.getElementById('state-filter');
    protoFilter?.addEventListener('change', renderSessionsTable);
    stateFilter?.addEventListener('change', renderSessionsTable);

    const autoRefreshToggle = document.getElementById('auto-refresh-toggle');
    autoRefreshToggle?.addEventListener('change', (e) => {
        console.log('🔄 Auto-refresh:', e.target.checked ? 'ON' : 'OFF');
    });
    
    console.log('  ✅ Event listeners attached');
}

// ── Init ──────────────────────────────────────────────────
window.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 Dashboard initializing...');
    console.log('1. Initializing charts...');
    initCharts();
    console.log('2. Connecting WebSocket...');
    connectWebSocket();
    console.log('3. Setting up event listeners...');
    setupListeners();
    console.log('4. Setting up interactive features...');
    setupInteractiveListeners();
    console.log('✅ Dashboard ready!');
});


// ══════════════════════════════════════════════════════════
// INTERACTIVE FEATURES
// ══════════════════════════════════════════════════════════

// Track active IP filter
let activeIPFilter = null;

// ── Session Detail Modal ──────────────────────────────────
function showSessionModal(session) {
    console.log('📊 Opening session detail modal:', session);
    
    const modal = document.getElementById('session-modal');
    
    // Populate basic info
    document.getElementById('modal-src-ip').textContent = session.srcIp;
    document.getElementById('modal-dst-ip').textContent = session.dstIp;
    document.getElementById('modal-protocol').textContent = session.protocol;
    document.getElementById('modal-port').textContent = session.port;
    document.getElementById('modal-application').textContent = session.application;
    document.getElementById('modal-bytes').textContent = formatBytes(session.bytes);
    document.getElementById('modal-duration').textContent = formatDuration(session.duration);
    
    // Set state with color
    const stateEl = document.getElementById('modal-state');
    stateEl.textContent = session.state;
    stateEl.className = 'modal-info-value ' + (session.isMalicious ? 'threat' : 'safe');
    
    // Generate ML model scores (simulated - would come from backend in real scenario)
    const baseScore = session.isMalicious ? 0.75 + Math.random() * 0.2 : 0.1 + Math.random() * 0.15;
    const rfScore = (baseScore + Math.random() * 0.05).toFixed(2);
    const xgbScore = (baseScore + Math.random() * 0.05).toFixed(2);
    const isoScore = (baseScore + Math.random() * 0.05).toFixed(2);
    const lstmScore = (baseScore + Math.random() * 0.05).toFixed(2);
    
    const scoreClass = session.isMalicious ? 'threat' : '';
    document.getElementById('ml-score-rf').textContent = (rfScore * 100).toFixed(1) + '%';
    document.getElementById('ml-score-rf').className = 'ml-score-value ' + scoreClass;
    document.getElementById('ml-score-xgb').textContent = (xgbScore * 100).toFixed(1) + '%';
    document.getElementById('ml-score-xgb').className = 'ml-score-value ' + scoreClass;
    document.getElementById('ml-score-iso').textContent = (isoScore * 100).toFixed(1) + '%';
    document.getElementById('ml-score-iso').className = 'ml-score-value ' + scoreClass;
    document.getElementById('ml-score-lstm').textContent = (lstmScore * 100).toFixed(1) + '%';
    document.getElementById('ml-score-lstm').className = 'ml-score-value ' + scoreClass;
    
    // Verdict
    const verdictEl = document.getElementById('modal-verdict');
    verdictEl.textContent = session.isMalicious ? 'THREAT DETECTED' : 'SAFE';
    verdictEl.className = 'modal-info-value ' + (session.isMalicious ? 'threat' : 'safe');
    
    // Confidence (average of model scores)
    const avgConfidence = ((parseFloat(rfScore) + parseFloat(xgbScore) + parseFloat(isoScore) + parseFloat(lstmScore)) / 4 * 100).toFixed(1);
    document.getElementById('modal-confidence').textContent = avgConfidence + '%';
    document.getElementById('modal-confidence').className = 'modal-info-value ' + scoreClass;
    
    // Store session data for action buttons
    modal.dataset.srcIp = session.srcIp;
    modal.dataset.dstIp = session.dstIp;
    
    // Show modal
    modal.classList.add('active');
}

function closeSessionModal() {
    const modal = document.getElementById('session-modal');
    modal.classList.remove('active');
}

// ── IP Address Filtering ──────────────────────────────────
function filterByIP(ip) {
    console.log('🔍 Filtering by IP:', ip);
    
    activeIPFilter = ip;
    
    // Add filter badge to section title
    const sectionLeft = document.querySelector('.section-left');
    let filterBadge = document.getElementById('ip-filter-badge');
    
    if (!filterBadge) {
        filterBadge = document.createElement('span');
        filterBadge.id = 'ip-filter-badge';
        filterBadge.className = 'filter-badge';
        sectionLeft.appendChild(filterBadge);
    }
    
    filterBadge.innerHTML = `
        <i class="fas fa-filter"></i>
        <span>Filtered: ${ip}</span>
        <button onclick="clearIPFilter()"><i class="fas fa-times"></i></button>
    `;
    
    // Re-render table with filter
    renderSessionsTable();
    
    // Highlight filtered IPs
    document.querySelectorAll('.ip-cell').forEach(cell => {
        if (cell.textContent.trim() === ip) {
            cell.classList.add('filtered');
        } else {
            cell.classList.remove('filtered');
        }
    });
}

function clearIPFilter() {
    console.log('🔍 Clearing IP filter');
    
    activeIPFilter = null;
    
    const filterBadge = document.getElementById('ip-filter-badge');
    if (filterBadge) {
        filterBadge.remove();
    }
    
    // Remove highlights
    document.querySelectorAll('.ip-cell').forEach(cell => {
        cell.classList.remove('filtered');
    });
    
    // Re-render table
    renderSessionsTable();
}

// ── Protocol Chart Interaction ────────────────────────────
let hiddenProtocols = new Set();

function toggleProtocolInChart(protocolName) {
    console.log('📊 Toggling protocol:', protocolName);
    
    if (hiddenProtocols.has(protocolName)) {
        hiddenProtocols.delete(protocolName);
    } else {
        hiddenProtocols.add(protocolName);
    }
    
    updateProtocolChartWithHidden();
}

function updateProtocolChartWithHidden() {
    if (!protocolChart) return;
    
    const visibleData = ['TCP', 'UDP', 'ICMP', 'Other'].map(proto => 
        hiddenProtocols.has(proto) ? 0 : protocolData[proto]
    );
    
    protocolChart.data.datasets[0].data = visibleData;
    protocolChart.update('none');
}

// ── Setup Interactive Listeners ───────────────────────────
function setupInteractiveListeners() {
    console.log('  🎯 Setting up interactive features...');
    
    // Modal close handlers
    document.getElementById('modal-close-btn').addEventListener('click', closeSessionModal);
    document.getElementById('session-modal').addEventListener('click', (e) => {
        if (e.target.id === 'session-modal') {
            closeSessionModal();
        }
    });
    
    // Escape key to close modal
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            closeSessionModal();
        }
    });
    
    // Block IP button
    document.getElementById('modal-block-btn').addEventListener('click', () => {
        const modal = document.getElementById('session-modal');
        const ip = modal.dataset.srcIp;
        console.log('🚫 Blocking IP:', ip);
        alert(`IP ${ip} has been added to the block list.\n\nNote: This is a demo action. In production, this would update firewall rules.`);
        closeSessionModal();
    });
    
    // Whitelist button
    document.getElementById('modal-whitelist-btn').addEventListener('click', () => {
        const modal = document.getElementById('session-modal');
        const ip = modal.dataset.srcIp;
        console.log('✅ Whitelisting IP:', ip);
        alert(`IP ${ip} has been added to the whitelist.\n\nNote: This is a demo action. In production, this would update firewall rules.`);
        closeSessionModal();
    });
    
    // Protocol chart legend click handler
    if (protocolChart) {
        const canvas = document.getElementById('protocolChart');
        canvas.style.cursor = 'pointer';
        
        protocolChart.options.plugins.legend.onClick = (e, legendItem, legend) => {
            const protocolName = legendItem.text;
            toggleProtocolInChart(protocolName);
            
            // Update legend item appearance
            if (hiddenProtocols.has(protocolName)) {
                legendItem.hidden = true;
                legendItem.fontColor = '#999';
                legendItem.strikethrough = true;
            } else {
                legendItem.hidden = false;
                legendItem.fontColor = '#71717a';
                legendItem.strikethrough = false;
            }
        };
    }
    
    console.log('  ✅ Interactive features ready!');
}
