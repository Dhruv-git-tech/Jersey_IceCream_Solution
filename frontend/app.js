/* =============================================================================
   Jersey Ice Cream — Business Intelligence Suite (Growth MVP)
   All Charts, Maps, Simulated Data & Scaling Interactivity
   ============================================================================= */

const COLORS = {
    blue: '#58a6ff', green: '#3fb950', purple: '#bc8cff', red: '#f85149',
    orange: '#d29922', cyan: '#39d2c0', pink: '#f778ba', gray: '#6e7681',
};

// Chart.js defaults
Chart.defaults.color = '#8b949e';
Chart.defaults.borderColor = 'rgba(255,255,255,0.03)';
Chart.defaults.font.family = "'Inter', sans-serif";
Chart.defaults.font.size = 10;
Chart.defaults.plugins.legend.labels.usePointStyle = true;
Chart.defaults.plugins.legend.labels.pointStyleWidth = 8;
Chart.defaults.plugins.tooltip.backgroundColor = 'rgba(6,8,15,0.95)';
Chart.defaults.plugins.tooltip.borderColor = 'rgba(255,255,255,0.08)';
Chart.defaults.plugins.tooltip.borderWidth = 1;
Chart.defaults.plugins.tooltip.cornerRadius = 8;
Chart.defaults.plugins.tooltip.padding = 10;
Chart.defaults.elements.point.radius = 0;
Chart.defaults.elements.point.hoverRadius = 4;

// ─── Helpers ────────────────────────────────────────────────────────────────────

const rand = (min, max) => Math.floor(Math.random() * (max - min + 1)) + min;
const pick = arr => arr[Math.floor(Math.random() * arr.length)];
const hourLabels = n => {
    const d = [];
    const now = new Date();
    for (let i = n - 1; i >= 0; i--) {
        const dt = new Date(now - i * 36e5);
        d.push(dt.getHours().toString().padStart(2, '0') + ':00');
    }
    return d;
};
const fmtNum = n => n >= 1e7 ? (n / 1e7).toFixed(2) + ' Cr' : n >= 1e5 ? (n / 1e5).toFixed(1) + ' L' : n >= 1e3 ? (n / 1e3).toFixed(1) + 'K' : n.toString();

const VENDORS = ['Raju Kumar', 'Suresh Yadav', 'Mohd Imran', 'Srinivas Reddy', 'Lakshmi Devi', 'Ramesh Patel', 'Ajay Singh', 'Venkat Rao', 'Pradeep Sharma', 'Manoj Gupta'];
const AREAS = ['Jubilee Hills', 'Banjara Hills', 'Hitech City', 'Gachibowli', 'Madhapur', 'Kukatpally', 'Ameerpet', 'Secunderabad', 'Uppal', 'Charminar'];

// Global State for Scaling Simulator
const EXP_STATE = {
    vending: { count: 48, revenue: 1.2 },
    qcomm: { count: 21, sales: 820 },
    subs: { count: 12854, mrr: 18.4 },
    trucks: { count: 8, yield: 88.5 },
    totalAssets: 8624,
    spoilageSaved: 48200
};

// ─── DOM Ready Initializer ───────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
    initNav();
    animateKPIs();

    // Command Center Widgets
    initRevenueTrajectory();
    initAlertFeed();

    // Lazy load dashboards on section visibility
    let mapInit = false;
    new MutationObserver(() => {
        if (document.getElementById('section-operations')?.classList.contains('active') && !mapInit) {
            setTimeout(() => {
                initMap();
                initColdChainChart();
                initSupplyRefillFeed();
            }, 100);
            mapInit = true;
        }
    }).observe(document.getElementById('section-operations'), { attributes: true });

    let orchInit = false;
    new MutationObserver(() => {
        if (document.getElementById('section-orchestrator')?.classList.contains('active') && !orchInit) {
            setTimeout(initOrchestrator, 100);
            orchInit = true;
        }
    }).observe(document.getElementById('section-orchestrator'), { attributes: true });

    let expInit = false;
    new MutationObserver(() => {
        if (document.getElementById('section-expansion')?.classList.contains('active') && !expInit) {
            setTimeout(initExpansion, 100);
            expInit = true;
        }
    }).observe(document.getElementById('section-expansion'), { attributes: true });

    // Wire Interactive Storyboard Tour
    initStoryboard();

    // Auto-update dashboard metrics periodically
    setInterval(liveUpdate, 4500);
});

// ─── Navigation & Router ────────────────────────────────────────────────────────

function navTo(key) {
    const items = document.querySelectorAll('.menu-item');
    const sections = document.querySelectorAll('.section');
    const h1 = document.getElementById('page-title');
    const sub = document.getElementById('page-subtitle');

    const meta = {
        'command-center': ['Command Center', 'Strategic revenue trajectory and live risk alert feeds'],
        'orchestrator': ['Melt-Risk & Demand Orchestrator', 'Autonomous sellability scoring, flavor slot optimization & recovery actions'],
        'operations': ['Logistics & Carts', 'Live push cart telemetry map, refill dispatch queues & cold chain status'],
        'expansion': ['Smart Expansion', 'Scale simulator for high-margin vending, Q-commerce, D2C, and catering assets'],
    };

    items.forEach(i => {
        if (i.dataset.section === key) {
            i.classList.add('active');
        } else {
            i.classList.remove('active');
        }
    });

    sections.forEach(s => {
        if (s.id === `section-${key}`) {
            s.classList.add('active');
        } else {
            s.classList.remove('active');
        }
    });

    if (meta[key]) {
        if (h1) h1.textContent = meta[key][0];
        if (sub) sub.textContent = meta[key][1];
    }
}

function initNav() {
    const items = document.querySelectorAll('.menu-item');
    items.forEach(item => {
        item.addEventListener('click', e => {
            const key = item.dataset.section;
            if (!key) return; // Allow normal link navigation for pitch deck
            e.preventDefault();
            navTo(key);
            document.getElementById('sidebar')?.classList.remove('open');
        });
    });

    document.getElementById('menu-toggle')?.addEventListener('click', () => {
        document.getElementById('sidebar')?.classList.toggle('open');
    });
}

// ─── KPI Animations ─────────────────────────────────────────────────────────────

function animateKPIs() {
    document.querySelectorAll('.kpi-value[data-target]').forEach(el => {
        const target = parseFloat(el.dataset.target);
        const pfx = el.dataset.prefix || '';
        const sfx = el.dataset.suffix || '';
        const start = performance.now();
        const dur = 1500;

        function step(now) {
            const t = Math.min((now - start) / dur, 1);
            const ease = 1 - Math.pow(1 - t, 4);
            const val = target * ease;

            if (sfx === '%') el.textContent = val.toFixed(1) + sfx;
            else if (target >= 10000) el.textContent = pfx + fmtNum(Math.round(val));
            else el.textContent = pfx + Math.round(val).toLocaleString('en-IN') + sfx;

            if (t < 1) requestAnimationFrame(step);
            else {
                if (sfx === '%') el.textContent = target + sfx;
                else if (target >= 10000) el.textContent = pfx + fmtNum(target);
                else el.textContent = pfx + target.toLocaleString('en-IN') + sfx;
            }
        }
        requestAnimationFrame(step);
    });
}

