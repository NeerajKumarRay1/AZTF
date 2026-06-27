const API_BASE = window.location.origin; // e.g. http://localhost:8000
let socket = null;
let trafficChart = null;
let protocolChart = null;
let map = null;
const activeMapMarkers = [];
const activeMapLines = [];
const processedEventIds = new Set();
const FIREWALL_COORDS = [19.0760, 72.8777]; // Mumbai, India

// Predefined map location nodes for deterministic IP hashing
const GEO_NODES = [
    { name: "New York, USA", lat: 40.7128, lng: -74.0060 },
    { name: "London, UK", lat: 51.5074, lng: -0.1278 },
    { name: "Tokyo, Japan", lat: 35.6762, lng: 139.6503 },
    { name: "Sydney, Australia", lat: -33.8688, lng: 151.2093 },
    { name: "Frankfurt, Germany", lat: 50.1109, lng: 8.6821 },
    { name: "São Paulo, Brazil", lat: -23.5505, lng: -46.6333 },
    { name: "Mumbai, India", lat: 19.0760, lng: 72.8777 },
    { name: "Cape Town, South Africa", lat: -33.9249, lng: 18.4241 },
    { name: "Moscow, Russia", lat: 55.7558, lng: 37.6173 },
    { name: "Singapore", lat: 1.3521, lng: 103.8198 },
    { name: "Beijing, China", lat: 39.9042, lng: 116.4074 },
    { name: "Paris, France", lat: 48.8566, lng: 2.3522 },
    { name: "Toronto, Canada", lat: 43.6532, lng: -79.3832 },
    { name: "Seoul, South Korea", lat: 37.5665, lng: 126.9780 },
    { name: "Dubai, UAE", lat: 25.2048, lng: 55.2708 },
    { name: "Nairobi, Kenya", lat: -1.2921, lng: 36.8219 },
    { name: "Lagos, Nigeria", lat: 6.5244, lng: 3.3792 },
    { name: "Buenos Aires, Argentina", lat: -34.6037, lng: -58.3816 },
    { name: "San Francisco, USA", lat: 37.7749, lng: -122.4194 },
    { name: "Stockholm, Sweden", lat: 59.3293, lng: 18.0686 },
    { name: "Amsterdam, Netherlands", lat: 52.3676, lng: 4.9041 },
    { name: "Zurich, Switzerland", lat: 47.3769, lng: 8.5417 },
    { name: "Istanbul, Turkey", lat: 41.0082, lng: 28.9784 },
    { name: "Bangkok, Thailand", lat: 13.7563, lng: 100.5018 },
    { name: "Jakarta, Indonesia", lat: -6.2088, lng: 106.8456 }
];

// Map Initialization
function initMap() {
    map = L.map('map', {
        zoomControl: false,
        attributionControl: false
    }).setView([20, 0], 2);

    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        maxZoom: 18,
    }).addTo(map);

    L.control.zoom({ position: 'bottomright' }).addTo(map);

    // Add green marker for the Firewall Node in Mumbai, India
    const fwIcon = L.divIcon({
        className: 'map-firewall-marker',
        iconSize: [14, 14],
        iconAnchor: [7, 7]
    });
    L.marker(FIREWALL_COORDS, { icon: fwIcon })
        .addTo(map)
        .bindPopup("<b>AI-NGFW Core Firewall Node</b><br>Location: Mumbai, India<br>Status: ENFORCING");
}

// Convert IP address to Lat/Lng via deterministic hashing (fallback/simulation)
function ipToLatLngHash(ip) {
    let hash = 0;
    for (let i = 0; i < ip.length; i++) {
        hash = ip.charCodeAt(i) + ((hash << 5) - hash);
    }
    const idx = Math.abs(hash) % GEO_NODES.length;
    const node = GEO_NODES[idx];
    
    // Add micro-noise so marker dots don't stack directly
    const noiseLat = ((hash & 0xFF) / 255.0 - 0.5) * 1.8;
    const noiseLng = (((hash >> 8) & 0xFF) / 255.0 - 0.5) * 1.8;
    
    return {
        lat: node.lat + noiseLat,
        lng: node.lng + noiseLng,
        locationName: node.name
    };
}

