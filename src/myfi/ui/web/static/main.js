// =====================
// UTILITÁRIOS
// =====================
function formatBytes(numBytes) {
    for (const unit of ['B', 'KB', 'MB', 'GB']) {
        if (numBytes < 1024) return `${numBytes.toFixed(2)} ${unit}`;
        numBytes /= 1024;
    }
    return `${numBytes.toFixed(2)} TB`;
}

async function fetchJSON(url) {
    try {
        const res = await fetch(url);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return await res.json();
    } catch (e) {
        console.warn(`API ${url} indisponível:`, e.message);
        return null;
    }
}

// Ícones para dispositivos
const deviceIcons = {
    desktop: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>',
    laptop: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 16V7a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v9m16 0H4m16 0l1.28 2.55a1 1 0 0 1-.9 1.45H3.62a1 1 0 0 1-.9-1.45L4 16"/></svg>',
    tv: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="7" width="20" height="15" rx="2"/><polyline points="17 2 12 7 7 2"/></svg>',
    smartphone: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="5" y="2" width="14" height="20" rx="2"/><line x1="12" y1="18" x2="12.01" y2="18"/></svg>',
};

function guessDeviceType(hostname) {
    if (!hostname) return 'desktop';
    const h = hostname.toLowerCase();
    if (h.includes('tv')) return 'tv';
    if (h.includes('laptop') || h.includes('portátil')) return 'laptop';
    if (h.includes('iphone') || h.includes('smartphone') || h.includes('android')) return 'smartphone';
    return 'desktop';
}

// =====================
// SIDEBAR
// =====================
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    if (!sidebar) return;
    sidebar.classList.toggle('collapsed');
    localStorage.setItem('sidebar-collapsed', sidebar.classList.contains('collapsed'));
}

// Restaurar estado colapsado
if (localStorage.getItem('sidebar-collapsed') === 'true') {
    document.addEventListener('DOMContentLoaded', () => {
        const sidebar = document.getElementById('sidebar');
        if (sidebar) sidebar.classList.add('collapsed');
    });
}

// =====================
// DASHBOARD
// =====================
let chartData = [];
let liveDevices = [];

async function loadDashboard() {
    const data = await fetchJSON('/api/dashboard');
    if (!data) return;
    liveDevices = data.devices || [];

    // KPIs
    document.getElementById('kpi-devices').textContent = data.active_devices || '0';
    const mb = ((data.today_traffic_bytes || 0) / (1024 * 1024)).toFixed(0);
    document.getElementById('kpi-traffic').textContent = mb;
    document.getElementById('kpi-alerts').textContent = data.pending_alerts || '0';

    const badge = document.getElementById('active-badge');
    if (badge) badge.textContent = `${data.active_devices || 0} ativos`;

    // Gráfico
    if (data.chart_data && data.chart_data.length > 0) {
        chartData = data.chart_data;
    }
    drawChart();
    rebuildNetworkGraph(liveDevices);
}

function drawChart() {
    const canvas = document.getElementById('trafficChart');
    if (!canvas || chartData.length === 0) return;
    const ctx = canvas.getContext('2d');
    const W = canvas.offsetWidth;
    const H = canvas.offsetHeight;
    if (canvas.width !== W) canvas.width = W;
    if (canvas.height !== H) canvas.height = H;
    ctx.clearRect(0, 0, W, H);
    const pad = { top: 10, right: 12, bottom: 36, left: 32 };
    const w = W - pad.left - pad.right;
    const h = H - pad.top - pad.bottom;
    const maxV = Math.max(500, ...chartData.map(d => d.value));
    const n = chartData.length;

    // Grid
    ctx.strokeStyle = 'rgba(255,255,255,0.04)';
    ctx.lineWidth = 1;
    for (let v = 0; v <= maxV; v += Math.ceil(maxV / 4)) {
        const y = pad.top + h - (v / maxV) * h;
        ctx.beginPath(); ctx.moveTo(pad.left, y); ctx.lineTo(pad.left + w, y); ctx.stroke();
    }

    // Y labels
    ctx.fillStyle = 'hsl(215,18%,62%)'; ctx.font = '11px Manrope,sans-serif'; ctx.textAlign = 'right';
    for (let v = 0; v <= maxV; v += Math.ceil(maxV / 4)) {
        const y = pad.top + h - (v / maxV) * h;
        ctx.fillText(v, pad.left - 6, y + 4);
    }

    // X labels
    ctx.textAlign = 'center';
    const step = Math.max(1, Math.floor(n / 5));
    for (let i = 0; i < n; i += step) {
        const x = pad.left + (i / (n - 1)) * w;
        ctx.fillText(chartData[i].time, x, pad.top + h + 18);
    }

    // Area
    const grad = ctx.createLinearGradient(0, pad.top, 0, pad.top + h);
    grad.addColorStop(0, 'hsla(195,100%,56%,0.45)');
    grad.addColorStop(1, 'hsla(195,100%,56%,0)');
    ctx.beginPath();
    chartData.forEach((d, i) => {
        const x = pad.left + (i / (n - 1)) * w;
        const y = pad.top + h - (d.value / maxV) * h;
        i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    });
    ctx.lineTo(pad.left + w, pad.top + h); ctx.lineTo(pad.left, pad.top + h); ctx.closePath();
    ctx.fillStyle = grad; ctx.fill();

    // Line
    ctx.beginPath(); ctx.strokeStyle = 'hsl(195,100%,56%)'; ctx.lineWidth = 2; ctx.lineJoin = 'round';
    chartData.forEach((d, i) => {
        const x = pad.left + (i / (n - 1)) * w;
        const y = pad.top + h - (d.value / maxV) * h;
        i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    });
    ctx.stroke();

    document.getElementById('peak-val').textContent = Math.max(...chartData.map(d => d.value));
}

