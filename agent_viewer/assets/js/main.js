/**
 * Main application logic
 */
const DEFAULT_AGENTS = [
    'claude-3.7-sonnet',
    'claude-3.7-sonnet-with-news',
    'claude-3.7-sonnet-ReverseExpectations'
];

let selectedAgents = [];
let allDates = [];
let agentMeta = [];
let labelMap = {};
let colorOverrides = {};

document.addEventListener('DOMContentLoaded', async () => {
    try {
        showLoading();
        
        if (typeof Chart === 'undefined') {
            console.error('Chart.js not loaded');
            alert('Failed to load Chart.js. Please check your network connection.');
            hideLoading();
            return;
        }
        
        initChartManager();
        
        await new Promise(resolve => setTimeout(resolve, 100));
        
        console.log('Begin loading data...');
        await dataLoader.load();
        console.log('Data loaded');

        agentMeta = dataLoader.getConfiguredAgents();
        if (!agentMeta.length) {
            agentMeta = dataLoader.getAgentNames().map(id => ({ id, label: id }));
        }
        labelMap = dataLoader.getLabelMap();
        if (!Object.keys(labelMap).length) {
            agentMeta.forEach(meta => labelMap[meta.id] = meta.label || meta.id);
        }
        colorOverrides = dataLoader.getColorOverrides();
        selectedAgents = agentMeta.map(meta => meta.id);

        initializePage();
        
        hideLoading();
    } catch (error) {
        console.error('Initialization failed:', error);
        alert('Failed to load data: ' + error.message + '\nPlease make sure data/agents_data.json exists.');
        hideLoading();
    }
});

function initializePage() {
    console.log('Initializing Agent Dashboard ...');
    
    initializeAgentSelector();
    initializeDateSelector();
    bindEvents();
    updateDisplay();
    
    console.log('Agent Dashboard ready');
}

function initializeAgentSelector() {
    const checkboxes = document.querySelectorAll('.agent-checkbox input[type="checkbox"]');
    const metaMap = agentMeta.reduce((acc, meta) => {
        acc[meta.id] = meta;
        return acc;
    }, {});

    selectedAgents = selectedAgents.length ? [...selectedAgents] : Array.from(Object.keys(metaMap));

    checkboxes.forEach(checkbox => {
        const meta = metaMap[checkbox.value];
        const shouldBeChecked = selectedAgents.includes(checkbox.value);
        checkbox.checked = shouldBeChecked;

        const container = checkbox.closest('.agent-checkbox');
        if (container && meta) {
            const nameEl = container.querySelector('.agent-name');
            const descEl = container.querySelector('.agent-desc');
            if (nameEl) nameEl.textContent = meta.label || meta.id;
            if (descEl && meta.description) descEl.textContent = meta.description;
        }

        checkbox.addEventListener('change', (e) => {
            if (e.target.checked) {
                if (!selectedAgents.includes(e.target.value)) {
                    selectedAgents.push(e.target.value);
                }
            } else {
                selectedAgents = selectedAgents.filter(agent => agent !== e.target.value);
            }
            updateDisplay();
        });
    });

    console.log('Initial agents:', selectedAgents);
}

function initializeDateSelector() {
    allDates = dataLoader.getAllDates();
    const dateSelector = document.getElementById('dateSelector');
    
    dateSelector.innerHTML = '<option value="">Select a date...</option>';
    
    allDates.forEach(date => {
        const option = document.createElement('option');
        option.value = date;
        option.textContent = date;
        dateSelector.appendChild(option);
    });
    
    console.log('Available dates:', allDates.length);
}

function bindEvents() {
    const toggleLogBtn = document.getElementById('toggle-log');
    if (toggleLogBtn) {
        toggleLogBtn.addEventListener('click', () => {
            if (!chartManager) return;
            const isLog = chartManager.toggleLogScale();
            toggleLogBtn.textContent = isLog ? 'Linear Scale' : 'Log Scale';
        });
    }
    
    const exportBtn = document.getElementById('export-chart');
    if (exportBtn) {
        exportBtn.addEventListener('click', () => {
            if (!chartManager) return;
            chartManager.exportData();
        });
    }

    const downloadBtn = document.getElementById('download-chart');
    if (downloadBtn) {
        downloadBtn.addEventListener('click', () => {
            if (!chartManager) return;
            chartManager.exportImage();
        });
    }
    
    const loadStepsBtn = document.getElementById('loadStepsBtn');
    if (loadStepsBtn) {
        loadStepsBtn.addEventListener('click', () => {
            loadSteps();
        });
    }
}

function updateDisplay() {
    console.log('Update display, selected agents:', selectedAgents);
    
    if (selectedAgents.length === 0) {
        if (chartManager) chartManager.clear();
        updateStatistics({});
        updateComparisonTable([]);
        return;
    }
    
    const curves = dataLoader.getAssetCurveData(selectedAgents);
    console.log('Loaded curve data:', Object.keys(curves));
    const qqqCurve = dataLoader.getQQQCurve ? (typeof dataLoader.getQQQCurve === 'function' ? dataLoader.getQQQCurve() : null) : null;

    if (chartManager && Object.keys(curves).length > 0) {
        chartManager.updateData(curves, selectedAgents, qqqCurve, colorOverrides, labelMap);
    } else {
        console.warn('Chart manager not initialized or no curve data');
    }
    
    const stats = dataLoader.getStatistics(selectedAgents);
    updateStatistics(stats);
    updateComparisonTable(selectedAgents);
    updateTableHeaders(selectedAgents);
}

