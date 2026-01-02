const chatContainer = document.getElementById('chat'), messagesContainer = document.getElementById('messages'), chatForm = document.getElementById('chatForm'), userInput = document.getElementById('userInput'), sendBtn = document.getElementById('sendBtn'), welcomeScreen = document.getElementById('welcome'), charCount = document.getElementById('charCount'), themeToggle = document.getElementById('themeToggle'), clearChatBtn = document.getElementById('clearChatBtn'), menuBtn = document.getElementById('menuBtn'), sidebar = document.getElementById('sidebar'), sidebarClose = document.getElementById('sidebarClose'), newChatBtn = document.getElementById('newChatBtn'), chatHistory = document.getElementById('chatHistory'), toastContainer = document.getElementById('toastContainer'), attachBtn = document.getElementById('attachBtn'), mcpDropdown = document.getElementById('mcpDropdown'), mcpToolsList = document.getElementById('mcpToolsList');
let isLoading = false, chatSessions = JSON.parse(localStorage.getItem('chatSessions') || '[]'), currentSessionId = Date.now().toString(), pendingActionData = null;
document.addEventListener('DOMContentLoaded', () => { initTheme(); loadChatHistory(); updateCharCount(); loadMCPTools(); userInput.focus(); });
function initTheme() { const savedTheme = localStorage.getItem('theme') || 'dark'; document.documentElement.setAttribute('data-theme', savedTheme); updateLogoGradient(savedTheme); }
function updateLogoGradient(theme) { const logoPath = document.querySelector('.logo-path'); if (logoPath) { logoPath.setAttribute('stroke', theme === 'light' ? 'url(#brandGradLight)' : 'url(#brandGradDark)'); } }
if (themeToggle) { themeToggle.addEventListener('click', () => { const currentTheme = document.documentElement.getAttribute('data-theme'); const newTheme = currentTheme === 'dark' ? 'light' : 'dark'; document.documentElement.setAttribute('data-theme', newTheme); localStorage.setItem('theme', newTheme); updateLogoGradient(newTheme); showToast(`Switched to ${newTheme} theme`, 'success'); }); }
if (menuBtn) { menuBtn.addEventListener('click', () => { sidebar.classList.add('open'); createOverlay(); }); }
if (sidebarClose) { sidebarClose.addEventListener('click', closeSidebar); }
function createOverlay() { const overlay = document.createElement('div'); overlay.className = 'sidebar-overlay show'; overlay.id = 'sidebarOverlay'; overlay.addEventListener('click', closeSidebar); document.body.appendChild(overlay); }
function closeSidebar() { sidebar.classList.remove('open'); const overlay = document.getElementById('sidebarOverlay'); if (overlay) overlay.remove(); }
if (newChatBtn) { newChatBtn.addEventListener('click', () => { saveChatSession(); clearMessages(); currentSessionId = Date.now().toString(); closeSidebar(); showToast('New chat started', 'success'); }); }
if (clearChatBtn) { clearChatBtn.addEventListener('click', () => { if (messagesContainer.children.length === 0) { showToast('Chat is already empty', 'info'); return; } clearMessages(); showToast('Chat cleared', 'success'); }); }
function clearMessages() { messagesContainer.innerHTML = ''; if (welcomeScreen) { welcomeScreen.style.display = 'flex'; } }
function saveChatSession() { if (messagesContainer.children.length === 0) return; const firstMessage = messagesContainer.querySelector('.message.user .msg-content'); const title = firstMessage ? firstMessage.textContent.substring(0, 40) + '...' : 'Chat Session'; const session = { id: currentSessionId, title: title, timestamp: Date.now(), messages: messagesContainer.innerHTML }; const existingIndex = chatSessions.findIndex(s => s.id === currentSessionId); if (existingIndex >= 0) { chatSessions[existingIndex] = session; } else { chatSessions.unshift(session); } chatSessions = chatSessions.slice(0, 20); localStorage.setItem('chatSessions', JSON.stringify(chatSessions)); loadChatHistory(); }
function loadChatHistory() { if (!chatHistory) return; chatHistory.innerHTML = chatSessions.map(session => `<div class="chat-history-item" data-id="${session.id}"><div class="title">${escapeHtml(session.title)}</div><div class="time">${formatTimestamp(session.timestamp)}</div></div>`).join(''); chatHistory.querySelectorAll('.chat-history-item').forEach(item => { item.addEventListener('click', () => { const session = chatSessions.find(s => s.id === item.dataset.id); if (session) { saveChatSession(); currentSessionId = session.id; messagesContainer.innerHTML = session.messages; if (welcomeScreen) welcomeScreen.style.display = 'none'; closeSidebar(); chatContainer.scrollTop = chatContainer.scrollHeight; } }); }); }
function formatTimestamp(timestamp) { const date = new Date(timestamp); const now = new Date(); const diff = now - date; if (diff < 60000) return 'Just now'; if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`; if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`; return date.toLocaleDateString(); }
function updateCharCount() { if (charCount) { charCount.textContent = userInput.value.length; } }
userInput.addEventListener('input', function () { this.style.height = 'auto'; this.style.height = Math.min(this.scrollHeight, 150) + 'px'; updateCharCount(); });
userInput.addEventListener('keydown', function (e) { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); chatForm.dispatchEvent(new Event('submit')); } });

