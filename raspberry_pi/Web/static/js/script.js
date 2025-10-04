const socket = io(window.location.origin);
let currentScene = '', currentCommand = '', autoScroll = true;
let sceneStartTime = null, sceneDuration = 0;
const activeFilters = new Set(['debug', 'info', 'warning', 'error', 'critical']);
const logCounts = { debug: 0, info: 0, warning: 0, error: 0, critical: 0 };

// Pripojenie k serveru
socket.on('connect', () => {
    console.log('Pripojené k serveru');
    updateMainDashboard();
    loadResourceList('scenes', 'sceneList', 'sceneSelect', runScene, editScene);
    loadResourceList('commands', 'commandList', 'commandSelect', runCommand, editCommand);
});

// Event listenery
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
    showNotification(success ? `Príkaz '${command}' vykonaný úspešne` : `Príkaz '${command}' zlyhal: ${error}`, success ? 'success' : 'error');
});

// =======================================
// HLAVNÝ DASHBOARD - Nové funkcie
// =======================================

function updateMainDashboard() {
    updateSystemStatus();
    updateDeviceStatus();
    // Aktualizuj progress aj keď nie je zobrazený - server povie či má byť
    updateSceneProgress();
}

function updateSystemStatus() {
    fetch('/api/status')
        .then(res => res.json())
        .then(data => {
            const { room_id, scene_running, mqtt_connected, uptime } = data;
            
            // Aktualizuj hlavný status
            updateMainStatus(scene_running, mqtt_connected);
            
            // Aktualizuj detailné stavy
            updateRoomStatus(room_id);
            updateMqttStatus(mqtt_connected);
            updateSceneStatus(scene_running);
            
            // Aktualizuj ovládacie tlačidlá
            updateControlButtons(scene_running, mqtt_connected);
        })
        .catch(err => {
            console.error('Chyba pri načítaní stavu:', err);
            updateMainStatus(false, false, true);
        });
}

function updateMainStatus(sceneRunning, mqttConnected, hasError = false) {
    const statusElement = document.getElementById('mainSystemStatus');
    
    if (hasError) {
        statusElement.className = 'main-status error';
        statusElement.innerHTML = `
            <div class="status-icon">❌</div>
            <div class="status-text">Chyba komunikácie</div>
            <div class="status-description">Nemožno načítať stav systému</div>
        `;
        return;
    }
    
    if (sceneRunning) {
        statusElement.className = 'main-status running pulse';
        statusElement.innerHTML = `
            <div class="status-icon">🎭</div>
            <div class="status-text">Scéna prebieha</div>
            <div class="status-description">Predstavenie je v priebehu</div>
        `;
        showSceneProgress();
    } else if (mqttConnected) {
        statusElement.className = 'main-status ready';
        statusElement.innerHTML = `
            <div class="status-icon">✅</div>
            <div class="status-text">Systém pripravený</div>
            <div class="status-description">Môžete spustiť predstavenie</div>
        `;
        hideSceneProgress();
    } else {
        statusElement.className = 'main-status error';
        statusElement.innerHTML = `
            <div class="status-icon">⚠️</div>
            <div class="status-text">Systém nedostupný</div>
            <div class="status-description">Skontrolujte MQTT pripojenie</div>
        `;
        hideSceneProgress();
    }
}

function updateRoomStatus(roomId) {
    const element = document.getElementById('roomStatus');
    document.getElementById('roomId').textContent = roomId || 'Neznáma';
    element.className = 'status-item good';
}

function updateMqttStatus(connected) {
    const element = document.getElementById('mqttStatus');
    const valueElement = document.getElementById('mqttConnection');
    
    if (connected) {
        element.className = 'status-item good';
        valueElement.textContent = 'Pripojené';
    } else {
        element.className = 'status-item error';
        valueElement.textContent = 'Odpojené';
    }
}

function updateSceneStatus(running) {
    const element = document.getElementById('sceneStatus');
    const valueElement = document.getElementById('sceneState');
    
    if (running) {
        element.className = 'status-item warning';
        valueElement.textContent = 'Prebieha';
    } else {
        element.className = 'status-item good';
        valueElement.textContent = 'Pripravená';
    }
}