// ═══════════════════════════════════════════════════════════════════════════════
// COMMAND CENTER PAGE
// ═══════════════════════════════════════════════════════════════════════════════

function initRevenueTrajectory() {
    const ctx = document.getElementById('revenue-trajectory-chart');
    if (!ctx) return;
    const months = ['Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec','Jan','Feb','Mar'];
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: months,
            datasets: [
                {
                    label: 'Revenue (₹ Cr)',
                    data: [14.2, 16.8, 21.3, 28.5, 32.1, 24.7, 18.9, 15.2, 12.8, 11.4, 13.6, 17.5],
                    backgroundColor: ctx2 => {
                        const g = ctx2.chart.ctx.createLinearGradient(0, 0, 0, 220);
                        g.addColorStop(0, 'rgba(88, 166, 255, 0.5)');
                        g.addColorStop(1, 'rgba(88, 166, 255, 0.03)');
                        return g;
                    },
                    borderRadius: 6,
                    borderSkipped: false
                },
                {
                    label: 'Cost (₹ Cr)',
                    data: [9.8, 11.2, 13.1, 17.4, 19.6, 15.3, 12.1, 10.4, 8.9, 8.2, 9.4, 11.8],
                    backgroundColor: 'rgba(248, 81, 73, 0.15)',
                    borderRadius: 6,
                    borderSkipped: false
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { position: 'top' } },
            scales: {
                x: { grid: { display: false } },
                y: { grid: { color: 'rgba(255,255,255,.03)' }, ticks: { callback: v => '₹' + v + ' Cr' } }
            }
        },
    });
}

function initAlertFeed() {
    const feed = document.getElementById('alert-feed');
    if (!feed) return;

    const alerts = [
        { type: 'critical', icon: '🚨', title: 'Stockout Danger: Mango Kulfi at Uppal Hub', detail: '8 carts report below 5 units. Autonomous dispatch queue triggered.', time: '2m ago' },
        { type: 'warning', icon: '⚠️', title: 'Freezer Temp Strain: Cart JC-802', detail: 'Sensor reports -12.0°C (threshold: -18°C). Spoilage risk rising.', time: '5m ago' },
        { type: 'success', icon: '📈', title: 'Q-Commerce integration active', detail: '2 new Gachibowli stores online. Hourly sales up 12%.', time: '18m ago' },
        { type: 'info', icon: '🤖', title: 'Slot Optimizer complete: Banjara Hills', detail: 'Planogram adjusted to family tubs based on evening weather change.', time: '25m ago' },
        { type: 'success', icon: '🎯', title: 'D2C Subscriber drive milestone', detail: 'Passed 12,800 active monthly members. MRR projection: ₹18.4L.', time: '1h ago' }
    ];

    feed.innerHTML = alerts.map(a => `
        <div class="alert-item ${a.type}">
            <span class="alert-icon">${a.icon}</span>
            <div class="alert-body">
                <div class="alert-title">${a.title}</div>
                <div class="alert-detail">${a.detail}</div>
            </div>
            <span class="alert-time">${a.time}</span>
        </div>`).join('');
}

// ═══════════════════════════════════════════════════════════════════════════════
// LOGISTICS & CARTS OPERATIONS PAGE
// ═══════════════════════════════════════════════════════════════════════════════

let map = null;
let storyCartMarker = null;

function initMap() {
    if (map) return;

    const lightMap = L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; OpenStreetMap &copy; CARTO',
        maxZoom: 20
    });

    map = L.map('live-map', { 
        center: [17.3912, 78.4867], 
        zoom: 12, 
        zoomControl: true,
        layers: [lightMap]
    });

    const statuses = ['active','active','active','active','active','low-stock','low-stock','offline'];
    
    // Seed 120 random push cart coordinates around Hyderabad
    for (let i = 0; i < 120; i++) {
        const lat = 17.3912 + (Math.random() - 0.5) * 0.12;
        const lng = 78.4867 + (Math.random() - 0.5) * 0.15;
        const status = pick(statuses);
        const size = status === 'active' ? 7 : status === 'low-stock' ? 9 : 5;
        const icon = L.divIcon({ className: `cart-marker ${status}`, iconSize: [size, size] });
        const marker = L.marker([lat, lng], { icon }).addTo(map);
        const stock = status === 'active' ? rand(40, 100) : status === 'low-stock' ? rand(3, 20) : 0;
        const sc = status === 'active' ? COLORS.green : status === 'low-stock' ? COLORS.orange : COLORS.red;
        const sl = status === 'active' ? 'Active' : status === 'low-stock' ? 'Low Stock' : 'Offline';
        marker.bindPopup(`
            <div class="popup-header">🛒 Cart JC-${String(i + 1001).padStart(4, '0')}</div>
            <div class="popup-detail"><b>Vendor:</b> ${pick(VENDORS)}</div>
            <div class="popup-detail"><b>Area:</b> ${pick(AREAS)}</div>
            <div class="popup-detail"><b>Stock:</b> ${stock} units</div>
            <div class="popup-detail"><b>Status:</b> <span class="popup-status" style="background:${sc}22;color:${sc}">${sl}</span></div>
        `, { maxWidth: 220 });
    }

    // Storyboard Specific Cart (Low stock near Uppal Stadium)
    const storyIcon = L.divIcon({ className: 'cart-marker low-stock', iconSize: [9, 9] });
    storyCartMarker = L.marker([17.3920, 78.5510], { icon: storyIcon }).addTo(map);
    storyCartMarker.bindPopup(`
        <div class="popup-header">🛒 Cart JC-6890 (Uppal Stadium)</div>
        <div class="popup-detail"><b>Vendor:</b> Raju Kumar</div>
        <div class="popup-detail"><b>Status:</b> <span class="popup-status" style="background:${COLORS.orange}22;color:${COLORS.orange}">Low Stock</span></div>
        <div class="popup-detail"><b>Stock:</b> 4 units (Mango Kulfi)</div>
        <div class="popup-detail"><b>Refill Queue:</b> Auto-queued</div>
    `, { maxWidth: 220 });

    // Custom Hyderabad Landmark Pins
    const landmarks = [
        { name: 'Rajiv Gandhi International Cricket Stadium', lat: 17.3912, lng: 78.5527, desc: '🏟️ Uppal Stadium (IPL Match Venue - +42% Demand Spurt)' },
        { name: 'Hitech City Hub', lat: 17.4483, lng: 78.3741, desc: '🏢 Corporate Hotspot (High day-time demand)' },
        { name: 'Charminar Heritage Zone', lat: 17.3616, lng: 78.4747, desc: '🕌 Evening Tourist Hub (Peak evening sales)' }
    ];

    landmarks.forEach(lm => {
        const lmIcon = L.divIcon({ className: 'cart-marker landmark-pin', iconSize: [16, 16] });
        L.marker([lm.lat, lm.lng], { icon: lmIcon }).addTo(map).bindPopup(`
            <div class="popup-header" style="color: var(--accent-cyan)">📍 ${lm.name}</div>
            <div class="popup-detail" style="margin-top: 4px;"><b>Details:</b> ${lm.desc}</div>
        `, { maxWidth: 250 });
    });

    // Warehouses
    const warehouses = [
        { name: 'Main Cold Storage - Kukatpally', lat: 17.495, lng: 78.399 },
        { name: 'Distribution Hub - Uppal', lat: 17.399, lng: 78.559 },
        { name: 'Warehouse - Miyapur', lat: 17.497, lng: 78.357 }
    ];
    warehouses.forEach(wh => {
        const icon = L.divIcon({ className: 'cart-marker warehouse', iconSize: [14, 14] });
        L.marker([wh.lat, wh.lng], { icon }).addTo(map).bindPopup(`
            <div class="popup-header">🏭 ${wh.name}</div>
            <div class="popup-detail"><b>Capacity:</b> ${rand(60, 90)}% utilized</div>
            <div class="popup-detail"><b>Temp:</b> <span style="color:${COLORS.green}">-21.3°C ✓</span></div>
        `, { maxWidth: 250 });
    });
}

