let commands = [];
let editingIndex = null;

function toggleCustomTopic() {
    const topic = document.getElementById('topic').value;
    const customTopicSection = document.getElementById('custom-topic-section');
    customTopicSection.classList.toggle('hidden', topic !== 'custom');
}

function toggleControls() {
    const topic = document.getElementById('topic').value;
    const audioControls = document.getElementById('audio-controls');
    const videoControls = document.getElementById('video-controls');
    const messageSection = document.getElementById('message-section');
    audioControls.classList.toggle('hidden', topic !== 'audio');
    videoControls.classList.toggle('hidden', topic !== 'video');
    messageSection.classList.toggle('hidden', topic === 'audio' || topic === 'video');
    updateAudioFields();
    updateVideoFields();
}

function updateMessageOptions() {
    const topic = document.getElementById('topic').value;
    const messageSelect = document.getElementById('message');
    messageSelect.innerHTML = '';

    if (topic === 'light') {
        messageSelect.innerHTML = `
            <option value="ON">ON</option>
            <option value="OFF">OFF</option>
        `;
    } else if (topic === 'motor') {
        messageSelect.innerHTML = `
            <option value="START">START</option>
            <option value="STOP">STOP</option>
            <option value="SPEED:0">SPEED:0</option>
        `;
    } else if (topic === 'custom') {
        messageSelect.innerHTML = `
            <option value="CUSTOM">CUSTOM</option>
        `;
    }
}

function updateAudioFields() {
    const action = document.getElementById('audio-action').value;
    const playFields = document.getElementById('audio-play-fields');
    const volumeField = document.getElementById('audio-volume-field');
    playFields.classList.toggle('hidden', action !== 'PLAY');
    volumeField.classList.toggle('hidden', !['PLAY', 'VOLUME'].includes(action));
}

function updateVideoFields() {
    const action = document.getElementById('video-action').value;
    const playFields = document.getElementById('video-play-fields');
    const seekField = document.getElementById('video-seek-field');
    playFields.classList.toggle('hidden', action !== 'PLAY_VIDEO');
    seekField.classList.toggle('hidden', action !== 'SEEK');
}

function addCommand() {
    const room = document.getElementById('room').value;
    const timestamp = document.getElementById('timestamp').value;
    let topicType = document.getElementById('topic').value;
    const customTopic = document.getElementById('custom-topic').value;
    const message = document.getElementById('custom-message').value || document.getElementById('message').value;
    const audioAction = document.getElementById('audio-action')?.value;
    const audioFilename = document.getElementById('audio-filename')?.value;
    const audioVolume = document.getElementById('audio-volume')?.value;
    const videoAction = document.getElementById('video-action')?.value;
    const videoFilename = document.getElementById('video-filename')?.value;
    const videoSeek = document.getElementById('video-seek')?.value;

    const topic = topicType === 'custom' && customTopic ? `${room}/${customTopic}` : `${room}/${topicType}`;

    let finalMessage = message;
    if (topicType === 'audio' && audioAction) {
        if (audioAction === 'PLAY' && audioFilename) {
            finalMessage = `PLAY:${audioFilename}:${audioVolume}`;
        } else if (audioAction === 'VOLUME') {
            finalMessage = `VOLUME:${audioVolume}`;
        } else {
            finalMessage = audioAction;
        }
    } else if (topicType === 'video' && videoAction) {
        if (videoAction === 'PLAY_VIDEO' && videoFilename) {
            finalMessage = `PLAY_VIDEO:${videoFilename}`;
        } else if (videoAction === 'SEEK') {
            finalMessage = `SEEK:${videoSeek}`;
        } else {
            finalMessage = videoAction;
        }
    }

    const command = { message: finalMessage, timestamp: parseInt(timestamp), topic };

    if (editingIndex !== null) {
        commands[editingIndex] = command;
        editingIndex = null;
        document.getElementById('add-command-text').textContent = 'Pridať príkaz';
        document.getElementById('add-command-btn').classList.replace('bg-yellow-500', 'bg-blue-500');
        document.getElementById('add-command-btn').classList.replace('hover:bg-yellow-600', 'hover:bg-blue-600');
        document.getElementById('cancel-edit-btn').classList.add('hidden');
    } else {
        commands.push(command);
    }

    updateCommandList();
    updateJsonPreview();
    resetForm();
}

