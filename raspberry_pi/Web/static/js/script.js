const socket = io();
let currentScene = '', currentCommand = '', autoScroll = true;
const activeFilters = new Set(['debug', 'info', 'warning', 'error', 'critical']);
const logCounts = { debug: 0, info: 0, warning: 0, error: 0, critical: 0 };

socket.on('connect', () => {
    console.log('Connected to server');
    updateAll();
    loadResourceList('scenes', 'sceneList', 'sceneSelect', runScene, editScene);
    loadResourceList('commands', 'commandList', 'commandSelect', runCommand, editCommand);
});

socket.on('new_log', addLogEntry);
socket.on('log_history', logs => {
    document.getElementById('logContainer').innerHTML = '';
    Object.assign(logCounts, { debug: 0, info: 0, warning: 0, error: 0, critical: 0 });
    logs.forEach(addLogEntry);
    updateLogStats();
});
socket.on('logs_cleared', () => {
    document.getElementById('logContainer').innerHTML = '';
    Object.assign(logCounts, { debug: 0, info: 0, warning: 0, error: 0, critical: 0 });
    updateLogStats();
});
socket.on('stats_update', updateStats);
socket.on('command_executed', ({ success, command, error }) => {
    showNotification(success ? `Command '${command}' executed successfully` : `Command '${command}' failed: ${error}`, success ? 'success' : 'error');
});

function showTab(tabName) {
    document.querySelectorAll('.tab, .tab-content').forEach(el => el.classList.remove('active'));
    document.querySelector(`.tab[onclick="showTab('${tabName}')"]`).classList.add('active');
    document.getElementById(tabName).classList.add('active');
    if (tabName === 'scenes') {
        loadResourceList('scenes', 'sceneList', 'sceneSelect', runScene, editScene);
        // Ensure the editor is ready if a scene is selected
        const selectedScene = document.getElementById('sceneSelect').value;
        if (selectedScene) loadSceneForEditing(selectedScene);
    } else if (tabName === 'stats') {
        loadStats();
    } else if (tabName === 'commands') {
        loadResourceList('commands', 'commandList', 'commandSelect', runCommand, editCommand);
    }
}

function toggleLogLevel(level) {
    const button = document.querySelector(`.filter-btn[data-level="${level}"]`);
    activeFilters[activeFilters.has(level) ? 'delete' : 'add'](level);
    button.classList.toggle('active');
    applyLogFilters();
}

function applyLogFilters() {
    const possibleLevels = ['debug', 'info', 'warning', 'error', 'critical'];
    document.querySelectorAll('.log-entry').forEach(entry => {
        // Najdi skutečnou úroveň logu z jeho tříd (classList)
        const level = Array.from(entry.classList).find(cls => possibleLevels.includes(cls)) || 'info';
        // Skryj, pokud úroveň není v aktivních filtrech
        entry.classList.toggle('hidden', !activeFilters.has(level));
    });
}

function updateStatus() {
    fetch('/api/status')
        .then(res => res.json())
        .then(({ room_id, scene_running, mqtt_connected, uptime }) => {
            document.getElementById('roomId').textContent = room_id;
            document.getElementById('sceneStatus').textContent = scene_running ? 'Running' : 'Idle';
            document.getElementById('sceneStatus').className = `status-value${scene_running ? ' pulse' : ''}`;
            document.getElementById('mqttStatus').textContent = mqtt_connected ? 'Connected' : 'Disconnected';
            document.getElementById('mqttStatus').className = `status-value status-${mqtt_connected ? 'connected' : 'disconnected'}`;

            const [h, m, s] = [
                Math.floor(uptime / 3600),
                Math.floor((uptime % 3600) / 60),
                Math.floor(uptime % 60)
            ];
            document.getElementById('uptime').textContent = `${h}h ${m}m ${s}s`;
        });
}