function initColdChainChart() {
    const ctx = document.getElementById('cold-chain-chart');
    if (!ctx) return;
    const labels = hourLabels(24);
    const gen = (base, v) => Array.from({length: 24}, () => base + (Math.random() - 0.5) * v);

    new Chart(ctx, {
        type: 'line',
        data: {
            labels,
            datasets: [
                { label: 'Kukatpally Storage', data: gen(-20.5, 1.2), borderColor: COLORS.blue, borderWidth: 2, tension: .4 },
                { label: 'Uppal Hub', data: gen(-19.8, 1.8), borderColor: COLORS.green, borderWidth: 2, tension: .4 },
                { label: 'Miyapur Hub', data: gen(-21.0, 1.0), borderColor: COLORS.purple, borderWidth: 2, tension: .4 }
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            scales: {
                x: { grid: { display: false }, ticks: { maxTicksLimit: 8 } },
                y: { title: { display: true, text: 'Temp (°C)' }, grid: { color: 'rgba(255,255,255,.03)' }, max: -12, min: -25 }
            },
        },
    });
}

function initSupplyRefillFeed() {
    const feed = document.getElementById('supply-refill-feed');
    if (!feed) return;
    const items = [];
    for (let i = 0; i < 5; i++) {
        const priority = pick(['critical', 'high', 'medium']);
        const icon = priority === 'critical' ? '🚨' : priority === 'high' ? '⚠️' : '📦';
        const now = new Date();
        items.push(`
            <div class="refill-item ${priority}">
                <span style="font-size:16px">${icon}</span>
                <div class="refill-content">
                    <div class="refill-title"><span class="priority-badge ${priority}">${priority}</span> Cart JC-${rand(1000, 9999)} · ${pick(VENDORS)}</div>
                    <div class="refill-details">${pick(AREAS)} · Auto Refill Dispatched</div>
                </div>
                <span class="refill-time">${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}</span>
            </div>`);
    }
    feed.innerHTML = items.join('');
}

// ═══════════════════════════════════════════════════════════════════════════════
// MELT-RISK ORCHESTRATOR PAGE
// ═══════════════════════════════════════════════════════════════════════════════

let orchestratorDecayChart = null;

function initOrchestrator() {
    const tempInput = document.getElementById('orch-input-temp');
    const humInput = document.getElementById('orch-input-humidity');
    const neighInput = document.getElementById('orch-input-neighborhood');
    const teleInput = document.getElementById('orch-input-telemetry');

    if (!tempInput) return;

    tempInput.addEventListener('input', updateOrchestratorState);
    humInput.addEventListener('input', updateOrchestratorState);
    neighInput.addEventListener('change', updateOrchestratorState);
    teleInput.addEventListener('change', updateOrchestratorState);

    updateOrchestratorState();
}

function updateOrchestratorState() {
    const temp = parseInt(document.getElementById('orch-input-temp').value);
    const humidity = parseInt(document.getElementById('orch-input-humidity').value);
    const neighborhood = document.getElementById('orch-input-neighborhood').value;
    const telemetry = document.getElementById('orch-input-telemetry').value;

    document.getElementById('orch-lbl-temp').textContent = temp + '°C';
    document.getElementById('orch-lbl-humidity').textContent = humidity + '%';

    // 1. Calculate Sellable Minutes
    let baseMinutes = 320;
    if (temp > 30) baseMinutes -= (temp - 30) * 10;
    if (humidity > 50) baseMinutes -= (humidity - 50) * 1.5;
    
    let telemetryMult = 1.0;
    if (telemetry === 'strain') telemetryMult = 0.45;
    else if (telemetry === 'outage') telemetryMult = 0.12;

    let sellableMinutes = Math.max(12, Math.round(baseMinutes * telemetryMult));
    
    const sellableVal = document.getElementById('val-sellable-minutes');
    sellableVal.textContent = sellableMinutes + ' min';
    const sellableChange = document.getElementById('change-sellable-minutes');
    if (sellableMinutes > 200) {
        sellableVal.style.color = 'var(--text-primary)';
        sellableChange.textContent = 'Normal decay rate';
        sellableChange.className = 'kpi-change up';
    } else if (sellableMinutes > 80) {
        sellableVal.style.color = 'var(--accent-orange)';
        sellableChange.textContent = '⚠️ Elevated decay rate';
        sellableChange.className = 'kpi-change down';
    } else {
        sellableVal.style.color = 'var(--accent-red)';
        sellableChange.textContent = '🚨 Fast spoilage decay';
        sellableChange.className = 'kpi-change down';
    }

    // 2. Alert States
    const meltVal = document.getElementById('val-melt-risk');
    const meltChange = document.getElementById('change-melt-risk');
    if (telemetry === 'normal') {
        if (temp < 38) {
            meltVal.textContent = 'STABLE';
            meltVal.style.color = 'var(--accent-green)';
            meltChange.textContent = 'All freezers within range';
            meltChange.className = 'kpi-change up';
        } else {
            meltVal.textContent = 'ELEVATED';
            meltVal.style.color = 'var(--accent-orange)';
            meltChange.textContent = 'High ambient temp stress';
            meltChange.className = 'kpi-change down';
        }
    } else if (telemetry === 'strain') {
        meltVal.textContent = 'HIGH RISK';
        meltVal.style.color = 'var(--accent-orange)';
        meltChange.textContent = 'Compressor strain alert';
        meltChange.className = 'kpi-change down';
    } else {
        meltVal.textContent = 'CRITICAL';
        meltVal.style.color = 'var(--accent-red)';
        meltChange.textContent = 'Power loss alert dispatched';
        meltChange.className = 'kpi-change down';
    }

    // 3. Yield efficiency calculation
    let baseYield = 95.0;
    if (temp > 35 && neighborhood === 'rainy-evening') baseYield -= 22.5;
    if (temp < 25 && neighborhood === 'stadium-ipl') baseYield -= 14.2;
    if (telemetry === 'strain') baseYield -= 8.5;
    if (telemetry === 'outage') baseYield -= 26.0;
    
    let yieldVal = Math.max(45.2, baseYield + (Math.random() - 0.5) * 1.5).toFixed(1);
    const yieldEl = document.getElementById('val-yield-efficiency');
    yieldEl.textContent = yieldVal + '%';
    const yieldChange = document.getElementById('change-yield-efficiency');
    if (yieldVal > 85) {
        yieldChange.textContent = '↑ 2.4% vs normal layout';
        yieldChange.className = 'kpi-change up';
    } else {
        yieldChange.textContent = '↓ ' + (92.5 - yieldVal).toFixed(1) + '% space mismatch';
        yieldChange.className = 'kpi-change down';
    }

    document.getElementById('val-spoilage-saved').textContent = '₹' + EXP_STATE.spoilageSaved.toLocaleString('en-IN');

    // 4. Flavor Pocket Adjustments
    let pockets = [];
    const gridPockets = document.getElementById('freezer-grid-pockets');
    gridPockets.className = 'freezer-grid';
    if (telemetry === 'strain') gridPockets.classList.add('telemetry-strain');
    else if (telemetry === 'outage') gridPockets.classList.add('telemetry-outage');

    if (telemetry === 'outage') {
        pockets = [
            { sku: 'Melting Mango Cup', cat: 'cup', qty: 2, capacity: 50, demand: 'LOW', emoji: '🥭' },
            { sku: 'Melting Berry Cup', cat: 'cup', qty: 3, capacity: 50, demand: 'LOW', emoji: '🍓' },
            { sku: 'Choco Bar Supreme', cat: 'bar', qty: 5, capacity: 60, demand: 'LOW', emoji: '🍫' },
            { sku: 'Vanilla Cone Classic', cat: 'cone', qty: 8, capacity: 80, demand: 'LOW', emoji: '🍦' },
            { sku: 'Empty Slot', cat: 'empty', qty: 0, capacity: 0, demand: 'NONE', emoji: '⏹️' },
            { sku: 'Empty Slot', cat: 'empty', qty: 0, capacity: 0, demand: 'NONE', emoji: '⏹️' },
            { sku: 'Empty Slot', cat: 'empty', qty: 0, capacity: 0, demand: 'NONE', emoji: '⏹️' },
            { sku: 'Empty Slot', cat: 'empty', qty: 0, capacity: 0, demand: 'NONE', emoji: '⏹️' }
        ];
    } else if (telemetry === 'strain') {
        pockets = [
            { sku: 'Vanilla Cone Classic', cat: 'cone', qty: 35, capacity: 80, demand: 'HIGH', emoji: '🍦' },
            { sku: 'Vanilla Cone Classic', cat: 'cone', qty: 22, capacity: 80, demand: 'HIGH', emoji: '🍦' },
            { sku: 'Choco Bar Supreme', cat: 'bar', qty: 45, capacity: 60, demand: 'HIGH', emoji: '🍫' },
            { sku: 'Choco Bar Supreme', cat: 'bar', qty: 15, capacity: 60, demand: 'HIGH', emoji: '🍫' },
            { sku: 'Mango Kulfi Cup', cat: 'cup', qty: 18, capacity: 50, demand: 'MED', emoji: '🥭' },
            { sku: 'Matcha Green Tea Cup', cat: 'cup', qty: 12, capacity: 50, demand: 'MED', emoji: '🍵' },
            { sku: 'Empty Slot', cat: 'empty', qty: 0, capacity: 0, demand: 'NONE', emoji: '⏹️' },
            { sku: 'Empty Slot', cat: 'empty', qty: 0, capacity: 0, demand: 'NONE', emoji: '⏹️' }
        ];
    } else {
        if (neighborhood === 'stadium-ipl') {
            pockets = [
                { sku: 'Vanilla Cone Classic', cat: 'cone', qty: 74, capacity: 80, demand: 'HIGH', emoji: '🍦' },
                { sku: 'Vanilla Cone Classic', cat: 'cone', qty: 68, capacity: 80, demand: 'HIGH', emoji: '🍦' },
                { sku: 'Choco Bar Supreme', cat: 'bar', qty: 58, capacity: 60, demand: 'HIGH', emoji: '🍫' },
                { sku: 'Choco Bar Supreme', cat: 'bar', qty: 52, capacity: 60, demand: 'HIGH', emoji: '🍫' },
                { sku: 'Mango Kulfi Cup', cat: 'cup', qty: 47, capacity: 50, demand: 'HIGH', emoji: '🥭' },
                { sku: 'Wild Berry Sorbet Cup', cat: 'cup', qty: 44, capacity: 50, demand: 'HIGH', emoji: '🍓' },
                { sku: 'Vanilla Cup Classic', cat: 'cup', qty: 38, capacity: 50, demand: 'MED', emoji: '🍨' },
                { sku: 'Matcha Green Tea Cup', cat: 'cup', qty: 35, capacity: 50, demand: 'MED', emoji: '🍵' }
            ];
        } else if (neighborhood === 'rainy-evening') {
            pockets = [
                { sku: 'Chocolate Family Tub', cat: 'tub', qty: 26, capacity: 30, demand: 'HIGH', emoji: '🍨' },
                { sku: 'Butterscotch Family Tub', cat: 'tub', qty: 22, capacity: 30, demand: 'HIGH', emoji: '🍨' },
                { sku: 'Vanilla Cone Classic', cat: 'cone', qty: 15, capacity: 80, demand: 'LOW', emoji: '🍦' },
                { sku: 'Choco Bar Supreme', cat: 'bar', qty: 12, capacity: 60, demand: 'LOW', emoji: '🍫' },
                { sku: 'Empty Slot', cat: 'empty', qty: 0, capacity: 0, demand: 'NONE', emoji: '⏹️' },
                { sku: 'Empty Slot', cat: 'empty', qty: 0, capacity: 0, demand: 'NONE', emoji: '⏹️' },
                { sku: 'Empty Slot', cat: 'empty', qty: 0, capacity: 0, demand: 'NONE', emoji: '⏹️' },
                { sku: 'Empty Slot', cat: 'empty', qty: 0, capacity: 0, demand: 'NONE', emoji: '⏹️' }
            ];
        } else {
            pockets = [
                { sku: 'Vanilla Cone Classic', cat: 'cone', qty: 48, capacity: 80, demand: 'HIGH', emoji: '🍦' },
                { sku: 'Choco Bar Supreme', cat: 'bar', qty: 36, capacity: 60, demand: 'HIGH', emoji: '🍫' },
                { sku: 'Mango Kulfi Cup', cat: 'cup', qty: 28, capacity: 50, demand: 'MED', emoji: '🥭' },
                { sku: 'Chocolate Family Tub', cat: 'tub', qty: 18, capacity: 30, demand: 'HIGH', emoji: '🍨' },
                { sku: 'Wild Berry Sorbet Cup', cat: 'cup', qty: 24, capacity: 50, demand: 'MED', emoji: '🍓' },
                { sku: 'Matcha Green Tea Cup', cat: 'cup', qty: 15, capacity: 50, demand: 'LOW', emoji: '🍵' },
                { sku: 'Lavender Honey Cup', cat: 'cup', qty: 12, capacity: 50, demand: 'LOW', emoji: '🍯' },
                { sku: 'Butterscotch Family Tub', cat: 'tub', qty: 10, capacity: 30, demand: 'MED', emoji: '🍨' }
            ];
        }
    }

    gridPockets.innerHTML = pockets.map((p, idx) => {
        const fill = p.capacity > 0 ? (p.qty / p.capacity * 100) : 0;
        return `
            <div class="freezer-pocket ${p.cat}">
                <div class="pocket-header">
                    <span class="pocket-num">SLOT ${idx + 1}</span>
                    <span class="pocket-tag ${p.cat}">${p.cat}</span>
                </div>
                <div class="pocket-name">${p.emoji} ${p.sku}</div>
                <div class="pocket-stats">
                    <span>Stock: ${p.qty}/${p.capacity}</span>
                    <span class="pocket-demand-score ${p.demand.toLowerCase()}">Demand: ${p.demand}</span>
                </div>
                <div class="pocket-bar-bg">
                    <div class="pocket-bar ${p.cat}" style="width: ${fill}%"></div>
                </div>
            </div>`;
    }).join('');

    gridPockets.querySelectorAll('.freezer-pocket').forEach((pocket, i) => {
        setTimeout(() => pocket.classList.add('pocket-transition'), i * 30);
    });

    // 5. Update predicted decay chart and action feeds
    updateOrchestratorDecayChart(temp, telemetry);
    updateOrchestratorActions(temp, humidity, neighborhood, telemetry);
}

function updateOrchestratorDecayChart(temp, telemetry) {
    const ctx = document.getElementById('orchestrator-decay-chart');
    if (!ctx) return;

    const labels = Array.from({length: 12}, (_, i) => `${i + 1}h`);
    let sellabilityData = [];
    let temperatureData = [];
    let currentSellability = 100;
    let currentFreezerTemp = -21.5;

    if (telemetry === 'strain') currentFreezerTemp = -12.0;
    else if (telemetry === 'outage') currentFreezerTemp = 0.0;

    for (let i = 0; i < 12; i++) {
        if (telemetry === 'normal') {
            currentFreezerTemp = -21.5 + Math.sin(i / 2) * 0.5;
        } else if (telemetry === 'strain') {
            currentFreezerTemp += 0.8 + (temp - 30) * 0.05;
        } else {
            currentFreezerTemp += 1.6 + (temp - 30) * 0.12;
        }
        temperatureData.push(parseFloat(currentFreezerTemp.toFixed(1)));

        let decayRate = 0.5;
        if (currentFreezerTemp > -18) decayRate = 3.0;
        if (currentFreezerTemp > -12) decayRate = 8.0;
        if (currentFreezerTemp > -6) decayRate = 18.0;
        if (currentFreezerTemp > 0) decayRate = 35.0;

        currentSellability = Math.max(0, currentSellability - decayRate);
        sellabilityData.push(parseFloat(currentSellability.toFixed(1)));
    }

    if (orchestratorDecayChart) {
        orchestratorDecayChart.data.labels = labels;
        orchestratorDecayChart.data.datasets[0].data = sellabilityData;
        orchestratorDecayChart.data.datasets[1].data = temperatureData;
        orchestratorDecayChart.update();
    } else {
        orchestratorDecayChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels,
                datasets: [
                    { label: 'Sellable Score (%)', data: sellabilityData, borderColor: COLORS.blue, backgroundColor: COLORS.blue + '05', borderWidth: 2, tension: 0.4, fill: true, yAxisID: 'y' },
                    { label: 'Freezer Temp (°C)', data: temperatureData, borderColor: COLORS.orange, borderWidth: 1.5, tension: 0.4, borderDash: [4, 4], yAxisID: 'y1' }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { mode: 'index', intersect: false },
                scales: {
                    x: { grid: { display: false } },
                    y: { position: 'left', min: 0, max: 100, title: { display: true, text: 'Sellability %' }, grid: { color: 'rgba(255,255,255,.03)' } },
                    y1: { position: 'right', min: -25, max: 20, title: { display: true, text: 'Temp °C' }, grid: { display: false } }
                }
            }
        });
    }
}