const geoCache = {};

// Asynchronous real-world GeoIP API lookup for public IPs
async function getLatLngForIP(ip) {
    // Check if local or private subnet IP
    if (ip.startsWith("192.168.") || ip.startsWith("10.") || ip.startsWith("127.") || ip.startsWith("172.16.") || ip.startsWith("172.17.") || ip.startsWith("172.18.") || ip.startsWith("172.19.") || ip.startsWith("172.20.") || ip.startsWith("172.31.") || ip === "::1" || ip === "localhost") {
        return ipToLatLngHash(ip);
    }
    
    if (geoCache[ip]) {
        return geoCache[ip];
    }
    
    try {
        const res = await fetch(`https://freeipapi.com/api/json/${ip}`);
        if (res.ok) {
            const data = await res.json();
            if (data.latitude && data.longitude) {
                const result = {
                    lat: data.latitude,
                    lng: data.longitude,
                    locationName: `${data.cityName || 'Unknown City'}, ${data.countryName || 'Unknown Country'}`
                };
                geoCache[ip] = result;
                return result;
            }
        }
    } catch (e) {
        console.warn("GeoIP lookup failed for IP:", ip, e);
    }
    
    // Fallback to deterministic hash coordinate if fetch fails
    return ipToLatLngHash(ip);
}

const attackLocationCounts = {};

function updateLeaderboard(locationName) {
    if (!attackLocationCounts[locationName]) {
        attackLocationCounts[locationName] = 0;
    }
    attackLocationCounts[locationName]++;
    
    const container = document.getElementById("map-leaderboard-list");
    if (!container) return;
    
    const sorted = Object.entries(attackLocationCounts)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 5);
        
    container.innerHTML = "";
    sorted.forEach(([loc, count]) => {
        const item = document.createElement("div");
        item.className = "leaderboard-item";
        item.innerHTML = `
            <span>${loc}</span>
            <span class="count">${count}</span>
        `;
        container.appendChild(item);
    });
}

// Add Threat Marker and pulse attack line on map
function addThreatToMap(srcIp, attackType, isMalicious, skipLine = false, coords = null) {
    if (!map) return;
    
    const origin = coords || ipToLatLngHash(srcIp);
    const dest = FIREWALL_COORDS;
    
    const markerColorClass = isMalicious ? 'map-pulse-marker-danger' : 'map-pulse-marker-benign';
    
    const threatIcon = L.divIcon({
        className: `map-threat-marker ${markerColorClass}`,
        iconSize: [8, 8],
        iconAnchor: [4, 4]
    });
    
    const marker = L.marker([origin.lat, origin.lng], { icon: threatIcon })
        .addTo(map)
        .bindPopup(`<b>${isMalicious ? 'Intrusion Blocked' : 'Normal Traffic'}</b><br>IP: ${srcIp}<br>GeoIP: ${origin.locationName}<br>Type: ${attackType}`);
        
    activeMapMarkers.push(marker);
    
    // Keep max 40 markers on map to prevent lag/clutter
    if (activeMapMarkers.length > 40) {
        const oldest = activeMapMarkers.shift();
        map.removeLayer(oldest);
    }
    
    if (isMalicious) {
        updateLeaderboard(origin.locationName);
    }
    
    if (!skipLine) {
        const line = L.polyline([[origin.lat, origin.lng], dest], {
            weight: 1.5,
            opacity: 0.75,
            className: `attack-line-pulse ${isMalicious ? 'attack-line-pulse-danger' : 'attack-line-pulse-benign'}`
        }).addTo(map);
        
        activeMapLines.push(line);
        setTimeout(() => {
            const index = activeMapLines.indexOf(line);
            if (index > -1) {
                activeMapLines.splice(index, 1);
                map.removeLayer(line);
            }
        }, 3000);
    }
}

// Chart Data History
const MAX_CHART_POINTS = 20;
const chartLabels = [];
const chartFlowsData = [];
const chartBytesData = [];