let editorSynced = true;

chatForm.addEventListener('submit', async function (e) {
    e.preventDefault();
    const message = userInput.value.trim();
    if (!message || isLoading) return;
    if (welcomeScreen) { welcomeScreen.style.display = 'none'; }
    addMessage(message, 'user');

    userInput.value = '';
    userInput.style.height = 'auto';
    updateCharCount();
    isLoading = true;
    sendBtn.disabled = true;
    sendBtn.classList.add('loading');
    const loadingEl = addLoadingMessage();

    try {
        const requestBody = { message };
        if (codeEditor && codeEditor.value) {
            requestBody.file_content = codeEditor.value;
            if (currentEditorFile) {
                requestBody.file_path = currentEditorFile;
            }
        }

        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestBody)
        });
        const data = await response.json();
        loadingEl.remove();

        if (data.error) {
            addMessage('Error: ' + data.error, 'bot');
            showToast('Error: ' + data.error, 'error');
        } else {
            addMessageWithMeta(data.response, 'bot', data.action_data, data.mcp_logs);

            if (data.needs_clarification) {
                showToast('Agent needs clarification', 'info');
            }

            const pendingAction = data.pending_action;
            const actionData = data.action_data;

            if (pendingAction === 'stream_to_editor' && actionData && actionData.code && editorSynced) {
                if (actionData.path && actionData.path !== currentEditorFile) {
                    await loadFileInEditor(actionData.path);
                }
                showPendingChanges(actionData.code, actionData.changes || 'Code changes');
            } else if (pendingAction === 'stream_to_editor' && !editorSynced) {
                showToast('Editor disconnected - changes shown in chat only', 'info');
            } else if (pendingAction === 'delete') {
                showToast('Click Accept to confirm deletion', 'warning');
            } else if (pendingAction === 'run_python') {
                showToast('Click Accept to run Python code', 'warning');
            }

            saveChatSession();
        }
    } catch (error) {
        loadingEl.remove();
        addMessage('Error: Connection error. Please try again.', 'bot');
        showToast('Connection error', 'error');
    } finally {
        isLoading = false;
        sendBtn.disabled = false;
        sendBtn.classList.remove('loading');
        userInput.focus();
    }
});

let pendingNewCode = null, originalEditorCode = null;
const changeButtons = document.getElementById('changeButtons'), acceptChangeBtn = document.getElementById('acceptChangeBtn'), rejectChangeBtn = document.getElementById('rejectChangeBtn');

function showPendingChanges(newCode, summary) {
    if (!codeEditor) return;
    const originalCode = codeEditor.value;
    openEditor();
    showDiffModal(originalCode, newCode, currentEditorFile || 'Untitled', summary);
}

function acceptChanges() {
    if (!pendingNewCode) return;
    codeEditor.classList.remove('pending-changes');
    changeButtons.classList.add('hidden');
    setEditorModified(true);
    editorStatus.textContent = 'Changes accepted - Save to apply';
    editorStatus.className = 'editor-status saved';
    showToast('Changes accepted! Click Save to write to file.', 'success');
    pendingNewCode = null;
    originalEditorCode = null;
}

function rejectChanges() {
    if (!originalEditorCode) return;
    codeEditor.value = originalEditorCode;
    codeEditor.classList.remove('pending-changes');
    changeButtons.classList.add('hidden');
    updateLineNumbers();
    updateEditorInfo();
    editorStatus.textContent = 'Changes rejected';
    editorStatus.className = 'editor-status';
    showToast('Changes rejected', 'info');
    pendingNewCode = null;
    originalEditorCode = null;
}

if (acceptChangeBtn) { acceptChangeBtn.addEventListener('click', acceptChanges); }
if (rejectChangeBtn) { rejectChangeBtn.addEventListener('click', rejectChanges); }

