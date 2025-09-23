// 树莓派衰减器控制系统前端JavaScript

// 全局变量
let connectedDevices = [];
let availablePorts = [];
let currentFrequency = 1000;
let systemStatus = 'disconnected';
let currentMinAttenuation = 0; // 当前频率下的最小衰减值

// DOM元素
const elements = {
    // 按钮
    scanPortsBtn: document.getElementById('scan-ports-btn'),
    connectBtn: document.getElementById('connect-btn'),
    disconnectBtn: document.getElementById('disconnect-btn'),
    setFrequencyBtn: document.getElementById('set-frequency-btn'),
    getFrequencyBtn: document.getElementById('get-frequency-btn'),
    setAttenuationBtn: document.getElementById('set-attenuation-btn'),
    getAttenuationBtn: document.getElementById('get-attenuation-btn'),
    clearLogBtn: document.getElementById('clear-log-btn'),
    
    // 输入框
    frequencyInput: document.getElementById('frequency-input'),
    attenuationInput: document.getElementById('attenuation-input'),
    
    // 显示区域
    availablePorts: document.getElementById('available-ports'),
    connectedDevices: document.getElementById('connected-devices'),
    currentFrequency: document.getElementById('current-frequency'),
    currentMinAttenuation: document.getElementById('current-min-attenuation'),
    deviceStatusTable: document.getElementById('device-status-table'),
    logContainer: document.getElementById('log-container'),
    systemStatus: document.getElementById('system-status'),
    
    // 模态框
    loadingOverlay: document.getElementById('loading-overlay'),
    messageModal: new bootstrap.Modal(document.getElementById('messageModal'))
};

// 初始化
document.addEventListener('DOMContentLoaded', function() {
    initializeEventListeners();
    loadSystemStatus();
    addLog('系统初始化完成', 'info');
    
    // 初始化时立即更新最小衰减值
    setTimeout(async () => {
        await updateMinAttenuation();
    }, 1000); // 延迟1秒确保系统状态加载完成
    
    // 初始化单设备控制功能
    loadDeviceList();
    
    // 绑定单设备控制事件
    const deviceSelect = document.getElementById('device-select');
    const setSingleBtn = document.getElementById('set-single-attenuation-btn');
    const getSingleBtn = document.getElementById('get-single-attenuation-btn');
    
    if (deviceSelect) deviceSelect.addEventListener('change', onDeviceSelectionChange);
    if (setSingleBtn) setSingleBtn.addEventListener('click', setSingleAttenuation);
    if (getSingleBtn) getSingleBtn.addEventListener('click', getSingleAttenuation);
});

// 初始化事件监听器
function initializeEventListeners() {
    // 设备连接
    elements.scanPortsBtn.addEventListener('click', scanPorts);
    elements.connectBtn.addEventListener('click', connectDevices);
    elements.disconnectBtn.addEventListener('click', disconnectDevices);
    
    // 频率控制
    elements.setFrequencyBtn.addEventListener('click', setFrequency);
    elements.getFrequencyBtn.addEventListener('click', getFrequency);
    
    // 衰减控制
    elements.setAttenuationBtn.addEventListener('click', setAttenuation);
    elements.getAttenuationBtn.addEventListener('click', getAttenuation);
    
    // 快速设置按钮
    document.querySelectorAll('.quick-set').forEach(btn => {
        btn.addEventListener('click', async function() {
            const value = parseFloat(this.dataset.value);
            
            // 先更新最小衰减值
            await updateMinAttenuation();
            
            // 检查快速设置值是否符合最小值要求
            if (value < currentMinAttenuation) {
                showMessage('输入错误', `快速设置值${value}dB小于当前频率的最小衰减值${currentMinAttenuation}dB`, 'warning');
                elements.attenuationInput.value = currentMinAttenuation;
            } else {
                elements.attenuationInput.value = value;
            }
            
            setAttenuation();
        });
    });
    
    // 清空日志
    elements.clearLogBtn.addEventListener('click', clearLog);
    
    // 输入验证
    elements.frequencyInput.addEventListener('input', validateFrequencyInput);
    elements.attenuationInput.addEventListener('input', validateAttenuationInput);
}

