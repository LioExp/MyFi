// =====================
// ESTADO
// =====================
let nodes = [];
let selectedNode = null;

// =====================
// BLOCOS DISPONÍVEIS (Chunks registados)
// =====================
const availableChunks = [
  { name: 'Scanner', icon: '📡', inputs: [], outputs: ['devices'] },
  { name: 'Monitor', icon: '📊', inputs: ['devices'], outputs: ['traffic'] },
  { name: 'Limite', icon: '⏳', inputs: ['traffic'], outputs: ['alert'] },
  { name: 'Bloquear', icon: '🚫', inputs: ['alert'], outputs: [] },
  { name: 'Notificar', icon: '✉️', inputs: ['alert'], outputs: [] },
  { name: 'Log', icon: '📝', inputs: ['any'], outputs: [] },
];

// =====================
// INICIALIZAÇÃO
// =====================
document.addEventListener('DOMContentLoaded', () => {
  renderBlockList();
  carregarWorkflowSalvo();
});

function renderBlockList() {
  const list = document.getElementById('blockList');
  list.innerHTML = availableChunks.map(chunk => `
    <div class="block-item" draggable="true" ondragstart="dragBlock(event, '${chunk.name}')">
      ${chunk.icon} ${chunk.name}
    </div>
  `).join('');
}

// =====================
// DRAG & DROP
// =====================
function dragBlock(event, blockName) {
  event.dataTransfer.setData('text/plain', blockName);
}

document.addEventListener('DOMContentLoaded', () => {
  const canvas = document.getElementById('canvas');
  canvas.addEventListener('dragover', (e) => e.preventDefault());
  canvas.addEventListener('drop', (e) => {
    e.preventDefault();
    const blockName = e.dataTransfer.getData('text/plain');
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left - 60;
    const y = e.clientY - rect.top - 20;
    addNode(blockName, x, y);
  });
});

// =====================
// NÓS
// =====================
function addNode(name, x, y) {
  const chunk = availableChunks.find(c => c.name === name);
  const node = {
    id: Date.now(),
    name: name,
    icon: chunk ? chunk.icon : '⚙️',
    x: x,
    y: y,
  };
  nodes.push(node);
  renderNodes();
}

function renderNodes() {
  const canvas = document.getElementById('canvas');
  // Limpa nós antigos (mas mantém o evento de drop)
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
  element.addEventListener('mousedown', (e) => {
    offsetX = e.clientX - element.getBoundingClientRect().left;
    offsetY = e.clientY - element.getBoundingClientRect().top;
    document.addEventListener('mousemove', onMouseMove);
    document.addEventListener('mouseup', onMouseUp);
  });

  function onMouseMove(e) {
    const canvas = document.getElementById('canvas');
    const rect = canvas.getBoundingClientRect();
    node.x = e.clientX - rect.left - offsetX;
    node.y = e.clientY - rect.top - offsetY;
    element.style.left = node.x + 'px';
    element.style.top = node.y + 'px';
  }

  function onMouseUp() {
    document.removeEventListener('mousemove', onMouseMove);
    document.removeEventListener('mouseup', onMouseUp);
  }
}

function selectNode(node) {
  selectedNode = node;
  const panel = document.getElementById('propsPanel');
  const chunk = availableChunks.find(c => c.name === node.name);
  panel.innerHTML = `
    <h3>Propriedades — ${node.name}</h3>
    <p>Entradas: ${chunk ? chunk.inputs.join(', ') || 'Nenhuma' : 'N/A'}</p>
    <p>Saídas: ${chunk ? chunk.outputs.join(', ') || 'Nenhuma' : 'N/A'}</p>
    <p>Posição: (${Math.round(node.x)}, ${Math.round(node.y)})</p>
  `;
}

// =====================
// AÇÕES
// =====================
function newWorkflow() {
  nodes = [];
  selectedNode = null;
  renderNodes();
  document.getElementById('propsPanel').innerHTML = '<h3>Propriedades</h3><p class="empty-state">Clique num nó para ver as propriedades</p>';
}

function saveWorkflow() {
  const workflow = {
    name: 'workflow_' + Date.now(),
    steps: nodes.map(n => n.name),
  };
  localStorage.setItem('myfi_workflow', JSON.stringify(workflow));
  alert('Workflow guardado localmente.');
}

function carregarWorkflowSalvo() {
  const saved = localStorage.getItem('myfi_workflow');
  if (!saved) return;
  try {
    const workflow = JSON.parse(saved);
    workflow.steps.forEach((step, i) => {
      addNode(step, 80 + i * 140, 100);
    });
  } catch (e) {}
}

function clearCanvas() {
  nodes = [];
  selectedNode = null;
  renderNodes();
}

function runWorkflow() {
  if (nodes.length === 0) return alert('Adicione pelo menos um bloco.');
  const steps = nodes.map(n => n.name);
  fetch('/api/workflow/run', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name: 'manual_run', steps: steps }),
  })
  .then(r => r.json())
  .then(data => alert('Workflow executado: ' + JSON.stringify(data)))
  .catch(err => alert('Erro ao executar workflow.'));
}