async function streamCodeToEditor(code) {
    if (!codeEditor || !editorPanel.classList.contains('open')) { openEditor(); }
    editorPanel.classList.add('streaming');
    editorStatus.textContent = 'Streaming...';
    editorStatus.className = 'editor-status streaming';
    codeEditor.value = '';
    const chars = code.split('');
    let index = 0;
    return new Promise((resolve) => {
        const streamInterval = setInterval(() => {
            if (index < chars.length) {
                codeEditor.value += chars[index];
                index++;
                if (index % 10 === 0) {
                    updateLineNumbers();
                    updateEditorInfo();
                    codeEditor.scrollTop = codeEditor.scrollHeight;
                }
            } else {
                clearInterval(streamInterval);
                editorPanel.classList.remove('streaming');
                updateLineNumbers();
                updateEditorInfo();
                setEditorModified(true);
                editorStatus.textContent = 'Code updated';
                editorStatus.className = 'editor-status saved';
                showToast('Code streamed to editor', 'success');
                resolve();
            }
        }, 5);
    });
}

function addMessage(content, type) { addMessageWithMeta(content, type, null, null); }

function addMessageWithMeta(content, type, actionData, mcp_logs) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}`;

    const avatar = document.createElement('div');
    avatar.className = 'msg-avatar';
    if (type === 'user') {
        avatar.innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>';
    } else {
        avatar.innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>';
    }

    const wrapper = document.createElement('div');
    wrapper.className = 'msg-wrapper';

    if (mcp_logs && Array.isArray(mcp_logs) && mcp_logs.length > 0) {
        const logsDiv = document.createElement('div');
        logsDiv.className = 'mcp-logs';
        mcp_logs.forEach(log => {
            const logItem = document.createElement('div');
            logItem.className = 'mcp-log-item';
            logItem.innerHTML = `<svg class="mcp-log-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><path d="M20 6L9 17l-5-5"/></svg><span>${escapeHtml(log)}</span>`;
            logsDiv.appendChild(logItem);
        });
        wrapper.appendChild(logsDiv);
    }

    const contentDiv = document.createElement('div');
    contentDiv.className = 'msg-content';
    contentDiv.innerHTML = formatMessage(content);
    wrapper.appendChild(contentDiv);

    if (actionData) {
        const actionBar = document.createElement('div');
        actionBar.className = 'action-bar';
        actionBar.innerHTML = `<button class="action-btn accept" onclick="handleConfirmAction('accept',${JSON.stringify(actionData).replace(/"/g, '&quot;')})"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>Accept</button><button class="action-btn reject" onclick="handleConfirmAction('reject',${JSON.stringify(actionData).replace(/"/g, '&quot;')})"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>Reject</button>`;
        wrapper.appendChild(actionBar);
    }

    const timeDiv = document.createElement('div');
    timeDiv.className = 'msg-time';
    timeDiv.textContent = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    wrapper.appendChild(timeDiv);

    messageDiv.appendChild(avatar);
    messageDiv.appendChild(wrapper);
    messagesContainer.appendChild(messageDiv);

    requestAnimationFrame(() => {
        chatContainer.scrollTo({ top: chatContainer.scrollHeight, behavior: 'smooth' });
    });

    messageDiv.querySelectorAll('pre code').forEach((block) => {
        if (window.Prism) { Prism.highlightElement(block); }
    });
}

function addLoadingMessage() {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message bot loading-message';
    const avatar = document.createElement('div');
    avatar.className = 'msg-avatar';
    avatar.innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>';
    const wrapper = document.createElement('div');
    wrapper.className = 'msg-wrapper';
    const contentDiv = document.createElement('div');
    contentDiv.className = 'msg-content';
    contentDiv.innerHTML = `<div class="loading-dots"><span></span><span></span><span></span></div>`;
    wrapper.appendChild(contentDiv);
    messageDiv.appendChild(avatar);
    messageDiv.appendChild(wrapper);
    messagesContainer.appendChild(messageDiv);
    chatContainer.scrollTo({ top: chatContainer.scrollHeight, behavior: 'smooth' });
    return messageDiv;
}

function formatMessage(content) {
    let formatted = escapeHtml(content);
    formatted = formatted.replace(/```(\w*)\n?([\s\S]*?)```/g, (match, lang, code) => {
        const language = lang || 'plaintext';
        const codeHtml = code.replace(/\n/g, '&#10;');
        return `<div class="code-block-wrapper"><div class="code-header"><span class="code-lang">${language}</span><button class="copy-btn" onclick="copyCode(this)"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>Copy</button></div><pre><code class="language-${language}">${codeHtml}</code></pre></div>`;
    });
    formatted = formatted.replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>');
    formatted = formatted.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    formatted = formatted.replace(/\*([^*]+)\*/g, '<em>$1</em>');
    const parts = formatted.split(/(<div class="code-block-wrapper">[\s\S]*?<\/div>)/g);
    formatted = parts.map(part => {
        if (part.includes('code-block-wrapper')) return part;
        return part.replace(/\n/g, '<br>');
    }).join('');
    return formatted;
}

