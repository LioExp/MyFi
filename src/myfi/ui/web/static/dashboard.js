// =====================
// API
// =====================
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

// =====================
// STATE
// =====================
let liveDevices = [];
let chartData = [];

// =====================
// KPIs
// =====================
async function loadKPIs() {
  const data = await fetchJSON('/api/dashboard');
  if (!data) return;
  liveDevices = data.devices || [];

  document.getElementById('kpi-devices').textContent = data.active_devices || '0';
  const mb = ((data.today_traffic_bytes || 0) / (1024 * 1024)).toFixed(0);
  document.getElementById('kpi-traffic').textContent = mb;
  document.getElementById('kpi-alerts').textContent = data.pending_alerts || '0';

  const badge = document.getElementById('active-badge');
  if (badge) badge.textContent = `${data.active_devices || 0} ativos`;

  // Dados do gráfico (vindos da API)
  if (data.chart_data && data.chart_data.length > 0) {
    chartData = data.chart_data;
  }

  rebuildNetworkGraph(liveDevices);
  drawChart(); // Redesenhar gráfico com dados reais
}

// =====================
// CHART (Canvas) — agora usa chartData real
// =====================
function drawChart() {
  const canvas = document.getElementById('trafficChart');
  if(!canvas || chartData.length === 0) return;
  const ctx = canvas.getContext('2d');
  const W = canvas.offsetWidth;
  const H = canvas.offsetHeight;
  if(canvas.width !== W) canvas.width = W;
  if(canvas.height !== H) canvas.height = H;
  ctx.clearRect(0,0,W,H);
  const pad = { top:10, right:12, bottom:36, left:32 };
  const w = W - pad.left - pad.right;
  const h = H - pad.top - pad.bottom;
  const minV = 0;
  const maxV = Math.max(500, ...chartData.map(d=>d.value));
  const n = chartData.length;

  // Grid
  ctx.strokeStyle='rgba(255,255,255,0.04)'; ctx.lineWidth=1;
  for(let v=0; v<=maxV; v+=Math.ceil(maxV/4)) {
    const y = pad.top + h - (v-minV)/(maxV-minV)*h;
    ctx.beginPath(); ctx.moveTo(pad.left,y); ctx.lineTo(pad.left+w,y); ctx.stroke();
  }

  // Y labels
  ctx.fillStyle='hsl(215,18%,62%)'; ctx.font='11px Manrope,sans-serif'; ctx.textAlign='right';
  for(let v=0; v<=maxV; v+=Math.ceil(maxV/4)) {
    const y = pad.top + h - (v-minV)/(maxV-minV)*h;
    ctx.fillText(v, pad.left-6, y+4);
  }

  // X labels
  ctx.textAlign='center';
  const step = Math.max(1, Math.floor(n/5));
  for(let i=0; i<n; i+=step) {
    const x = pad.left + (i/(n-1))*w;
    ctx.fillText(chartData[i].time, x, pad.top+h+18);
  }

  // Area
  const grad = ctx.createLinearGradient(0,pad.top,0,pad.top+h);
  grad.addColorStop(0,'hsla(195,100%,56%,0.45)');
  grad.addColorStop(1,'hsla(195,100%,56%,0)');
  ctx.beginPath();
  chartData.forEach((d,i)=>{
    const x = pad.left + (i/(n-1))*w;
    const y = pad.top + h - (d.value-minV)/(maxV-minV)*h;
    i===0 ? ctx.moveTo(x,y) : ctx.lineTo(x,y);
  });
  ctx.lineTo(pad.left+w, pad.top+h); ctx.lineTo(pad.left, pad.top+h); ctx.closePath();
  ctx.fillStyle=grad; ctx.fill();

  // Line
  ctx.beginPath(); ctx.strokeStyle='hsl(195,100%,56%)'; ctx.lineWidth=2; ctx.lineJoin='round';
  chartData.forEach((d,i)=>{
    const x = pad.left + (i/(n-1))*w;
    const y = pad.top + h - (d.value-minV)/(maxV-minV)*h;
    i===0 ? ctx.moveTo(x,y) : ctx.lineTo(x,y);
  });
  ctx.stroke();

  // Peak
  const peak = Math.max(...chartData.map(d=>d.value));
  document.getElementById('peak-val').textContent = peak;
}

