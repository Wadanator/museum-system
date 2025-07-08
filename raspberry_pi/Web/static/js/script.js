const socket = io();
let currentScene = '';
let autoScroll = true;
let activeFilters = new Set(['debug', 'info', 'warning', 'error', 'critical']);
let logCounts = {
    debug: 0,
    info: 0,
    warning: 0,
    error: 0,
    critical: 0
};

// Socket event handlers
socket.on('connect', function() {
    console.log('Connected to server');
    updateStatus();
    loadScenes();
    loadStats();
});

socket.on('new_log', function(logEntry) {
    addLogEntry(logEntry);
});

socket.on('log_history', function(logs) {
    const logContainer = document.getElementById('logContainer');
    logContainer.innerHTML = '';
    logCounts = { debug: 0, info: 0, warning: 0, error: 0, critical: 0 };
    logs.forEach(log => addLogEntry(log));
    updateLogStats();
});

socket.on('logs_cleared', function() {
    const logContainer = document.getElementById('logContainer');
    logContainer.innerHTML = '';
    logCounts = { debug: 0, info: 0, warning: 0, error: 0, critical: 0 };
    updateLogStats();
});

socket.on('stats_update', function(stats) {
    updateStats(stats);
});

// Tab switching
function showTab(tabName) {
    document.querySelectorAll('.tab').forEach(tab => tab.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
    
    event.target.classList.add('active');
    document.getElementById(tabName).classList.add('active');
    
    if (tabName === 'scenes') {
        loadScenes();
    } else if (tabName === 'stats') {
        loadStats();
    } else if (tabName === 'editor') {
        const sceneSelect = document.getElementById('sceneSelect');
        if (sceneSelect.value) {
            loadSceneForEditing(sceneSelect.value);
        }
    }
}

// Log level filtering
function toggleLogLevel(level) {
    const button = document.querySelector(`.filter-btn[data-level="${level}"]`);
    
    if (activeFilters.has(level)) {
        activeFilters.delete(level);
        button.classList.remove('active');
    } else {
        activeFilters.add(level);
        button.classList.add('active');
    }
    
    applyLogFilters();
}

function applyLogFilters() {
    const logEntries = document.querySelectorAll('.log-entry');
    
    logEntries.forEach(entry => {
        const level = entry.classList.contains('debug') ? 'debug' :
                     entry.classList.contains('info') ? 'info' :
                     entry.classList.contains('warning') ? 'warning' :
                     entry.classList.contains('error') ? 'error' :
                     entry.classList.contains('critical') ? 'critical' : 'info';
        
        if (activeFilters.has(level)) {
            entry.classList.remove('hidden');
        } else {
            entry.classList.add('hidden');
        }
    });
}

// Status update
function updateStatus() {
    fetch('/api/status')
        .then(response => response.json())
        .then(data => {
            document.getElementById('roomId').textContent = data.room_id;
            document.getElementById('sceneStatus').textContent = data.scene_running ? 'Running' : 'Idle';
            document.getElementById('sceneStatus').className = data.scene_running ? 'status-value pulse' : 'status-value';
            
            const mqttStatus = document.getElementById('mqttStatus');
            mqttStatus.textContent = data.mqtt_connected ? 'Connected' : 'Disconnected';
            mqttStatus.className = data.mqtt_connected ? 'status-value status-connected' : 'status-value status-disconnected';
            
            const uptime = Math.floor(data.uptime);
            const hours = Math.floor(uptime / 3600);
            const minutes = Math.floor((uptime % 3600) / 60);
            const seconds = uptime % 60;
            document.getElementById('uptime').textContent = `${hours}h ${minutes}m ${seconds}s`;
        });
}

// Statistics update
function updateStats(stats) {
    document.getElementById('totalScenesPlayed').textContent = stats.total_scenes_played || 0;
    
    const totalUptime = stats.total_uptime || 0;
    const hours = Math.floor(totalUptime / 3600);
    const minutes = Math.floor((totalUptime % 3600) / 60);
    const seconds = Math.floor(totalUptime % 60);
    document.getElementById('totalUptime').textContent = `${hours}h ${minutes}m ${seconds}s`;
    
    const sceneStatsList = document.getElementById('sceneStatsList');
    sceneStatsList.innerHTML = '';
    
    if (stats.scene_play_counts && Object.keys(stats.scene_play_counts).length > 0) {
        Object.entries(stats.scene_play_counts).forEach(([sceneName, count]) => {
            const statDiv = document.createElement('div');
            statDiv.className = 'scene-item';
            statDiv.innerHTML = `
                <div class="scene-info">
                    <h4>${sceneName}</h4>
                    <p>Played: ${count} times</p>
                </div>
            `;
            sceneStatsList.appendChild(statDiv);
        });
    } else {
        sceneStatsList.innerHTML = `
            <div class="scene-item">
                <div class="scene-info">
                    <h4>No statistics available</h4>
                    <p>No scenes have been played yet</p>
                </div>
            </div>
        `;
    }
}

function loadStats() {
    fetch('/api/stats')
        .then(response => response.json())
        .then(data => updateStats(data));
}

// Log handling
function addLogEntry(logEntry) {
    const logContainer = document.getElementById('logContainer');
    const logDiv = document.createElement('div');
    const level = logEntry.level.toLowerCase();
    
    logDiv.className = `log-entry ${level}`;
    
    if (logCounts.hasOwnProperty(level)) {
        logCounts[level]++;
    }
    
    if (!activeFilters.has(level)) {
        logDiv.classList.add('hidden');
    }
    
    logDiv.innerHTML = `
        <span class="log-timestamp">${logEntry.timestamp}</span>
        <span class="log-level ${level}">${logEntry.level}</span>
        <span class="log-module">${logEntry.module || 'system'}</span>
        <span>${logEntry.message}</span>
    `;
    
    logContainer.appendChild(logDiv);
    
    if (autoScroll) {
        logContainer.scrollTop = logContainer.scrollHeight;
    }
    
    while (logContainer.children.length > 500) {
        const firstChild = logContainer.firstChild;
        const firstLevel = firstChild.classList.contains('debug') ? 'debug' :
                          firstChild.classList.contains('info') ? 'info' :
                          firstChild.classList.contains('warning') ? 'warning' :
                          firstChild.classList.contains('error') ? 'error' :
                          firstChild.classList.contains('critical') ? 'critical' : 'info';
        if (logCounts.hasOwnProperty(firstLevel)) {
            logCounts[firstLevel]--;
        }
        logContainer.removeChild(firstChild);
    }
    
    updateLogStats();
}

function updateLogStats() {
    document.getElementById('debugCount').textContent = logCounts.debug;
    document.getElementById('infoCount').textContent = logCounts.info;
    document.getElementById('warningCount').textContent = logCounts.warning;
    document.getElementById('errorCount').textContent = logCounts.error;
    document.getElementById('criticalCount').textContent = logCounts.critical;
}

function clearLogs() {
    if (confirm('Are you sure you want to clear all logs?')) {
        fetch('/api/logs/clear', { method: 'POST' })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showNotification('Logs cleared successfully', 'success');
                } else {
                    showNotification('Failed to clear logs', 'error');
                }
            });
    }
}