function escapeHtml(text) { const div = document.createElement('div'); div.textContent = text; return div.innerHTML; }

function copyCode(button) {
    const codeBlock = button.closest('.code-block-wrapper').querySelector('code');
    const text = codeBlock.textContent;
    navigator.clipboard.writeText(text).then(() => {
        button.classList.add('copied');
        button.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>Copied!`;
        showToast('Code copied to clipboard', 'success');
        setTimeout(() => {
            button.classList.remove('copied');
            button.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>Copy`;
        }, 2000);
    });
}

function useSuggestion(text) { userInput.value = text; userInput.focus(); userInput.dispatchEvent(new Event('input')); }

function showToast(message, type = 'info') {
    if (!toastContainer) return;
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `<span class="toast-icon"></span>${message}`;
    toastContainer.appendChild(toast);
    setTimeout(() => { toast.remove(); }, 3000);
}

window.copyCode = copyCode;

// File Browser
const fileBrowserBtn = document.getElementById('fileBrowserBtn'), fileBrowserModal = document.getElementById('fileBrowserModal'), modalBackdrop = document.getElementById('modalBackdrop'), modalClose = document.getElementById('modalClose'), driveSelect = document.getElementById('driveSelect'), pathInput = document.getElementById('pathInput'), goUpBtn = document.getElementById('goUpBtn'), goPathBtn = document.getElementById('goPathBtn'), fileList = document.getElementById('fileList'), previewFileName = document.getElementById('previewFileName'), filePreviewContent = document.getElementById('filePreviewContent'), useFileBtn = document.getElementById('useFileBtn'), copyPathBtn = document.getElementById('copyPathBtn'), selectedPathEl = document.getElementById('selectedPath'), selectFileBtn = document.getElementById('selectFileBtn');
let currentPath = '', selectedFile = null, parentPath = null;

if (fileBrowserBtn) { fileBrowserBtn.addEventListener('click', () => { openFileBrowser(); }); }
if (modalClose) { modalClose.addEventListener('click', closeFileBrowser); }
if (modalBackdrop) { modalBackdrop.addEventListener('click', closeFileBrowser); }

function openFileBrowser() { fileBrowserModal.classList.add('open'); loadDrives(); }
function closeFileBrowser() { fileBrowserModal.classList.remove('open'); selectedFile = null; updateSelectedFile(); }

async function loadDrives() {
    try {
        const response = await fetch('/api/drives');
        const data = await response.json();
        driveSelect.innerHTML = '<option value="">Select Drive</option>';
        data.drives.forEach(drive => {
            const option = document.createElement('option');
            option.value = drive.path;
            option.textContent = drive.name;
            driveSelect.appendChild(option);
        });
        loadFiles('');
    } catch (error) {
        showToast('Failed to load drives', 'error');
    }
}

if (driveSelect) { driveSelect.addEventListener('change', () => { if (driveSelect.value) { loadFiles(driveSelect.value); } }); }
if (goUpBtn) { goUpBtn.addEventListener('click', () => { if (parentPath) { loadFiles(parentPath); } }); }
if (goPathBtn) { goPathBtn.addEventListener('click', () => { if (pathInput.value.trim()) { loadFiles(pathInput.value.trim()); } }); }
if (pathInput) { pathInput.addEventListener('keydown', (e) => { if (e.key === 'Enter') { loadFiles(pathInput.value.trim()); } }); }

async function loadFiles(path) {
    fileList.innerHTML = '<div class="file-list-loading">Loading...</div>';
    try {
        const url = path ? `/api/files?path=${encodeURIComponent(path)}` : '/api/files';
        const response = await fetch(url);
        const data = await response.json();
        if (data.error) {
            fileList.innerHTML = `<div class="file-list-loading">Error: ${data.error}</div>`;
            showToast(data.error, 'error');
            return;
        }
        currentPath = data.currentPath;
        parentPath = data.parentPath;
        pathInput.value = currentPath;
        renderFileList(data.items);
    } catch (error) {
        fileList.innerHTML = '<div class="file-list-loading">Failed to load files</div>';
        showToast('Failed to load files', 'error');
    }
}