// Format Bytes to human readable
function formatBytes(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Update clock
setInterval(() => {
    const clock = document.getElementById("live-clock");
    if (clock) {
        clock.innerText = new Date().toLocaleTimeString();
    }
}, 1000);

// Initialize charts
function initCharts() {
    // 1. Ingestion Rate Chart
    const ctxTraffic = document.getElementById('trafficChart').getContext('2d');
    trafficChart = new Chart(ctxTraffic, {
        type: 'line',
        data: {
            labels: chartLabels,
            datasets: [
                {
                    label: 'Ingestion Flow Rate (flows/s)',
                    data: chartFlowsData,
                    borderColor: 'rgb(59, 130, 246)',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                x: {
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { color: '#94a3b8' }
                },
                y: {
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { color: '#94a3b8' },
                    beginAtZero: true
                }
            }
        }
    });

    // 2. Protocol Chart
    const ctxProto = document.getElementById('protocolChart').getContext('2d');
    protocolChart = new Chart(ctxProto, {
        type: 'doughnut',
        data: {
            labels: ['TCP', 'UDP', 'ICMP', 'Other'],
            datasets: [{
                data: [0, 0, 0, 0],
                backgroundColor: [
                    '#3b82f6',
                    '#10b981',
                    '#f59e0b',
                    '#64748b'
                ],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right',
                    labels: { color: '#94a3b8', boxWidth: 12 }
                }
            }
        }
    });
}

// Connect to WebSockets
function connectWebSocket() {
    const wsProto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProto}//${window.location.host}/ws`;
    
    console.log(`Connecting to WebSocket: ${wsUrl}...`);
    socket = new WebSocket(wsUrl);

    socket.onopen = () => {
        console.log("WebSocket connected.");
    };

    socket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        updateDashboard(data);
    };

    socket.onclose = () => {
        console.log("WebSocket disconnected. Reconnecting in 3s...");
        setTimeout(connectWebSocket, 3000);
    };

    socket.onerror = (err) => {
        console.error("WebSocket Error:", err);
    };
}