function updateStats({ total_scenes_played = 0, total_uptime = 0, scene_play_counts = {}, connected_devices = {} }) {
    document.getElementById('totalScenesPlayed').textContent = total_scenes_played;
    const [h, m, s] = [
        Math.floor(total_uptime / 3600),
        Math.floor((total_uptime % 3600) / 60),
        Math.floor(total_uptime % 60)
    ];
    document.getElementById('totalUptime').textContent = `${h}h ${m}m ${s}s`;

    const sceneStatsList = document.getElementById('sceneStatsList');
    sceneStatsList.innerHTML = Object.entries(scene_play_counts).length
        ? Object.entries(scene_play_counts).map(([name, count]) => `
            <div class="scene-item">
                <div class="scene-info">
                    <h4>${name}</h4>
                    <p>Played: ${count} times</p>
                </div>
            </div>`).join('')
        : '<div class="scene-item"><div class="scene-info"><h4>No statistics available</h4><p>No scenes have been played yet</p></div></div>';

    const deviceList = document.getElementById('deviceList');
    deviceList.innerHTML = Object.entries(connected_devices).length
        ? Object.entries(connected_devices).map(([id, { status, last_updated }]) => `
            <div class="scene-item device">
                <div class="scene-info">
                    <h4>Device: ${id}</h4>
                    <div class="device-status ${status.toLowerCase()}">${status}</div>
                    <p>Last Updated: ${new Date(last_updated * 1000).toLocaleString()}</p>
                </div>
            </div>`).join('')
        : '<div class="scene-item device"><div class="scene-info"><h4>No devices connected</h4><p>No devices are currently connected to the MQTT broker, THERE SHOULD BE!!!</p></div></div>';
}

function loadStats() {
    fetch('/api/stats').then(res => res.json()).then(updateStats);
}

function addLogEntry({ timestamp, level, module = 'system', message }) {
    const logContainer = document.getElementById('logContainer');
    level = level.toLowerCase();
    if (logCounts[level] !== undefined) logCounts[level]++;
    const logDiv = document.createElement('div');
    logDiv.className = `log-entry ${level}${activeFilters.has(level) ? '' : ' hidden'}`;
    logDiv.innerHTML = `<span class="log-timestamp">${timestamp}</span><span class="log-level ${level}">${level}</span><span class="log-module">${module}</span><span>${message}</span>`;
    logContainer.appendChild(logDiv);
    if (autoScroll) logContainer.scrollTop = logContainer.scrollHeight;
    while (logContainer.children.length > 500) {
        const firstLevel = Array.from(logContainer.firstChild.classList).find(cls => logCounts[cls]) || 'info';
        logCounts[firstLevel]--;
        logContainer.removeChild(logContainer.firstChild);
    }
    updateLogStats();
}

function updateLogStats() {
    ['debug', 'info', 'warning', 'error', 'critical'].forEach(level => {
        document.getElementById(`${level}Count`).textContent = logCounts[level];
    });
}

function clearLogs() {
    if (confirm('Are you sure you want to clear all logs?')) {
        fetch('/api/logs/clear', { method: 'POST' })
            .then(res => {
                if (!res.ok) {
                    console.error('Clear logs failed with status:', res.status);
                    throw new Error('Network response was not ok');
                }
                return res.json();
            })
            .then(({ success }) => {
                showNotification(success ? 'Logs cleared successfully' : 'Failed to clear logs', success ? 'success' : 'error');
            })
            .catch(err => {
                console.error('Error clearing logs:', err);
                showNotification('Error clearing logs: ' + err.message, 'error');
            });
    }
}