function exportLogs() {
    fetch('/api/logs/export')
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to export logs');
            }
            return response.blob();
        })
        .then(blob => {
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `museum_logs_${new Date().toISOString().replace(/[:.]/g, '-')}.json`;
            document.body.appendChild(a);
            a.click();
            a.remove();
            window.URL.revokeObjectURL(url);
            showNotification('Logs exported successfully', 'success');
        })
        .catch(error => {
            showNotification('Error exporting logs: ' + error.message, 'error');
        });
}

function toggleAutoScroll() {
    autoScroll = !autoScroll;
    const button = event.target;
    button.textContent = autoScroll ? '📜 Auto-scroll' : '📜 Manual';
    button.style.background = autoScroll ? '' : '#ffc107';
}

// Scene management
function loadScenes() {
    fetch('/api/scenes')
        .then(response => response.json())
        .then(scenes => {
            const sceneList = document.getElementById('sceneList');
            const sceneSelect = document.getElementById('sceneSelect');
            
            sceneList.innerHTML = '';
            sceneSelect.innerHTML = '<option value="">Select a scene to edit</option>';
            
            scenes.forEach(scene => {
                const sceneDiv = document.createElement('div');
                sceneDiv.className = 'scene-item';
                sceneDiv.innerHTML = `
                    <div class="scene-info">
                        <h4>${scene.name}</h4>
                        <p>Modified: ${new Date(scene.modified * 1000).toLocaleString()}</p>
                    </div>
                    <div class="scene-actions">
                        <button class="btn btn-primary" onclick="runScene('${scene.name}')">▶️ Run</button>
                        <button class="btn btn-secondary" onclick="editScene('${scene.name}')">✏️ Edit</button>
                    </div>
                `;
                sceneList.appendChild(sceneDiv);
                
                const option = document.createElement('option');
                option.value = scene.name;
                option.textContent = scene.name;
                sceneSelect.appendChild(option);
            });
        });
}

