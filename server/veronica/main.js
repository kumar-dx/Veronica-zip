const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const fetch = (...args) => import('node-fetch').then(({ default: fetch }) => fetch(...args));
require('dotenv').config({ path: path.join(__dirname, '.env') });

let pythonProcess = null;
let noDataTimeout = null;

function log(message) {
  // Log message handled by main process
}

function createWindow() {
  log("Creating Electron window...");
  
  const mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    resizable: true,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js'),
    },
    icon: path.join(__dirname, 'assets', process.platform === 'darwin' ? 'icon.icns' : 'icon.ico'),
  });

  mainWindow.loadFile(path.join(__dirname, 'src', 'index.html'));
  setupIpcHandlers(mainWindow);
}

function setupIpcHandlers(mainWindow) {
  log("Setting up IPC handlers...");
  
  ipcMain.handle('start-python', async () => startPythonProcess(mainWindow));
  ipcMain.handle('stop-python', async () => stopPythonProcess(mainWindow));
  ipcMain.handle('fetch-visitor-count', async () => fetchVisitorCount(mainWindow));
}

async function startPythonProcess(mainWindow) {
  log("Starting Python process...");
  
  return new Promise((resolve, reject) => {
    if (pythonProcess) {
      log("Python process already running.");
      reject(new Error('Python process already running'));
      return;
    }

    try {
      const projectRoot = path.join(__dirname);
      const pythonCommand = process.env.PYTHON_PATH || (process.platform === 'win32' ? 'python' : 'python3');
      const scriptPath = path.join(projectRoot,'main.py');

      log(`Executing Python: ${pythonCommand} ${scriptPath}`);

      const env = {
        ...process.env,
        PYTHONPATH: projectRoot + (process.env.PYTHONPATH ? path.delimiter + process.env.PYTHONPATH : ''),
      };

      pythonProcess = spawn(pythonCommand, [scriptPath], {
        cwd: projectRoot,
        env: env,
        stdio: ['pipe', 'pipe', 'pipe'],
      });

      let dataBuffer = '';
      let lastDataTime = Date.now();
      let initializing = true;

      // Initial connection timeout
      noDataTimeout = setTimeout(() => {
        if (initializing) {
          log("Waiting for camera connection...");
          mainWindow.webContents.send('process-status', {
            type: 'info',
            data: 'Establishing camera connection...',
          });
        }
      }, 10000); // Give more time for initial connection

      // Monitor data stream
      const checkDataStream = () => {
        const timeSinceLastData = Date.now() - lastDataTime;
        if (timeSinceLastData > 5000 && !initializing) {
          log("Camera stream appears to be down.");
          mainWindow.webContents.send('process-status', {
            type: 'warning',
            data: 'Camera stream interrupted. Attempting to reconnect...',
          });
        }
      };

      // Start stream monitoring
      const streamMonitor = setInterval(checkDataStream, 5000);

      pythonProcess.stdout.on('data', (data) => {
        const output = data.toString().trim();
        log(`Python stdout: ${output}`);
        
        // Update last data time
        lastDataTime = Date.now();
        
        // If we're getting data, we're no longer initializing
        if (initializing && output.includes('Successfully connected')) {
          initializing = false;
          clearTimeout(noDataTimeout);
          mainWindow.webContents.send('process-status', {
            type: 'success',
            data: 'Camera connection established successfully.',
          });
        }

        dataBuffer += data.toString();

        // Process the Python output
        const lines = dataBuffer.split('\n');
        dataBuffer = lines.pop(); // Keep the last incomplete line in the buffer
        
        for (const line of lines) {
          try {
            const trimmedLine = line.trim();
            if (trimmedLine) {
              // Try to parse as JSON first
              try {
              const jsonData = JSON.parse(trimmedLine);
              if (jsonData.type === 'frame') {
                // Send frame data through stream-data channel
                mainWindow.webContents.send('stream-data', jsonData.data);
              } else {
                // Send other status updates through process-status channel
                mainWindow.webContents.send('process-status', {
                  type: 'data',
                  data: jsonData
                });
              }
              } catch {
                // If not JSON, send as plain text
                mainWindow.webContents.send('process-status', {
                  type: 'info',
                  data: trimmedLine
                });
              }
            }
          } catch (error) {
            log(`Error processing Python output: ${error.message}`);
          }
        }
      });

      pythonProcess.stderr.on('data', (data) => {
        log(`Python stderr: ${data.toString().trim()}`);
        mainWindow.webContents.send('process-status', {
          type: 'stderr',
          data: data.toString(),
        });
      });

      pythonProcess.on('error', (error) => {
        log(`Python process error: ${error.message}`);
        clearTimeout(noDataTimeout);
        pythonProcess = null;
        reject(error);
      });

      pythonProcess.on('close', (code) => {
        log(`Python process closed with code ${code}`);
        clearTimeout(noDataTimeout);
        clearInterval(streamMonitor);
        pythonProcess = null;
        mainWindow.webContents.send('process-status', { type: 'exit', code });
      });

      resolve({ success: true });
    } catch (error) {
      log(`Error starting Python: ${error.message}`);
      pythonProcess = null;
      reject(error);
    }
  });
}