function updateOrchestratorActions(temp, humidity, neighborhood, telemetry) {
    const feed = document.getElementById('orchestrator-actions-feed');
    const badge = document.getElementById('orch-action-count');
    if (!feed) return;

    let actions = [];

    if (telemetry === 'outage') {
        actions.push({
            id: 'act-outage-reroute',
            type: 'critical',
            emoji: '🚨',
            title: 'Critical Outage: Charminar Cart JC-1102',
            desc: 'Freezer temp at 0°C. Compressor fail. Reroute dispatch van for stock rescue and apply markdown.',
            btnText: 'Dispatch Recovery Van'
        });
    }

    if (telemetry === 'strain' || telemetry === 'outage') {
        actions.push({
            id: 'act-strain-markdown',
            type: 'warning',
            emoji: '⚠️',
            title: 'Temperature Warning: Jubilee Hills Cart JC-802',
            desc: 'Elevated temp (-12.0°C). Suggest auto-markdown of cups by 20% to clear inventory.',
            btnText: 'Deploy 20% Markdown Promo'
        });
    }

    if (neighborhood === 'stadium-ipl') {
        actions.push({
            id: 'act-stadium-refill',
            type: 'info',
            emoji: '🏏',
            title: 'IPL Crowd Spike: Uppal Cart JC-6890',
            desc: 'Stadium surge starting. Adjust freezer compartments to 100% impulse cones & bars.',
            btnText: 'Optimize Flavor Assortment'
        });
    }

    if (temp >= 40 && telemetry === 'normal') {
        actions.push({
            id: 'act-heat-alert',
            type: 'warning',
            emoji: '☀️',
            title: 'Extreme Heat: Gachibowli Cart JC-109',
            desc: 'Ambient temperature reached 41°C. Deploy thermal shield alert and 10% flash discount.',
            btnText: 'Approve Heat Discount'
        });
    }

    // Default action to avoid empty feed
    actions.push({
        id: 'act-default-align',
        type: 'info',
        emoji: '🔄',
        title: 'Banjara Hills Cart JC-331: Layout Mismatch',
        desc: 'Peak evening hour behavior detected. Realign Slot 7-8 to high-margin family tubs.',
        btnText: 'Approve Planogram Realign'
    });

    badge.textContent = actions.length + ' Action' + (actions.length > 1 ? 's' : '') + ' Pending';
    badge.className = actions.length > 1 ? 'card-badge alert-card' : 'card-badge pulse-badge';

    feed.innerHTML = actions.map(act => `
        <div class="alert-item ${act.type}" id="${act.id}">
            <span class="alert-icon">${act.emoji}</span>
            <div class="alert-body">
                <div class="alert-title" style="font-weight: 700;">${act.title}</div>
                <div class="alert-detail" style="margin-bottom: 8px;">${act.desc}</div>
                <button class="btn-action-execute" onclick="executeOrchestratorAction('${act.id}', '${act.title}')">${act.btnText}</button>
            </div>
            <span class="alert-time">New</span>
        </div>`).join('');
}