function renderFileList(items) {
    if (items.length === 0) {
        fileList.innerHTML = '<div class="file-list-loading">Empty folder</div>';
        return;
    }
    fileList.innerHTML = items.map(item => `<div class="file-item ${item.isDirectory ? 'directory' : ''}" data-path="${escapeHtml(item.path)}" data-is-dir="${item.isDirectory}" data-name="${escapeHtml(item.name)}"><div class="file-icon">${getFileIcon(item)}</div><div class="file-info"><div class="file-name">${escapeHtml(item.name)}</div><div class="file-meta">${item.isDirectory ? 'Folder' : formatFileSize(item.size)}</div></div></div>`).join('');
    fileList.querySelectorAll('.file-item').forEach(item => {
        item.addEventListener('click', () => handleFileClick(item));
        item.addEventListener('dblclick', () => handleFileDoubleClick(item));
    });
}

function getFileIcon(item) { return item.isDirectory ? '' : ''; }
function formatFileSize(bytes) { if (bytes === 0) return '0 B'; const k = 1024; const sizes = ['B', 'KB', 'MB', 'GB']; const i = Math.floor(Math.log(bytes) / Math.log(k)); return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]; }

function handleFileClick(item) {
    fileList.querySelectorAll('.file-item.selected').forEach(el => el.classList.remove('selected'));
    item.classList.add('selected');
    const isDir = item.dataset.isDir === 'true';
    const path = item.dataset.path;
    const name = item.dataset.name;
    if (!isDir) {
        selectedFile = { path, name };
        updateSelectedFile();
        loadFilePreview(path);
    } else {
        selectedFile = null;
        updateSelectedFile();
        filePreviewContent.innerHTML = '<p class="preview-placeholder">Select a file to preview</p>';
        previewFileName.textContent = 'Folder selected';
    }
}

function handleFileDoubleClick(item) {
    const isDir = item.dataset.isDir === 'true';
    const path = item.dataset.path;
    if (isDir) { loadFiles(path); } else { selectFileForChat(); }
}

async function loadFilePreview(path) {
    previewFileName.textContent = 'Loading...';
    filePreviewContent.innerHTML = '<p class="preview-placeholder">Loading preview...</p>';
    try {
        const response = await fetch(`/api/file/read?path=${encodeURIComponent(path)}`);
        const data = await response.json();
        if (data.error) {
            previewFileName.textContent = 'Error';
            filePreviewContent.innerHTML = `<p class="preview-placeholder">${data.error}</p>`;
            return;
        }
        previewFileName.textContent = data.filename;
        filePreviewContent.innerHTML = `<pre>${escapeHtml(data.content)}</pre>`;
    } catch (error) {
        previewFileName.textContent = 'Error';
        filePreviewContent.innerHTML = '<p class="preview-placeholder">Failed to load preview</p>';
    }
}

function updateSelectedFile() {
    if (selectedFile) {
        selectedPathEl.textContent = selectedFile.path;
        selectFileBtn.disabled = false;
    } else {
        selectedPathEl.textContent = 'No file selected';
        selectFileBtn.disabled = true;
    }
}

if (useFileBtn) { useFileBtn.addEventListener('click', () => { if (selectedFile) { const content = filePreviewContent.querySelector('pre')?.textContent || ''; userInput.value = `Here's the content of ${selectedFile.name}:\n\n\`\`\`\n${content}\n\`\`\`\n\nPlease analyze this code.`; closeFileBrowser(); userInput.focus(); showToast('File content added to chat', 'success'); } }); }
if (copyPathBtn) { copyPathBtn.addEventListener('click', () => { if (selectedFile) { navigator.clipboard.writeText(selectedFile.path); showToast('Path copied to clipboard', 'success'); } }); }
if (selectFileBtn) { selectFileBtn.addEventListener('click', selectFileForChat); }

function selectFileForChat() { if (selectedFile) { loadFileInEditor(selectedFile.path); closeFileBrowser(); showToast(`Loaded ${selectedFile.name} into editor`, 'success'); } }
document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && fileBrowserModal.classList.contains('open')) { closeFileBrowser(); } });

// Editor
const toggleEditorBtn = document.getElementById('toggleEditorBtn'), editorPanel = document.getElementById('editorPanel'), mainContent = document.getElementById('mainContent'), editorFileName = document.getElementById('editorFileName'), editorPath = document.getElementById('editorPath'), codeEditor = document.getElementById('codeEditor'), lineNumbers = document.getElementById('lineNumbers'), editorSaveBtn = document.getElementById('editorSaveBtn'), editorBrowseBtn = document.getElementById('editorBrowseBtn'), editorStatus = document.getElementById('editorStatus'), editorInfo = document.getElementById('editorInfo');
let currentEditorFile = null, originalContent = '', isEditorModified = false;

if (toggleEditorBtn) { toggleEditorBtn.addEventListener('click', toggleEditor); }

