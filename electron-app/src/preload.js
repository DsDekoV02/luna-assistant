/**
 * Luna JARVIS - Electron Preload Script
 * Bridges main process and renderer with secure IPC.
 */

const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('lunaAPI', {
    // Send messages
    sendMessage: (text) => ipcRenderer.invoke('send-message', text),
    sendAudio: (audioBase64) => ipcRenderer.invoke('send-audio', audioBase64),
    setMode: (mode) => ipcRenderer.invoke('set-mode', mode),
    getStatus: () => ipcRenderer.invoke('get-status'),
    toggleClickthrough: (enabled) => ipcRenderer.invoke('toggle-clickthrough', enabled),

    // Streaming audio
    audioStart: () => ipcRenderer.invoke('audio-start'),
    audioChunk: (chunkB64, format) => ipcRenderer.invoke('audio-chunk', chunkB64, format),
    audioStop: () => ipcRenderer.invoke('audio-stop'),

    // Receive messages
    onMessage: (callback) => {
        ipcRenderer.on('ws-message', (event, msg) => callback(msg));
    },
    onStatusChange: (callback) => {
        ipcRenderer.on('ws-status', (event, status) => callback(status));
    },

    // Window controls
    minimize: () => ipcRenderer.invoke('window-minimize'),
    close: () => ipcRenderer.invoke('window-close'),
});