window.executeOrchestratorAction = function(id, title) {
    const btn = document.querySelector(`#${id} .btn-action-execute`);
    if (!btn || btn.classList.contains('success-state')) return;

    btn.innerHTML = '⚡ Deploying...';
    btn.disabled = true;

    setTimeout(() => {
        btn.innerHTML = '✓ Deployed Successfully';
        btn.className = 'btn-action-execute success-state';

        const savedIncrement = rand(8500, 16000);
        EXP_STATE.spoilageSaved += savedIncrement;
        document.getElementById('val-spoilage-saved').textContent = '₹' + EXP_STATE.spoilageSaved.toLocaleString('en-IN');
        
        // Command Center KPI update
        const valCmdSpoilage = document.getElementById('val-cmd-spoilage-saved');
        if (valCmdSpoilage) {
            valCmdSpoilage.textContent = '₹' + EXP_STATE.spoilageSaved.toLocaleString('en-IN');
            valCmdSpoilage.classList.add('text-green');
            setTimeout(() => valCmdSpoilage.classList.remove('text-green'), 1200);
        }

        showOrchToast('Recovery Deployed', `Successfully executed autonomous action: ${title}`);

        // Push to main alerts feed
        const dashboardFeed = document.getElementById('alert-feed');
        if (dashboardFeed) {
            dashboardFeed.insertAdjacentHTML('afterbegin', `
                <div class="alert-item success">
                    <span class="alert-icon">🤖</span>
                    <div class="alert-body">
                        <div class="alert-title">Orchestrator Recovery Success</div>
                        <div class="alert-detail">${title} - Spoilage averted, saving ₹${savedIncrement.toLocaleString('en-IN')}.</div>
                    </div>
                    <span class="alert-time">Just now</span>
                </div>`);
        }

        setTimeout(() => {
            const item = document.getElementById(id);
            if (item) {
                item.style.transition = 'all 0.4s ease';
                item.style.opacity = '0';
                item.style.height = '0';
                item.style.padding = '0';
                item.style.margin = '0';
                setTimeout(() => {
                    item.remove();
                    const badge = document.getElementById('orch-action-count');
                    const remaining = document.querySelectorAll('#orchestrator-actions-feed .alert-item').length;
                    badge.textContent = remaining + ' Action' + (remaining !== 1 ? 's' : '') + ' Pending';
                }, 400);
            }
        }, 1000);

    }, 1000);
};