function rebuildNetworkGraph(devices) {
    const container = document.getElementById('network-devices');
    if (!container) return;
    const displayDevices = devices.slice(0, 4);
    const positions = [
        { top: '6%', left: '6%' },
        { top: '6%', right: '6%' },
        { bottom: '8%', left: '6%' },
        { bottom: '8%', right: '6%' },
    ];
    container.innerHTML = displayDevices.map((d, i) => {
        const pos = positions[i] || positions[0];
        const style = Object.entries(pos).map(([k, v]) => `${k}:${v}`).join(';');
        const type = guessDeviceType(d.hostname);
        return `
            <div class="device-node" style="${style}">
                <div class="device-circle">${deviceIcons[type]}</div>
                <span class="device-label">${d.hostname || d.ip || 'Dispositivo'}</span>
            </div>
        `;
    }).join('');
}

function initNetGraph() {
    const svg = document.getElementById('netSvg');
    if (!svg) return;
    svg.querySelectorAll('g').forEach(g => g.remove());
    const cx = 200, cy = 160;
    const deviceCoords = [{ x: 60, y: 60 }, { x: 340, y: 60 }, { x: 60, y: 260 }, { x: 340, y: 260 }];
    const durs = [2.2, 2.8, 3.4, 2.6];
    deviceCoords.forEach((d, i) => {
        const mx = (cx + d.x) / 2, my = cy + (d.y - cy) * 0.15;
        const pathD = `M ${cx} ${cy} Q ${mx} ${my} ${d.x} ${d.y}`;
        const id = `conn-path-${i}`;
        const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        path.setAttribute('id', id); path.setAttribute('d', pathD);
        path.setAttribute('fill', 'none'); path.setAttribute('stroke', 'url(#connGrad)'); path.setAttribute('stroke-width', '1.25');
        g.appendChild(path);

        const dot = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        dot.setAttribute('r', '2.4'); dot.setAttribute('fill', 'hsl(195,100%,56%)'); dot.setAttribute('opacity', '0.95');

        const am = document.createElementNS('http://www.w3.org/2000/svg', 'animateMotion');
        am.setAttribute('dur', `${durs[i]}s`); am.setAttribute('repeatCount', 'indefinite');
        const mpath = document.createElementNS('http://www.w3.org/2000/svg', 'mpath');
        mpath.setAttribute('href', `#${id}`); am.appendChild(mpath);

        const anim = document.createElementNS('http://www.w3.org/2000/svg', 'animate');
        anim.setAttribute('attributeName', 'opacity');
        anim.setAttribute('values', '0;1;1;0'); anim.setAttribute('keyTimes', '0;0.15;0.85;1');
        anim.setAttribute('dur', `${durs[i]}s`); anim.setAttribute('repeatCount', 'indefinite');

        dot.appendChild(am); dot.appendChild(anim); g.appendChild(dot);
        svg.appendChild(g);
    });
}

// =====================
// DISPOSITIVOS
// =====================
let allDevices = [];

async function loadDevices() {
    try {
        const res = await fetch('/api/devices');
        if (!res.ok) throw new Error('Erro ao carregar');
        allDevices = await res.json();
        document.getElementById('device-count').textContent = `${allDevices.length} dispositivo(s) encontrado(s)`;
        renderDeviceTable(allDevices);
    } catch (e) {
        document.getElementById('device-count').textContent = 'Erro ao carregar';
    }
}