// API请求封装
async function apiRequest(url, options = {}) {
    showLoading(true);
    
    try {
        const response = await fetch(url, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            // 对于400错误，直接抛出详细的错误信息
            if (response.status === 400 && data.detail) {
                throw new Error(data.detail);
            }
            throw new Error(data.message || data.detail || `HTTP ${response.status}`);
        }
        
        return data;
        
    } catch (error) {
        console.error('API请求失败:', error);
        // 不在这里显示错误消息，让调用方处理
        throw error;
    } finally {
        showLoading(false);
    }
}

// 扫描串口
async function scanPorts() {
    try {
        addLog('正在扫描串口设备...', 'info');
        
        const response = await apiRequest('/api/scan_ports');
        
        if (response.success) {
            availablePorts = response.data.ports;
            updatePortsDisplay();
            addLog(`发现 ${availablePorts.length} 个串口设备`, 'success');
        } else {
            addLog('扫描串口失败: ' + response.message, 'error');
        }
        
    } catch (error) {
        addLog('扫描串口异常: ' + error.message, 'error');
    }
}

// 更新端口显示
function updatePortsDisplay() {
    if (availablePorts.length === 0) {
        elements.availablePorts.innerHTML = '<small class="text-muted">未发现可用串口</small>';
        return;
    }
    
    const portsHtml = availablePorts.map(port => 
        `<div class="port-item" data-port="${port}" onclick="togglePortSelection(this)">
            ${port}
        </div>`
    ).join('');
    
    elements.availablePorts.innerHTML = portsHtml;
}

// 切换端口选择
function togglePortSelection(element) {
    element.classList.toggle('selected');
}

// 连接设备
async function connectDevices() {
    try {
        const selectedPorts = Array.from(document.querySelectorAll('.port-item.selected'))
            .map(el => el.dataset.port);
        
        if (selectedPorts.length === 0) {
            showMessage('提示', '请先选择要连接的串口', 'warning');
            return;
        }
        
        addLog(`正在连接 ${selectedPorts.length} 个设备...`, 'info');
        
        const response = await apiRequest('/api/connect', {
            method: 'POST',
            body: JSON.stringify({ ports: selectedPorts })
        });
        
        if (response.success) {
            addLog(response.message, 'success');
            await loadDeviceStatus();
            await loadDeviceList(); // 刷新单设备控制区域的设备列表
            updateSystemStatus('connected');
        } else {
            addLog('连接失败: ' + response.message, 'error');
        }
        
    } catch (error) {
        addLog('连接异常: ' + error.message, 'error');
    }
}

// 断开设备
async function disconnectDevices() {
    try {
        addLog('正在断开所有设备连接...', 'info');
        
        const response = await apiRequest('/api/disconnect', {
            method: 'POST'
        });
        
        if (response.success) {
            addLog(response.message, 'success');
            connectedDevices = [];
            updateDevicesDisplay();
            updateDeviceStatusTable();
            await loadDeviceList(); // 清空单设备控制区域的设备列表
            updateSystemStatus('disconnected');
        } else {
            addLog('断开连接失败: ' + response.message, 'error');
        }
        
    } catch (error) {
        addLog('断开连接异常: ' + error.message, 'error');
    }
}

// 设置频率
async function setFrequency() {
    try {
        const frequency = parseFloat(elements.frequencyInput.value);
        
        if (!validateFrequency(frequency)) {
            return;
        }
        
        addLog(`正在设置频率为 ${frequency} MHz...`, 'info');
        
        const response = await apiRequest('/api/set_frequency', {
            method: 'POST',
            body: JSON.stringify({ frequency: frequency })
        });
        
        if (response.success) {
            currentFrequency = frequency;
            elements.currentFrequency.textContent = `${frequency} MHz`;
            addLog(`频率设置成功: ${frequency} MHz`, 'success');
            // 频率改变后更新最小衰减值
            await updateMinAttenuation();
        } else {
            addLog('设置频率失败: ' + response.message, 'error');
        }
        
    } catch (error) {
        addLog('设置频率异常: ' + error.message, 'error');
    }
}