function showOrchToast(title, desc) {
    document.querySelectorAll('.orch-toast').forEach(t => t.remove());

    const toast = document.createElement('div');
    toast.className = 'orch-toast';
    toast.innerHTML = `
        <span style="font-size: 16px;">✅</span>
        <div style="display: flex; flex-direction: column;">
            <div class="orch-toast-title">${title}</div>
            <div class="orch-toast-desc">${desc}</div>
        </div>`;
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.style.transition = 'all 0.3s ease';
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(10px)';
        setTimeout(() => toast.remove(), 300);
    }, 3500);
}

// ═══════════════════════════════════════════════════════════════════════════════
// SMART GROWTH EXPANSION Simulator PAGE
// ═══════════════════════════════════════════════════════════════════════════════

let expansionGrowthChart = null;
let growthBaseData = [11.2, 12.4, 13.8, 15.2, 16.9, 18.4, 20.2, 22.1, 24.5, 27.2, 30.5, 34.0]; 

function initExpansion() {
    updateExpansionKPIs();
    initExpansionChart();
}

function updateExpansionKPIs() {
    const valVending = document.getElementById('val-exp-vending');
    const lblVending = document.getElementById('lbl-exp-vending-revenue');
    if (valVending) valVending.textContent = `${EXP_STATE.vending.count} Kiosks`;
    if (lblVending) lblVending.textContent = `ARR: ₹${EXP_STATE.vending.revenue.toFixed(2)} Cr`;

    const valQcomm = document.getElementById('val-exp-qcomm');
    const lblQcomm = document.getElementById('lbl-exp-qcomm-sales');
    if (valQcomm) valQcomm.textContent = `${EXP_STATE.qcomm.count} Hubs`;
    if (lblQcomm) lblQcomm.textContent = `Sales: ${EXP_STATE.qcomm.sales}/hr`;

    const valSubs = document.getElementById('val-exp-subs');
    const lblSubs = document.getElementById('lbl-exp-subs-mrr');
    if (valSubs) valSubs.textContent = EXP_STATE.subs.count.toLocaleString('en-IN');
    if (lblSubs) lblSubs.textContent = `MRR: ₹${EXP_STATE.subs.mrr.toFixed(1)}L`;

    const valTrucks = document.getElementById('val-exp-trucks');
    const lblTrucks = document.getElementById('lbl-exp-trucks-yield');
    if (valTrucks) valTrucks.textContent = `${EXP_STATE.trucks.count} Vans`;
    if (lblTrucks) lblTrucks.textContent = `Avg Yield: ${EXP_STATE.trucks.yield.toFixed(1)}%`;

    // Sync with Command Center & Operations
    const valCmdAssets = document.getElementById('val-cmd-active-assets');
    const valCmdMRR = document.getElementById('val-cmd-scaling-mrr');
    if (valCmdAssets) valCmdAssets.textContent = EXP_STATE.totalAssets.toLocaleString('en-IN');
    if (valCmdMRR) valCmdMRR.textContent = `₹${EXP_STATE.subs.mrr.toFixed(1)}L`;

    const valOpsCarts = document.getElementById('val-ops-active-carts');
    if (valOpsCarts) valOpsCarts.textContent = (8547 + (EXP_STATE.vending.count - 48)).toLocaleString('en-IN');
}

