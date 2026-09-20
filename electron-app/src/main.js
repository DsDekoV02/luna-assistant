/**
 * Luna JARVIS - Electron Main Process
 * Creates a floating, transparent overlay window.
 */

const { app, BrowserWindow, ipcMain, globalShortcut, Tray, Menu, nativeImage } = require('electron');
const path = require('path');
const WebSocket = require('ws');

// ── Configuration ────────────────────────────────────────────────

const CONFIG = {
    wsUrl: 'ws://127.0.0.1:8765/ws',
    overlayWidth: 420,
    overlayHeight: 700,
    avatarSize: 180,
    devMode: process.argv.includes('--dev'),
};

// ── State ────────────────────────────────────────────────────────

let mainWindow = null;
let tray = null;
let ws = null;
let isConnected = false;
let isOverlayVisible = true;
let reconnectAttempts = 0;

// ── Window Creation ──────────────────────────────────────────────

function createWindow() {
    mainWindow = new BrowserWindow({
        width: CONFIG.overlayWidth,
        height: CONFIG.overlayHeight,
        x: undefined,
        y: undefined,
        frame: false,
        transparent: true,
        alwaysOnTop: true,
        skipTaskbar: true,
        resizable: true,
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true,
            preload: path.join(__dirname, 'preload.js'),
        },
    });

    mainWindow.loadFile(path.join(__dirname, 'index.html'));

    if (CONFIG.devMode) {
        mainWindow.webContents.openDevTools({ mode: 'detach' });
    }

    mainWindow.on('closed', () => {
        mainWindow = null;
    });

    // Make window click-through on transparent areas
    mainWindow.setIgnoreMouseEvents(false);
}

// ── System Tray ──────────────────────────────────────────────────

function createTray() {
    // Create a simple moon icon
    const icon = nativeImage.createFromDataURL(
        'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAAB4SURBVFhH7c4xDQAgDATRHpD4dwMaUIAzSECAPeyky+Yv6X77JjIDYgbEDIgZEDMgZkDMgJgBMQNiBsQMiBkQMyBmQMyAmAExA2IGxAyIGRAzIGZAzICYATEDYgbEDIgZEDMgZkDMgJgBMQNiBsQMiBkQW0Z8A3VmBCdl5i9RAAAAAElFTkSuQmCC'
    );
    tray = new Tray(icon);

    const contextMenu = Menu.buildFromTemplate([
        { label: '🌙 Luna JARVIS', enabled: false },
        { type: 'separator' },
        { label: 'Mostrar/Ocultar', click: toggleOverlay },
        { label: 'Reconectar WS', click: connectWS },
        { type: 'separator' },
        { label: 'Salir', click: () => app.quit() },
    ]);

    tray.setToolTip('Luna JARVIS');
    tray.setContextMenu(contextMenu);
    tray.on('click', toggleOverlay);
}

function toggleOverlay() {
    if (!mainWindow) return;

    if (isOverlayVisible) {
        mainWindow.hide();
    } else {
        mainWindow.show();
        mainWindow.focus();
    }
    isOverlayVisible = !isOverlayVisible;
}

// ── WebSocket Connection ─────────────────────────────────────────

function connectWS() {
    if (ws) {
        ws.close();
    }

    try {
        ws = new WebSocket(CONFIG.wsUrl);

        ws.on('open', () => {
            isConnected = true;
            reconnectAttempts = 0;
            console.log('✅ Connected to Luna JARVIS service');
            sendToRenderer('ws-status', { connected: true });
        });

        ws.on('message', (data) => {
            try {
                const msg = JSON.parse(data.toString());
                sendToRenderer('ws-message', msg);
            } catch (e) {
                console.error('WS parse error:', e);
            }
        });

        ws.on('close', () => {
            isConnected = false;
            console.log('❌ Disconnected from Luna JARVIS service');
            sendToRenderer('ws-status', { connected: false });

            // Auto-reconnect with exponential backoff (max 30s)
            const delay = Math.min(5000 * Math.pow(1.5, reconnectAttempts), 30000);
            reconnectAttempts++;
            console.log(`Reconnecting in ${Math.round(delay/1000)}s (attempt ${reconnectAttempts})...`);
            setTimeout(connectWS, delay);
        });

        ws.on('error', (err) => {
            console.error('WS error:', err.message);
            isConnected = false;
        });

    } catch (e) {
        console.error('WS connection failed:', e);
        setTimeout(connectWS, 5000);
    }
}

function sendToRenderer(channel, data) {
    if (mainWindow && mainWindow.webContents) {
        mainWindow.webContents.send(channel, data);
    }
}

function sendToWS(data) {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify(data));
    }
}

// ── IPC Handlers ─────────────────────────────────────────────────

ipcMain.handle('send-message', async (event, text) => {
    sendToWS({ type: 'text', content: text });
});

ipcMain.handle('send-audio', async (event, audioBase64) => {
    sendToWS({ type: 'audio', data: audioBase64, format: 'wav' });
});

// Streaming audio IPC handlers
ipcMain.handle('audio-start', async () => {
    sendToWS({ type: 'audio_start' });
});

ipcMain.handle('audio-chunk', async (event, chunkB64, format) => {
    sendToWS({ type: 'audio_chunk', data: chunkB64, format: format || 'wav' });
});

ipcMain.handle('audio-stop', async () => {
    sendToWS({ type: 'audio_stop' });
});

ipcMain.handle('set-mode', async (event, mode) => {
    sendToWS({ type: 'mode', mode: mode });
});

ipcMain.handle('get-status', async () => {
    return { connected: isConnected };
});

ipcMain.handle('toggle-clickthrough', async (event, enabled) => {
    if (mainWindow) {
        mainWindow.setIgnoreMouseEvents(enabled, { forward: true });
    }
});

// ── App Lifecycle ────────────────────────────────────────────────

// ── Window Control Handlers ───────────────────────────────────────

ipcMain.handle('window-minimize', async () => {
    if (mainWindow) {
        mainWindow.minimize();
    }
});

ipcMain.handle('window-close', async () => {
    if (mainWindow) {
        mainWindow.hide();
    }
    isOverlayVisible = false;
});


app.whenReady().then(() => {
    createWindow();
    createTray();
    connectWS();

    // Global hotkey to toggle overlay
    globalShortcut.register('Alt+L', toggleOverlay);

    // Periodic health check every 60 seconds
    setInterval(() => {
        if (!isConnected) return;
        sendToWS({ type: 'command', command: 'datetime', params: {} });
    }, 60000);
});

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
        createWindow();
    }
});

app.on('will-quit', () => {
    globalShortcut.unregisterAll();
    if (ws) ws.close();
});