function renderDeviceTable(devices) {
    const tbody = document.getElementById('devices-tbody');
    if (!tbody) return;
    if (!devices || devices.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;padding:40px;color:var(--muted-fg)">Nenhum dispositivo encontrado.</td></tr>';
        return;
    }
    tbody.innerHTML = devices.map(d => {
        const statusDot = '<div class="dot online"></div>';
        return `
            <tr>
                <td><span class="device-name-cell">${d.hostname || 'Dispositivo'}</span></td>
                <td class="mono">${d.ip || '--'}</td>
                <td class="mono">${d.mac || '--'}</td>
                <td>${d.consumo || '0 B'}</td>
                <td><div class="status">${statusDot} online</div></td>
                <td>
                    <span class="icon" title="Bloquear">🔒</span>
                    <span class="icon" title="Alertas">🔔</span>
                </td>
            </tr>
        `;
    }).join('');
}

function filterDevices() {
    const term = document.getElementById('searchInput').value.toLowerCase();
    const filtered = allDevices.filter(d =>
        (d.hostname || '').toLowerCase().includes(term) ||
        (d.ip || '').includes(term) ||
        (d.mac || '').toLowerCase().includes(term)
    );
    renderDeviceTable(filtered);
}

function addRule() {
    window.location.href = '/automacao';
}

// =====================
// ALERTAS
// =====================
const alertIconsMap = {
    critical: '<svg viewBox="0 0 24 24" fill="none" stroke="hsl(358,78%,72%)" stroke-width="2" style="width:20px;height:20px"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>',
    warning: '<svg viewBox="0 0 24 24" fill="none" stroke="hsl(38,92%,65%)" stroke-width="2" style="width:20px;height:20px"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
    info: '<svg viewBox="0 0 24 24" fill="none" stroke="hsl(210,80%,72%)" stroke-width="2" style="width:20px;height:20px"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>'
};
const alertBadgeStyle = {
    critical: 'background:hsla(358,78%,62%,0.1);color:hsl(358,78%,72%);border:1px solid hsla(358,78%,62%,0.25)',
    warning: 'background:hsla(38,92%,58%,0.1);color:hsl(38,92%,65%);border:1px solid hsla(38,92%,58%,0.25)',
    info: 'background:hsla(210,80%,65%,0.1);color:hsl(210,80%,72%);border:1px solid hsla(210,80%,65%,0.25)'
};
const alertBadgeLabels = { critical: 'Crítico', warning: 'Aviso', info: 'Info' };

let allAlerts = [];
let currentFilter = 'todos';

async function loadAlerts() {
    try {
        const res = await fetch('/api/alerts');
        if (!res.ok) throw new Error('Erro ao carregar');
        allAlerts = await res.json();
        renderAlerts();
    } catch (e) {
        document.getElementById('alert-summary').textContent = 'Erro ao carregar alertas';
    }
}

function renderAlerts() {
    const filtered = allAlerts.filter(a => {
        if (currentFilter === 'criticos') return a.severity === 'critical';
        return true;
    });
    const container = document.getElementById('alertList');
    container.innerHTML = filtered.map(a => `
        <div class="alert-card ${a.severity}">
            <div class="alert-left">
                <div class="alert-icon">${alertIconsMap[a.severity] || alertIconsMap.info}</div>
                <div class="alert-content">
                    <strong>${a.message} <span class="badge" style="${alertBadgeStyle[a.severity]}">${alertBadgeLabels[a.severity] || 'Info'}</span></strong>
                    <p><b>${a.mac || 'Dispositivo'}</b></p>
                    <p>${a.alert_type || ''}</p>
                </div>
            </div>
            <div class="alert-right">
                ${a.timestamp}
                <div class="alert-actions">
                    <span class="link">Ver detalhes</span>
                    <span class="link" style="color:var(--muted-fg)" onclick="dismissAlert(${a.id})">Ignorar</span>
                </div>
            </div>
        </div>
    `).join('');
    document.getElementById('alert-summary').textContent = `${filtered.length} alerta(s) encontrado(s)`;
}

function filterAlerts(filter, el) {
    currentFilter = filter;
    document.querySelectorAll('.filter').forEach(f => f.classList.remove('active'));
    el.classList.add('active');
    renderAlerts();
}

function markAllRead() { alert('Funcionalidade em breve.'); }
function dismissAlert(id) { allAlerts = allAlerts.filter(a => a.id !== id); renderAlerts(); }

// =====================
// AUTOMAÇÃO (protótipo)
// =====================
let nodes = [];
let selectedNode = null;

const availableChunks = [
    { name: 'Scanner', icon: '📡', inputs: [], outputs: ['devices'] },
    { name: 'Monitor', icon: '📊', inputs: ['devices'], outputs: ['traffic'] },
    { name: 'Limite', icon: '⏳', inputs: ['traffic'], outputs: ['alert'] },
    { name: 'Bloquear', icon: '🚫', inputs: ['alert'], outputs: [] },
    { name: 'Notificar', icon: '✉️', inputs: ['alert'], outputs: [] },
    { name: 'Log', icon: '📝', inputs: ['any'], outputs: [] },
];