function initExpansionChart() {
    const ctx = document.getElementById('expansion-growth-chart');
    if (!ctx) return;

    const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    
    if (expansionGrowthChart) {
        expansionGrowthChart.destroy();
    }

    expansionGrowthChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: months,
            datasets: [
                {
                    label: 'Actual MRR (₹ Lakhs)',
                    data: [...growthBaseData.slice(0, 6), ...Array(6).fill(null)],
                    borderColor: COLORS.blue,
                    backgroundColor: COLORS.blue + '08',
                    borderWidth: 3,
                    tension: 0.4,
                    fill: true
                },
                {
                    label: 'Projected MRR (₹ Lakhs)',
                    data: [...Array(5).fill(null), growthBaseData[5], ...growthBaseData.slice(6)],
                    borderColor: COLORS.purple,
                    borderWidth: 2,
                    tension: 0.4,
                    borderDash: [5, 4]
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            scales: {
                x: { grid: { display: false } },
                y: {
                    title: { display: true, text: 'MRR (₹ Lakhs)' },
                    grid: { color: 'rgba(255,255,255,.03)' },
                    min: 10
                }
            }
        }
    });
}

window.simulateExpansionVector = function(vector, presetAmt) {
    const feed = document.getElementById('expansion-status-feed');
    const now = new Date();
    const timeStr = `${now.getHours().toString().padStart(2,'0')}:${now.getMinutes().toString().padStart(2,'0')}`;
    
    let logHTML = '';
    
    if (vector === 'vending') {
        EXP_STATE.vending.count += 5;
        EXP_STATE.vending.revenue += 0.125;
        EXP_STATE.totalAssets += 5;
        
        growthBaseData = growthBaseData.map((val, idx) => idx >= 6 ? val + 0.8 : val);
        
        logHTML = `
            <div class="alert-item success">
                <span class="alert-icon">🤖</span>
                <div class="alert-body">
                    <div class="alert-title">IoT Kiosk Network Launched</div>
                    <div class="alert-detail">Launched +5 smart freezers. Total ARR reaches ₹${EXP_STATE.vending.revenue.toFixed(2)} Cr.</div>
                </div>
                <span class="alert-time">${timeStr}</span>
            </div>`;
        showOrchToast('Kiosks Added', 'Launched 5 new smart vending kiosks.');
    } else if (vector === 'qcomm') {
        EXP_STATE.qcomm.count += 2;
        EXP_STATE.qcomm.sales += 75;
        EXP_STATE.totalAssets += 2;
        
        growthBaseData = growthBaseData.map((val, idx) => idx >= 6 ? val + 1.4 : val);
        
        logHTML = `
            <div class="alert-item success">
                <span class="alert-icon">⚡</span>
                <div class="alert-body">
                    <div class="alert-title">Q-Commerce Dark Stores Linked</div>
                    <div class="alert-detail">Integrated 2 dark stores. Overall order rate boosted by +75/hr.</div>
                </div>
                <span class="alert-time">${timeStr}</span>
            </div>`;
        showOrchToast('Stores Linked', 'Integrated 2 Q-Commerce distribution hubs.');
    } else if (vector === 'subs') {
        const amt = presetAmt || 500;
        EXP_STATE.subs.count += amt;
        const mrrBoost = (amt / 500) * 0.72;
        EXP_STATE.subs.mrr += mrrBoost;
        
        growthBaseData = growthBaseData.map((val, idx) => idx >= 6 ? val + mrrBoost : val);
        
        logHTML = `
            <div class="alert-item success">
                <span class="alert-icon">🍓</span>
                <div class="alert-body">
                    <div class="alert-title">Gourmet Subscription Campaign</div>
                    <div class="alert-detail">Acquired +${amt} members. Monthly Recurring Revenue boosted by +₹${mrrBoost.toFixed(2)}L.</div>
                </div>
                <span class="alert-time">${timeStr}</span>
            </div>`;
        showOrchToast('Members Added', `Acquired ${amt} gourmet club subscribers.`);
    } else if (vector === 'trucks') {
        EXP_STATE.trucks.count += 1;
        EXP_STATE.totalAssets += 1;
        EXP_STATE.trucks.yield = 88.5 + (Math.random() - 0.3) * 1.5;
        
        growthBaseData = growthBaseData.map((val, idx) => idx >= 6 ? val + 2.2 : val);
        
        logHTML = `
            <div class="alert-item success">
                <span class="alert-icon">🚛</span>
                <div class="alert-body">
                    <div class="alert-title">Catering Van Dispatched</div>
                    <div class="alert-detail">Deployed 1 new mobile catering truck. Capacity yield tracking at ${EXP_STATE.trucks.yield.toFixed(1)}%.</div>
                </div>
                <span class="alert-time">${timeStr}</span>
            </div>`;
        showOrchToast('Van Deployed', 'Mobile catering van deployed to active hub.');
    }
    
    updateExpansionKPIs();
    
    if (feed) {
        feed.insertAdjacentHTML('afterbegin', logHTML);
    }
    
    if (expansionGrowthChart) {
        expansionGrowthChart.data.datasets[1].data = [...Array(5).fill(null), growthBaseData[5], ...growthBaseData.slice(6)];
        expansionGrowthChart.update();
    }
};

// ═══════════════════════════════════════════════════════════════════════════════
// ROLE FOOTER & INTERACTIVE STORYBOARD
// ═══════════════════════════════════════════════════════════════════════════════

function setRole(role) {
    const avatar = document.querySelector('.user-avatar');
    const name = document.querySelector('.user-name');
    const urole = document.querySelector('.user-role');

    if (role === 'company') {
        if (avatar) avatar.textContent = 'DG';
        if (name) name.textContent = 'Dhruv G.';
        if (urole) urole.textContent = 'CEO · Admin';
    } else {
        if (avatar) avatar.textContent = 'OC';
        if (name) name.textContent = 'Ops Crew';
        if (urole) urole.textContent = 'Field Operations';
    }
}