function initChart() {
  const canvas = document.getElementById('trafficChart');
  if(!canvas) return;
  drawChart();
  window.addEventListener('resize', drawChart);
}

// =====================
// NETWORK GRAPH
// =====================
const deviceIcons = {
  desktop: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>`,
  laptop: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 16V7a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v9m16 0H4m16 0l1.28 2.55a1 1 0 0 1-.9 1.45H3.62a1 1 0 0 1-.9-1.45L4 16"/></svg>`,
  tv: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="7" width="20" height="15" rx="2"/><polyline points="17 2 12 7 7 2"/></svg>`,
  smartphone: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="5" y="2" width="14" height="20" rx="2"/><line x1="12" y1="18" x2="12.01" y2="18"/></svg>`,
};

function guessDeviceType(hostname) {
  if (!hostname) return 'desktop';
  const h = hostname.toLowerCase();
  if (h.includes('tv')) return 'tv';
  if (h.includes('laptop') || h.includes('portátil')) return 'laptop';
  if (h.includes('iphone') || h.includes('smartphone') || h.includes('android')) return 'smartphone';
  return 'desktop';
}

function rebuildNetworkGraph(devices) {
  const container = document.getElementById('network-devices');
  if (!container) return;
  const displayDevices = devices.slice(0, 4);
  const positions = [
    {top:'6%', left:'6%'},
    {top:'6%', right:'6%'},
    {bottom:'8%', left:'6%'},
    {bottom:'8%', right:'6%'},
  ];
  container.innerHTML = displayDevices.map((d, i) => {
    const pos = positions[i] || positions[0];
    const type = guessDeviceType(d.hostname);
    const style = Object.entries(pos).map(([k,v]) => `${k}:${v}`).join(';');
    return `
      <div class="device-node" style="${style}">
        <div class="device-circle">${deviceIcons[type]}</div>
        <span class="device-label">${d.hostname || d.ip || 'Dispositivo'}</span>
      </div>
    `;
  }).join('');
  const badge = document.getElementById('active-badge');
  if (badge) badge.textContent = `${devices.length} ativos`;
}

function initNetGraph() {
  const svg = document.getElementById('netSvg');
  if(!svg) return;
  svg.querySelectorAll('g').forEach(g => g.remove());
  const cx=200, cy=160;
  const deviceCoords = [{x:60,y:60},{x:340,y:60},{x:60,y:260},{x:340,y:260}];
  const durs = [2.2, 2.8, 3.4, 2.6];
  deviceCoords.forEach((d,i)=>{
    const mx=(cx+d.x)/2, my=cy+(d.y-cy)*0.15;
    const pathD=`M ${cx} ${cy} Q ${mx} ${my} ${d.x} ${d.y}`;
    const id=`conn-path-${i}`;
    const g=document.createElementNS('http://www.w3.org/2000/svg','g');
    const path=document.createElementNS('http://www.w3.org/2000/svg','path');
    path.setAttribute('id',id); path.setAttribute('d',pathD);
    path.setAttribute('fill','none'); path.setAttribute('stroke','url(#connGrad)'); path.setAttribute('stroke-width','1.25');
    g.appendChild(path);
    const dot=document.createElementNS('http://www.w3.org/2000/svg','circle');
    dot.setAttribute('r','2.4'); dot.setAttribute('fill','hsl(195,100%,56%)'); dot.setAttribute('opacity','0.95');
    const am=document.createElementNS('http://www.w3.org/2000/svg','animateMotion');
    am.setAttribute('dur',`${durs[i]}s`); am.setAttribute('repeatCount','indefinite');
    const mpath=document.createElementNS('http://www.w3.org/2000/svg','mpath');
    mpath.setAttribute('href',`#${id}`); am.appendChild(mpath);
    const anim=document.createElementNS('http://www.w3.org/2000/svg','animate');
    anim.setAttribute('attributeName','opacity');
    anim.setAttribute('values','0;1;1;0'); anim.setAttribute('keyTimes','0;0.15;0.85;1');
    anim.setAttribute('dur',`${durs[i]}s`); anim.setAttribute('repeatCount','indefinite');
    dot.appendChild(am); dot.appendChild(anim); g.appendChild(dot);
    svg.appendChild(g);
  });
}

// =====================
// INIT
// =====================
document.addEventListener('DOMContentLoaded', async ()=>{
  initNetGraph();
  await loadKPIs();
  initChart();
});