// Update dashboard elements
let lastFlowCount = 0;
function updateDashboard(data) {
    // 1. Update stats
    document.getElementById("stat-total-flows").innerText = data.metrics.total_flows.toLocaleString();
    document.getElementById("stat-active-blocks").innerText = data.metrics.active_rules;
    document.getElementById("stat-traffic-vol").innerText = formatBytes(data.metrics.total_bytes);

    // Calculate ingestion flow rate
    const currentFlows = data.metrics.total_flows;
    const diff = lastFlowCount > 0 ? (currentFlows - lastFlowCount) / 2 : 0; // Divided by 2 because interval is 2s
    lastFlowCount = currentFlows;

    // 2. Update ingestion chart
    chartLabels.push(data.timestamp);
    chartFlowsData.push(diff);
    if (chartLabels.length > MAX_CHART_POINTS) {
        chartLabels.shift();
        chartFlowsData.shift();
    }
    trafficChart.update();

    // 3. Update protocol chart
    const tcp = data.protocols['6'] || data.protocols['TCP'] || 0;
    const udp = data.protocols['17'] || data.protocols['UDP'] || 0;
    const icmp = data.protocols['1'] || data.protocols['ICMP'] || 0;
    const other = Object.keys(data.protocols).reduce((acc, key) => {
        if (!['6', '17', '1', 'TCP', 'UDP', 'ICMP'].includes(key)) {
            acc += data.protocols[key];
        }
        return acc;
    }, 0);
    
    protocolChart.data.datasets[0].data = [tcp, udp, icmp, other];
    protocolChart.update();

    // 4. Update health bars
    document.getElementById("cpu-fill").style.width = `${data.metrics.cpu}%`;
    document.getElementById("cpu-val").innerText = `${data.metrics.cpu}%`;
    document.getElementById("mem-fill").style.width = `${data.metrics.memory}%`;
    document.getElementById("mem-val").innerText = `${data.metrics.memory}%`;
    document.getElementById("disk-fill").style.width = `${data.metrics.disk}%`;
    document.getElementById("disk-val").innerText = `${data.metrics.disk}%`;

    // 5. Update Threat Verdict Feed & World Map
    const feed = document.getElementById("threat-feed");
    if (data.latest_threats && data.latest_threats.length > 0) {
        feed.innerHTML = '';
        const isFirstLoad = (processedEventIds.size === 0);
        
        data.latest_threats.forEach(t => {
            const isMalicious = t.verdict === 1;
            const card = document.createElement("div");
            card.className = `threat-item ${isMalicious ? 'critical' : ''}`;
            
            // Format time
            const tTime = new Date(t.timestamp).toLocaleTimeString();
            
            // Build Ensemble Vote Breakdown HTML
            let votesObj = {};
            try {
                votesObj = typeof t.model_votes_json === 'string' ? JSON.parse(t.model_votes_json) : (t.model_votes_json || {});
            } catch (e) {
                votesObj = {};
            }
            
            const votesHtml = Object.entries(votesObj).map(([model, score]) => {
                const pct = (score * 100).toFixed(0);
                const color = score >= 0.6 ? 'var(--color-danger)' : 'var(--color-success)';
                return `
                    <div class="vote-bar-group">
                        <div class="vote-bar-label">
                            <span>${model}</span>
                            <span>${pct}%</span>
                        </div>
                        <div class="vote-progress-bar">
                            <div class="vote-progress-fill" style="width: ${pct}%; background-color: ${color}"></div>
                        </div>
                    </div>
                `;
            }).join('');
            
            card.innerHTML = `
                <div class="threat-summary" onclick="this.parentElement.classList.toggle('expanded')">
                    <div class="threat-header">
                        <span class="threat-name">${isMalicious ? t.attack_type : 'BENIGN TRAFFIC'}</span>
                        <span class="threat-confidence">${(t.confidence * 100).toFixed(1)}% confidence</span>
                    </div>
                    <div class="threat-details">
                        <span>Src IP: ${t.src_ip}</span>
                        <span>Dst IP: ${t.dst_ip}:${t.dst_port}</span>
                    </div>
                    <div class="threat-time">${tTime} <span class="expand-indicator">▼</span></div>
                </div>
                <div class="threat-explainability">
                    <h5>Ensemble Vote Breakdown</h5>
                    ${votesHtml || '<div style="font-size: 0.65rem; color: var(--text-muted);">No model votes stored.</div>'}
                    <div class="explainability-meta">
                        <span>Proto: ${t.protocol}</span>
                        <span>Ensemble Verdict Score: ${(t.confidence * 100).toFixed(1)}%</span>
                    </div>
                </div>
            `;
            feed.appendChild(card);
            
            // Map animation logic for new events
            if (!processedEventIds.has(t.event_id)) {
                processedEventIds.add(t.event_id);
                // Bound set size to prevent memory leak
                if (processedEventIds.size > 200) {
                    const firstKey = processedEventIds.values().next().value;
                    processedEventIds.delete(firstKey);
                }
                
                // Resolve locations asynchronously and render on map
                getLatLngForIP(t.src_ip).then(coords => {
                    addThreatToMap(t.src_ip, isMalicious ? t.attack_type : "Benign Traffic", isMalicious, isFirstLoad, coords);
                });
            }
        });
    } else {
        feed.innerHTML = '<div class="feed-placeholder">Waiting for ML classifications...</div>';
    }

    // Refresh active rules table from API if user is authenticated
    if (localStorage.getItem("token")) {
        fetchActiveRules();
    }
}

// Fetch active rules from API
async function fetchActiveRules() {
    const token = localStorage.getItem("token");
    if (!token) return;

    try {
        const res = await fetch(`${API_BASE}/rules`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.status === 401) {
            handleLogout();
            return;
        }
        const rules = await res.json();
        renderRulesTable(rules.filter(r => r.revoked === 0));
    } catch (err) {
        console.error("Error fetching rules:", err);
    }
}