function renderBlockList() {
    const list = document.getElementById('blockList');
    if (!list) return;
    list.innerHTML = availableChunks.map(chunk => `
        <div class="block-item" draggable="true" ondragstart="dragBlock(event, '${chunk.name}')">${chunk.icon} ${chunk.name}</div>
    `).join('');
}

function dragBlock(event, blockName) { event.dataTransfer.setData('text/plain', blockName); }

function addNode(name, x, y) {
    const chunk = availableChunks.find(c => c.name === name);
    nodes.push({ id: Date.now(), name, icon: chunk?.icon || '⚙️', x, y });
    renderNodes();
}

function renderNodes() {
    const canvas = document.getElementById('canvas');
    if (!canvas) return;
    canvas.querySelectorAll('.workflow-node').forEach(el => el.remove());
    nodes.forEach(node => {
        const div = document.createElement('div');
        div.className = 'workflow-node';
        div.style.left = node.x + 'px';
        div.style.top = node.y + 'px';
        div.innerHTML = `${node.icon} ${node.name}`;
        div.setAttribute('data-id', node.id);
        div.onclick = () => selectNode(node);
        makeDraggable(div, node);
        canvas.appendChild(div);
    });
}

function makeDraggable(element, node) {
    let offsetX, offsetY;
    element.addEventListener('mousedown', e => {
        offsetX = e.clientX - element.getBoundingClientRect().left;
        offsetY = e.clientY - element.getBoundingClientRect().top;
        const onMouseMove = e => {
            const rect = document.getElementById('canvas').getBoundingClientRect();
            node.x = e.clientX - rect.left - offsetX;
            node.y = e.clientY - rect.top - offsetY;
            element.style.left = node.x + 'px';
            element.style.top = node.y + 'px';
        };
        const onMouseUp = () => {
            document.removeEventListener('mousemove', onMouseMove);
            document.removeEventListener('mouseup', onMouseUp);
        };
        document.addEventListener('mousemove', onMouseMove);
        document.addEventListener('mouseup', onMouseUp);
    });
}

function selectNode(node) {
    selectedNode = node;
    const panel = document.getElementById('propsPanel');
    const chunk = availableChunks.find(c => c.name === node.name);
    panel.innerHTML = `
        <h3>Propriedades — ${node.name}</h3>
        <p>Entradas: ${chunk ? chunk.inputs.join(', ') || 'Nenhuma' : 'N/A'}</p>
        <p>Saídas: ${chunk ? chunk.outputs.join(', ') || 'Nenhuma' : 'N/A'}</p>
    `;
}

function newWorkflow() { nodes = []; selectedNode = null; renderNodes(); }
function clearCanvas() { nodes = []; renderNodes(); }
function runWorkflow() { alert('Workflow executado (placeholder).'); }
function saveWorkflow() { localStorage.setItem('myfi_workflow', JSON.stringify({ steps: nodes.map(n => n.name) })); alert('Workflow guardado.'); }
function carregarWorkflowSalvo() {
    const saved = localStorage.getItem('myfi_workflow');
    if (!saved) return;
    JSON.parse(saved).steps.forEach((step, i) => addNode(step, 80 + i * 140, 100));
}

// Inicializar canvas de automação
document.addEventListener('DOMContentLoaded', () => {
    const canvas = document.getElementById('canvas');
    if (canvas) {
        canvas.addEventListener('dragover', e => e.preventDefault());
        canvas.addEventListener('drop', e => {
            e.preventDefault();
            const name = e.dataTransfer.getData('text/plain');
            const rect = canvas.getBoundingClientRect();
            addNode(name, e.clientX - rect.left - 60, e.clientY - rect.top - 20);
        });
        renderBlockList();
        carregarWorkflowSalvo();
    }
});

// =====================
// CONFIGURAÇÕES
// =====================
function updateSensitivity(val) {
    document.getElementById('sensitivity-value').textContent = parseFloat(val).toFixed(1);
}
function saveSetting(key, value) { console.log('Guardar:', key, value); }
function exportConfig() { alert('Exportação em breve.'); }

// =====================
// INICIALIZAÇÃO POR PÁGINA
// =====================
document.addEventListener('DOMContentLoaded', () => {
    // Dashboard
    if (document.getElementById('trafficChart')) {
        initNetGraph();
        loadDashboard();
        setInterval(loadDashboard, 30000);
    }
    // Dispositivos
    if (document.getElementById('devices-tbody')) {
        loadDevices();
    }
    // Alertas
    if (document.getElementById('alertList')) {
        loadAlerts();
    }
});