function updateDeviceStatus() {
    fetch('/api/stats')
        .then(res => res.json())
        .then(data => {
            const connectedCount = Object.keys(data.connected_devices || {}).length;
            const element = document.getElementById('deviceStatus');
            const valueElement = document.getElementById('deviceCount');
            
            valueElement.textContent = `${connectedCount} pripojených`;
            
            if (connectedCount > 0) {
                element.className = 'status-item good';
            } else {
                element.className = 'status-item warning';
            }
        })
        .catch(err => {
            const element = document.getElementById('deviceStatus');
            element.className = 'status-item error';
            document.getElementById('deviceCount').textContent = 'Chyba';
        });
}

function updateControlButtons(sceneRunning, mqttConnected) {
    const runBtn = document.getElementById('runMainSceneBtn');
    const stopBtn = document.getElementById('stopSceneBtn');
    
    if (sceneRunning) {
        runBtn.style.display = 'none';
        stopBtn.style.display = 'block';
    } else {
        runBtn.style.display = 'block';
        stopBtn.style.display = 'none';
        runBtn.disabled = !mqttConnected;
        
        if (!mqttConnected) {
            runBtn.innerHTML = `
                <div class="button-icon">⚠️</div>
                <div class="button-text">Systém nedostupný</div>
                <div class="button-subtext">Skontrolujte MQTT pripojenie</div>
            `;
        } else {
            runBtn.innerHTML = `
                <div class="button-icon">▶️</div>
                <div class="button-text">Spustiť hlavnú scénu</div>
                <div class="button-subtext">Stlačte pre začatie predstavenia</div>
            `;
        }
    }
}

// =======================================
// PROGRESS BAR PRE SCÉNU
// =======================================

function showSceneProgress() {
    const container = document.getElementById('sceneProgressContainer');
    container.style.display = 'block';
    // Nezapisujeme sceneStartTime tu - dostaneme ho z servera
}

function hideSceneProgress() {
    const container = document.getElementById('sceneProgressContainer');
    container.style.display = 'none';
    sceneStartTime = null;
    sceneDuration = 0;
}

function updateSceneProgress() {
    fetch('/api/scene/progress')
        .then(res => res.json())
        .then(data => {
            if (data.scene_running) {
                // State machine mode
                if (data.mode === 'state_machine') {
                    const progress = Math.min(Math.max(data.progress * 100, 0), 100);
                    
                    document.getElementById('sceneProgressBar').style.width = `${progress}%`;
                    document.getElementById('sceneProgressText').textContent = `${Math.round(progress)}%`;
                    
                    // Zobraz aktuálny stav namiesto času
                    const stateInfo = `Stav: ${data.current_state} (${data.states_completed}/${data.total_states})`;
                    document.getElementById('sceneTimeRemaining').textContent = stateInfo;
                    
                    // Ak je scéna ukončená (current_state === "END")
                    if (data.current_state === "END" || progress >= 100) {
                        setTimeout(() => {
                            if (!data.scene_running) {
                                hideSceneProgress();
                            }
                        }, 2000);
                    }
                } else {
                    // Fallback pre iné režimy
                    hideSceneProgress();
                }
            } else {
                hideSceneProgress();
            }
        })
        .catch(err => {
            console.error('Chyba pri získavaní scene progress:', err);
            hideSceneProgress();
        });
}

// =======================================
// HLAVNÉ AKCIE
// =======================================

function runMainScene() {
    // Fetch configured main scene name from API
    fetch('/api/config/main_scene')
        .then(res => res.json())
        .then(config => {
            const mainSceneName = config.json_file_name;
            
            fetch(`/api/run_scene/${mainSceneName}`, { method: 'POST' })
                .then(res => res.json())
                .then(({ success, message, error }) => {
                    if (success) {
                        showNotification(message, 'success');
                        updateMainDashboard();
                    } else {
                        showNotification(error, 'error');
                    }
                })
                .catch(err => {
                    showNotification('Chyba pri komunikácii so serverom', 'error');
                });
        });
}

function stopScene() {
    if (confirm('Skutočne chcete zastaviť prebiehajúcu scénu?')) {
        fetch('/api/stop_scene', { method: 'POST' })
            .then(res => res.json())
            .then(({ success, message, error }) => {
                showNotification(success ? message : error, success ? 'success' : 'error');
                if (success) updateMainDashboard();
            })
            .catch(err => {
                showNotification('Chyba pri komunikácii so serverom', 'error');
            });
    }
}

function testSystem() {
    showNotification('Spúšťam test systému...', 'info');
    
    // Test MQTT pripojenia
    fetch('/api/status')
        .then(res => res.json())
        .then(data => {
            if (data.mqtt_connected) {
                showNotification('✅ Test úspešný - systém funguje správne', 'success');
            } else {
                showNotification('⚠️ MQTT pripojenie zlyhalo', 'error');
            }
        })
        .catch(() => {
            showNotification('❌ Test zlyhal - server neodpovedá', 'error');
        });
}

