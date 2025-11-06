/**
 * 主应用逻辑
 */
let selectedAgents = [];
let allDates = [];

document.addEventListener('DOMContentLoaded', async () => {
    try {
        showLoading();
        
        if (typeof Chart === 'undefined') {
            console.error('Chart.js not loaded');
            alert('Chart.js 库加载失败，请检查网络连接');
            hideLoading();
            return;
        }
        
        initChartManager();
        
        await new Promise(resolve => setTimeout(resolve, 100));
        
        console.log('开始加载数据...');
        await dataLoader.load();
        console.log('数据加载完成');
        
        initializePage();
        
        hideLoading();
    } catch (error) {
        console.error('初始化失败:', error);
        alert('加载数据失败: ' + error.message + '\n请检查 data/agents_data.json 文件是否存在');
        hideLoading();
    }
});

function initializePage() {
    console.log('初始化页面...');
    
    initializeAgentSelector();
    initializeDateSelector();
    bindEvents();
    updateDisplay();
    
    console.log('页面初始化完成');
}

function initializeAgentSelector() {
    const checkboxes = document.querySelectorAll('.agent-checkbox input[type="checkbox"]');
    checkboxes.forEach(checkbox => {
        if (checkbox.checked) {
            selectedAgents.push(checkbox.value);
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
    
    console.log('初始选中的agents:', selectedAgents);
}

function initializeDateSelector() {
    allDates = dataLoader.getAllDates();
    const dateSelector = document.getElementById('dateSelector');
    
    dateSelector.innerHTML = '<option value="">请选择日期...</option>';
    
    allDates.forEach(date => {
        const option = document.createElement('option');
        option.value = date;
        option.textContent = date;
        dateSelector.appendChild(option);
    });
    
    console.log('可用日期数量:', allDates.length);
}

function bindEvents() {
    const toggleLogBtn = document.getElementById('toggle-log');
    if (toggleLogBtn) {
        toggleLogBtn.addEventListener('click', () => {
            if (!chartManager) return;
            const isLog = chartManager.toggleLogScale();
            toggleLogBtn.textContent = isLog ? '线性刻度' : '对数刻度';
        });
    }
    
    const exportBtn = document.getElementById('export-chart');
    if (exportBtn) {
        exportBtn.addEventListener('click', () => {
            if (!chartManager) return;
            chartManager.exportData();
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
    console.log('更新显示，选中的agents:', selectedAgents);
    
    if (selectedAgents.length === 0) {
        if (chartManager) chartManager.clear();
        updateStatistics({});
        updateComparisonTable([]);
        return;
    }
    
    const curves = dataLoader.getAssetCurveData(selectedAgents);
    console.log('获取到的曲线数据:', Object.keys(curves));
    
    if (chartManager && Object.keys(curves).length > 0) {
        chartManager.updateData(curves, selectedAgents);
    } else {
        console.warn('图表管理器未初始化或没有曲线数据');
    }
    
    const stats = dataLoader.getStatistics(selectedAgents);
    updateStatistics(stats);
    updateComparisonTable(selectedAgents);
    updateTableHeaders(selectedAgents);
}

/**
 * 获取agent的友好显示名称（与图表图例一致）
 */
function getAgentDisplayName(agentName) {
    const agentNameMap = {
        'deepseek-v3-whole-month': '基础版本 (无工具)',
        'deepseek-v3-whole-month-with-x-and-reddit': '含 X & Reddit 工具',
        'deepseek-v3-whole-month-with-x-and-reddit-1105': '含 X & Reddit 工具 (1105版)'
    };
    return agentNameMap[agentName] || agentName.split('-').slice(-2).join('-').replace(/-/g, ' ');
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
    // 使用友好名称显示最佳agent
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
                        <div>现金: $${cash.toFixed(2)}</div>
                        <div style="font-size: 0.85rem; color: #718096;">持仓: ${stockCount} 只</div>
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
                header.textContent = agentNames[index].split('-').pop();
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
        alert('请先选择日期');
        return;
    }
    
    if (selectedAgents.length === 0) {
        alert('请至少选择一个Agent');
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
        header.innerHTML = `<h4>${agentName}</h4><span>${logs.length} 条记录</span>`;
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
                        <span style="font-size: 0.85rem; color: #718096;">步骤 ${index + 1}</span>
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