function toggleEditor() { editorPanel.classList.toggle('open'); mainContent.classList.toggle('editor-open'); }
function openEditor() { editorPanel.classList.add('open'); mainContent.classList.add('editor-open'); }
function closeEditor() { editorPanel.classList.remove('open'); mainContent.classList.remove('editor-open'); }

async function loadFileInEditor(path) {
    editorStatus.textContent = 'Loading...';
    editorStatus.className = 'editor-status';
    try {
        const response = await fetch(`/api/file/read?path=${encodeURIComponent(path)}`);
        const data = await response.json();
        if (data.error) {
            showToast(data.error, 'error');
            editorStatus.textContent = 'Error loading file';
            return;
        }
        currentEditorFile = path;
        originalContent = data.content;
        codeEditor.value = data.content;
        editorPath.value = path;
        editorFileName.textContent = data.filename;
        updateLineNumbers();
        updateEditorInfo();
        setEditorModified(false);
        openEditor();
        editorStatus.textContent = 'Ready';
        showToast(`Opened ${data.filename}`, 'success');
    } catch (error) {
        showToast('Failed to load file', 'error');
        editorStatus.textContent = 'Error';
    }
}

function updateLineNumbers() { const lines = codeEditor.value.split('\n'); const numbers = lines.map((_, i) => i + 1).join('\n'); lineNumbers.textContent = numbers; }
function updateEditorInfo() { const lines = codeEditor.value.split('\n').length; const chars = codeEditor.value.length; editorInfo.textContent = `Lines: ${lines} | Chars: ${chars}`; }
function setEditorModified(modified) { isEditorModified = modified; editorSaveBtn.disabled = !modified; editorStatus.className = modified ? 'editor-status modified' : 'editor-status'; editorStatus.textContent = modified ? 'Modified' : 'Ready'; }

if (codeEditor) {
    codeEditor.addEventListener('input', () => {
        updateLineNumbers();
        updateEditorInfo();
        if (codeEditor.value !== originalContent) { setEditorModified(true); } else { setEditorModified(false); }
    });
    codeEditor.addEventListener('scroll', () => { lineNumbers.scrollTop = codeEditor.scrollTop; });
    codeEditor.addEventListener('keydown', (e) => {
        if (e.key === 'Tab') {
            e.preventDefault();
            const start = codeEditor.selectionStart;
            const end = codeEditor.selectionEnd;
            codeEditor.value = codeEditor.value.substring(0, start) + '    ' + codeEditor.value.substring(end);
            codeEditor.selectionStart = codeEditor.selectionEnd = start + 4;
            updateLineNumbers();
            setEditorModified(true);
        }
        if (e.key === 's' && (e.ctrlKey || e.metaKey)) {
            e.preventDefault();
            saveEditorFile();
        }
    });
}

async function saveEditorFile() {
    if (!currentEditorFile || !isEditorModified) return;
    editorStatus.textContent = 'Saving...';
    try {
        const response = await fetch('/api/file/write', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ path: currentEditorFile, content: codeEditor.value })
        });
        const data = await response.json();
        if (data.error) {
            showToast(data.error, 'error');
            editorStatus.textContent = 'Save failed';
            return;
        }
        originalContent = codeEditor.value;
        setEditorModified(false);
        editorStatus.className = 'editor-status saved';
        editorStatus.textContent = 'Saved';
        showToast('File saved successfully', 'success');
        setTimeout(() => {
            if (!isEditorModified) {
                editorStatus.className = 'editor-status';
                editorStatus.textContent = 'Ready';
            }
        }, 2000);
    } catch (error) {
        showToast('Failed to save file', 'error');
        editorStatus.textContent = 'Save failed';
    }
}

if (editorSaveBtn) { editorSaveBtn.addEventListener('click', saveEditorFile); }
if (editorBrowseBtn) { editorBrowseBtn.addEventListener('click', () => { openFileBrowser(); }); }

window.loadFileInEditor = loadFileInEditor;
window.toggleEditor = toggleEditor;

// MCP Tools
async function loadMCPTools() {
    if (!mcpToolsList) return;
    try {
        const response = await fetch('/api/mcp/tools');
        const data = await response.json();
        if (data.tools && data.tools.length > 0) {
            mcpToolsList.innerHTML = data.tools.map(tool =>
                `<div class="mcp-tool-item" onclick="useMCPTool('${tool.name}')">
                    <span class="tool-name">${tool.name}</span>
                    <span class="tool-desc">${tool.description}</span>
                </div>`
            ).join('');
        } else {
            mcpToolsList.innerHTML = '<div class="mcp-tool-item">No tools available</div>';
        }
    } catch (error) {
        mcpToolsList.innerHTML = '<div class="mcp-tool-item">Error loading tools</div>';
    }
}