function editCommand(index) {
    const cmd = commands[index];
    editingIndex = index;

    document.getElementById('room').value = cmd.topic.split('/')[0];
    document.getElementById('timestamp').value = cmd.timestamp;
    const topicType = cmd.topic.split('/')[1];
    document.getElementById('topic').value = ['light', 'motor', 'audio', 'video'].includes(topicType) ? topicType : 'custom';
    toggleCustomTopic();
    toggleControls();

    if (topicType !== 'light' && topicType !== 'motor' && topicType !== 'audio' && topicType !== 'video') {
        document.getElementById('custom-topic').value = topicType;
    }

    updateMessageOptions();

    if (topicType === 'audio') {
        const audioAction = document.getElementById('audio-action');
        if (cmd.message.startsWith('PLAY:')) {
            const [, filename, volume] = cmd.message.split(':');
            audioAction.value = 'PLAY';
            document.getElementById('audio-filename').value = filename;
            document.getElementById('audio-volume').value = volume;
            document.getElementById('audio-volume-value').textContent = volume;
        } else if (cmd.message.startsWith('VOLUME:')) {
            const [, volume] = cmd.message.split(':');
            audioAction.value = 'VOLUME';
            document.getElementById('audio-volume').value = volume;
            document.getElementById('audio-volume-value').textContent = volume;
        } else {
            audioAction.value = cmd.message;
        }
        updateAudioFields();
    } else if (topicType === 'video') {
        const videoAction = document.getElementById('video-action');
        if (cmd.message.startsWith('PLAY_VIDEO:')) {
            const [, filename] = cmd.message.split(':');
            videoAction.value = 'PLAY_VIDEO';
            document.getElementById('video-filename').value = filename;
        } else if (cmd.message.startsWith('SEEK:')) {
            const [, seconds] = cmd.message.split(':');
            videoAction.value = 'SEEK';
            document.getElementById('video-seek').value = seconds;
        } else {
            videoAction.value = cmd.message;
        }
        updateVideoFields();
    } else {
        document.getElementById('message').value = ['ON', 'OFF', 'START', 'STOP', 'SPEED:0', 'CUSTOM'].includes(cmd.message) ? cmd.message : 'CUSTOM';
        document.getElementById('custom-message').value = !['ON', 'OFF', 'START', 'STOP', 'SPEED:0', 'CUSTOM'].includes(cmd.message) ? cmd.message : '';
    }

    document.getElementById('add-command-text').textContent = 'Upraviť príkaz';
    document.getElementById('add-command-btn').classList.replace('bg-blue-500', 'bg-yellow-500');
    document.getElementById('add-command-btn').classList.replace('hover:bg-blue-600', 'hover:bg-yellow-600');
    document.getElementById('cancel-edit-btn').classList.remove('hidden');
}

function cancelEdit() {
    editingIndex = null;
    document.getElementById('add-command-text').textContent = 'Pridať príkaz';
    document.getElementById('add-command-btn').classList.replace('bg-yellow-500', 'bg-blue-500');
    document.getElementById('add-command-btn').classList.replace('hover:bg-yellow-600', 'hover:bg-blue-600');
    document.getElementById('cancel-edit-btn').classList.add('hidden');
    resetForm();
}

function deleteCommand(index) {
    commands.splice(index, 1);
    updateCommandList();
    updateJsonPreview();
}

function resetForm() {
    document.getElementById('room').value = 'room1';
    document.getElementById('timestamp').value = '0';
    document.getElementById('topic').value = 'light';
    document.getElementById('custom-topic').value = '';
    document.getElementById('message').value = 'ON';
    document.getElementById('custom-message').value = '';
    if (document.getElementById('audio-action')) {
        document.getElementById('audio-action').value = 'PLAY';
        document.getElementById('audio-filename').value = '';
        document.getElementById('audio-volume').value = '0.7';
        document.getElementById('audio-volume-value').textContent = '0.7';
    }
    if (document.getElementById('video-action')) {
        document.getElementById('video-action').value = 'PLAY_VIDEO';
        document.getElementById('video-filename').value = '';
        document.getElementById('video-seek').value = '0';
    }
    toggleCustomTopic();
    toggleControls();
    updateMessageOptions();
}

function updateCommandList() {
    const commandList = document.getElementById('command-list');
    commandList.innerHTML = '';
    commands.forEach((cmd, index) => {
        const li = document.createElement('li');
        li.innerHTML = `
            <span>Timestamp: ${cmd.timestamp}s, Topic: ${cmd.topic}, Message: ${cmd.message}</span>
            <div>
                <button class="edit-btn" onclick="editCommand(${index})" title="Edit command"><i class="fas fa-edit"></i></button>
                <button onclick="deleteCommand(${index})" title="Delete command"><i class="fas fa-trash"></i></button>
            </div>
        `;
        commandList.appendChild(li);
    });
}

function updateJsonPreview() {
    const jsonOutput = document.getElementById('json-output');
    jsonOutput.value = JSON.stringify(commands, null, 2);
}

function generateJson() {
    updateJsonPreview();
}

function downloadJson() {
    const json = JSON.stringify(commands, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'commands.json';
    a.click();
    URL.revokeObjectURL(url);
}

function loadJson() {
    const fileInput = document.getElementById('load-json');
    const file = fileInput.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = function(e) {
            try {
                commands = JSON.parse(e.target.result);
                updateCommandList();
                updateJsonPreview();
            } catch (error) {
                alert('Error loading JSON file: ' + error.message);
            }
        };
        reader.readAsText(file);
    }
}

document.getElementById('theme-toggle').addEventListener('click', () => {
    document.body.classList.toggle('dark');
    const icon = document.getElementById('theme-toggle').querySelector('i');
    icon.classList.toggle('fa-moon');
    icon.classList.toggle('fa-sun');
});

document.getElementById('audio-volume')?.addEventListener('input', () => {
    const volume = document.getElementById('audio-volume').value;
    document.getElementById('audio-volume-value').textContent = volume;
});

document.getElementById('audio-action')?.addEventListener('change', updateAudioFields);

document.getElementById('video-action')?.addEventListener('change', updateVideoFields);

// Initialize UI on page load
document.addEventListener('DOMContentLoaded', () => {
    updateJsonPreview();
    toggleCustomTopic();
    toggleControls();
    updateMessageOptions();
});