// =======================================
// TAB SYSTÉM
// =======================================

function showTab(tabName) {
    // Skry všetky tab contents
    document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.tab').forEach(el => el.classList.remove('active'));
    
    // Zobraz vybraný tab
    if (tabName === 'dashboard') {
        // Pre dashboard tab, zobraz main-dashboard namiesto tab-content
        document.querySelector('.main-dashboard').style.display = 'block';
        document.querySelector('.tab[onclick="showTab(\'dashboard\')"]').classList.add('active');
    } else {
        // Skry main dashboard
        document.querySelector('.main-dashboard').style.display = 'none';
        
        // Zobraz vybraný tab content
        document.getElementById(tabName).classList.add('active');
        document.querySelector(`.tab[onclick="showTab('${tabName}')"]`).classList.add('active');
        
        // Špecifické akcie pre rôzne taby
        if (tabName === 'scenes') {
            loadResourceList('scenes', 'sceneList', 'sceneSelect', runScene, editScene);
        } else if (tabName === 'stats') {
            loadStats();
        } else if (tabName === 'commands') {
            loadResourceList('commands', 'commandList', 'commandSelect', runCommand, editCommand);
        }
    }
}

// Inicializuj dashboard tab ako aktívny
document.addEventListener('DOMContentLoaded', () => {
    showTab('dashboard');
});

// =======================================
// EXISTUJÚCE FUNKCIE - Nezmenené
// =======================================

function toggleLogLevel(level) {
    const button = document.querySelector(`.filter-btn[data-level="${level}"]`);
    activeFilters[activeFilters.has(level) ? 'delete' : 'add'](level);
    button.classList.toggle('active');
    applyLogFilters();
}