// 获取频率
async function getFrequency() {
    try {
        addLog('正在获取当前频率...', 'info');
        
        const response = await apiRequest('/api/get_frequency');
        
        if (response.success) {
            currentFrequency = response.data.frequency;
            elements.frequencyInput.value = currentFrequency;
            elements.currentFrequency.textContent = `${currentFrequency} MHz`;
            addLog(`当前频率: ${currentFrequency} MHz`, 'info');
            // 频率改变后更新最小衰减值
            await updateMinAttenuation();
        } else {
            addLog('获取频率失败: ' + response.message, 'error');
        }
        
    } catch (error) {
        addLog('获取频率异常: ' + error.message, 'error');
    }
}

// 设置衰减值
async function setAttenuation() {
    try {
        const attenuation = parseFloat(elements.attenuationInput.value);
        
        if (connectedDevices.length === 0) {
            showMessage('提示', '请先连接设备', 'warning');
            return;
        }
        
        // 先更新最小衰减值，确保验证使用最新的值
        await updateMinAttenuation();
        
        if (!validateAttenuation(attenuation)) {
            return;
        }
        
        addLog(`正在设置衰减值为 ${attenuation} dB...`, 'info');
        
        const response = await apiRequest('/api/set_attenuation', {
            method: 'POST',
            body: JSON.stringify({ value: attenuation })
        });
        
        if (response.success) {
            addLog(response.message, 'success');
            await loadDeviceStatus(); // 刷新设备状态
        } else {
            addLog('设置衰减值失败: ' + response.message, 'error');
        }
        
    } catch (error) {
        // 处理验证错误
        if (error.message.includes('衰减值必须在')) {
            // 先更新最小衰减值，然后显示正确的错误信息
            await updateMinAttenuation();
            showMessage('输入错误', error.message, 'error');
            addLog('设置衰减值失败: ' + error.message, 'error');
        } else {
            addLog('设置衰减值异常: ' + error.message, 'error');
            showMessage('错误', '设置衰减值失败: ' + error.message, 'error');
        }
    }
}

// 获取衰减值
async function getAttenuation() {
    try {
        if (connectedDevices.length === 0) {
            showMessage('提示', '请先连接设备', 'warning');
            return;
        }
        
        addLog('正在获取当前衰减值...', 'info');
        
        const response = await apiRequest('/api/get_attenuation');
        
        if (response.success) {
            const attenuations = response.data.attenuations;
            let logMessage = '当前衰减值: ';
            
            for (const [deviceId, value] of Object.entries(attenuations)) {
                logMessage += `${deviceId}=${value}dB `;
            }
            
            addLog(logMessage, 'info');
            await loadDeviceStatus(); // 刷新设备状态显示
        } else {
            addLog('获取衰减值失败: ' + response.message, 'error');
        }
        
    } catch (error) {
        addLog('获取衰减值异常: ' + error.message, 'error');
    }
}