const storyboardSteps = [
    {
        title: "Step 1: AI Hyperlocal Demand Forecasting",
        text: "Jersey's models analyze variables: Hyderabad temp rises to 38°C with an IPL Cricket Match at Uppal Stadium, forecasting +42% demand. Observe the growth warning in the Command Center alert feed.",
        role: "company",
        section: "command-center",
        highlightId: "revenue-trajectory-chart",
        action: () => {
            const feed = document.getElementById('alert-feed');
            if (feed) {
                feed.insertAdjacentHTML('afterbegin', `
                    <div class="alert-item info story-highlight">
                        <span class="alert-icon">🌦️</span>
                        <div class="alert-body">
                            <div class="alert-title">AI Forecast Trigger: Uppal Stadium IPL Match</div>
                            <div class="alert-detail">Temp stress + cricket match crowds indicate a 42% impulse demand spurt.</div>
                        </div>
                        <span class="alert-time">Just now</span>
                    </div>`);
            }
        }
    },
    {
        title: "Step 2: Zonal operations & GPS-Tracked Push Carts",
        text: "With 8,500+ push carts, tracking is critical. Switch to Logistics & Carts to map active units in Uppal Stadium zone and view cold-chain logs.",
        role: "employee",
        section: "operations",
        highlightId: "live-map",
        action: () => {
            initMap();
            if (map) {
                map.setView([17.3920, 78.5510], 15);
                setTimeout(() => {
                    if (storyCartMarker) {
                        const icon = L.divIcon({ className: 'cart-marker low-stock story-highlight', iconSize: [12, 12] });
                        storyCartMarker.setIcon(icon);
                        storyCartMarker.openPopup();
                    }
                }, 600);
            }
        }
    },
    {
        title: "Step 3: Melt-Risk & Flavor Slot Orchestration",
        text: "The Melt-Risk Orchestrator handles inventory decay. Adjust weather controls or select compressor strain to see slots dynamically adjust to secure product sellability.",
        role: "company",
        section: "orchestrator",
        highlightClass: "orchestrator-config-card",
        action: () => {
            const tempInput = document.getElementById('orch-input-temp');
            const teleInput = document.getElementById('orch-input-telemetry');
            if (tempInput && teleInput) {
                tempInput.value = 38;
                teleInput.value = 'strain';
                tempInput.dispatchEvent(new Event('input'));
                teleInput.dispatchEvent(new Event('change'));
            }
        }
    },
    {
        title: "Step 4: Autonomous Recovery Actions",
        text: "The action engine suggests a recovery task (e.g., planogram optimization or discount markdown). Click 'Acknowledge' or 'Deploy' to automatically secure sellable minutes and increase the Spoilage Cost Saved.",
        role: "company",
        section: "orchestrator",
        highlightClass: "orchestrator-actions-card",
        action: () => {
            const feed = document.getElementById('orchestrator-actions-feed');
            if (feed && feed.firstElementChild) {
                feed.firstElementChild.classList.add('story-highlight');
            }
        }
    },
    {
        title: "Step 5: Smart Growth Scaling Simulator",
        text: "Expand beyond push carts. Switch to the Smart Expansion simulator to launch IoT kiosks, link dark stores (Q-Commerce), acquire subscribers, and deploy mobile vans to see MRR curve rise.",
        role: "company",
        section: "expansion",
        highlightId: "expansion-growth-chart",
        action: () => {
            simulateExpansionVector('subs', 300);
        }
    }
];

let currentStepIndex = 0;

function initStoryboard() {
    const btnPrev = document.getElementById('btn-story-prev');
    const btnNext = document.getElementById('btn-story-next');
    const dots = document.querySelectorAll('.story-dot');

    if (!btnPrev || !btnNext) return;

    updateStoryboardUI();

    btnPrev.addEventListener('click', () => {
        if (currentStepIndex > 0) {
            currentStepIndex--;
            updateStoryboardUI();
            runStepAction(currentStepIndex);
        }
    });

    btnNext.addEventListener('click', () => {
        if (currentStepIndex < storyboardSteps.length - 1) {
            currentStepIndex++;
            updateStoryboardUI();
            runStepAction(currentStepIndex);
        } else {
            currentStepIndex = 0;
            updateStoryboardUI();
            runStepAction(currentStepIndex);
        }
    });

    dots.forEach(dot => {
        dot.addEventListener('click', () => {
            const step = parseInt(dot.dataset.step);
            if (!isNaN(step)) {
                currentStepIndex = step;
                updateStoryboardUI();
                runStepAction(currentStepIndex);
            }
        });
    });
}

function updateStoryboardUI() {
    const btnPrev = document.getElementById('btn-story-prev');
    const btnNext = document.getElementById('btn-story-next');
    const titleEl = document.getElementById('story-title');
    const textEl = document.getElementById('story-text');
    const dots = document.querySelectorAll('.story-dot');

    const step = storyboardSteps[currentStepIndex];
    if (!step) return;

    if (titleEl) titleEl.textContent = step.title;
    if (textEl) textEl.textContent = step.text;

    if (btnPrev) btnPrev.disabled = currentStepIndex === 0;

    if (btnNext) {
        if (currentStepIndex === storyboardSteps.length - 1) {
            btnNext.innerHTML = "Restart Tour 🔄";
            btnNext.classList.remove('btn-pulse');
        } else {
            btnNext.innerHTML = "Next Step →";
            btnNext.classList.add('btn-pulse');
        }
    }

    dots.forEach((dot, idx) => {
        dot.classList.remove('active', 'completed');
        if (idx === currentStepIndex) {
            dot.classList.add('active');
        } else if (idx < currentStepIndex) {
            dot.classList.add('completed');
        }
    });
}

function runStepAction(idx) {
    const step = storyboardSteps[idx];
    if (!step) return;

    clearHighlights();
    setRole(step.role);
    navTo(step.section);

    setTimeout(() => {
        let targetEl = null;
        if (step.highlightId) {
            targetEl = document.getElementById(step.highlightId);
            if (targetEl && targetEl.tagName === 'CANVAS') {
                targetEl = targetEl.closest('.chart-card') || targetEl.closest('.card') || targetEl;
            }
        } else if (step.highlightClass) {
            targetEl = document.querySelector('.' + step.highlightClass);
        }

        if (targetEl) {
            targetEl.classList.add('story-highlight');
            targetEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }

        if (typeof step.action === 'function') {
            step.action();
        }
    }, 400);
}

function clearHighlights() {
    document.querySelectorAll('.story-highlight').forEach(el => {
        el.classList.remove('story-highlight');
    });
}

// ─── Live Updates Poller ────────────────────────────────────────────────────────

function liveUpdate() {
    // Keep ambient weather temp fluctuating slightly
    const temp = document.querySelector('.weather-temp');
    if (temp) {
        const cur = parseInt(temp.textContent);
        const nv = Math.max(30, Math.min(42, cur + (Math.random() > 0.5 ? 1 : -1)));
        temp.textContent = nv + '°C';
        const impact = document.querySelector('.weather-impact');
        if (impact) impact.textContent = `+${Math.round((nv - 25) * 2.8)}% demand`;
    }

    // Keep active asset counts drifting slightly upwards
    if (Math.random() > 0.6) {
        EXP_STATE.totalAssets += rand(1, 3);
        const valCmdAssets = document.getElementById('val-cmd-active-assets');
        if (valCmdAssets) valCmdAssets.textContent = EXP_STATE.totalAssets.toLocaleString('en-IN');
    }
}
