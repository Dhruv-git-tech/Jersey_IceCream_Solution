/* =============================================================================
   Jersey Ice Cream — Business Intelligence Suite (MVP)
   All Charts, Maps, Simulated Data & Interactivity
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
const dayLabels = n => { const m = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']; const d = []; const now = new Date(); for(let i=n-1;i>=0;i--){ const dt = new Date(now-i*864e5); d.push(`${m[dt.getMonth()]} ${dt.getDate()}`); } return d; };
const hourLabels = n => { const d = []; const now = new Date(); for(let i=n-1;i>=0;i--){ const dt = new Date(now-i*36e5); d.push(dt.getHours().toString().padStart(2,'0')+':00'); } return d; };
const fmtNum = n => n>=1e7 ? (n/1e7).toFixed(2)+' Cr' : n>=1e5 ? (n/1e5).toFixed(1)+' L' : n>=1e3 ? (n/1e3).toFixed(1)+'K' : n.toString();

const VENDORS = ['Raju Kumar','Suresh Yadav','Mohd Imran','Srinivas Reddy','Lakshmi Devi','Ramesh Patel','Ajay Singh','Venkat Rao','Pradeep Sharma','Manoj Gupta','Anil Verma','Deepak Joshi','Salim Khan','Naveen Prasad','Gopal Das'];
const AREAS = ['Jubilee Hills','Banjara Hills','Hitech City','Gachibowli','Madhapur','Kukatpally','Ameerpet','Secunderabad','Begumpet','Somajiguda','Tarnaka','Uppal','Dilsukhnagar','Charminar','Miyapur','Kondapur'];

// ─── Init ───────────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
    initNav();
    animateKPIs();

    // Command Center
    initRevenueTrajectory();
    initAlertFeed();

    // Supply Chain
    initColdChainChart();
    initInventoryWarehouseChart();
    initSupplyRefillFeed();
    initWastageChart();

    // Production
    initProductionDemandChart();
    initProductMixChart();
    initProductsTable();

    // Distribution
    initRouteEfficiencyChart();
    initDistributorRankChart();
    initNetworkGrowthChart();

    // Marketing
    initCampaignROIChart();
    initSentimentChart();
    initCompetitorChart();
    initCampaignList();

    // Finance
    initPnLWaterfallChart();
    initCostStructureChart();
    initRevVsExpenseChart();

    // AI Hub
    initAIForecastChart();
    initFeatureImportance();
    initWeatherDemandChart();
    initTechStack();
    initYOLOSandbox();

    // Map (lazy)
    let mapInit = false;
    new MutationObserver(() => {
        if (document.getElementById('section-live-map')?.classList.contains('active') && !mapInit) {
            setTimeout(initMap, 100);
            mapInit = true;
        }
    }).observe(document.getElementById('section-live-map'), { attributes: true });

    // Orchestrator (lazy)
    let orchInit = false;
    new MutationObserver(() => {
        if (document.getElementById('section-orchestrator')?.classList.contains('active') && !orchInit) {
            setTimeout(initOrchestrator, 100);
            orchInit = true;
        }
    }).observe(document.getElementById('section-orchestrator'), { attributes: true });

    // Domain card clicks
    document.querySelectorAll('.domain-card').forEach(card => {
        card.addEventListener('click', () => {
            const section = card.dataset.goto;
            if (section) navTo(section);
        });
    });

    // Role Switching & Storyboard
    initRoleSwitcher();
    initStoryboard();

    setInterval(liveUpdate, 3500);
});

// ─── Navigation ─────────────────────────────────────────────────────────────────

function navTo(key) {
    const items = document.querySelectorAll('.menu-item');
    const sections = document.querySelectorAll('.section');
    const h1 = document.getElementById('page-title');
    const sub = document.getElementById('page-subtitle');

    const meta = {
        'command-center': ['Command Center', 'Holistic business intelligence at a glance'],
        'supply-chain': ['Supply Chain', 'Cold chain, inventory & logistics management'],
        'production': ['Production', 'Manufacturing output, quality & SKU performance'],
        'distribution': ['Distribution', 'Fleet, distributor network & coverage'],
        'marketing': ['Marketing', 'Brand growth, campaigns & competitor intelligence'],
        'finance': ['Finance', 'Revenue, margins, costs & path to profitability'],
        'ai-hub': ['AI Hub', 'Demand forecasting, vision models & tech infrastructure'],
        'live-map': ['Live Cart Map', 'Track 8,500+ push carts across the city in real-time'],
        'orchestrator': ['Melt-Risk & Demand Orchestrator', 'Real-time sellability scoring, adaptive flavor slotting & autonomous actions'],
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
        const dur = 2200;

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
// COMMAND CENTER
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
                { label: 'Revenue (₹ Cr)', data: [14.2,16.8,21.3,28.5,32.1,24.7,18.9,15.2,12.8,11.4,13.6,17.5], backgroundColor: ctx => { const g = ctx.chart.ctx.createLinearGradient(0,0,0,250); g.addColorStop(0,'rgba(88,166,255,.5)'); g.addColorStop(1,'rgba(88,166,255,.05)'); return g; }, borderRadius: 6, borderSkipped: false },
                { label: 'Cost (₹ Cr)', data: [9.8,11.2,13.1,17.4,19.6,15.3,12.1,10.4,8.9,8.2,9.4,11.8], backgroundColor: 'rgba(248,81,73,.15)', borderRadius: 6, borderSkipped: false },
            ],
        },
        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'top' } }, scales: { x: { grid: { display: false } }, y: { grid: { color: 'rgba(255,255,255,.03)' }, ticks: { callback: v => '₹'+v+'Cr' } } } },
    });
}

function initAlertFeed() {
    const feed = document.getElementById('alert-feed');
    if (!feed) return;

    const alerts = [
        { type: 'critical', icon: '🚨', title: 'Stockout: Mango Kulfi at Hitech City Zone', detail: '14 carts below 5 units · AI auto-dispatching refills', time: '2 min ago' },
        { type: 'warning', icon: '⚠️', title: 'Cold chain breach: Vehicle TN-07-4521', detail: 'Temperature rose to -14°C (threshold: -18°C) for 8 mins', time: '7 min ago' },
        { type: 'success', icon: '✅', title: 'Production batch #B2847 QC passed', detail: 'Vanilla Cone Classic · 4,200 units · FSSAI Grade A+', time: '12 min ago' },
        { type: 'info', icon: '📊', title: 'AI model retrained with latest 48hr data', detail: 'Accuracy improved 91.3% → 91.7% · R² = 0.94', time: '25 min ago' },
        { type: 'success', icon: '🎯', title: 'Instagram campaign "Summer Kulfi" crossed 1M reach', detail: 'CTR: 4.8% · Conversion: 2.1% · ₹3.2L revenue attributed', time: '38 min ago' },
        { type: 'warning', icon: '💰', title: 'Raw milk price alert: ₹52/L → ₹54/L (+3.8%)', detail: 'Margin impact: -0.4pp on Vanilla line · Hedging recommended', time: '1h ago' },
        { type: 'info', icon: '🚛', title: 'Distributor "Patel & Sons" onboarded', detail: 'Region: Warangal · 45 carts · Expected revenue: ₹8.2L/month', time: '2h ago' },
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
// SUPPLY CHAIN
// ═══════════════════════════════════════════════════════════════════════════════

function initColdChainChart() {
    const ctx = document.getElementById('cold-chain-chart');
    if (!ctx) return;
    const labels = hourLabels(24);
    const gen = (base, v) => Array.from({length:24}, () => base + (Math.random()-.5)*v);

    new Chart(ctx, {
        type: 'line',
        data: {
            labels,
            datasets: [
                { label: 'Kukatpally', data: gen(-20, 2), borderColor: COLORS.blue, borderWidth: 2, tension: .4 },
                { label: 'Uppal', data: gen(-19.5, 2.5), borderColor: COLORS.green, borderWidth: 2, tension: .4 },
                { label: 'Miyapur', data: gen(-21, 1.5), borderColor: COLORS.purple, borderWidth: 2, tension: .4 },
                { label: 'Secunderabad', data: gen(-19, 3), borderColor: COLORS.orange, borderWidth: 2, tension: .4, pointRadius: ctx2 => { const i = ctx2.dataIndex; return gen(-19,3)[i] > -17 ? 5 : 0; }, pointBackgroundColor: COLORS.red },
            ],
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            plugins: {
                annotation: { annotations: { threshold: { type: 'line', yMin: -18, yMax: -18, borderColor: 'rgba(248,81,73,.5)', borderWidth: 1, borderDash: [4,4], label: { display: true, content: 'Max Safe Temp (-18°C)', position: 'end', font: { size: 9 } } } } },
            },
            scales: { x: { grid: { display: false } }, y: { title: { display: true, text: '°C' }, grid: { color: 'rgba(255,255,255,.03)' } } },
        },
    });
}

function initInventoryWarehouseChart() {
    const ctx = document.getElementById('inventory-warehouse-chart');
    if (!ctx) return;
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['Kukatpally\nMain', 'Uppal Hub', 'Miyapur', 'Secunderabad', 'Nalgonda', 'Warangal'],
            datasets: [
                { label: 'Current Stock (L)', data: [38000, 22000, 28000, 15000, 8000, 6500], backgroundColor: COLORS.blue+'99', borderRadius: 6, borderSkipped: false },
                { label: 'Capacity (L)', data: [50000, 35000, 40000, 25000, 15000, 15000], backgroundColor: 'rgba(255,255,255,.04)', borderRadius: 6, borderSkipped: false },
            ],
        },
        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'top' } }, scales: { x: { grid: { display: false } }, y: { grid: { color: 'rgba(255,255,255,.03)' }, ticks: { callback: v => (v/1000)+'K L' } } } },
    });
}

function initSupplyRefillFeed() {
    const feed = document.getElementById('supply-refill-feed');
    if (!feed) return;
    const items = [];
    for (let i = 0; i < 8; i++) {
        const priority = pick(['critical','high','high','medium','medium','medium']);
        const icons = { critical: '🚨', high: '⚠️', medium: '📦' };
        const source = pick(['WhatsApp', 'AI Auto', 'App', 'Photo']);
        const sourceIcons = { WhatsApp: '💬', 'AI Auto': '🤖', App: '📱', Photo: '📸' };
        const now = new Date();
        items.push(`
            <div class="refill-item ${priority}">
                <span style="font-size:16px">${icons[priority]}</span>
                <div class="refill-content">
                    <div class="refill-title"><span class="priority-badge ${priority}">${priority}</span> Cart JC-${rand(1000,9999)} · ${pick(VENDORS)}</div>
                    <div class="refill-details">${pick(AREAS)} · via ${sourceIcons[source]} ${source}</div>
                </div>
                <span class="refill-time">${now.getHours().toString().padStart(2,'0')}:${now.getMinutes().toString().padStart(2,'0')}</span>
            </div>`);
    }
    feed.innerHTML = items.join('');
}

function initWastageChart() {
    const ctx = document.getElementById('wastage-chart');
    if (!ctx) return;
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'],
            datasets: [
                { label: 'Before AI (%)', data: [14.2,13.8,15.1,14.5,16.2,17.8,15.9,14.7,13.2,12.8,13.5,14.1], borderColor: COLORS.red+'99', borderWidth: 2, tension: .4, borderDash: [4,4] },
                { label: 'After AI (%)', data: [null,null,null,null,null,null,8.2,6.1,4.8,3.9,3.2,2.9], borderColor: COLORS.green, backgroundColor: COLORS.green+'10', borderWidth: 2.5, tension: .4, fill: true },
            ],
        },
        options: { responsive: true, maintainAspectRatio: false, interaction: { mode: 'index', intersect: false }, scales: { x: { grid: { display: false } }, y: { title: { display: true, text: 'Wastage %' }, grid: { color: 'rgba(255,255,255,.03)' } } } },
    });
}

// ═══════════════════════════════════════════════════════════════════════════════
// PRODUCTION
// ═══════════════════════════════════════════════════════════════════════════════

function initProductionDemandChart() {
    const ctx = document.getElementById('production-demand-chart');
    if (!ctx) return;
    const labels = dayLabels(14);
    const production = [38000,40000,42000,41000,39000,43000,44000,42500,41000,43500,45000,44000,42000,42500];
    const demand = [36000,41000,39000,43000,38000,44000,42000,43000,40000,45000,43000,42000,44000,43000];

    new Chart(ctx, {
        type: 'line',
        data: {
            labels,
            datasets: [
                { label: 'Production (L)', data: production, borderColor: COLORS.blue, backgroundColor: COLORS.blue+'08', borderWidth: 2.5, tension: .4, fill: true },
                { label: 'Demand (L)', data: demand, borderColor: COLORS.orange, borderWidth: 2, tension: .4, borderDash: [5,3] },
            ],
        },
        options: { responsive: true, maintainAspectRatio: false, interaction: { mode: 'index', intersect: false }, scales: { x: { grid: { display: false } }, y: { grid: { color: 'rgba(255,255,255,.03)' }, ticks: { callback: v => (v/1000)+'K' } } } },
    });
}

function initProductMixChart() {
    const ctx = document.getElementById('product-mix-chart');
    if (!ctx) return;
    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Cone', 'Bar', 'Kulfi', 'Cup', 'Sandwich', 'Stick', 'Family Pack', 'Seasonal'],
            datasets: [{ data: [28,22,18,12,8,5,4,3], backgroundColor: [COLORS.blue,COLORS.green,COLORS.orange,COLORS.purple,COLORS.cyan,COLORS.pink,COLORS.gray,'#444'], borderColor: 'rgba(6,8,15,.8)', borderWidth: 3 }],
        },
        options: { responsive: true, maintainAspectRatio: false, cutout: '62%', plugins: { legend: { position: 'right', labels: { padding: 10 } } } },
    });
}

function initProductsTable() {
    const container = document.getElementById('products-table');
    if (!container) return;
    const products = [
        { emoji: '🍦', name: 'Vanilla Cone Classic', cat: 'Cone', units: 12847, rev: '₹2.57 L', margin: '44.2%', trend: 12.4 },
        { emoji: '🍫', name: 'Choco Bar Supreme', cat: 'Bar', units: 10293, rev: '₹3.09 L', margin: '41.8%', trend: 8.7 },
        { emoji: '🥭', name: 'Mango Kulfi Royal', cat: 'Kulfi', units: 9871, rev: '₹2.96 L', margin: '46.1%', trend: 23.1 },
        { emoji: '🍓', name: 'Strawberry Cup Delight', cat: 'Cup', units: 8456, rev: '₹2.11 L', margin: '39.5%', trend: 5.2 },
        { emoji: '🧇', name: 'Butterscotch Sandwich', cat: 'Sandwich', units: 7823, rev: '₹2.35 L', margin: '38.9%', trend: -2.1 },
        { emoji: '🍡', name: 'Pista Malai Stick', cat: 'Stick', units: 6547, rev: '₹1.96 L', margin: '42.3%', trend: 15.8 },
        { emoji: '📦', name: 'Family Pack Assorted', cat: 'Family', units: 2134, rev: '₹4.27 L', margin: '35.7%', trend: 18.9 },
        { emoji: '🍊', name: 'Orange Candy Bar', cat: 'Bar', units: 5892, rev: '₹1.18 L', margin: '52.1%', trend: 7.3 },
    ];

    container.innerHTML = `<table><thead><tr><th>#</th><th></th><th>Product</th><th>Category</th><th>Units Sold</th><th>Revenue</th><th>Margin</th><th>Trend (7d)</th></tr></thead><tbody>${products.map((p,i)=>{
        const rc = i===0?'gold':i===1?'silver':i===2?'bronze':'';
        const tc = p.trend>0?'trend-up':'trend-down';
        return `<tr><td class="rank ${rc}">#${i+1}</td><td>${p.emoji}</td><td class="prod-name">${p.name}</td><td>${p.cat}</td><td style="font-family:var(--font-mono)">${p.units.toLocaleString()}</td><td style="font-family:var(--font-mono)">${p.rev}</td><td style="font-family:var(--font-mono)">${p.margin}</td><td class="${tc}" style="font-family:var(--font-mono);font-weight:600">${p.trend>0?'↑':'↓'} ${Math.abs(p.trend)}%</td></tr>`;
    }).join('')}</tbody></table>`;
}

// ═══════════════════════════════════════════════════════════════════════════════
// DISTRIBUTION
// ═══════════════════════════════════════════════════════════════════════════════

function initRouteEfficiencyChart() {
    const ctx = document.getElementById('route-efficiency-chart');
    if (!ctx) return;
    new Chart(ctx, {
        type: 'radar',
        data: {
            labels: ['On-Time %', 'Cost/Km', 'Coverage', 'Utilization', 'Cold Chain', 'Customer Sat'],
            datasets: [
                { label: 'Current', data: [82,75,68,72,98,85], borderColor: COLORS.blue, backgroundColor: COLORS.blue+'15', borderWidth: 2, pointBackgroundColor: COLORS.blue },
                { label: 'Target', data: [95,90,90,85,99,92], borderColor: COLORS.green+'70', backgroundColor: 'transparent', borderWidth: 1.5, borderDash: [4,4], pointBackgroundColor: COLORS.green },
            ],
        },
        options: { responsive: true, maintainAspectRatio: false, scales: { r: { beginAtZero: true, max: 100, ticks: { display: false }, grid: { color: 'rgba(255,255,255,.04)' }, pointLabels: { color: '#8b949e', font: { size: 10 } }, angleLines: { color: 'rgba(255,255,255,.04)' } } } },
    });
}

function initDistributorRankChart() {
    const ctx = document.getElementById('distributor-rank-chart');
    if (!ctx) return;
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['Patel & Sons', 'Sri Laxmi Dist.', 'Hyderabad Cool', 'Reddy Enterprises', 'Deccan Ice', 'Telangana Traders'],
            datasets: [
                { label: 'Revenue (₹L)', data: [45.2,38.7,32.1,28.9,25.4,22.8], backgroundColor: [COLORS.blue,COLORS.purple,COLORS.green,COLORS.cyan,COLORS.orange,COLORS.pink], borderRadius: 6, borderSkipped: false },
            ],
        },
        options: { responsive: true, maintainAspectRatio: false, indexAxis: 'y', plugins: { legend: { display: false } }, scales: { x: { grid: { color: 'rgba(255,255,255,.03)' }, title: { display: true, text: '₹ Lakhs/month' } }, y: { grid: { display: false } } } },
    });
}

function initNetworkGrowthChart() {
    const ctx = document.getElementById('network-growth-chart');
    if (!ctx) return;
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: ['Q1 FY25','Q2 FY25','Q3 FY25','Q4 FY25','Q1 FY26','Q2 FY26','Q3 FY26*','Q4 FY26*'],
            datasets: [
                { label: 'Distributors', data: [42,58,72,89,105,127,150,180], borderColor: COLORS.blue, borderWidth: 2.5, tension: .4, yAxisID: 'y' },
                { label: 'Active Carts', data: [2100,3200,4800,6100,7200,8547,10000,12000], borderColor: COLORS.green, borderWidth: 2.5, tension: .4, yAxisID: 'y1' },
                { label: 'Districts Covered', data: [8,14,20,24,28,34,42,50], borderColor: COLORS.purple, borderWidth: 2, tension: .4, borderDash: [4,3], yAxisID: 'y' },
            ],
        },
        options: {
            responsive: true, maintainAspectRatio: false, interaction: { mode: 'index', intersect: false },
            scales: { x: { grid: { display: false } }, y: { position: 'left', grid: { color: 'rgba(255,255,255,.03)' }, title: { display: true, text: 'Distributors / Districts' } }, y1: { position: 'right', grid: { display: false }, title: { display: true, text: 'Carts' } } },
        },
    });
}

// ═══════════════════════════════════════════════════════════════════════════════
// MARKETING
// ═══════════════════════════════════════════════════════════════════════════════

function initCampaignROIChart() {
    const ctx = document.getElementById('campaign-roi-chart');
    if (!ctx) return;
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['Instagram', 'YouTube', 'WhatsApp', 'In-Store', 'Cricket IPL', 'Print/OOH'],
            datasets: [
                { label: 'Spend (₹L)', data: [12,18,5,8,25,10], backgroundColor: 'rgba(255,255,255,.06)', borderRadius: 6, borderSkipped: false },
                { label: 'Revenue (₹L)', data: [52,62,24,28,82,15], backgroundColor: ctx => { const g = ctx.chart.ctx.createLinearGradient(0,0,0,280); g.addColorStop(0,COLORS.green+'80'); g.addColorStop(1,COLORS.green+'10'); return g; }, borderRadius: 6, borderSkipped: false },
            ],
        },
        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'top' } }, scales: { x: { grid: { display: false } }, y: { grid: { color: 'rgba(255,255,255,.03)' }, ticks: { callback: v => '₹'+v+'L' } } } },
    });
}

function initSentimentChart() {
    const ctx = document.getElementById('sentiment-chart');
    if (!ctx) return;
    const labels = dayLabels(30);
    const pos = Array.from({length:30}, (_,i) => 65 + i*.5 + (Math.random()-.3)*8);
    const neg = Array.from({length:30}, () => 5 + Math.random()*6);
    const neu = pos.map((p,i) => 100 - p - neg[i]);

    new Chart(ctx, {
        type: 'line',
        data: {
            labels,
            datasets: [
                { label: 'Positive', data: pos, borderColor: COLORS.green, backgroundColor: COLORS.green+'10', borderWidth: 2, tension: .4, fill: true },
                { label: 'Neutral', data: neu, borderColor: COLORS.blue+'60', borderWidth: 1.5, tension: .4 },
                { label: 'Negative', data: neg, borderColor: COLORS.red+'60', borderWidth: 1.5, tension: .4, borderDash: [3,3] },
            ],
        },
        options: { responsive: true, maintainAspectRatio: false, interaction: { mode: 'index', intersect: false }, scales: { x: { grid: { display: false }, ticks: { maxTicksLimit: 10 } }, y: { stacked: false, grid: { color: 'rgba(255,255,255,.03)' }, title: { display: true, text: '% of Mentions' } } } },
    });
}

function initCompetitorChart() {
    const ctx = document.getElementById('competitor-chart');
    if (!ctx) return;
    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Amul', 'Mother Dairy', 'Kwality Walls', 'Havmor', 'Baskin Robbins', 'Jersey', 'Others'],
            datasets: [{ data: [28,18,15,12,8,8.7,10.3], backgroundColor: ['#FFD700','#DC143C','#4169E1','#32CD32',COLORS.pink,COLORS.blue,COLORS.gray], borderColor: 'rgba(6,8,15,.8)', borderWidth: 3 }],
        },
        options: { responsive: true, maintainAspectRatio: false, cutout: '55%', plugins: { legend: { position: 'right', labels: { padding: 10 } } } },
    });
}

function initCampaignList() {
    const list = document.getElementById('campaign-list');
    if (!list) return;
    const campaigns = [
        { name: '🏏 IPL Summer Blast', channel: 'TV + Digital', budget: '₹25L', progress: 78, color: COLORS.orange, roi: '3.3x', status: 'Active' },
        { name: '📸 #JerseyKulfiMoment', channel: 'Instagram + Reels', budget: '₹12L', progress: 92, color: COLORS.pink, roi: '4.3x', status: 'Active' },
        { name: '🎓 College Campus Tour', channel: 'On-ground', budget: '₹8L', progress: 45, color: COLORS.purple, roi: '2.8x', status: 'Active' },
        { name: '💬 WhatsApp Vendor Referral', channel: 'WhatsApp', budget: '₹5L', progress: 100, color: COLORS.green, roi: '4.8x', status: 'Completed' },
        { name: '🎉 Mango Season Launch', channel: 'Multi-channel', budget: '₹18L', progress: 15, color: COLORS.cyan, roi: '—', status: 'Upcoming' },
    ];
    list.innerHTML = campaigns.map(c => `
        <div class="campaign-item">
            <div class="campaign-name">${c.name}</div>
            <div class="campaign-meta"><span>${c.channel}</span><span>Budget: ${c.budget}</span><span>ROI: ${c.roi}</span></div>
            <div class="campaign-bar-bg"><div class="campaign-bar" style="width:${c.progress}%;background:${c.color}"></div></div>
            <div class="campaign-status"><span>${c.progress}% complete</span><span style="color:${c.color}">${c.status}</span></div>
        </div>`).join('');
}

// ═══════════════════════════════════════════════════════════════════════════════
// FINANCE
// ═══════════════════════════════════════════════════════════════════════════════

function initPnLWaterfallChart() {
    const ctx = document.getElementById('pnl-waterfall-chart');
    if (!ctx) return;
    // Simulated waterfall using floating bars
    const labels = ['Revenue', 'COGS', 'Gross Profit', 'Marketing', 'Operations', 'Tech', 'Admin', 'EBITDA', 'Depreciation', 'Net Profit'];
    const values = [247, -141, 106, -24, -18, -12, -7, 45.2, -8, 37.2];
    const running = [0, 247, 106, 106, 82, 64, 52, 0, 45.2, 0];
    const barColors = values.map(v => v > 0 ? COLORS.green+'90' : COLORS.red+'60');
    barColors[2] = COLORS.blue+'80'; barColors[7] = COLORS.blue+'80'; barColors[9] = COLORS.green;

    const dataAbsolute = values.map(v => Math.abs(v));
    const dataInvisible = [0, 106, 0, 82, 64, 52, 45, 0, 37.2, 0];

    new Chart(ctx, {
        type: 'bar',
        data: {
            labels,
            datasets: [
                { label: 'Invisible', data: dataInvisible, backgroundColor: 'transparent', borderWidth: 0, borderSkipped: false },
                { label: '₹ Crore', data: dataAbsolute, backgroundColor: barColors, borderRadius: 4, borderSkipped: false },
            ],
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            plugins: { legend: { display: false }, tooltip: { callbacks: { label: ctx2 => ctx2.datasetIndex===1 ? `₹${values[ctx2.dataIndex]} Cr` : '' } } },
            scales: { x: { stacked: true, grid: { display: false } }, y: { stacked: true, grid: { color: 'rgba(255,255,255,.03)' }, ticks: { callback: v => '₹'+v+'Cr' } } },
        },
    });
}

function initCostStructureChart() {
    const ctx = document.getElementById('cost-structure-chart');
    if (!ctx) return;
    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Raw Materials (57%)', 'Distribution (12%)', 'Marketing (10%)', 'Workforce (9%)', 'Technology (5%)', 'Admin (4%)', 'Other (3%)'],
            datasets: [{ data: [57,12,10,9,5,4,3], backgroundColor: [COLORS.orange,COLORS.blue,COLORS.pink,COLORS.purple,COLORS.cyan,COLORS.green,COLORS.gray], borderColor: 'rgba(6,8,15,.8)', borderWidth: 3 }],
        },
        options: { responsive: true, maintainAspectRatio: false, cutout: '58%', plugins: { legend: { position: 'right', labels: { padding: 8, font: { size: 10 } } } } },
    });
}

function initRevVsExpenseChart() {
    const ctx = document.getElementById('rev-vs-expense-chart');
    if (!ctx) return;
    const months = ['Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec','Jan','Feb','Mar'];
    const rev = [14.2,16.8,21.3,28.5,32.1,24.7,18.9,15.2,12.8,11.4,13.6,17.5];
    const exp = [12.8,14.2,16.1,20.4,22.6,17.3,13.1,11.4,9.9,9.2,10.4,12.8];
    const profit = rev.map((r,i) => +(r - exp[i]).toFixed(1));

    new Chart(ctx, {
        type: 'line',
        data: {
            labels: months,
            datasets: [
                { label: 'Revenue (₹Cr)', data: rev, borderColor: COLORS.green, backgroundColor: COLORS.green+'08', borderWidth: 2.5, tension: .4, fill: true },
                { label: 'Expenses (₹Cr)', data: exp, borderColor: COLORS.red, borderWidth: 2, tension: .4, borderDash: [4,3] },
                { label: 'Profit (₹Cr)', data: profit, borderColor: COLORS.blue, borderWidth: 2, tension: .4, type: 'bar', backgroundColor: ctx => { const g = ctx.chart.ctx.createLinearGradient(0,0,0,200); g.addColorStop(0,COLORS.blue+'50'); g.addColorStop(1,COLORS.blue+'05'); return g; }, borderRadius: 4, order: 1 },
            ],
        },
        options: { responsive: true, maintainAspectRatio: false, interaction: { mode: 'index', intersect: false }, scales: { x: { grid: { display: false } }, y: { grid: { color: 'rgba(255,255,255,.03)' }, ticks: { callback: v => '₹'+v+'Cr' } } } },
    });
}

// ═══════════════════════════════════════════════════════════════════════════════
// AI HUB
// ═══════════════════════════════════════════════════════════════════════════════

function initAIForecastChart() {
    const ctx = document.getElementById('ai-forecast-chart');
    if (!ctx) return;
    const labels = [];
    const now = new Date();
    for (let i = -12; i <= 24; i++) { const d = new Date(now.getTime()+i*36e5); labels.push(d.getHours().toString().padStart(2,'0')+':00'); }

    const hist = Array.from({length:12}, (_,i) => 300 + i*8 + (Math.random()-.5)*60);
    const pred = Array.from({length:25}, (_,i) => 380 + Math.sin(i/4)*80 + (Math.random()-.5)*30);
    const histP = [...hist, ...Array(25).fill(null)];
    const predP = [...Array(11).fill(null), hist[11], ...pred.slice(1)];
    const upper = predP.map(v => v ? v*1.14 : null);
    const lower = predP.map(v => v ? v*0.86 : null);

    new Chart(ctx, {
        type: 'line',
        data: {
            labels,
            datasets: [
                { label: 'Upper CI', data: upper, borderColor: 'transparent', backgroundColor: COLORS.blue+'08', fill: '+1', pointRadius: 0 },
                { label: 'AI Forecast', data: predP, borderColor: COLORS.blue, borderWidth: 2.5, tension: .4, borderDash: [6,4] },
                { label: 'Actual', data: histP, borderColor: COLORS.green, backgroundColor: COLORS.green+'08', borderWidth: 2.5, tension: .4, fill: true },
                { label: 'Lower CI', data: lower, borderColor: 'transparent', backgroundColor: 'transparent', fill: '-3', pointRadius: 0 },
            ],
        },
        options: {
            responsive: true, maintainAspectRatio: false, interaction: { mode: 'index', intersect: false },
            plugins: { legend: { labels: { filter: i => !['Upper CI','Lower CI'].includes(i.text) } } },
            scales: { x: { grid: { display: false } }, y: { title: { display: true, text: 'Units/Hour' }, grid: { color: 'rgba(255,255,255,.03)' } } },
        },
    });
}

function initFeatureImportance() {
    const container = document.getElementById('feature-importance');
    if (!container) return;
    const features = [
        { name: 'Temperature', val: 34, color: COLORS.orange },
        { name: 'Day of Week', val: 22, color: COLORS.blue },
        { name: 'Local Events', val: 18, color: COLORS.purple },
        { name: 'Historical', val: 12, color: COLORS.green },
        { name: 'Time of Day', val: 8, color: COLORS.cyan },
        { name: 'Holidays', val: 4, color: COLORS.pink },
        { name: 'Competitor', val: 2, color: COLORS.gray },
    ];
    container.innerHTML = features.map(f => `
        <div class="feature-item">
            <span class="feature-name">${f.name}</span>
            <div class="feature-bar-bg"><div class="feature-bar" style="width:${f.val}%;background:${f.color}"></div></div>
            <span class="feature-value">${f.val}%</span>
        </div>`).join('');
    setTimeout(() => {
        container.querySelectorAll('.feature-bar').forEach(b => { const w=b.style.width; b.style.width='0%'; setTimeout(()=>b.style.width=w, 50); });
    }, 300);
}

function initWeatherDemandChart() {
    const ctx = document.getElementById('weather-demand-chart');
    if (!ctx) return;
    const hours = hourLabels(12);
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: hours,
            datasets: [
                { label: 'Temperature (°C)', data: [32,33,35,37,38,39,38,37,36,35,34,33], borderColor: COLORS.orange, backgroundColor: COLORS.orange+'08', borderWidth: 2, tension: .4, fill: true, yAxisID: 'y' },
                { label: 'Demand (units/hr)', data: [280,310,380,450,520,580,540,480,420,360,310,270], borderColor: COLORS.cyan, borderWidth: 2, tension: .4, borderDash: [4,4], yAxisID: 'y1' },
            ],
        },
        options: { responsive: true, maintainAspectRatio: false, interaction: { mode: 'index', intersect: false }, scales: { x: { grid: { display: false } }, y: { position: 'left', title: { display: true, text: '°C' }, grid: { color: 'rgba(255,255,255,.03)' } }, y1: { position: 'right', title: { display: true, text: 'Units/hr' }, grid: { display: false } } } },
    });
}

function initTechStack() {
    const container = document.getElementById('tech-stack');
    if (!container) return;
    const stack = [
        { icon: '⚡', name: 'FastAPI', desc: 'Async Python backend' },
        { icon: '🐘', name: 'PostgreSQL + PostGIS', desc: 'Geospatial database' },
        { icon: '🧠', name: 'XGBoost + LSTM', desc: 'Demand forecasting' },
        { icon: '👁️', name: 'YOLO v11', desc: 'Inventory vision AI' },
        { icon: '📡', name: 'Apache Kafka', desc: 'Event streaming' },
        { icon: '🗄️', name: 'Redis', desc: 'Cache & sessions' },
        { icon: '📦', name: 'MinIO', desc: 'S3-compatible storage' },
        { icon: '🐳', name: 'Docker + K8s', desc: 'Container orchestration' },
        { icon: '📊', name: 'Prometheus + Grafana', desc: 'Monitoring & alerts' },
    ];
    container.innerHTML = stack.map(s => `
        <div class="tech-item">
            <span class="tech-name">${s.icon} ${s.name}</span>
            <span class="tech-desc">${s.desc}</span>
        </div>`).join('');
}

// ═══════════════════════════════════════════════════════════════════════════════
// MAP
// ═══════════════════════════════════════════════════════════════════════════════

let map = null;
let storyCartMarker = null;

function initMap() {
    if (map) return;

    const lightMap = L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; OpenStreetMap &copy; CARTO',
        maxZoom: 20
    });

    const satelliteMap = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
        attribution: 'Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community',
        maxZoom: 18
    });

    map = L.map('live-map', { 
        center: [17.385, 78.4867], 
        zoom: 12, 
        zoomControl: true,
        layers: [lightMap]
    });

    const baseMaps = {
        "🗺️ Light Theme": lightMap,
        "🛰️ Satellite View": satelliteMap
    };

    L.control.layers(baseMaps, null, { position: 'topright' }).addTo(map);

    const statuses = ['active','active','active','active','active','active','low-stock','low-stock','offline'];
    for (let i = 0; i < 250; i++) {
        const lat = 17.385 + (Math.random()-.5)*.15;
        const lng = 78.487 + (Math.random()-.5)*.2;
        const status = pick(statuses);
        const size = status === 'active' ? 7 : status === 'low-stock' ? 9 : 5;
        const icon = L.divIcon({ className: `cart-marker ${status}`, iconSize: [size, size] });
        const marker = L.marker([lat, lng], { icon }).addTo(map);
        const stock = status==='active'?rand(40,100):status==='low-stock'?rand(3,20):0;
        const sc = status==='active'?COLORS.green:status==='low-stock'?COLORS.orange:COLORS.red;
        const sl = status==='active'?'Active':status==='low-stock'?'Low Stock':'Offline';
        marker.bindPopup(`<div class="popup-header">🛒 JC-${String(i+1001).padStart(4,'0')}</div><div class="popup-detail"><b>Vendor:</b> ${pick(VENDORS)}</div><div class="popup-detail"><b>Area:</b> ${pick(AREAS)}</div><div class="popup-detail"><b>Stock:</b> ${stock} units</div><div class="popup-detail"><b>Status:</b> <span class="popup-status" style="background:${sc}22;color:${sc}">${sl}</span></div>`, { maxWidth: 220 });
    }

    // Storyboard Cart JC-6890 (placed near Uppal Stadium hotspot)
    const storyIcon = L.divIcon({ className: 'cart-marker low-stock', iconSize: [9, 9] });
    storyCartMarker = L.marker([17.3920, 78.5510], { icon: storyIcon }).addTo(map);
    storyCartMarker.bindPopup(`
        <div class="popup-header">🛒 JC-6890 (Uppal Stadium)</div>
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
        const lmIcon = L.divIcon({ 
            className: 'cart-marker landmark-pin', 
            iconSize: [16, 16] 
        });
        L.marker([lm.lat, lm.lng], { icon: lmIcon }).addTo(map).bindPopup(`
            <div class="popup-header" style="color: var(--accent-cyan)">📍 ${lm.name}</div>
            <div class="popup-detail" style="margin-top: 4px;"><b>Details:</b> ${lm.desc}</div>
        `, { maxWidth: 250 });
    });

    [{name:'Main Cold Storage - Kukatpally',lat:17.495,lng:78.399},{name:'Distribution Hub - Uppal',lat:17.399,lng:78.559},{name:'Warehouse - Miyapur',lat:17.497,lng:78.357},{name:'Regional Hub - Secunderabad',lat:17.434,lng:78.502}].forEach(wh => {
        const icon = L.divIcon({ className: 'cart-marker warehouse', iconSize: [14,14] });
        L.marker([wh.lat, wh.lng], { icon }).addTo(map).bindPopup(`<div class="popup-header">🏭 ${wh.name}</div><div class="popup-detail"><b>Capacity:</b> ${rand(60,90)}% utilized</div><div class="popup-detail"><b>Temp:</b> <span style="color:${COLORS.green}">-21.3°C ✓</span></div>`, { maxWidth: 250 });
    });
}

// ─── Live Updates ───────────────────────────────────────────────────────────────

function liveUpdate() {
    const temp = document.querySelector('.weather-temp');
    if (temp) {
        const cur = parseInt(temp.textContent);
        const nv = Math.max(30, Math.min(42, cur + (Math.random()>.5?1:-1)));
        temp.textContent = nv + '°C';
        const impact = document.querySelector('.weather-impact');
        if (impact) impact.textContent = `+${Math.round((nv-25)*2.8)}% demand`;
    }
}

// ═══════════════════════════════════════════════════════════════════════════════
// YOLO SKU SANDBOX
// ═══════════════════════════════════════════════════════════════════════════════

const YOLO_DETECTIONS = {
    'well-stocked': {
        image: 'freezer-well-stocked.png',
        latency: '142ms',
        confidence: '96.8%',
        count: 16,
        items: [
            { label: 'Vanilla Cone [98%]', class: 'cone', top: 19.5, left: 25.5, width: 7.5, height: 18.5 },
            { label: 'Vanilla Cone [97%]', class: 'cone', top: 20.5, left: 30.5, width: 6.8, height: 18 },
            { label: 'Vanilla Cone [95%]', class: 'cone', top: 19.5, left: 34.5, width: 7.2, height: 18.2 },
            { label: 'Vanilla Cone [96%]', class: 'cone', top: 19.8, left: 43, width: 7.4, height: 18.5 },
            { label: 'Vanilla Cone [98%]', class: 'cone', top: 19.8, left: 51.5, width: 7.0, height: 18.5 },
            { label: 'Vanilla Cone [97%]', class: 'cone', top: 19, left: 60, width: 7.2, height: 18 },
            { label: 'Vanilla Cone [94%]', class: 'cone', top: 20, left: 64.5, width: 7.0, height: 18 },
            { label: 'Vanilla Cone [97%]', class: 'cone', top: 19, left: 69, width: 6.8, height: 18.5 },
            
            { label: 'Choco Bar [97%]', class: 'bar', top: 38, left: 26.5, width: 10.5, height: 21 },
            { label: 'Choco Bar [99%]', class: 'bar', top: 39.5, left: 39.5, width: 10.5, height: 21 },
            { label: 'Choco Bar [96%]', class: 'bar', top: 38, left: 52.5, width: 10.5, height: 21 },
            { label: 'Choco Bar [98%]', class: 'bar', top: 38, left: 65.5, width: 10.5, height: 21 },
            
            { label: 'Mango Cup [99%]', class: 'cup', top: 60, left: 26.2, width: 11, height: 11 },
            { label: 'Matcha Cup [98%]', class: 'cup', top: 60, left: 39.2, width: 11, height: 11 },
            { label: 'Berry Cup [97%]', class: 'cup', top: 60, left: 52.2, width: 11, height: 11 },
            { label: 'Honey Cup [95%]', class: 'cup', top: 60, left: 65.2, width: 11, height: 11 },
        ],
        audit: [
            { emoji: '🍦', name: 'Vanilla Cone Classic', qty: 8, cat: 'cone' },
            { emoji: '🍫', name: 'Choco Bar Supreme', qty: 4, cat: 'bar' },
            { emoji: '🥭', name: 'Mango Kulfi Cup', qty: 1, cat: 'cup' },
            { emoji: '🍵', name: 'Matcha Green Tea Cup', qty: 1, cat: 'cup' },
            { emoji: '🍓', name: 'Wild Berry Sorbet Cup', qty: 1, cat: 'cup' },
            { emoji: '🍯', name: 'Lavender Honey Cup', qty: 1, cat: 'cup' }
        ]
    },
    'low-stock': {
        image: 'freezer-low-stock.png',
        latency: '138ms',
        confidence: '95.1%',
        count: 4,
        items: [
            { label: 'Vanilla Cone [96%]', class: 'cone', top: 30, left: 26, width: 18, height: 17 },
            { label: 'Vanilla Cone [94%]', class: 'cone', top: 27, left: 57, width: 18, height: 10 },
            { label: 'Vanilla Cone [95%]', class: 'cone', top: 53, left: 45, width: 14, height: 18 },
            { label: 'Choco Bar [96%]', class: 'bar', top: 44, left: 23, width: 24, height: 13 },
        ],
        audit: [
            { emoji: '🍦', name: 'Vanilla Cone Classic', qty: 3, cat: 'cone' },
            { emoji: '🍫', name: 'Choco Bar Supreme', qty: 1, cat: 'bar' }
        ]
    },
    'stockout': {
        image: 'freezer-stockout.png',
        latency: '135ms',
        confidence: '94.3%',
        count: 1,
        items: [
            { label: 'Vanilla Cup [94%]', class: 'cup', top: 43, left: 43, width: 14, height: 15 },
        ],
        audit: [
            { emoji: '🍦', name: 'Vanilla Cup Classic', qty: 1, cat: 'cup' }
        ]
    }
};

function initYOLOSandbox() {
    const btnWell = document.getElementById('btn-well-stocked');
    const btnLow = document.getElementById('btn-low-stock');
    const btnStockout = document.getElementById('btn-stockout');
    const btnRun = document.getElementById('btn-run-yolo');
    const img = document.getElementById('freezer-img');
    const scanner = document.getElementById('yolo-scanner');
    const overlay = document.getElementById('detection-overlay');
    
    const latVal = document.getElementById('inf-latency');
    const countVal = document.getElementById('inf-count');
    const confVal = document.getElementById('inf-confidence');
    const auditVal = document.getElementById('detected-items');

    if (!btnWell) return;

    let currentState = 'well-stocked';
    let isScanning = false;

    function switchState(state) {
        if (isScanning) return;
        currentState = state;
        
        btnWell.classList.toggle('active', state === 'well-stocked');
        btnLow.classList.toggle('active', state === 'low-stock');
        btnStockout.classList.toggle('active', state === 'stockout');
        
        img.src = YOLO_DETECTIONS[state].image;
        overlay.innerHTML = '';
        
        // Reset stats
        latVal.textContent = '—';
        countVal.textContent = '—';
        confVal.textContent = '—';
        auditVal.innerHTML = '<span class="placeholder-text">Select a freezer state above and click "Run YOLO Scanner" to start analysis.</span>';
    }

    btnWell.addEventListener('click', () => switchState('well-stocked'));
    btnLow.addEventListener('click', () => switchState('low-stock'));
    btnStockout.addEventListener('click', () => switchState('stockout'));

    btnRun.addEventListener('click', () => {
        if (isScanning) return;
        isScanning = true;
        
        // UI feedback during scan
        btnRun.disabled = true;
        btnRun.textContent = '⏱️ Running YOLO...';
        scanner.style.display = 'block';
        overlay.innerHTML = '';
        
        latVal.textContent = 'Inference...';
        countVal.textContent = 'Inference...';
        confVal.textContent = 'Inference...';
        auditVal.innerHTML = '<span class="placeholder-text" style="color:var(--accent-purple); text-align:center;">Running deep bounding box inference on GPU cluster...</span>';

        setTimeout(() => {
            scanner.style.display = 'none';
            btnRun.disabled = false;
            btnRun.innerHTML = '⚡ Run YOLO Scanner';
            isScanning = false;

            const data = YOLO_DETECTIONS[currentState];
            
            // Set statistics
            latVal.textContent = data.latency;
            countVal.textContent = data.count;
            confVal.textContent = data.confidence;

            // Render bounding boxes
            overlay.innerHTML = data.items.map(item => `
                <div class="yolo-bbox ${item.class}" style="top:${item.top}%; left:${item.left}%; width:${item.width}%; height:${item.height}%;">
                    <span class="yolo-label">${item.label}</span>
                </div>
            `).join('');

            // Cascade visibility of bounding boxes for premium look
            const boxes = overlay.querySelectorAll('.yolo-bbox');
            boxes.forEach((box, i) => {
                setTimeout(() => box.classList.add('visible'), i * 60);
            });

            // Render inventory audit list
            const total = data.audit.reduce((sum, item) => sum + item.qty, 0);
            const auditHTML = data.audit.map(item => `
                <div class="audit-row">
                    <div class="audit-item-info">
                        <span class="audit-item-dot ${item.cat}"></span>
                        <span>${item.emoji} <b>${item.name}</b></span>
                    </div>
                    <span class="audit-qty">${item.qty} units</span>
                </div>
            `).join('') + `
                <div class="audit-total-row">
                    <span>Total Detected</span>
                    <span class="text-cyan">${total} units</span>
                </div>
            `;
            auditVal.innerHTML = auditHTML;

            // Push a live alert to the Command Center alerts feed if stock is low or out!
            const feed = document.getElementById('alert-feed');
            if (feed) {
                let newAlertHTML = '';
                if (currentState === 'low-stock') {
                    newAlertHTML = `
                        <div class="alert-item warning">
                            <span class="alert-icon">⚠️</span>
                            <div class="alert-body">
                                <div class="alert-title">YOLO Alert: Cart JC-${rand(1000,9999)} Low Stock</div>
                                <div class="alert-detail">Only 4 items remaining in freezer chest · Priority refill auto-queued</div>
                            </div>
                            <span class="alert-time">Just now</span>
                        </div>
                    `;
                } else if (currentState === 'stockout') {
                    newAlertHTML = `
                        <div class="alert-item critical">
                            <span class="alert-icon">🚨</span>
                            <div class="alert-body">
                                <div class="alert-title">YOLO Alert: Cart JC-${rand(1000,9999)} Stockout Detected</div>
                                <div class="alert-detail">Freezer empty except for 1 melting cup · Urgent refill dispatched</div>
                            </div>
                            <span class="alert-time">Just now</span>
                        </div>
                    `;
                } else {
                    newAlertHTML = `
                        <div class="alert-item success">
                            <span class="alert-icon">✅</span>
                            <div class="alert-body">
                                <div class="alert-title">YOLO Check: Cart JC-${rand(1000,9999)} Stock Level Normal</div>
                                <div class="alert-detail">16 items counted · Cold chain compliance at -21.1°C</div>
                            </div>
                            <span class="alert-time">Just now</span>
                        </div>
                    `;
                }
                feed.insertAdjacentHTML('afterbegin', newAlertHTML);
            }
        }, 1800);
    });
}

// ═══════════════════════════════════════════════════════════════════════════════
// ROLE SWITCHING & STORYBOARD CONTROLLER
// ═══════════════════════════════════════════════════════════════════════════════

function initRoleSwitcher() {
    const btnCompany = document.getElementById('btn-role-company');
    const btnEmployee = document.getElementById('btn-role-employee');
    
    if (!btnCompany || !btnEmployee) return;

    btnCompany.addEventListener('click', () => {
        setRole('company');
    });

    btnEmployee.addEventListener('click', () => {
        setRole('employee');
    });
}

function setRole(role) {
    const btnCompany = document.getElementById('btn-role-company');
    const btnEmployee = document.getElementById('btn-role-employee');
    const body = document.body;

    const avatar = document.querySelector('.user-avatar');
    const name = document.querySelector('.user-name');
    const urole = document.querySelector('.user-role');

    if (role === 'company') {
        body.classList.remove('view-employee');
        body.classList.add('view-company');
        if (btnCompany) btnCompany.classList.add('active');
        if (btnEmployee) btnEmployee.classList.remove('active');

        if (avatar) avatar.textContent = 'DG';
        if (name) name.textContent = 'Dhruv G.';
        if (urole) urole.textContent = 'CEO · Admin';

        // Auto-navigate to Command Center if current section is not part of Company View
        const activeSection = document.querySelector('.section.active');
        if (activeSection && (activeSection.id === 'section-live-map' || activeSection.id === 'section-supply-chain')) {
            navTo('command-center');
        }
    } else {
        body.classList.remove('view-company');
        body.classList.add('view-employee');
        if (btnEmployee) btnEmployee.classList.add('active');
        if (btnCompany) btnCompany.classList.remove('active');

        if (avatar) avatar.textContent = 'OC';
        if (name) name.textContent = 'Ops Crew';
        if (urole) urole.textContent = 'Field Operations';

        // Auto-navigate to Live Map if current section is not part of Employee View
        const activeSection = document.querySelector('.section.active');
        if (activeSection && activeSection.id !== 'section-live-map' && activeSection.id !== 'section-supply-chain') {
            navTo('live-map');
        }
    }
}

const storyboardSteps = [
    {
        title: "Step 1: AI Hyperlocal Demand Forecasting (IT/AI)",
        text: "Jersey's AI models predict tomorrow will hit 40°C with an IPL Cricket Match at Uppal Stadium, triggering a 42% demand spike. Watch the forecast spike on the AI Hub chart.",
        role: "company",
        section: "ai-hub",
        highlightId: "ai-forecast-chart",
        action: () => {}
    },
    {
        title: "Step 2: Forecast-Aligned Production (Production)",
        text: "The factory automatically schedules manufacture of 42,500L (Vanilla Cone, Mango Kulfi) to match this predicted spike, ensuring zero overproduction.",
        role: "company",
        section: "production",
        highlightId: "production-demand-chart",
        action: () => {}
    },
    {
        title: "Step 3: Smart Cold Chain Dispatch (Supply Chain)",
        text: "Refrigerated fleet is dispatched to regional hubs. Live IoT sensor charts track cold chain compliance at -21°C across all vehicles.",
        role: "employee",
        section: "supply-chain",
        highlightId: "cold-chain-chart",
        action: () => {}
    },
    {
        title: "Step 4: Push Cart Street Sales (Live Map)",
        text: "8,500+ carts are live in Hyderabad. As crowds arrive at the cricket stadium, Cart JC-6890 near Uppal Stadium starts running low on Mango Kulfi.",
        role: "employee",
        section: "live-map",
        highlightId: "live-map",
        action: () => {
            initMap();
            if (map) {
                map.setView([17.3912, 78.5527], 15);
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
        title: "Step 5: WhatsApp YOLO SKU Detection (YOLO Sandbox)",
        text: "The vendor snaps a WhatsApp photo of their freezer chest. YOLO v11 counts inventory in 142ms, detects low stock (4 items left), and triggers auto-refill.",
        role: "company",
        section: "ai-hub",
        highlightClass: "yolo-sandbox-card",
        action: () => {
            const yoloCard = document.querySelector('.yolo-sandbox-card');
            if (yoloCard) {
                yoloCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
            const btnLow = document.getElementById('btn-low-stock');
            const btnRun = document.getElementById('btn-run-yolo');
            if (btnLow && btnRun) {
                btnLow.click();
                setTimeout(() => {
                    btnRun.click();
                }, 500);
            }
        }
    },
    {
        title: "Step 6: Smart Route Refill (Operations)",
        text: "The system auto-prioritizes the refill queue, calculates the fastest route, and delivers stock in 42 mins. Cart JC-6890 goes green. Sales saved!",
        role: "company",
        section: "command-center",
        highlightClass: "alert-card",
        action: () => {
            if (storyCartMarker) {
                const icon = L.divIcon({ className: 'cart-marker active story-highlight', iconSize: [9, 9] });
                storyCartMarker.setIcon(icon);
                storyCartMarker.setPopupContent(`
                    <div class="popup-header">🛒 JC-6890 (Uppal Stadium)</div>
                    <div class="popup-detail"><b>Vendor:</b> Raju Kumar</div>
                    <div class="popup-detail"><b>Status:</b> <span class="popup-status" style="background:${COLORS.green}22;color:${COLORS.green}">Active (Refilled)</span></div>
                    <div class="popup-detail"><b>Stock:</b> 80 units (Mango Kulfi)</div>
                    <div class="popup-detail"><b>Refill Time:</b> 42 mins ago</div>
                `);
            }
            const feed = document.getElementById('alert-feed');
            if (feed) {
                const newAlertHTML = `
                    <div class="alert-item success story-highlight">
                        <span class="alert-icon">✅</span>
                        <div class="alert-body">
                            <div class="alert-title">Refill Complete: Cart JC-6890</div>
                            <div class="alert-detail">Raju Kumar (Uppal Stadium) refilled with 80 units · Delivery time: 42 mins</div>
                        </div>
                        <span class="alert-time">Just now</span>
                    </div>
                `;
                feed.insertAdjacentHTML('afterbegin', newAlertHTML);
            }
        }
    },
    {
        title: "Step 7: Autonomous Sellability & Flavor Orchestration (Orchestrator)",
        text: "The Orchestrator actively aligns freezer layouts to weather/event demand. Try changing temperature or neighborhood in the simulator to see flavor slots dynamically adjust and actions deploy!",
        role: "company",
        section: "orchestrator",
        highlightClass: "orchestrator-config-card",
        action: () => {
            const tempInput = document.getElementById('orch-input-temp');
            const teleInput = document.getElementById('orch-input-telemetry');
            if (tempInput && teleInput) {
                tempInput.value = 40;
                teleInput.value = 'strain';
                // Trigger change events manually
                tempInput.dispatchEvent(new Event('input'));
                teleInput.dispatchEvent(new Event('change'));
            }
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
    navTo(step.section);
    setRole(step.role);

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

// ═══════════════════════════════════════════════════════════════════════════════
// ORCHESTRATOR
// ═══════════════════════════════════════════════════════════════════════════════

let orchestratorDecayChart = null;
let savedSpoilageRevenue = 48200;

function initOrchestrator() {
    const tempInput = document.getElementById('orch-input-temp');
    const humInput = document.getElementById('orch-input-humidity');
    const neighInput = document.getElementById('orch-input-neighborhood');
    const teleInput = document.getElementById('orch-input-telemetry');

    if (!tempInput) return;

    // Attach listeners
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

    // Update slider labels
    document.getElementById('orch-lbl-temp').textContent = temp + '°C';
    document.getElementById('orch-lbl-humidity').textContent = humidity + '%';

    // 1. Calculate KPIs
    let baseMinutes = 320;
    if (temp > 30) baseMinutes -= (temp - 30) * 10;
    if (humidity > 50) baseMinutes -= (humidity - 50) * 1.5;
    
    let telemetryMult = 1.0;
    if (telemetry === 'strain') telemetryMult = 0.45;
    else if (telemetry === 'outage') telemetryMult = 0.12;

    let sellableMinutes = Math.max(12, Math.round(baseMinutes * telemetryMult));
    
    // Update Sellable Minutes KPI
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

    // Update Melt-Risk Alert State KPI
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

    // Update Assortment Yield KPI
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

    // Update Spoilage Cost Saved KPI
    document.getElementById('val-spoilage-saved').textContent = '₹' + savedSpoilageRevenue.toLocaleString();

    // 2. Adjust planogram pockets based on neighborhood/event + telemetry
    let pockets = [];
    
    // Select freezer status border class
    const gridPockets = document.getElementById('freezer-grid-pockets');
    gridPockets.className = 'freezer-grid';
    if (telemetry === 'strain') gridPockets.classList.add('telemetry-strain');
    else if (telemetry === 'outage') gridPockets.classList.add('telemetry-outage');

    if (telemetry === 'outage') {
        // Meltdown mode: restrict to high margin and show melting
        pockets = [
            { sku: 'Vanilla Cone Classic', cat: 'cone', qty: 8, capacity: 80, demand: 'LOW', emoji: '🍦' },
            { sku: 'Choco Bar Supreme', cat: 'bar', qty: 5, capacity: 60, demand: 'LOW', emoji: '🍫' },
            { sku: 'Melting Mango Cup', cat: 'cup', qty: 2, capacity: 50, demand: 'LOW', emoji: '🥭' },
            { sku: 'Melting Berry Cup', cat: 'cup', qty: 3, capacity: 50, demand: 'LOW', emoji: '🍓' },
            { sku: 'Empty Space', cat: 'empty', qty: 0, capacity: 40, demand: 'NONE', emoji: '⏹️' },
            { sku: 'Empty Space', cat: 'empty', qty: 0, capacity: 40, demand: 'NONE', emoji: '⏹️' },
            { sku: 'Empty Space', cat: 'empty', qty: 0, capacity: 40, demand: 'NONE', emoji: '⏹️' },
            { sku: 'Empty Space', cat: 'empty', qty: 0, capacity: 40, demand: 'NONE', emoji: '⏹️' },
        ];
    } else if (telemetry === 'strain') {
        // Priority high margin compression
        pockets = [
            { sku: 'Vanilla Cone Classic', cat: 'cone', qty: 35, capacity: 80, demand: 'HIGH', emoji: '🍦' },
            { sku: 'Vanilla Cone Classic', cat: 'cone', qty: 22, capacity: 80, demand: 'HIGH', emoji: '🍦' },
            { sku: 'Choco Bar Supreme', cat: 'bar', qty: 45, capacity: 60, demand: 'HIGH', emoji: '🍫' },
            { sku: 'Choco Bar Supreme', cat: 'bar', qty: 15, capacity: 60, demand: 'HIGH', emoji: '🍫' },
            { sku: 'Mango Kulfi Cup', cat: 'cup', qty: 18, capacity: 50, demand: 'MED', emoji: '🥭' },
            { sku: 'Matcha Green Tea Cup', cat: 'cup', qty: 12, capacity: 50, demand: 'MED', emoji: '🍵' },
            { sku: 'Empty Space', cat: 'empty', qty: 0, capacity: 40, demand: 'NONE', emoji: '⏹️' },
            { sku: 'Empty Space', cat: 'empty', qty: 0, capacity: 40, demand: 'NONE', emoji: '⏹️' },
        ];
    } else {
        // Normal layouts by neighborhood
        if (neighborhood === 'stadium-ipl') {
            // Impulse sticks and cups
            pockets = [
                { sku: 'Vanilla Cone Classic', cat: 'cone', qty: 74, capacity: 80, demand: 'HIGH', emoji: '🍦' },
                { sku: 'Vanilla Cone Classic', cat: 'cone', qty: 68, capacity: 80, demand: 'HIGH', emoji: '🍦' },
                { sku: 'Choco Bar Supreme', cat: 'bar', qty: 58, capacity: 60, demand: 'HIGH', emoji: '🍫' },
                { sku: 'Choco Bar Supreme', cat: 'bar', qty: 52, capacity: 60, demand: 'HIGH', emoji: '🍫' },
                { sku: 'Mango Kulfi Cup', cat: 'cup', qty: 47, capacity: 50, demand: 'HIGH', emoji: '🥭' },
                { sku: 'Wild Berry Sorbet Cup', cat: 'cup', qty: 44, capacity: 50, demand: 'HIGH', emoji: '🍓' },
                { sku: 'Vanilla Cup Classic', cat: 'cup', qty: 38, capacity: 50, demand: 'MED', emoji: '🍨' },
                { sku: 'Matcha Green Tea Cup', cat: 'cup', qty: 35, capacity: 50, demand: 'MED', emoji: '🍵' },
            ];
        } else if (neighborhood === 'rainy-evening') {
            // Family tubs, compress single cups
            pockets = [
                { sku: 'Chocolate Family Tub', cat: 'tub', qty: 26, capacity: 30, demand: 'HIGH', emoji: '🍨' },
                { sku: 'Butterscotch Family Tub', cat: 'tub', qty: 22, capacity: 30, demand: 'HIGH', emoji: '🍨' },
                { sku: 'Vanilla Cone Classic', cat: 'cone', qty: 15, capacity: 80, demand: 'LOW', emoji: '🍦' },
                { sku: 'Choco Bar Supreme', cat: 'bar', qty: 12, capacity: 60, demand: 'LOW', emoji: '🍫' },
                { sku: 'Reduced Space', cat: 'empty', qty: 0, capacity: 40, demand: 'NONE', emoji: '⏹️' },
                { sku: 'Reduced Space', cat: 'empty', qty: 0, capacity: 40, demand: 'NONE', emoji: '⏹️' },
                { sku: 'Reduced Space', cat: 'empty', qty: 0, capacity: 40, demand: 'NONE', emoji: '⏹️' },
                { sku: 'Reduced Space', cat: 'empty', qty: 0, capacity: 40, demand: 'NONE', emoji: '⏹️' },
            ];
        } else if (neighborhood === 'corporate-hotspot') {
            // High impulse cones/bars
            pockets = [
                { sku: 'Vanilla Cone Classic', cat: 'cone', qty: 62, capacity: 80, demand: 'HIGH', emoji: '🍦' },
                { sku: 'Vanilla Cone Classic', cat: 'cone', qty: 54, capacity: 80, demand: 'HIGH', emoji: '🍦' },
                { sku: 'Choco Bar Supreme', cat: 'bar', qty: 48, capacity: 60, demand: 'HIGH', emoji: '🍫' },
                { sku: 'Choco Bar Supreme', cat: 'bar', qty: 42, capacity: 60, demand: 'HIGH', emoji: '🍫' },
                { sku: 'Matcha Green Tea Cup', cat: 'cup', qty: 36, capacity: 50, demand: 'HIGH', emoji: '🍵' },
                { sku: 'Lavender Honey Cup', cat: 'cup', qty: 32, capacity: 50, demand: 'MED', emoji: '🍯' },
                { sku: 'Wild Berry Sorbet Cup', cat: 'cup', qty: 24, capacity: 50, demand: 'MED', emoji: '🍓' },
                { sku: 'Chocolate Family Tub', cat: 'tub', qty: 8, capacity: 30, demand: 'LOW', emoji: '🍨' },
            ];
        } else {
            // Balanced Suburban
            pockets = [
                { sku: 'Vanilla Cone Classic', cat: 'cone', qty: 48, capacity: 80, demand: 'HIGH', emoji: '🍦' },
                { sku: 'Choco Bar Supreme', cat: 'bar', qty: 36, capacity: 60, demand: 'HIGH', emoji: '🍫' },
                { sku: 'Mango Kulfi Cup', cat: 'cup', qty: 28, capacity: 50, demand: 'MED', emoji: '🥭' },
                { sku: 'Chocolate Family Tub', cat: 'tub', qty: 18, capacity: 30, demand: 'HIGH', emoji: '🍨' },
                { sku: 'Wild Berry Sorbet Cup', cat: 'cup', qty: 24, capacity: 50, demand: 'MED', emoji: '🍓' },
                { sku: 'Matcha Green Tea Cup', cat: 'cup', qty: 15, capacity: 50, demand: 'LOW', emoji: '🍵' },
                { sku: 'Lavender Honey Cup', cat: 'cup', qty: 12, capacity: 50, demand: 'LOW', emoji: '🍯' },
                { sku: 'Butterscotch Family Tub', cat: 'tub', qty: 10, capacity: 30, demand: 'MED', emoji: '🍨' },
            ];
        }
    }

    // Render Pockets HTML
    gridPockets.innerHTML = pockets.map((p, idx) => {
        const fill = p.capacity > 0 ? (p.qty / p.capacity * 100) : 0;
        return `
            <div class="freezer-pocket ${p.cat}">
                <div class="pocket-header">
                    <span class="pocket-num">SLOT ${idx+1}</span>
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
            </div>
        `;
    }).join('');

    // Trigger pocket highlight pop-in effect
    gridPockets.querySelectorAll('.freezer-pocket').forEach((pocket, i) => {
        setTimeout(() => pocket.classList.add('pocket-transition'), i * 40);
    });

    // 3. Update predicted decay chart
    updateOrchestratorDecayChart(temp, telemetry);

    // 4. Generate dynamic actions
    updateOrchestratorActions(temp, humidity, neighborhood, telemetry);
}

function updateOrchestratorDecayChart(temp, telemetry) {
    const ctx = document.getElementById('orchestrator-decay-chart');
    if (!ctx) return;

    // Generate simulated data based on parameters
    const labels = Array.from({length: 12}, (_, i) => `${i + 1}h`);
    
    let sellabilityData = [];
    let temperatureData = [];
    
    let currentSellability = 100;
    let currentFreezerTemp = -21.5;

    // Telemetry initial temp
    if (telemetry === 'strain') currentFreezerTemp = -12.0;
    else if (telemetry === 'outage') currentFreezerTemp = 0.0;

    for (let i = 0; i < 12; i++) {
        // Temperature rises based on state
        if (telemetry === 'normal') {
            currentFreezerTemp = -21.5 + Math.sin(i / 2) * 0.5;
        } else if (telemetry === 'strain') {
            currentFreezerTemp += 0.8 + (temp - 30) * 0.05; // slowly heats up
        } else {
            currentFreezerTemp += 1.6 + (temp - 30) * 0.12; // quickly heats up
        }
        temperatureData.push(parseFloat(currentFreezerTemp.toFixed(1)));

        // Sellability decays depending on freezer temp
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
                    { label: 'Sellable Score (%)', data: sellabilityData, borderColor: COLORS.blue, backgroundColor: COLORS.blue + '08', borderWidth: 2.5, tension: 0.4, fill: true, yAxisID: 'y' },
                    { label: 'Freezer Temp (°C)', data: temperatureData, borderColor: COLORS.orange, borderWidth: 2, tension: 0.4, borderDash: [4,4], yAxisID: 'y1' }
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
            desc: 'Freezer temperature has reached 0°C. Cold chain breach detected! Auto-action needed to dispatch cold transfer van and markdown stocks.',
            btnText: 'Deploy Recovery Van & Promo'
        });
    }

    if (telemetry === 'strain' || telemetry === 'outage') {
        actions.push({
            id: 'act-strain-markdown',
            type: 'warning',
            emoji: '⚠️',
            title: 'Compressor Overheat: Jubilee Hills Cart JC-802',
            desc: 'Slow temperature rise (-12.0°C). Suggest auto-markdown of cups/cones by 20% to accelerate sales velocity before spoilage.',
            btnText: 'Approve 20% Promo Markdown'
        });
    }

    if (neighborhood === 'stadium-ipl') {
        actions.push({
            id: 'act-stadium-refill',
            type: 'info',
            emoji: '🏏',
            title: 'IPL Stadium Surge: Uppal Cart JC-6890',
            desc: 'Stadium gate opening. Impulse demand spike predicted (+42%). Deploy slot adjustments to lock 100% cones/bars layout.',
            btnText: 'Approve Slot Optimization'
        });
    }

    if (temp >= 40 && telemetry === 'normal') {
        actions.push({
            id: 'act-heat-alert',
            type: 'warning',
            emoji: '☀️',
            title: 'Extreme Weather Stress: Hitech City Cart JC-109',
            desc: 'Ambient temperature reached 41°C. Sunshade deployment alert sent. Suggest minor price markdown (10%) to preserve sellable minutes.',
            btnText: 'Acknowledge & Deploy Promo'
        });
    }

    if (neighborhood === 'rainy-evening') {
        actions.push({
            id: 'act-rainy-compress',
            type: 'info',
            emoji: '🌧️',
            title: 'Assortment Compression: Secunderabad Cart JC-2401',
            desc: 'Rainfall drops impulse footfall by 70%. Activate compression to vacate single cone slots and prioritize family tubs.',
            btnText: 'Deploy Planogram Compression'
        });
    }

    // Default suburban action to ensure feed is never empty
    actions.push({
        id: 'act-default-align',
        type: 'info',
        emoji: '🔄',
        title: 'Banjara Hills Cart JC-331: Layout Mismatch',
        desc: 'Suburban evening behavior detected but planogram is locked on daytime impulse slots. Auto-realign slot 7-8 to family chocolate tubs.',
        btnText: 'Approve Realignment'
    });

    badge.textContent = actions.length + ' Action' + (actions.length > 1 ? 's' : '') + ' Pending';
    if (actions.length > 1) {
        badge.className = 'card-badge alert-card';
    } else {
        badge.className = 'card-badge pulse-badge';
    }

    feed.innerHTML = actions.map(act => `
        <div class="alert-item ${act.type}" id="${act.id}">
            <span class="alert-icon">${act.emoji}</span>
            <div class="alert-body">
                <div class="alert-title" style="font-weight: 700;">${act.title}</div>
                <div class="alert-detail" style="margin-bottom: 8px;">${act.desc}</div>
                <button class="btn-action-execute" onclick="executeOrchestratorAction('${act.id}', '${act.title}')">${act.btnText}</button>
            </div>
            <span class="alert-time">New</span>
        </div>
    `).join('');
}

// Global action executor called by button onclick
window.executeOrchestratorAction = function(id, title) {
    const btn = document.querySelector(`#${id} .btn-action-execute`);
    if (!btn || btn.classList.contains('success-state')) return;

    btn.innerHTML = '⚡ Deploying...';
    btn.disabled = true;

    setTimeout(() => {
        btn.innerHTML = '✓ Deployed Successfully';
        btn.className = 'btn-action-execute success-state';
        btn.disabled = true;

        // Increase spoilage saved metrics
        const savedIncrement = rand(8500, 16000);
        savedSpoilageRevenue += savedIncrement;
        document.getElementById('val-spoilage-saved').textContent = '₹' + savedSpoilageRevenue.toLocaleString();
        
        // Show premium toast
        showOrchToast('Action Complete', `Orchestrator successfully deployed recovery for: ${title}`);

        // Update main dashboard alerts feed
        const dashboardFeed = document.getElementById('alert-feed');
        if (dashboardFeed) {
            dashboardFeed.insertAdjacentHTML('afterbegin', `
                <div class="alert-item success">
                    <span class="alert-icon">🤖</span>
                    <div class="alert-body">
                        <div class="alert-title">Orchestrator Recovery Success</div>
                        <div class="alert-detail">${title} - Spoilage averted, savings: ₹${savedIncrement.toLocaleString()}</div>
                    </div>
                    <span class="alert-time">Just now</span>
                </div>
            `);
        }

        // Trigger pulse highlight on saved value
        const savedCardVal = document.getElementById('val-spoilage-saved');
        if (savedCardVal) {
            savedCardVal.classList.add('text-green');
            setTimeout(() => savedCardVal.classList.remove('text-green'), 1200);
        }

        // Fade out the alert item from the list
        setTimeout(() => {
            const item = document.getElementById(id);
            if (item) {
                item.style.transition = 'all 0.5s ease';
                item.style.opacity = '0';
                item.style.height = '0';
                item.style.padding = '0';
                item.style.margin = '0';
                setTimeout(() => {
                    item.remove();
                    // Update count
                    const badge = document.getElementById('orch-action-count');
                    const remaining = document.querySelectorAll('#orchestrator-actions-feed .alert-item').length;
                    badge.textContent = remaining + ' Action' + (remaining !== 1 ? 's' : '') + ' Pending';
                }, 500);
            }
        }, 1200);

    }, 1200);
};

function showOrchToast(title, desc) {
    // Remove existing toasts if any
    document.querySelectorAll('.orch-toast').forEach(t => t.remove());

    const toast = document.createElement('div');
    toast.className = 'orch-toast';
    toast.innerHTML = `
        <span style="font-size: 16px;">✅</span>
        <div style="display: flex; flex-direction: column;">
            <div class="orch-toast-title">${title}</div>
            <div class="orch-toast-desc">${desc}</div>
        </div>
    `;
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.style.transition = 'all 0.3s ease';
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(10px)';
        setTimeout(() => toast.remove(), 300);
    }, 3500);
}