// 更新最小衰减值
async function updateMinAttenuation() {
    try {
        // 不显示加载遮罩，避免频繁弹出
        const response = await fetch('/api/get_attenuation_range', {
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        
        if (data.success) {
            currentMinAttenuation = data.data.min_attenuation;
            
            // 更新输入框的最小值属性
            elements.attenuationInput.min = currentMinAttenuation;
            
            // 更新界面显示的范围提示
            updateAttenuationRangeDisplay(data.data);
            
            // 重新验证当前输入值
            validateAttenuationInput();
            
            addLog(`最小衰减值已更新: ${currentMinAttenuation}dB (频率: ${currentFrequency}MHz)`, 'info');
        }
        
    } catch (error) {
        console.error('更新最小衰减值失败:', error);
    }
}

// 更新衰减值范围显示
function updateAttenuationRangeDisplay(rangeData) {
    // 更新输入框下方的提示文字
    const formText = document.querySelector('#attenuation-input').parentNode.nextElementSibling;
    if (formText && formText.classList.contains('form-text')) {
        formText.textContent = `范围: ${rangeData.range_text}`;
        formText.style.color = '#dc3545'; // 红色突出显示
        formText.style.fontWeight = 'bold';
    }
    
    // 更新频率信息区域的最小衰减值显示
    if (elements.currentMinAttenuation) {
        elements.currentMinAttenuation.textContent = `${rangeData.min_attenuation}dB`;
    }
    
    // 更新警告信息中的补偿说明
    const alertText = document.querySelector('.alert-warning small');
    if (alertText) {
        alertText.innerHTML = `
            <i class="bi bi-info-circle"></i>
            <strong>注意:</strong> 系统会根据当前频率自动进行插入损耗补偿<br>
            <strong>当前频率 ${rangeData.frequency}MHz 的最小衰减值: ${rangeData.min_attenuation}dB</strong>
        `;
    }
    
    // 如果当前输入值小于最小值，自动调整
    const currentValue = parseFloat(elements.attenuationInput.value);
    if (currentValue < rangeData.min_attenuation) {
        elements.attenuationInput.value = rangeData.min_attenuation;
        addLog(`输入值已自动调整为最小值: ${rangeData.min_attenuation}dB`, 'warning');
    }
}

// 加载系统状态
async function loadSystemStatus() {
    try {
        const response = await apiRequest('/api/status');
        
        if (response.success) {
            const data = response.data;
            
            if (data.connected_devices > 0) {
                updateSystemStatus('connected');
                await loadDeviceStatus();
            } else {
                updateSystemStatus('disconnected');
            }
            
            currentFrequency = data.current_frequency;
            elements.frequencyInput.value = currentFrequency;
            elements.currentFrequency.textContent = `${currentFrequency} MHz`;
            
            availablePorts = data.available_ports || [];
            updatePortsDisplay();
            
            // 初始化时更新最小衰减值
            await updateMinAttenuation();
        }
        
    } catch (error) {
        console.error('加载系统状态失败:', error);
    }
}

// 加载设备状态
async function loadDeviceStatus() {
    try {
        const response = await apiRequest('/api/devices');
        
        if (response.success) {
            connectedDevices = response.data.devices;
            updateDevicesDisplay();
            updateDeviceStatusTable();
        }
        
    } catch (error) {
        console.error('加载设备状态失败:', error);
    }
}

// 更新设备显示
function updateDevicesDisplay() {
    if (connectedDevices.length === 0) {
        elements.connectedDevices.innerHTML = '<small class="text-muted">暂无连接的设备</small>';
        return;
    }
    
    const devicesHtml = connectedDevices.map(device => 
        `<div class="device-item">
            <div class="device-info">
                <div class="device-name">${device.device_id}</div>
                <div class="device-port">${device.port}</div>
            </div>
            <div class="device-status">
                <span class="status-indicator ${device.connected ? 'status-connected' : 'status-disconnected'}"></span>
                <small>${device.connected ? '已连接' : '未连接'}</small>
            </div>
        </div>`
    ).join('');
    
    elements.connectedDevices.innerHTML = devicesHtml;
}

// 更新设备状态表格
function updateDeviceStatusTable() {
    if (connectedDevices.length === 0) {
        elements.deviceStatusTable.innerHTML = `
            <div class="text-center text-muted py-4">
                <i class="bi bi-inbox display-4"></i>
                <p class="mt-2">暂无连接的设备</p>
            </div>`;
        return;
    }
    
    const tableHtml = `
        <table class="table table-hover device-table">
            <thead>
                <tr>
                    <th>设备ID</th>
                    <th>串口</th>
                    <th>状态</th>
                    <th>当前衰减值</th>
                </tr>
            </thead>
            <tbody>
                ${connectedDevices.map(device => `
                    <tr>
                        <td><strong>${device.device_id}</strong></td>
                        <td><code>${device.port}</code></td>
                        <td>
                            <span class="status-indicator ${device.connected ? 'status-connected' : 'status-disconnected'}"></span>
                            ${device.connected ? '已连接' : '未连接'}
                        </td>
                        <td>
                            ${device.current_attenuation !== null ? 
                                `<strong>${device.current_attenuation} dB</strong>` : 
                                '<span class="text-muted">未知</span>'}
                        </td>
                    </tr>
                `).join('')}
            </tbody>
        </table>`;
    
    elements.deviceStatusTable.innerHTML = tableHtml;
}

// 更新系统状态
function updateSystemStatus(status) {
    systemStatus = status;
    
    const statusConfig = {
        'connected': { text: '已连接', class: 'bg-success' },
        'disconnected': { text: '未连接', class: 'bg-secondary' },
        'connecting': { text: '连接中', class: 'bg-warning' },
        'error': { text: '错误', class: 'bg-danger' }
    };
    
    const config = statusConfig[status] || statusConfig['disconnected'];
    
    elements.systemStatus.textContent = config.text;
    elements.systemStatus.className = `badge ${config.class}`;
}

// 输入验证
function validateFrequency(frequency) {
    if (isNaN(frequency) || frequency < 1 || frequency > 8000) {
        showMessage('输入错误', '频率必须在1-8000MHz范围内', 'error');
        return false;
    }
    return true;
}

function validateAttenuation(attenuation) {
    if (isNaN(attenuation) || attenuation < currentMinAttenuation || attenuation > 90) {
        showMessage('输入错误', `衰减值必须在${currentMinAttenuation}-90dB范围内（当前频率${currentFrequency}MHz）`, 'error');
        return false;
    }
    return true;
}

function validateFrequencyInput() {
    const value = parseFloat(elements.frequencyInput.value);
    const isValid = !isNaN(value) && value >= 1 && value <= 10000;
    
    elements.frequencyInput.classList.toggle('is-invalid', !isValid);
    elements.frequencyInput.classList.toggle('is-valid', isValid);
}

function validateAttenuationInput() {
    const value = parseFloat(elements.attenuationInput.value);
    const isValid = !isNaN(value) && value >= currentMinAttenuation && value <= 90;
    
    elements.attenuationInput.classList.toggle('is-invalid', !isValid);
    elements.attenuationInput.classList.toggle('is-valid', isValid);
}

// 日志管理
function addLog(message, type = 'info') {
    const timestamp = new Date().toLocaleTimeString();
    const logEntry = document.createElement('div');
    logEntry.className = `log-entry log-${type} fade-in`;
    logEntry.innerHTML = `
        <span class="log-time">[${timestamp}]</span>
        <span class="log-message">${message}</span>
    `;
    
    elements.logContainer.appendChild(logEntry);
    elements.logContainer.scrollTop = elements.logContainer.scrollHeight;
    
    // 限制日志条数
    const logEntries = elements.logContainer.querySelectorAll('.log-entry');
    if (logEntries.length > 100) {
        logEntries[0].remove();
    }
}

function clearLog() {
    elements.logContainer.innerHTML = '';
    addLog('日志已清空', 'info');
}

// UI辅助函数
function showLoading(show) {
    elements.loadingOverlay.style.display = show ? 'flex' : 'none';
}

function showMessage(title, message, type = 'info') {
    const modal = document.getElementById('messageModal');
    const titleEl = document.getElementById('messageModalTitle');
    const bodyEl = document.getElementById('messageModalBody');
    
    titleEl.textContent = title;
    bodyEl.textContent = message;
    
    // 根据类型设置样式
    const typeClasses = {
        'success': 'text-success',
        'error': 'text-danger',
        'warning': 'text-warning',
        'info': 'text-info'
    };
    
    bodyEl.className = typeClasses[type] || '';
    
    elements.messageModal.show();
}

// 单设备控制相关函数
async function loadDeviceList() {
    try {
        const response = await fetch('/api/devices/ids');
        const data = await response.json();
        
        const deviceSelect = document.getElementById('device-select');
        deviceSelect.innerHTML = '<option value="">请选择设备</option>';
        
        if (data.data && data.data.device_ids && data.data.device_ids.length > 0) {
            data.data.device_ids.forEach(deviceId => {
                const option = document.createElement('option');
                option.value = deviceId;
                option.textContent = `设备 ${deviceId}`;
                deviceSelect.appendChild(option);
            });
        }
    } catch (error) {
        console.error('获取设备列表失败:', error);
        showMessage('错误', '获取设备列表失败', 'error');
    }
}

async function setSingleAttenuation() {
    const deviceSelect = document.getElementById('device-select');
    const attenuationInput = document.getElementById('single-attenuation-input');
    
    const deviceId = deviceSelect.value;
    const attenuation = parseFloat(attenuationInput.value);
    
    if (!deviceId) {
        showMessage('提示', '请先选择设备', 'warning');
        return;
    }
    
    if (isNaN(attenuation) || attenuation < 0 || attenuation > 90) {
        showMessage('输入错误', '请输入有效的衰减值 (0-90 dB)', 'error');
        return;
    }
    
    try {
        const response = await fetch('/api/attenuators/set', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                device_id: deviceId,
                value: attenuation
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showMessage('成功', `设备 ${deviceId} 衰减值已设置为 ${attenuation} dB`, 'success');
            updateSingleDeviceInfo(deviceId, attenuation);
        } else {
            showMessage('错误', data.detail || '设置失败', 'error');
        }
    } catch (error) {
        console.error('设置单设备衰减值失败:', error);
        showMessage('错误', '设置单设备衰减值失败', 'error');
    }
}

async function getSingleAttenuation() {
    const deviceSelect = document.getElementById('device-select');
    const deviceId = deviceSelect.value;
    
    if (!deviceId) {
        showMessage('提示', '请先选择设备', 'warning');
        return;
    }
    
    try {
        const response = await fetch(`/api/attenuators/${deviceId}`);
        const data = await response.json();
        
        if (response.ok) {
            const attenuationInput = document.getElementById('single-attenuation-input');
            attenuationInput.value = data.data.current_attenuation;
            updateSingleDeviceInfo(deviceId, data.data.current_attenuation);
            showMessage('成功', `设备 ${deviceId} 当前衰减值: ${data.data.current_attenuation} dB`, 'success');
        } else {
            showMessage('错误', data.detail || '读取失败', 'error');
        }
    } catch (error) {
        console.error('读取单设备衰减值失败:', error);
        showMessage('错误', '读取单设备衰减值失败', 'error');
    }
}

function updateSingleDeviceInfo(deviceId, attenuation) {
    const deviceInfo = document.getElementById('single-device-info');
    deviceInfo.textContent = `设备 ${deviceId} - 当前衰减值: ${attenuation} dB`;
}

// 设备选择变化时的处理
function onDeviceSelectionChange() {
    const deviceSelect = document.getElementById('device-select');
    const deviceId = deviceSelect.value;
    
    if (deviceId) {
        // 自动读取选中设备的当前衰减值
        getSingleAttenuation();
    } else {
        const deviceInfo = document.getElementById('single-device-info');
        deviceInfo.textContent = '请先选择设备';
        document.getElementById('single-attenuation-input').value = '0';
    }
}

// 定期刷新状态
setInterval(async () => {
    if (systemStatus === 'connected') {
        try {
            await loadDeviceStatus();
            await loadDeviceList(); // 定时更新设备列表
        } catch (error) {
            console.error('定期刷新状态失败:', error);
        }
    }
}, 120000); // 每2分钟刷新一次

// 页面可见性变化时刷新状态
document.addEventListener('visibilitychange', () => {
    if (!document.hidden && systemStatus === 'connected') {
        loadDeviceStatus();
        loadDeviceList();
    }
});