/**
 * Get display name for agent (matches chart legend)
 */
function getAgentDisplayName(agentName) {
    return labelMap[agentName] || agentName;
}

function updateStatistics(stats) {
    if (!stats || Object.keys(stats).length === 0) {
        document.getElementById('total-assets').textContent = '-';
        document.getElementById('total-return').textContent = '-';
        document.getElementById('trade-count').textContent = '-';
        document.getElementById('best-agent').textContent = '-';
        return;
    }
    
    const totalAssets = Object.values(stats.totalAssets || {}).reduce((sum, val) => sum + parseFloat(val || 0), 0);
    const avgReturn = Object.values(stats.returns || {}).reduce((sum, val) => sum + parseFloat(val || 0), 0) / (Object.keys(stats.returns || {}).length || 1);
    const totalTrades = Object.values(stats.tradeCounts || {}).reduce((sum, val) => sum + (val || 0), 0);
    
    document.getElementById('total-assets').textContent = '$' + totalAssets.toFixed(2);
    document.getElementById('total-return').textContent = avgReturn.toFixed(2) + '%';
    document.getElementById('trade-count').textContent = totalTrades;
    // Use friendly name for best agent display
    document.getElementById('best-agent').textContent = stats.bestAgent ? getAgentDisplayName(stats.bestAgent) : '-';
}

function updateComparisonTable(agentNames) {
    const tbody = document.getElementById('comparisonTableBody');
    tbody.innerHTML = '';
    
    if (agentNames.length === 0) return;
    
    const dates = dataLoader.getAllDates();
    
    dates.forEach(date => {
        const row = document.createElement('tr');
        
        const dateCell = document.createElement('td');
        dateCell.textContent = date.split(' ')[0];
        row.appendChild(dateCell);
        
        agentNames.forEach(agentName => {
            const agentData = dataLoader.getAgentData(agentName);
            const cell = document.createElement('td');
            
            if (agentData) {
                const position = agentData.positions[date];
                if (position && position.positions) {
                    const cash = position.positions.CASH || 0;
                    const stockCount = Object.entries(position.positions)
                        .filter(([key, value]) => key !== 'CASH' && value > 0)
                        .length;
                    
                    cell.innerHTML = `
                        <div>Cash: $${cash.toFixed(2)}</div>
                        <div style="font-size: 0.85rem; color: #718096;">Positions: ${stockCount}</div>
                    `;
                } else {
                    cell.textContent = '-';
                }
            } else {
                cell.textContent = '-';
            }
            
            row.appendChild(cell);
        });
        
        tbody.appendChild(row);
    });
}

function updateTableHeaders(agentNames) {
    const headers = ['col-agent1', 'col-agent2', 'col-agent3'];
    headers.forEach((headerId, index) => {
        const header = document.getElementById(headerId);
        if (header) {
            if (index < agentNames.length) {
                header.textContent = getAgentDisplayName(agentNames[index]);
                header.style.display = '';
            } else {
                header.style.display = 'none';
            }
        }
    });
}

function loadSteps() {
    const dateSelector = document.getElementById('dateSelector');
    const selectedDate = dateSelector.value;
    
    if (!selectedDate) {
        alert('Please select a date first.');
        return;
    }
    
    if (selectedAgents.length === 0) {
        alert('Please select at least one agent.');
        return;
    }
    
    const stepsSection = document.getElementById('stepsSection');
    const stepsContainer = document.getElementById('stepsContainer');
    
    stepsSection.style.display = 'block';
    stepsContainer.innerHTML = '';
    
    selectedAgents.forEach(agentName => {
        const agentData = dataLoader.getAgentData(agentName);
        if (!agentData) return;
        
        const logs = agentData.logs[selectedDate] || [];
        if (logs.length === 0) return;
        
        const agentStepsDiv = document.createElement('div');
        agentStepsDiv.className = 'agent-steps';
        
        const header = document.createElement('div');
        header.className = 'agent-steps-header';
        header.innerHTML = `<h4>${agentName}</h4><span>${logs.length} entries</span>`;
        agentStepsDiv.appendChild(header);
        
        logs.forEach((log, index) => {
            const stepDiv = document.createElement('div');
            stepDiv.className = 'step-item';
            
            if (log.new_messages && Array.isArray(log.new_messages)) {
                log.new_messages.forEach(msg => {
                    const stepHeader = document.createElement('div');
                    stepHeader.className = 'step-header';
                    stepHeader.innerHTML = `
                        <span class="step-role">${msg.role || 'unknown'}</span>
                        <span style="font-size: 0.85rem; color: #718096;">Step ${index + 1}</span>
                    `;
                    stepDiv.appendChild(stepHeader);
                    
                    const stepContent = document.createElement('div');
                    stepContent.className = 'step-content';
                    let content = msg.content || '';
                    if (content.length > 500) {
                        content = content.substring(0, 500) + '...';
                    }
                    stepContent.textContent = content;
                    stepDiv.appendChild(stepContent);
                });
            }
            
            agentStepsDiv.appendChild(stepDiv);
        });
        
        stepsContainer.appendChild(agentStepsDiv);
    });
    
    stepsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function showLoading() {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) {
        overlay.classList.remove('hidden');
    }
}

function hideLoading() {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) {
        overlay.classList.add('hidden');
    }
}