function useMCPTool(toolName) {
    const prompts = {
        'read_file': 'Read file: ',
        'write_file': 'Write to file: ',
        'delete_file': 'Delete file: ',
        'list_files': 'List files in: ',
        'run_python': 'Run Python code: '
    };
    userInput.value = prompts[toolName] || `Use ${toolName}: `;
    userInput.focus();
    mcpDropdown.classList.remove('open');
}

window.useMCPTool = useMCPTool;

// Diff Modal
const diffModal = document.getElementById('diffModal');
const diffModalBackdrop = document.getElementById('diffModalBackdrop');
const diffFileName = document.getElementById('diffFileName');
const diffSummary = document.getElementById('diffSummary');
const diffView = document.getElementById('diffView');
const diffAcceptBtn = document.getElementById('diffAcceptBtn');
const diffRejectBtn = document.getElementById('diffRejectBtn');
let pendingDiffData = null;

function showDiffModal(originalCode, newCode, fileName, summary) {
    if (!diffModal) return;
    pendingDiffData = { originalCode, newCode, fileName };
    if (diffFileName) diffFileName.textContent = fileName || 'Code Changes';
    if (diffSummary) diffSummary.innerHTML = `<strong>Changes:</strong> ${escapeHtml(summary || 'Code modifications')}`;
    if (diffView) {
        const diffHtml = generateSimpleDiff(originalCode, newCode);
        diffView.innerHTML = diffHtml;
    }
    diffModal.classList.add('open');
}

function generateSimpleDiff(oldCode, newCode) {
    const oldLines = (oldCode || '').split('\n');
    const newLines = (newCode || '').split('\n');
    let html = '<div class="diff-container">';
    html += '<div class="diff-header"><span class="diff-old">Original</span> - <span class="diff-new">New</span></div>';
    html += '<div class="diff-view">';
    const maxLines = Math.max(oldLines.length, newLines.length);
    let oldNum = 1;
    let newNum = 1;
    for (let i = 0; i < Math.min(maxLines, 100); i++) {
        const oldLine = oldLines[i];
        const newLine = newLines[i];
        if (oldLine === newLine) {
            html += `<div class="diff-line unchanged"><span class="diff-line-number">${oldNum}</span><span class="diff-line-content">${escapeHtml(newLine) || ' '}</span></div>`;
            oldNum++;
            newNum++;
        } else {
            if (oldLine !== undefined) {
                html += `<div class="diff-line removed"><span class="diff-line-number">${oldNum}</span><span class="diff-line-content">${escapeHtml(oldLine) || ' '}</span></div>`;
                oldNum++;
            }
            if (newLine !== undefined) {
                html += `<div class="diff-line added"><span class="diff-line-number">${newNum}</span><span class="diff-line-content">${escapeHtml(newLine) || ' '}</span></div>`;
                newNum++;
            }
        }
    }
    if (maxLines > 100) {
        html += `<div class="diff-line unchanged"><span class="diff-line-number">...</span><span class="diff-line-content">(${maxLines - 100} more lines)</span></div>`;
    }
    html += '</div></div>';
    return html;
}

function closeDiffModal() {
    if (diffModal) { diffModal.classList.remove('open'); }
    pendingDiffData = null;
}

async function acceptDiffChanges() {
    if (!pendingDiffData) return;
    const filePath = currentEditorFile || pendingDiffData.fileName;
    const newCode = pendingDiffData.newCode;
    if (diffAcceptBtn) {
        diffAcceptBtn.disabled = true;
        diffAcceptBtn.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/></svg>Applying...';
    }
    try {
        await fetch('/api/confirm', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: 'accept', action_data: { path: filePath, code: newCode } })
        });
        if (codeEditor && newCode) {
            codeEditor.value = newCode;
            updateLineNumbers();
            updateEditorInfo();
            setEditorModified(true);
            editorStatus.textContent = 'Changes applied - Click Save to write file';
            editorStatus.className = 'editor-status modified';
            codeEditor.scrollTop = 0;
            codeEditor.classList.add('editor-pulse');
            setTimeout(() => codeEditor.classList.remove('editor-pulse'), 2000);
        }
        addMessage('Changes applied to editor. Click Save to write to file.', 'bot');
        saveChatSession();
        showToast('Changes applied to editor. Click Save to write to file.', 'success');
    } catch (error) {
        if (codeEditor && newCode) {
            codeEditor.value = newCode;
            updateLineNumbers();
            updateEditorInfo();
            setEditorModified(true);
            editorStatus.textContent = 'Changes applied - Click Save to write file';
            editorStatus.className = 'editor-status modified';
        }
        showToast('Changes applied to editor.', 'success');
    } finally {
        if (diffAcceptBtn) {
            diffAcceptBtn.disabled = false;
            diffAcceptBtn.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>Accept';
        }
        closeDiffModal();
    }
}