function applyLogFilters() {
    const possibleLevels = ['debug', 'info', 'warning', 'error', 'critical'];
    document.querySelectorAll('.log-entry').forEach(entry => {
        const level = Array.from(entry.classList).find(cls => possibleLevels.includes(cls)) || 'info';
        entry.classList.toggle('hidden', !activeFilters.has(level));
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
                    <p>Spustené: ${count} krát</p>
                </div>
            </div>`).join('')
        : '<div class="scene-item"><div class="scene-info"><h4>Žiadne štatistiky</h4><p>Zatiaľ neboli spustené žiadne scény</p></div></div>';

    const deviceList = document.getElementById('deviceList');
    deviceList.innerHTML = Object.entries(connected_devices).length
        ? Object.entries(connected_devices).map(([id, { status, last_updated }]) => `
            <div class="scene-item device">
                <div class="scene-info">
                    <h4>Zariadenie: ${id}</h4>
                    <div class="device-status ${status.toLowerCase()}">${status === 'online' ? 'Pripojené' : 'Odpojené'}</div>
                    <p>Posledná aktualizácia: ${new Date(last_updated * 1000).toLocaleString()}</p>
                </div>
            </div>`).join('')
        : '<div class="scene-item device"><div class="scene-info"><h4>Žiadne zariadenia</h4><p>Momentálne nie sú pripojené žiadne zariadenia</p></div></div>';
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
    
    // Zvýšený limit na 1000 logov (z 500)
    while (logContainer.children.length > 1000) {
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
    if (confirm('Skutočne chcete vymazať všetky logy?')) {
        fetch('/api/logs/clear', { method: 'POST' })
            .then(res => res.json())
            .then(({ success }) => {
                showNotification(success ? 'Logy vymazané úspešne' : 'Chyba pri mazaní logov', success ? 'success' : 'error');
            });
    }
}

function loadResourceList(type, listId, selectId, runFn, editFn) {
    fetch(`/api/${type}`)
        .then(res => res.json())
        .then(items => {
            const list = document.getElementById(listId);
            const select = document.getElementById(selectId);
            list.innerHTML = items.length
                ? items.map(({ name }) => `
                    <div class="scene-item">
                        <div class="scene-info">
                            <h4>${name}</h4>
                            <p>${type === 'scenes' ? 'Scéna' : 'Príkaz'}</p>
                        </div>
                        <div class="scene-actions">
                            <button class="btn btn-${type === 'commands' ? 'warning' : 'primary'}" onclick="${runFn.name}('${name}')">${type === 'commands' ? '⚡ Vykonať' : '▶️ Spustiť'}</button>
                            <button class="btn btn-secondary" onclick="${editFn.name}('${name}')">✏️ Upraviť</button>
                        </div>
                    </div>`).join('')
                : `<div class="scene-item"><div class="scene-info"><h4>Žiadne ${type === 'scenes' ? 'scény' : 'príkazy'}</h4><p>Zatiaľ neboli načítané žiadne ${type === 'scenes' ? 'scény' : 'príkazy'}</p></div></div>`;
            select.innerHTML = `<option value="">Vyberte ${type === 'scenes' ? 'scénu' : 'príkaz'} na úpravu</option>` + items.map(({ name }) => `<option value="${name}">${name}</option>`).join('');
        });
}

function runScene(sceneName) {
    fetch(`/api/run_scene/${sceneName}`, { method: 'POST' })
        .then(res => res.json())
        .then(({ success, message, error }) => {
            if (success) {
                showNotification(message, 'success');
                updateMainDashboard();
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
        showNotification('Prosím vyberte alebo vytvorte scénu', 'error');
        return;
    }
    
    const finalSceneName = sceneName.endsWith('.json') ? sceneName : sceneName + '.json';
    
    try {
        const sceneData = JSON.parse(document.getElementById('sceneEditor').value);
        
        if (!Array.isArray(sceneData)) {
            showNotification('Scéna musí byť pole akcií', 'error');
            return;
        }
        
        for (let i = 0; i < sceneData.length; i++) {
            const action = sceneData[i];
            if (!('timestamp' in action) || !('topic' in action) || !('message' in action)) {
                showNotification(`Akcia ${i + 1} nemá požadované polia (timestamp, topic, message)`, 'error');
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
                sceneSelect.value = finalSceneName;
                loadResourceList('scenes', 'sceneList', 'sceneSelect', runScene, editScene);
            } else {
                showNotification(error, 'error');
            }
        });
    } catch (e) {
        showNotification('Neplatný JSON formát. Skontrolujte syntax.', 'error');
    }
}

function createNewScene() {
    const sceneName = prompt('Zadajte názov scény (vrátane .json koncovky):');
    if (sceneName) {
        const sceneSelect = document.getElementById('sceneSelect');
        sceneSelect.value = '';
        
        const newOption = document.createElement('option');
        newOption.value = sceneName;
        newOption.textContent = sceneName;
        newOption.selected = true;
        sceneSelect.appendChild(newOption);
        
        document.getElementById('sceneEditor').value = JSON.stringify([
            {"timestamp": 0, "topic": "roomX/light", "message": "ON"},
            {"timestamp": 2.0, "topic": "roomX/audio", "message": "PLAY_WELCOME"},
            {"timestamp": 5.0, "topic": "roomX/light", "message": "OFF"}
        ], null, 2);
        
        currentScene = sceneName;
        
        if (!document.getElementById('scenes').classList.contains('active')) {
            showTab('scenes');
        }
        
        showNotification(`Nová scéna "${sceneName}" vytvorená. Upravte a uložte.`, 'info');
    }
}

function validateScene() {
    try {
        const sceneData = JSON.parse(document.getElementById('sceneEditor').value);
        
        if (!Array.isArray(sceneData)) {
            showNotification('Scéna musí byť pole akcií', 'error');
            return;
        }
        
        if (sceneData.length === 0) {
            showNotification('Scéna nemôže byť prázdna', 'error');
            return;
        }
        
        const errors = [];
        
        sceneData.forEach((action, index) => {
            if (!('timestamp' in action)) {
                errors.push(`Akcia ${index + 1}: Chýba timestamp`);
            } else if (typeof action.timestamp !== 'number') {
                errors.push(`Akcia ${index + 1}: Timestamp musí byť číslo`);
            } else if (action.timestamp < 0) {
                errors.push(`Akcia ${index + 1}: Timestamp nemôže byť záporný`);
            }
            
            if (!('topic' in action)) {
                errors.push(`Akcia ${index + 1}: Chýba topic`);
            } else if (typeof action.topic !== 'string' || action.topic.trim() === '') {
                errors.push(`Akcia ${index + 1}: Topic musí byť neprázdny reťazec`);
            }
            
            if (!('message' in action)) {
                errors.push(`Akcia ${index + 1}: Chýba message`);
            } else if (typeof action.message !== 'string') {
                errors.push(`Akcia ${index + 1}: Message musí byť reťazec`);
            }
        });
        
        if (errors.length > 0) {
            showNotification(`Chyby validácie:\n${errors.join('\n')}`, 'error');
        } else {
            const duration = Math.max(...sceneData.map(a => a.timestamp));
            showNotification(`Scéna je platná! Trvanie: ${duration}s, Akcie: ${sceneData.length}`, 'success');
        }
    } catch (e) {
        showNotification(`Neplatný JSON formát: ${e.message}`, 'error');
    }
}

function runCommand(commandName) {
    if (confirm(`Vykonať príkaz "${commandName}"? Príkaz sa okamžite pošle zariadeniam.`)) {
        fetch(`/api/run_command/${commandName}`, { method: 'POST' })
            .then(res => res.json())
            .then(({ success, message, error }) => {
                showNotification(success ? message : error, success ? 'success' : 'error');
                if (success) updateMainDashboard();
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
    if (!commandName) return showNotification('Prosím vyberte alebo pomenujte príkaz', 'error');
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
        showNotification('Neplatný JSON formát', 'error');
    }
}

function createNewCommand() {
    const commandName = prompt('Zadajte názov príkazu (napr. motor_stop, light_on, audio_stop):');
    if (commandName) {
        document.getElementById('commandSelect').value = '';
        document.getElementById('commandEditor').value = JSON.stringify([{"timestamp": 0, "topic": "prefix/device", "message": "COMMAND"}], null, 2);
        currentCommand = commandName;
        showNotification('Zadajte detaily príkazu a kliknite Uložiť príkaz', 'info');
    }
}

function validateCommand() {
    try {
        const commandData = JSON.parse(document.getElementById('commandEditor').value);
        if (Array.isArray(commandData) && commandData.every(a => 'timestamp' in a && 'topic' in a && 'message' in a)) {
            showNotification('Príkaz je platný!', 'success');
        } else {
            showNotification('Neplatný formát príkazu: chýbajú požadované polia', 'error');
        }
    } catch (e) {
        showNotification('Neplatný JSON formát', 'error');
    }
}

function showNotification(message, type) {
    const notification = document.getElementById('notification');
    notification.textContent = message;
    notification.className = `notification ${type} show`;
    setTimeout(() => notification.classList.remove('show'), 3000);
}

function restartSystem() {
    if (confirm('Skutočne chcete vykonať tvrdý reštart? Toto reštartuje Raspberry Pi a preruší všetky operácie.')) {
        fetch('/api/system/restart', { method: 'POST' })
            .then(res => res.json())
            .then(({ success, error }) => {
                showNotification(success ? 'Systém sa reštartuje...' : error || 'Chyba pri reštarte', success ? 'success' : 'error');
                if (success) document.querySelector('button[onclick="restartSystem()"]').disabled = true;
            })
            .catch(err => showNotification(`Chyba komunikácie so serverom: ${err.message}`, 'error'));
    }
}

function restartService() {
    if (confirm('Skutočne chcete reštartovať museum-system službu? Toto preruší aktuálne operácie.')) {
        fetch('/api/system/service/restart', { method: 'POST' })
            .then(res => res.json())
            .then(({ success, error }) => showNotification(success ? 'Služba sa reštartuje...' : error || 'Chyba pri reštarte služby', success ? 'success' : 'error'))
            .catch(err => showNotification(`Chyba komunikácie so serverom: ${err.message}`, 'error'));
    }
}

// Pravidelné aktualizácie
setInterval(updateMainDashboard, 2000); // Častejšie aktualizácie pre lepší progress
setInterval(() => {
    // Progress sa aktualizuje už v updateMainDashboard každé 2 sekundy
    // Tento interval sa používa pre jemnejšie aktualizácie progress baru
    const container = document.getElementById('sceneProgressContainer');
    if (container && container.style.display !== 'none') {
        updateSceneProgress();
    }
}, 500); // Aktualizuj progress každých 0.5 sekundy pre plynulosť

// Event listenery pre select elementy
document.addEventListener('DOMContentLoaded', () => {
    const sceneSelect = document.getElementById('sceneSelect');
    if (sceneSelect) {
        sceneSelect.addEventListener('change', function() {
            const value = this.value;
            document.getElementById('sceneEditor').value = '';
            if (value) loadSceneForEditing(value);
            else currentScene = '';
        });
    }

    const commandSelect = document.getElementById('commandSelect');
    if (commandSelect) {
        commandSelect.addEventListener('change', function() {
            const value = this.value;
            const editor = document.getElementById('commandEditor');
            editor.value = '';
            if (value) loadCommandForEditing(value);
            else currentCommand = '';
        });
    }
});