function exportLogs() {
    fetch('/api/logs/export')
        .then(res => {
            if (!res.ok) throw new Error('Failed to export logs');
            return res.blob();
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
        .catch(err => showNotification(`Error exporting logs: ${err.message}`, 'error'));
}

function toggleAutoScroll() {
    autoScroll = !autoScroll;
    event.target.textContent = autoScroll ? '📜 Auto-scroll' : '📜 Manual';
    event.target.style.background = autoScroll ? '' : '#ffc107';
}

function loadResourceList(type, listId, selectId, runFn, editFn) {
    fetch(`/api/${type}`)
        .then(res => res.json())
        .then(items => {
            const list = document.getElementById(listId);
            const select = document.getElementById(selectId);
            list.innerHTML = items.length
                ? type === 'commands'
                    ? Object.entries(items.reduce((groups, item) => {
                        const [deviceType = 'other'] = item.name.split('_');
                        (groups[deviceType] = groups[deviceType] || []).push(item);
                        return groups;
                    }, {})).sort().map(([deviceType, commands]) => `
                        <div class="command-group">
                            <h3 class="command-group-title">${deviceType.toUpperCase()} Commands</h3>
                            ${commands.map(({ name }) => `
                                <div class="command-item">
                                    <div class="command-info"><h4>${name}</h4></div>
                                    <div class="command-actions">
                                        <button class="btn btn-${type === 'commands' ? 'warning' : 'primary'}" onclick="${runFn.name}('${name}')">⚡ Execute</button>
                                        <button class="btn btn-secondary" onclick="${editFn.name}('${name}')">✏️ Edit</button>
                                    </div>
                                </div>`).join('')}
                        </div>`).join('')
                    : items.map(({ name }) => `
                        <div class="scene-item">
                            <div class="scene-info"><h4>${name}</h4></div>
                            <div class="scene-actions">
                                <button class="btn btn-primary" onclick="${runFn.name}('${name}')">▶️ Run</button>
                                <button class="btn btn-secondary" onclick="${editFn.name}('${name}')">✏️ Edit</button>
                            </div>
                        </div>`).join('')
                : `<div class="${type}-item"><div class="${type}-info"><h4>No ${type} available</h4><p>No ${type} have been loaded yet</p></div></div>`;
            select.innerHTML = `<option value="">Select a ${type.slice(0, -1)} to edit</option>` + items.map(({ name }) => `<option value="${name}">${name}</option>`).join('');
        });
}

function runScene(sceneName) {
    fetch(`/api/run_scene/${sceneName}`, { method: 'POST' })
        .then(res => res.json())
        .then(({ success, message, error }) => {
            if (success) {
                showNotification(message, 'success');
                updateAll();
            } else showNotification(error, 'error');
        });
}

function editScene(sceneName) {
    if (!document.getElementById('scenes').classList.contains('active')) showTab('scenes');
    document.getElementById('sceneSelect').value = sceneName;
    loadSceneForEditing(sceneName);
}

function loadSceneForEditing(sceneName) {
    fetch(`/api/scene/${sceneName}`)
        .then(res => res.json())
        .then(data => {
            document.getElementById('sceneEditor').value = data.error ? '' : JSON.stringify(data, null, 2);
            currentScene = data.error ? '' : sceneName;
            if (data.error) showNotification(data.error, 'error');
        });
}

function saveScene() {
    const sceneSelect = document.getElementById('sceneSelect');
    const sceneName = sceneSelect.value || currentScene;
    
    if (!sceneName) {
        showNotification('Please select or create a scene first', 'error');
        return;
    }
    
    // Ensure .json extension
    const finalSceneName = sceneName.endsWith('.json') ? sceneName : sceneName + '.json';
    
    try {
        const sceneData = JSON.parse(document.getElementById('sceneEditor').value);
        
        // Validate scene data structure
        if (!Array.isArray(sceneData)) {
            showNotification('Scene must be an array of actions', 'error');
            return;
        }
        
        // Validate each action has required fields
        for (let i = 0; i < sceneData.length; i++) {
            const action = sceneData[i];
            if (!('timestamp' in action) || !('topic' in action) || !('message' in action)) {
                showNotification(`Action ${i + 1} is missing required fields (timestamp, topic, message)`, 'error');
                return;
            }
        }
        
        fetch(`/api/scene/${finalSceneName}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(sceneData)
        })
        .then(res => res.json())
        .then(({ success, message, error }) => {
            if (success) {
                showNotification(message, 'success');
                currentScene = finalSceneName;
                
                // Update the select value to match saved name
                sceneSelect.value = finalSceneName;
                
                // Reload the scene list to show the new/updated scene
                loadResourceList('scenes', 'sceneList', 'sceneSelect', runScene, editScene);
            } else {
                showNotification(error, 'error');
            }
        })
        .catch(err => {
            showNotification(`Error saving scene: ${err.message}`, 'error');
        });
    } catch (e) {
        showNotification('Invalid JSON format. Please check your syntax.', 'error');
    }
}

function createNewScene() {
    const sceneName = prompt('Enter scene name (include .json extension):');
    if (sceneName) {
        // Clear the select to indicate new scene
        const sceneSelect = document.getElementById('sceneSelect');
        sceneSelect.value = '';
        
        // Add new option to select temporarily
        const newOption = document.createElement('option');
        newOption.value = sceneName;
        newOption.textContent = sceneName;
        newOption.selected = true;
        sceneSelect.appendChild(newOption);
        
        // Set up default scene content
        document.getElementById('sceneEditor').value = JSON.stringify([
            {"timestamp": 0, "topic": "roomX/light", "message": "ON"},
            {"timestamp": 2.0, "topic": "roomX/audio", "message": "PLAY_WELCOME"},
            {"timestamp": 5.0, "topic": "roomX/light", "message": "OFF"}
        ], null, 2);
        
        currentScene = sceneName;
        
        // Switch to scenes tab if not already active
        if (!document.getElementById('scenes').classList.contains('active')) {
            showTab('scenes');
        }
        
        showNotification(`New scene "${sceneName}" created. Edit and save to persist.`, 'info');
    }
}

function validateScene() {
    try {
        const sceneData = JSON.parse(document.getElementById('sceneEditor').value);
        
        if (!Array.isArray(sceneData)) {
            showNotification('Scene must be an array of actions', 'error');
            return;
        }
        
        if (sceneData.length === 0) {
            showNotification('Scene cannot be empty', 'error');
            return;
        }
        
        const errors = [];
        
        sceneData.forEach((action, index) => {
            // Check required fields
            if (!('timestamp' in action)) {
                errors.push(`Action ${index + 1}: Missing timestamp`);
            } else if (typeof action.timestamp !== 'number') {
                errors.push(`Action ${index + 1}: Timestamp must be a number`);
            } else if (action.timestamp < 0) {
                errors.push(`Action ${index + 1}: Timestamp cannot be negative`);
            }
            
            if (!('topic' in action)) {
                errors.push(`Action ${index + 1}: Missing topic`);
            } else if (typeof action.topic !== 'string' || action.topic.trim() === '') {
                errors.push(`Action ${index + 1}: Topic must be a non-empty string`);
            }
            
            if (!('message' in action)) {
                errors.push(`Action ${index + 1}: Missing message`);
            } else if (typeof action.message !== 'string') {
                errors.push(`Action ${index + 1}: Message must be a string`);
            }
        });
        
        if (errors.length > 0) {
            showNotification(`Validation errors:\n${errors.join('\n')}`, 'error');
        } else {
            const duration = Math.max(...sceneData.map(a => a.timestamp));
            showNotification(`Scene is valid! Duration: ${duration}s, Actions: ${sceneData.length}`, 'success');
        }
    } catch (e) {
        showNotification(`Invalid JSON format: ${e.message}`, 'error');
    }
}

function runCommand(commandName) {
    if (confirm(`Execute command "${commandName}"? This will immediately send the command to devices.`)) {
        fetch(`/api/run_command/${commandName}`, { method: 'POST' })
            .then(res => res.json())
            .then(({ success, message, error }) => {
                showNotification(success ? message : error, success ? 'success' : 'error');
                if (success) updateStatus();
            });
    }
}

function editCommand(commandName) {
    if (!document.getElementById('commands').classList.contains('active')) showTab('commands');
    document.getElementById('commandSelect').value = commandName;
    loadCommandForEditing(commandName);
}

function loadCommandForEditing(commandName) {
    fetch(`/api/command/${commandName}`)
        .then(res => res.json())
        .then(data => {
            document.getElementById('commandEditor').value = data.error ? '' : JSON.stringify(data, null, 2);
            currentCommand = data.error ? '' : commandName;
            if (data.error) showNotification(data.error, 'error');
        });
}

function saveCommand() {
    const commandName = document.getElementById('commandSelect').value || currentCommand;
    if (!commandName) return showNotification('Please select or name a command', 'error');
    try {
        const commandData = JSON.parse(document.getElementById('commandEditor').value);
        fetch(`/api/command/${commandName}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(commandData)
        })
            .then(res => res.json())
            .then(({ success, message, error }) => {
                showNotification(success ? message : error, success ? 'success' : 'error');
                if (success) loadResourceList('commands', 'commandList', 'commandSelect', runCommand, editCommand);
            });
    } catch (e) {
        showNotification('Invalid JSON format', 'error');
    }
}

function createNewCommand() {
    const commandName = prompt('Enter command name (e.g., motor_stop, light_on, audio_stop):');
    if (commandName) {
        document.getElementById('commandSelect').value = '';
        document.getElementById('commandEditor').value = JSON.stringify([{"timestamp": 0, "topic": "room1/device", "message": "COMMAND"}], null, 2);
        currentCommand = commandName;
        showNotification('Enter command details and click Save Command', 'info');
    }
}

function validateCommand() {
    try {
        const commandData = JSON.parse(document.getElementById('commandEditor').value);
        if (Array.isArray(commandData) && commandData.every(a => 'timestamp' in a && 'topic' in a && 'message' in a)) {
            showNotification('Command is valid!', 'success');
        } else {
            showNotification('Invalid command format: missing required fields', 'error');
        }
    } catch (e) {
        showNotification('Invalid JSON format', 'error');
    }
}

function showNotification(message, type) {
    const notification = document.getElementById('notification');
    notification.textContent = message;
    notification.className = `notification ${type} show`;
    setTimeout(() => notification.classList.remove('show'), 3000);
}

function restartSystem() {
    if (confirm('Are you sure you want to perform a hard reset? This will reboot the Raspberry Pi and interrupt all operations.')) {
        fetch('/api/system/restart', { method: 'POST' })
            .then(res => res.json())
            .then(({ success, error }) => {
                showNotification(success ? 'System is restarting...' : error || 'Failed to initiate reset', success ? 'success' : 'error');
                if (success) document.querySelector('button[onclick="restartSystem()"]').disabled = true;
            })
            .catch(err => showNotification(`Error communicating with server: ${err.message}`, 'error'));
    }
}

function restartService() {
    if (confirm('Are you sure you want to restart the museum-system service? This will interrupt current operations.')) {
        fetch('/api/system/service/restart', { method: 'POST' })
            .then(res => res.json())
            .then(({ success, error }) => showNotification(success ? 'Service is restarting...' : error || 'Failed to restart service', success ? 'success' : 'error'))
            .catch(err => showNotification(`Error communicating with server: ${err.message}`, 'error'));
    }
}

function updateAll() {
    updateStatus();
    loadStats();
}

document.getElementById('sceneSelect').addEventListener('change', function() {
    const value = this.value;
    document.getElementById('sceneEditor').value = '';
    if (value) loadSceneForEditing(value);
    else currentScene = '';
});

document.getElementById('commandSelect').addEventListener('change', function() {
    const value = this.value;
    const editor = document.getElementById('commandEditor');
    editor.value = '';
    if (value) loadCommandForEditing(value);
    else currentCommand = '';
});

setInterval(updateAll, 5000);