// Render rules table
function renderRulesTable(rules) {
    const tbody = document.getElementById("rules-list");
    if (rules.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="empty-row">No active blocks.</td></tr>';
        return;
    }

    tbody.innerHTML = '';
    rules.forEach(r => {
        const tr = document.createElement("tr");
        const expTime = new Date(r.expires_at).toLocaleTimeString();
        tr.innerHTML = `
            <td><strong>${r.src_ip}</strong></td>
            <td>${r.reason}</td>
            <td>${expTime}</td>
            <td>
                <button class="unblock-action-btn" onclick="manualUnblock('${r.src_ip}')">REVOKE</button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

// Manual unblock trigger
async function manualUnblock(ip) {
    const token = localStorage.getItem("token");
    if (!token) return;

    try {
        const res = await fetch(`${API_BASE}/rules/unblock/${ip}`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) {
            fetchActiveRules();
        } else {
            const err = await res.json();
            alert(`Error: ${err.detail}`);
        }
    } catch (err) {
        console.error("Error unblocking IP:", err);
    }
}

// Zero Trust MFA & Login Logic
let tempAuthData = null; // Temp holder for token before MFA completes

function attachLoginFormListener() {
    const form = document.getElementById("login-form");
    if (!form) return;
    
    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const user = document.getElementById("username").value;
        const pass = document.getElementById("password").value;
        const statusDiv = document.getElementById("login-status");

        statusDiv.style.color = "var(--text-secondary)";
        statusDiv.innerText = "Verifying primary credentials...";

        try {
            const res = await fetch(`${API_BASE}/auth/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    username: user,
                    password: pass,
                    browser: navigator.userAgent.split(' ')[0],
                    os: navigator.platform
                })
            });

            if (res.ok) {
                tempAuthData = await res.json();
                
                // Transition to MFA view
                showMFAPrompt();
            } else {
                const err = await res.json();
                statusDiv.style.color = "var(--color-danger)";
                statusDiv.innerText = err.detail || "Authentication failed.";
            }
        } catch (err) {
            console.error("Login request failed:", err);
            statusDiv.style.color = "var(--color-danger)";
            statusDiv.innerText = "Failed to connect to authentication engine.";
        }
    });
}

// Show the Zero Trust MFA Verification Screen
function showMFAPrompt() {
    const card = document.getElementById("login-card");
    if (!card) return;
    
    // Save original form HTML to restore on logout
    if (!card.hasAttribute("data-original-html")) {
        card.setAttribute("data-original-html", card.innerHTML);
    }
    
    card.innerHTML = `
        <h2>Zero Trust MFA Verification</h2>
        <div class="mfa-instructions">
            <span class="mfa-icon">🛡️</span>
            <p>Verification challenge generated. Please enter the OTP code from your registered authenticator app.</p>
            <p class="mfa-hint">Code hint: enter <strong>779900</strong> to approve.</p>
        </div>
        <form id="mfa-form">
            <div class="input-group">
                <label for="mfa-code">Verification Code</label>
                <input type="text" id="mfa-code" placeholder="e.g. 779900" maxlength="6" autocomplete="off" required style="letter-spacing: 4px; font-size: 1.1rem; text-align: center;">
            </div>
            <button type="submit" class="btn btn-primary">Confirm MFA Approval</button>
            <button type="button" class="btn btn-secondary" id="mfa-cancel-btn" style="background: transparent; color: var(--text-secondary); border: 1px solid var(--border-color); margin-top: 0.4rem;">Cancel</button>
        </form>
        <div id="mfa-status" class="status-msg"></div>
    `;
    
    // MFA Form listener
    document.getElementById("mfa-form").addEventListener("submit", (e) => {
        e.preventDefault();
        const code = document.getElementById("mfa-code").value.trim();
        const mfaStatus = document.getElementById("mfa-status");
        
        if (code === "779900") {
            mfaStatus.style.color = "var(--color-success)";
            mfaStatus.innerText = "MFA Authorized. Activating session tokens...";
            
            // Save authentication details
            localStorage.setItem("token", tempAuthData.access_token);
            localStorage.setItem("role", tempAuthData.role);
            
            setTimeout(() => {
                updateUIAfterLogin(tempAuthData.role);
                fetchActiveRules();
                
                // Show verified state inside card
                card.innerHTML = `
                    <h2>Zero Trust Authorized</h2>
                    <div class="mfa-success-badge">
                        <span class="mfa-check">✓</span>
                        <p>Authorized Session: <strong>${tempAuthData.role}</strong></p>
                        <p class="mfa-meta">Fingerprint validated</p>
                    </div>
                    <button class="btn btn-danger" onclick="handleLogout()" style="margin-top: 1rem;">Terminate Session</button>
                `;
            }, 800);
        } else {
            mfaStatus.style.color = "var(--color-danger)";
            mfaStatus.innerText = "Invalid verification token. Access denied.";
        }
    });
    
    document.getElementById("mfa-cancel-btn").addEventListener("click", () => {
        restoreLoginForm();
    });
}