async function stopPythonProcess(mainWindow) {
  log("Stopping Python process...");

  return new Promise((resolve, reject) => {
    if (!pythonProcess) {
      log("No Python process to stop.");
      resolve({ success: true });
      return;
    }

    try {
      pythonProcess.kill('SIGTERM');
      pythonProcess.on('close', () => {
        log("Python process stopped.");
        pythonProcess = null;
        mainWindow.webContents.send('process-status', {
          type: 'info',
          data: 'Camera stream stopped. Starting face recognition...',
        });

        startFaceRecognition(mainWindow);
        resolve({ success: true });
      });
    } catch (error) {
      log(`Error stopping Python: ${error.message}`);
      pythonProcess = null;
      reject(error);
    }
  });
}

function startFaceRecognition(mainWindow) {
  log("Starting face recognition...");

  try {
    const projectRoot = path.join(__dirname);
    const scriptPath = path.join(projectRoot,'face_rekognition.py');
    const pythonCommand = process.env.PYTHON_PATH || (process.platform === 'win32' ? 'python' : 'python3');

    log(`Executing face recognition: ${pythonCommand} ${scriptPath}`);
    const faceProcess = spawn(pythonCommand, [scriptPath], { cwd: projectRoot, env: process.env, stdio: ['pipe', 'pipe', 'pipe'] });

    faceProcess.stdout.on('data', (data) => {
      log(`Face recognition stdout: ${data.toString().trim()}`);
      mainWindow.webContents.send('recognition-status', { type: 'info', data: data.toString().trim() });
    });

    faceProcess.stderr.on('data', (data) => {
      log(`Face recognition stderr: ${data.toString().trim()}`);
      mainWindow.webContents.send('recognition-status', { type: 'error', data: data.toString().trim() });
    });

    faceProcess.on('close', (code) => {
      log(`Face recognition process exited with code ${code}`);
      if (code === 0) {
        mainWindow.webContents.send('recognition-status', { 
          type: 'success', 
          data: 'Face recognition completed successfully' 
        });
      } else {
        mainWindow.webContents.send('recognition-status', { 
          type: 'error', 
          data: `Face recognition failed with code ${code}` 
        });
      }
    });
  } catch (error) {
    log(`Error starting face recognition: ${error.message}`);
  }
}

async function fetchVisitorCount(mainWindow) {
  log("Fetching visitor count...");

  try {
    const apiEndpoint = process.env.API_ENDPOINT_BASE_URL;
    const storeId = process.env.STORE_ID;
    if (!apiEndpoint) throw new Error('API endpoint not configured');

    const today = new Date().toISOString().split('T')[0];
    const url = `${apiEndpoint}/api/v1/analytics/stores/metrics/?store_id=${storeId}&date=${today}`;

    log(`API Request: ${url}`);
    const response = await fetch(url, { method: 'GET', headers: { 'Accept': 'application/json', 'X-API-KEY': process.env.API_KEY } });
    const data = await response.json();

    if (response.ok && data.status === 'success' && data.data) {
      log(`Visitor count: ${data.data.unique_visitors}`);
      mainWindow.webContents.send('fetch-count-status', { type: 'success', data: { count: data.data.unique_visitors, date: data.data.date } });
    } else {
      throw new Error('Invalid API response format');
    }
  } catch (error) {
    log(`API Error: ${error.message}`);
    mainWindow.webContents.send('fetch-count-status', { type: 'error', data: `Failed to fetch visitor count: ${error.message}` });
  }
}

app.whenReady().then(createWindow);
app.on('window-all-closed', () => {
  if (pythonProcess) {
    pythonProcess.kill();
    pythonProcess = null;
  }
  if (process.platform !== 'darwin') app.quit();
});
app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow();
});