async function rejectDiffChanges() {
    try {
        await fetch('/api/confirm', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: 'reject', action_data: {} })
        });
        showToast('Changes rejected', 'info');
    } catch (error) {
        console.error('Error rejecting changes:', error);
    } finally {
        closeDiffModal();
    }
}

if (diffAcceptBtn) diffAcceptBtn.addEventListener('click', acceptDiffChanges);
if (diffRejectBtn) diffRejectBtn.addEventListener('click', rejectDiffChanges);
if (diffModalBackdrop) diffModalBackdrop.addEventListener('click', closeDiffModal);

// Handle confirm actions (Accept/Reject buttons in chat)
window.handleConfirmAction = async function (action, actionData) {
    // Handle delete action
    if (action === 'accept' && actionData && actionData.type === 'delete') {
        try {
            const response = await fetch('/api/confirm', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action: 'accept', action_data: actionData })
            });
            const data = await response.json();
            if (data.success) {
                addMessage(data.response || 'File deleted successfully.', 'bot');
                showToast(data.message || 'File deleted!', 'success');
                saveChatSession();
            } else {
                addMessage('Error: ' + (data.error || 'Delete failed'), 'bot');
                showToast(data.error || 'Delete failed', 'error');
            }
        } catch (error) {
            showToast('Error: ' + error.message, 'error');
        }
        return;
    }

    // Handle run_python action
    if (action === 'accept' && actionData && actionData.type === 'run_python') {
        try {
            const response = await fetch('/api/confirm', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action: 'accept', action_data: actionData })
            });
            const data = await response.json();
            if (data.success) {
                addMessage(data.response || 'Code executed.', 'bot');
                showToast('Python code executed!', 'success');
                saveChatSession();
            } else {
                addMessage('Error: ' + (data.error || 'Execution failed'), 'bot');
                showToast(data.error || 'Execution failed', 'error');
            }
        } catch (error) {
            showToast('Error: ' + error.message, 'error');
        }
        return;
    }

    // Handle code edit action
    if (action === 'accept' && actionData && actionData.code) {
        const originalCode = codeEditor ? codeEditor.value : '';
        showDiffModal(originalCode, actionData.code, currentEditorFile || actionData.path || 'Untitled', actionData.changes || 'Code changes');
    } else if (action === 'reject') {
        showToast('Action rejected', 'info');
    }
};

window.showDiffModal = showDiffModal;

// MCP dropdown toggle
if (attachBtn) {
    attachBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        mcpDropdown.classList.toggle('open');
        if (mcpDropdown.classList.contains('open')) {
            loadMCPTools();
        }
    });
}
document.addEventListener('click', (e) => {
    if (mcpDropdown && !mcpDropdown.contains(e.target) && !attachBtn.contains(e.target)) {
        mcpDropdown.classList.remove('open');
    }
});

// Editor control buttons
const closeEditorBtn = document.getElementById('closeEditorBtn');
const disconnectEditorBtn = document.getElementById('disconnectEditorBtn');
const clearEditorBtn = document.getElementById('clearEditorBtn');

if (closeEditorBtn) {
    closeEditorBtn.addEventListener('click', () => {
        closeEditor();
        showToast('Editor panel closed', 'info');
    });
}

if (disconnectEditorBtn) {
    disconnectEditorBtn.addEventListener('click', () => {
        editorSynced = !editorSynced;
        if (editorSynced) {
            disconnectEditorBtn.classList.remove('active');
            disconnectEditorBtn.title = 'Disconnect from chat (stop auto-sync)';
            showToast('Editor connected - will auto-update from chat', 'success');
        } else {
            disconnectEditorBtn.classList.add('active');
            disconnectEditorBtn.title = 'Connect to chat (enable auto-sync)';
            showToast('Editor disconnected - chat wont update editor', 'info');
        }
    });
}

if (clearEditorBtn) {
    clearEditorBtn.addEventListener('click', () => {
        if (codeEditor) {
            if (isEditorModified) {
                if (!confirm('You have unsaved changes. Clear anyway?')) {
                    return;
                }
            }
            codeEditor.value = '';
            currentEditorFile = null;
            originalContent = '';
            editorPath.value = '';
            editorFileName.textContent = 'No file open';
            updateLineNumbers();
            updateEditorInfo();
            setEditorModified(false);
            editorStatus.textContent = 'Cleared';
            editorStatus.className = 'editor-status';
            showToast('Editor cleared', 'info');
        }
    });
}

window.editorSynced = () => editorSynced;
window.closeEditor = closeEditor;
window.openEditor = openEditor;
