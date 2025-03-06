const { contextBridge, ipcRenderer } = require('electron');

// Remove event listeners when they're no longer needed
const cleanupEvents = new Set();

function safeCallback(channel, callback) {
    const wrappedCallback = (event, ...args) => callback(event, ...args);
    cleanupEvents.add(() => ipcRenderer.removeListener(channel, wrappedCallback));
    return wrappedCallback;
}

// Constants
const constants = {
    API_ENDPOINT_BASE_URL: process.env.API_ENDPOINT_BASE_URL,
    API_KEY: process.env.API_KEY,
    STORE_ID: process.env.STORE_ID
};

// Expose protected methods that allow the renderer process to use
// the ipcRenderer without exposing the entire object
contextBridge.exposeInMainWorld(
  'api', {
    // Constants
    constants,
    
    // Python Process Control
    startPythonProcess: () => ipcRenderer.invoke('start-python'),
    stopPythonProcess: () => ipcRenderer.invoke('stop-python'),
    
    // Stream Status
    onStreamData: (callback) => {
        const wrapped = safeCallback('stream-data', callback);
        ipcRenderer.on('stream-data', wrapped);
    },
    onStreamError: (callback) => {
        const wrapped = safeCallback('stream-error', callback);
        ipcRenderer.on('stream-error', wrapped);
    },
    
    // Process Status
    onProcessStatus: (callback) => {
        const wrapped = safeCallback('process-status', callback);
        ipcRenderer.on('process-status', wrapped);
    },
    
    // Face Recognition Status
    onRecognitionStatus: (callback) => {
        const wrapped = safeCallback('recognition-status', callback);
        ipcRenderer.on('recognition-status', wrapped);
    },
    
    // Fetch Count
    fetchVisitorCount: () => ipcRenderer.invoke('fetch-visitor-count'),
    onFetchCountStatus: (callback) => {
        const wrapped = safeCallback('fetch-count-status', callback);
        ipcRenderer.on('fetch-count-status', wrapped);
    },
    
    // Cleanup
    cleanup: () => {
        cleanupEvents.forEach(cleanup => cleanup());
        cleanupEvents.clear();
    }
  }
);

// Clean up event listeners when window is unloaded
window.addEventListener('unload', () => {
    cleanupEvents.forEach(cleanup => cleanup());
    cleanupEvents.clear();
});