function runScene(sceneName) {
    fetch(`/api/run_scene/${sceneName}`, { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showNotification(data.message, 'success');
                updateStatus();
                loadStats();
            } else {
                showNotification(data.error, 'error');
            }
        });
}

function editScene(sceneName) {
    showTab('editor');
    document.getElementById('sceneSelect').value = sceneName;
    loadSceneForEditing(sceneName);
}

function loadSceneForEditing(sceneName) {
    fetch(`/api/scene/${sceneName}`)
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                showNotification(data.error, 'error');
                document.getElementById('sceneEditor').value = '';
                currentScene = '';
            } else {
                document.getElementById('sceneEditor').value = JSON.stringify(data, null, 2);
                currentScene = sceneName;
            }
        });
}

function saveScene() {
    const sceneName = document.getElementById('sceneSelect').value || currentScene;
    if (!sceneName) {
        showNotification('Please select or name a scene', 'error');
        return;
    }

    try {
        const sceneData = JSON.parse(document.getElementById('sceneEditor').value);
        
        fetch(`/api/scene/${sceneName}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(sceneData)
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showNotification(data.message, 'success');
                loadScenes();
            } else {
                showNotification(data.error, 'error');
            }
        });
    } catch (e) {
        showNotification('Invalid JSON format', 'error');
    }
}

function createNewScene() {
    const sceneName = prompt('Enter scene name:');
    if (sceneName) {
        document.getElementById('sceneSelect').value = '';
        document.getElementById('sceneEditor').value = JSON.stringify([
            {"timestamp": 0, "topic": "room/light", "message": "ON"},
            {"timestamp": 2.0, "topic": "room/audio", "message": "PLAY_WELCOME"},
            {"timestamp": 5.0, "topic": "room/light", "message": "OFF"}
        ], null, 2);
        currentScene = sceneName;
    }
}

function validateScene() {
    try {
        const sceneData = JSON.parse(document.getElementById('sceneEditor').value);
        if (Array.isArray(sceneData)) {
            let valid = true;
            for (let action of sceneData) {
                if (!action.hasOwnProperty('timestamp') || !action.hasOwnProperty('topic') || !action.hasOwnProperty('message')) {
                    valid = false;
                    break;
                }
            }
            if (valid) {
                showNotification('Scene is valid!', 'success');
            } else {
                showNotification('Invalid scene format: missing required fields', 'error');
            }
        } else {
            showNotification('Scene must be an array of actions', 'error');
        }
    } catch (e) {
        showNotification('Invalid JSON format', 'error');
    }
}

function showNotification(message, type) {
    const notification = document.getElementById('notification');
    notification.textContent = message;
    notification.className = `notification ${type} show`;
    
    setTimeout(() => {
        notification.classList.remove('show');
    }, 3000);
}

function restartSystem() {
    if (confirm('Are you sure you want to perform a hard reset? This will reboot the Raspberry Pi and interrupt all operations.')) {
        fetch('/api/system/restart', { method: 'POST' })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showNotification('System is restarting...', 'success');
                    document.querySelector('button[onclick="restartSystem()"]').disabled = true;
                } else {
                    showNotification(data.error || 'Failed to initiate reset', 'error');
                }
            })
            .catch(error => {
                showNotification('Error communicating with server: ' + error.message, 'error');
            });
    }
}

function restartService() {
    if (confirm('Are you sure you want to restart the museum-system service? This will interrupt current operations.')) {
        fetch('/api/system/service/restart', { method: 'POST' })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showNotification('Service is restarting...', 'success');
                } else {
                    showNotification(data.error || 'Failed to restart service', 'error');
                }
            })
            .catch(error => {
                showNotification('Error communicating with server: ' + error.message, 'error');
            });
    }
}

document.getElementById('sceneSelect').addEventListener('change', function() {
    if (this.value) {
        loadSceneForEditing(this.value);
    } else {
        document.getElementById('sceneEditor').value = '';
        currentScene = '';
    }
});

setInterval(updateStatus, 5000);
updateStatus();