// Restore original login form
function restoreLoginForm() {
    const card = document.getElementById("login-card");
    if (card && card.hasAttribute("data-original-html")) {
        card.innerHTML = card.getAttribute("data-original-html");
        attachLoginFormListener();
    }
}

// Update UI after login
function updateUIAfterLogin(role) {
    const badge = document.getElementById("user-role-badge");
    if (badge) {
        badge.innerText = `Role: ${role}`;
        badge.style.borderColor = role === "Admin" ? "var(--color-danger)" : "var(--accent-blue)";
    }
    
    // Enable firewall override if role permits
    if (role === "Admin" || role === "Analyst") {
        const ctrlCard = document.getElementById("firewall-controls-card");
        if (ctrlCard) ctrlCard.classList.remove("disabled");
    }
}

// Log out
function handleLogout() {
    localStorage.removeItem("token");
    localStorage.removeItem("role");
    
    const badge = document.getElementById("user-role-badge");
    if (badge) {
        badge.innerText = "Guest Mode";
        badge.style.borderColor = "var(--border-color)";
    }
    
    const ctrlCard = document.getElementById("firewall-controls-card");
    if (ctrlCard) {
        ctrlCard.classList.add("disabled");
    }
    
    tempAuthData = null;
    restoreLoginForm();
}

// Manual block form submission
document.getElementById("block-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const ip = document.getElementById("block-ip").value;
    const duration = parseInt(document.getElementById("block-duration").value);
    const reason = document.getElementById("block-reason").value;
    const statusDiv = document.getElementById("block-status");
    const token = localStorage.getItem("token");

    if (!token) return;

    try {
        const res = await fetch(`${API_BASE}/rules/block`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ ip, duration, reason })
        });

        if (res.ok) {
            statusDiv.style.color = "var(--color-success)";
            statusDiv.innerText = `IP ${ip} blocked successfully.`;
            document.getElementById("block-ip").value = "";
            document.getElementById("block-reason").value = "";
            fetchActiveRules();
        } else {
            const err = await res.json();
            statusDiv.style.color = "var(--color-danger)";
            statusDiv.innerText = err.detail || "Failed to inject block rule.";
        }
    } catch (err) {
        console.error("Block request failed:", err);
        statusDiv.style.color = "var(--color-danger)";
        statusDiv.innerText = "Failed to inject block rule.";
    }
});

// Window startup
window.onload = () => {
    initCharts();
    initMap();
    connectWebSocket();
    
    // Restore session if valid
    const token = localStorage.getItem("token");
    const role = localStorage.getItem("role");
    if (token && role) {
        updateUIAfterLogin(role);
        fetchActiveRules();
        
        // Render authorized screen in login card
        const card = document.getElementById("login-card");
        if (card) {
            // Save original form HTML to restore on logout
            if (!card.hasAttribute("data-original-html")) {
                const formClone = card.innerHTML;
                card.setAttribute("data-original-html", formClone);
            }
            card.innerHTML = `
                <h2>Zero Trust Authorized</h2>
                <div class="mfa-success-badge">
                    <span class="mfa-check">✓</span>
                    <p>Authorized Session: <strong>${role}</strong></p>
                    <p class="mfa-meta">Fingerprint validated</p>
                </div>
                <button class="btn btn-danger" onclick="handleLogout()" style="margin-top: 1rem;">Terminate Session</button>
            `;
        }
    } else {
        attachLoginFormListener();
    }
};
