// Get constants from preload bridge
const { API_ENDPOINT_BASE_URL, API_KEY, STORE_ID } = window.api.constants;

// Settings Modal Elements
const settingsModal = document.getElementById('settings-modal');
const settingsButton = document.querySelector('.stream-controls .icon-button[title="Settings"]');
const settingsCloseButton = settingsModal.querySelector('.close-button');
const cameraConfigForm = document.getElementById('camera-config-form');

// Open settings modal
function openSettingsModal() {
    settingsModal.classList.add('active');
    // Fetch and populate current config if exists
    fetch(`${API_ENDPOINT_BASE_URL}/api/v1/analytics/stores/?store_id=${STORE_ID}`, {
        headers: {
            'X-API-KEY': API_KEY,
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success' && data.data?.camera_config) {
            const config = data.data.camera_config;
            document.getElementById('camera-ip').value = config.ip || '';
            document.getElementById('rtsp-port').value = config.rtsp_port || '';
            document.getElementById('username').value = config.username || '';
            document.getElementById('password').value = config.password || '';
            document.getElementById('main-stream').value = config.main_stream_path || '';
            document.getElementById('sub-stream').value = config.sub_stream_path || '';
            document.getElementById('max-retries').value = config.max_retries || 3;
            document.getElementById('retry-delay').value = config.retry_delay || 5;
            document.getElementById('rtsp-options').value = config.rtsp_env_options || 'rtsp_transport=tcp|max_delay=500000';
        }
    })
    .catch(error => console.error('Failed to fetch camera config:', error));
}

// Close settings modal
function closeSettingsModal() {
    settingsModal.classList.remove('active');
}

// Handle settings form submission
async function handleSettingsSubmit(event) {
    event.preventDefault();
    const submitButton = cameraConfigForm.querySelector('button[type="submit"]');
    submitButton.disabled = true;
    submitButton.innerHTML = '<span class="material-icons">hourglass_empty</span>Saving...';

    try {
        // First fetch store data
        const storeResponse = await fetch(`${API_ENDPOINT_BASE_URL}/api/v1/analytics/stores/?store_id=${STORE_ID}`, {
            headers: {
                'X-API-KEY': API_KEY,
                'Content-Type': 'application/json'
            }
        });
        const storeData = await storeResponse.json();
        
        if (!storeData.status === 'success' || !storeData.data?.name) {
            throw new Error('Failed to fetch store data');
        }

        const cameraConfig = {
            ip: document.getElementById('camera-ip').value,
            rtsp_port: document.getElementById('rtsp-port').value,
            username: document.getElementById('username').value,
            password: document.getElementById('password').value,
            main_stream_path: document.getElementById('main-stream').value,
            sub_stream_path: document.getElementById('sub-stream').value,
            max_retries: parseInt(document.getElementById('max-retries').value),
            retry_delay: parseInt(document.getElementById('retry-delay').value),
            rtsp_env_options: document.getElementById('rtsp-options').value
        };

        const response = await fetch(`${API_ENDPOINT_BASE_URL}/api/v1/analytics/stores/`, {
            method: 'POST',
            headers: {
                'X-API-KEY': API_KEY,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                store_id: STORE_ID,
                name: storeData.data.name,  // Use name from API
                camera_config: cameraConfig
            })
        });

        const data = await response.json();
        if (data.status === 'success') {
            closeSettingsModal();
        } else {
            throw new Error(data.message || 'Failed to save configuration');
        }
    } catch (error) {
        console.error('Failed to save camera config:', error);
        alert('Failed to save configuration: ' + error.message);
    } finally {
        submitButton.disabled = false;
        submitButton.innerHTML = '<span class="material-icons">save</span>Save Configuration';
    }
}

// Event listeners for settings modal
settingsButton.addEventListener('click', openSettingsModal);
settingsCloseButton.addEventListener('click', closeSettingsModal);
settingsModal.addEventListener('click', (e) => {
    if (e.target === settingsModal) {
        closeSettingsModal();
    }
});
cameraConfigForm.addEventListener('submit', handleSettingsSubmit);


// DOM Elements
const controlButton = document.getElementById('control-button');
const runtimeCounter = document.getElementById('runtime-counter');
const currentDate = document.getElementById('current-date');
const fetchCountButton = document.getElementById('fetch-count');
const visitorCount = document.getElementById('visitor-count');
const videoFeed = document.querySelector('.video-feed');
const fpsCounter = document.getElementById('fps-counter');
const statusIndicator = document.querySelector('.status-indicator');
const systemStatusText = document.querySelector('.system-status');

// Check internet connectivity and update status
function updateOnlineStatus() {
    const isOnline = navigator.onLine;
    systemStatusText.innerHTML = `
        <span class="material-icons" style="color: ${isOnline ? 'var(--success-color)' : 'var(--error-color)'}">
            ${isOnline ? 'cloud_done' : 'cloud_off'}
        </span>
        ${isOnline ? 'System Online' : 'System Offline'}
    `;
}

// Add online/offline event listeners
window.addEventListener('online', updateOnlineStatus);
window.addEventListener('offline', updateOnlineStatus);

// Initial check
updateOnlineStatus();

// Create image element for video display
const videoImage = document.createElement('img');
videoImage.style.width = '100%';
videoImage.style.height = '100%';
videoImage.style.objectFit = 'contain';
videoImage.style.display = 'none';
videoFeed.appendChild(videoImage);

// Loading indicator
const loadingText = document.createElement('div');
loadingText.innerHTML = '<span class="material-icons" style="font-size: 32px;">videocam</span><div>Connecting to camera...</div>';
loadingText.style.display = 'none';
loadingText.style.display = 'flex';
loadingText.style.flexDirection = 'column';
loadingText.style.alignItems = 'center';
loadingText.style.justifyContent = 'center';
loadingText.style.gap = '8px';
loadingText.style.position = 'absolute';
loadingText.style.left = '50%';
loadingText.style.top = '50%';
loadingText.style.transform = 'translate(-50%, -50%)';
loadingText.style.background = 'var(--glass-bg)';
loadingText.style.backdropFilter = 'blur(10px)';
loadingText.style.padding = '20px';
loadingText.style.borderRadius = '12px';
loadingText.style.boxShadow = 'var(--shadow-sm)';
loadingText.style.border = '1px solid rgba(255, 255, 255, 0.5)';
loadingText.style.textAlign = 'center';
loadingText.style.display = 'none';
videoFeed.appendChild(loadingText);

// Get start prompt element
const startPrompt = videoFeed.querySelector('.start-prompt');

// State
let isRunning = false;
let runtimeInterval = null;
let startTime = null;
let frameCount = 0;
let isProcessing = false;
let lastFrameTime = null;
let currentStep = 0;
const totalSteps = 3;

// Format time as HH:MM:SS
function formatTime(ms) {
    const seconds = Math.floor(ms / 1000);
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = seconds % 60;
    return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
}

// Update runtime counter
function updateRuntime() {
    if (startTime) {
        const elapsed = Date.now() - startTime;
        runtimeCounter.textContent = formatTime(elapsed);
    }
}

// Set current date
function setCurrentDate() {
    const date = new Date();
    const options = { day: 'numeric', month: 'long', year: 'numeric' };
    const formattedDate = date.toLocaleDateString('en-GB', options);
    const dateValue = document.getElementById('current-date-value');
    if (dateValue) {
        dateValue.textContent = formattedDate;
    }
}

// Update date immediately and then every minute
setCurrentDate();
setInterval(setCurrentDate, 60000);

// Update progress steps
function updateProgressSteps(step, status = 'active') {
    // Update progress bar
    const tracker = document.querySelector('.progress-tracker');
    if (tracker) {
        tracker.setAttribute('data-step', step);
    }
    
    // Update step icons
    for (let i = 1; i <= totalSteps; i++) {
        const stepEl = document.querySelector(`.progress-step[data-step="${i}"]`);
        if (stepEl) {
            stepEl.className = 'progress-step';
            
            // Mark previous steps as completed
            if (i < step) {
                stepEl.classList.add('completed');
            }
            // Mark current step as active or with status
            else if (i === step) {
                stepEl.classList.add(status);
            }
        }
    }
}

// Toggle control button state
function toggleControlButton(forceDisable = false) {
    isRunning = !isRunning;
    controlButton.className = isRunning ? 'stop-button' : 'start-button';
    controlButton.innerHTML = isRunning ? 
        '<span class="material-icons">stop</span>Stop' :
        '<span class="material-icons">play_arrow</span>Start';
    controlButton.disabled = forceDisable;
    controlButton.style.pointerEvents = forceDisable ? 'none' : 'auto';
    controlButton.style.opacity = forceDisable ? '0.5' : '1';
}

// Reset UI state
function resetUI(enableButton = true) {
    try {
        clearInterval(runtimeInterval);
        runtimeInterval = null;
        startTime = null;
        runtimeCounter.textContent = "00:00:00";
        fpsCounter.textContent = "0 FPS";
        isRunning = false;
        isProcessing = !enableButton;
        videoImage.style.display = 'none';
        loadingText.style.display = 'none';
        startPrompt.style.display = 'flex';
        frameCount = 0;
        lastFrameTime = null;
        videoFeed.classList.remove('active');
        
        if (enableButton) {
            // Clear status messages and hide status area
            const statusMessages = document.getElementById('status-messages');
            if (statusMessages) {
                statusMessages.innerHTML = '';
            }
            // Reset progress steps
            currentStep = 0;
            updateProgressSteps(0);
        }
        
        // Update button state
        controlButton.className = 'start-button';
        controlButton.innerHTML = '<span class="material-icons">play_arrow</span>Start';
        controlButton.disabled = !enableButton;
        
        if (enableButton) {
            controlButton.style.pointerEvents = 'auto';
            controlButton.style.opacity = '1';
        }
    } catch (error) {
        console.error('Error in resetUI:', error);
        // Fallback reset
        controlButton.className = 'start-button';
        controlButton.innerHTML = '<span class="material-icons">play_arrow</span>Start';
        controlButton.disabled = false;
        controlButton.style.pointerEvents = 'auto';
        controlButton.style.opacity = '1';
    }
}

// Event Listeners
controlButton.addEventListener('click', async () => {
    if (controlButton.disabled) {
        // Button is disabled, ignore click
        return;
    }
    
    try {
        if (isRunning) {
            // Stopping the process
            isProcessing = true;
            controlButton.innerHTML = '<span class="material-icons">hourglass_empty</span>Processing';
            controlButton.className = 'processing-button';
            
            // Update UI
            loadingText.innerHTML = '<span class="material-icons" style="font-size: 32px;">photo_library</span><div>Processing captured images...</div>';
            loadingText.style.display = 'block';
            
            await stopProcess();
        } else {
            // Starting the process
            loadingText.innerHTML = '<span class="material-icons" style="font-size: 32px;">videocam</span><div>Connecting to camera...</div>';
            loadingText.style.display = 'block';
            videoImage.style.display = 'none';
            startPrompt.style.display = 'none';
            await startProcess();
        }
    } catch (error) {
        console.error('Control button error:', error);
        console.error(`Error: ${error.message}. You can try again.`);
        resetUI(true);
    }
});

// Update visitor count display
function updateVisitorCount(data) {
    if (typeof data === 'object' && data.count !== undefined) {
        const date = new Date(data.date).toLocaleDateString('en-GB', {
            day: 'numeric',
            month: 'short',
            year: 'numeric'
        });
        visitorCount.textContent = data.count;
    } else if (typeof data === 'number') {
        visitorCount.textContent = data;
    } else {
        console.error('Invalid count data:', data);
        visitorCount.textContent = '-';
    }
}

// Handle fetch count button
fetchCountButton.addEventListener('click', async () => {
    try {
        const button = document.querySelector('.refresh-button');
        button.disabled = true;
        button.style.opacity = '0.5';
        visitorCount.textContent = 'Loading...';
        
        // Get today's date in YYYY-MM-DD format using local timezone
        const now = new Date();
        const today = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
        // Fetch metrics for current date
        
        // Fetch count for current date
        const response = await fetch(`${API_ENDPOINT_BASE_URL}/api/v1/analytics/stores/metrics/?store_id=${STORE_ID}&date=${today}`, { headers: {
            'X-API-KEY': API_KEY,
            'Content-Type': 'application/json'
          }});
        const data = await response.json();
        
        if (data.status === 'success') {
            // If data exists and has unique_visitors, show that, otherwise show 0
            visitorCount.textContent = data.data?.unique_visitors ?? 0;
        } else {
            console.error('Invalid response format:', data);
            visitorCount.textContent = '0';
        }
    } catch (error) {
        console.error('Failed to fetch count:', error);
        visitorCount.textContent = '-';
    } finally {
        const button = document.querySelector('.refresh-button');
        button.disabled = false;
        button.style.opacity = '1';
    }
});

// Handle fetch count status updates
window.api.onFetchCountStatus((event, status) => {
    // Process fetch count status
    switch (status.type) {
        case 'success':
            updateVisitorCount(status.data);
            
            // Keep button disabled until phase 3 completes
            controlButton.disabled = true;
            controlButton.style.pointerEvents = 'none';
            controlButton.style.opacity = '0.5';
            
            // Mark phase 3 as completed after a brief delay
            setTimeout(() => {
                updateProgressSteps(currentStep, 'completed');
                startPrompt.innerHTML = 'Please click on Start button to track visitors on the store';
                
                // Only enable button after phase 3 completes successfully
                controlButton.disabled = false;
                controlButton.style.pointerEvents = 'auto';
                controlButton.style.opacity = '1';
                controlButton.className = 'start-button';
                controlButton.innerHTML = '<span class="material-icons">play_arrow</span>Start';
                isRunning = false;
            }, 2000);
            break;
        case 'error':
            console.error('Fetch count error:', status.data);
            visitorCount.textContent = '-';
            updateProgressSteps(currentStep, 'error');
            resetUI(true);
            break;
        case 'info':
            visitorCount.textContent = 'Loading...';
            break;
    }
});

// History Modal Elements
const historyModal = document.getElementById('history-modal');
const checkHistoryButton = document.getElementById('check-history');
const historyCloseButton = historyModal.querySelector('.close-button');
const historyDateInput = document.getElementById('history-date');
const fetchHistoryButton = document.getElementById('fetch-history');
const historyVisitorCount = document.getElementById('history-visitor-count');

// Modal Functions
function openModal() {
    historyModal.classList.add('active');
    // Set date range to between 30 days ago and yesterday
    const now = new Date();
    const yesterday = new Date(now);
    yesterday.setDate(now.getDate() - 1);
    
    const thirtyDaysAgo = new Date(now);
    thirtyDaysAgo.setDate(now.getDate() - 30);
    
    const maxDate = `${yesterday.getFullYear()}-${String(yesterday.getMonth() + 1).padStart(2, '0')}-${String(yesterday.getDate()).padStart(2, '0')}`;
    const minDate = `${thirtyDaysAgo.getFullYear()}-${String(thirtyDaysAgo.getMonth() + 1).padStart(2, '0')}-${String(thirtyDaysAgo.getDate()).padStart(2, '0')}`;
    
    // Set modal date range
    
    historyDateInput.value = maxDate;
    historyDateInput.max = maxDate; // Prevent selecting today and future dates
    historyDateInput.min = minDate; // Prevent selecting dates older than 30 days
}

function closeModal() {
    historyModal.classList.remove('active');
}

// Fetch historical metrics
async function fetchHistoricalMetrics(date) {
    try {
        // Format date as YYYY-MM-DD
        const d = new Date(date);
        const formattedDate = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
        // Fetch metrics for selected date
        
        const url = `${API_ENDPOINT_BASE_URL}/api/v1/analytics/stores/metrics/?store_id=${STORE_ID}&date=${formattedDate}`;
        // Make API request
        
        const response = await fetch(url, { headers: {
            'X-API-KEY': API_KEY,
            'Content-Type': 'application/json'
          }});
        const data = await response.json();
        
        if (!response.ok) {
            if (response.status === 404) {
                throw new Error(`No records found for store ${STORE_ID}`);
            }
            const errorMessage = data.message || `Failed to fetch metrics: ${response.status} ${response.statusText}`;
            throw new Error(errorMessage);
        }
        
        if (data.status !== 'success') {
            throw new Error(data.message || 'Failed to fetch metrics: Invalid response status');
        }
        
        if (!data.data || data.data.unique_visitors === undefined) {
            throw new Error(`No records found for store ${STORE_ID}`);
        }
        
        return { 
            count: data.data.unique_visitors,
            message: data.message
        };
    } catch (error) {
        console.error('Error fetching metrics:', error);
        throw error;
    }
}

// Event Listeners for History Modal
checkHistoryButton.addEventListener('click', openModal);
historyCloseButton.addEventListener('click', closeModal);

fetchHistoryButton.addEventListener('click', async () => {
    const date = historyDateInput.value;
    if (!date) {
        alert('Please select a date');
        return;
    }

    try {
        fetchHistoryButton.disabled = true;
        historyVisitorCount.textContent = 'Loading...';
        
        const metrics = await fetchHistoricalMetrics(date);
        // Process normalized metrics
        
        if (typeof metrics.count !== 'undefined') {
            historyVisitorCount.textContent = metrics.count;
        } else {
            historyVisitorCount.textContent = '0';
            console.error('No count found in normalized metrics:', metrics);
        }
    } catch (error) {
        historyVisitorCount.textContent = '-';
        const errorMessage = document.createElement('div');
        errorMessage.style.color = 'var(--error-color)';
        errorMessage.style.fontSize = '14px';
        errorMessage.style.marginTop = '8px';
        errorMessage.style.textAlign = 'center';
        errorMessage.textContent = error.message || 'Failed to fetch metrics. Please try again.';
        
        // Remove any existing error message
        const existingError = historyVisitorCount.parentElement.querySelector('.error-message');
        if (existingError) {
            existingError.remove();
        }
        
        // Add new error message
        errorMessage.className = 'error-message';
        historyVisitorCount.parentElement.appendChild(errorMessage);
    } finally {
        fetchHistoryButton.disabled = false;
    }
});

// Close modal when clicking outside
historyModal.addEventListener('click', (e) => {
    if (e.target === historyModal) {
        closeModal();
    }
});

// Fetch store details
async function fetchStoreDetails() {
    try {
        const response = await fetch(`${API_ENDPOINT_BASE_URL}/api/v1/analytics/stores/?store_id=${STORE_ID}`, {
            headers: {
                'X-API-KEY': API_KEY,
                'Content-Type': 'application/json'
            }
        });
        const data = await response.json();
        if (data.status === 'success' && data.data?.name) {
            document.querySelector('.store-name').textContent = `Store ID: ${STORE_ID} (${data.data.name})`;
        } else {
            // Fallback to just showing store ID
            document.querySelector('.store-name').textContent = `Store ID: ${STORE_ID}`;
        }
    } catch (error) {
        console.error('Failed to fetch store details:', error);
        // Fallback to just showing store ID
        document.querySelector('.store-name').textContent = `Store ID: ${STORE_ID}`;
    }
}

// Initialize
async function initialize() {
    await fetchStoreDetails();
    setCurrentDate();
    
    // Update total visitors count on load
    try {
        visitorCount.textContent = 'Loading...';
        
        // Get today's date in YYYY-MM-DD format using local timezone
        const now = new Date();
        const today = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
        // Fetch current day metrics
        
        // Fetch count for current date
        const response = await fetch(`${API_ENDPOINT_BASE_URL}/api/v1/analytics/stores/metrics/?store_id=${STORE_ID}&date=${today}`, { headers: {
            'X-API-KEY': API_KEY,
            'Content-Type': 'application/json'
          }});
        const data = await response.json();
        
        if (data.status === 'success') {
            // If data exists and has unique_visitors, show that, otherwise show 0
            visitorCount.textContent = data.data?.unique_visitors ?? 0;
        } else {
            console.error('Invalid response format:', data);
            visitorCount.textContent = '0';
        }
    } catch (error) {
        console.error('Failed to fetch initial count:', error);
        visitorCount.textContent = '-';
    }
}

// Start initialization
initialize();

// Handle video stream data
window.api.onStreamData((event, frameData) => {
    if (!isRunning) return;
    
    const currentTime = performance.now();
    if (lastFrameTime) {
        const fps = Math.round(1000 / (currentTime - lastFrameTime));
        fpsCounter.textContent = `${fps} FPS`;
    }
    lastFrameTime = currentTime;
    
    videoImage.src = `data:image/jpeg;base64,${frameData}`;
    
    if (frameCount === 0) {
        loadingText.style.display = 'none';
        videoImage.style.display = 'block';
        videoFeed.classList.add('active');
    }
    frameCount++;
});

// Handle process status updates
window.api.onProcessStatus((event, status) => {
    switch (status.type) {
        case 'info':
            // Handle info status
            break;
        case 'stderr':
            console.error('Python error:', status.data);
            break;
        case 'error':
            console.error('Process error:', status.data);
            updateProgressSteps(currentStep, 'error');
            resetUI(true);
            if (status.data.includes('Failed to setup stream')) {
                console.error('Failed to connect to camera. Please check connection.');
            }
            break;
        case 'exit':
            // Handle Python process exit
            if (status.code !== 0) {
                console.error('Process exited with error code:', status.code);
                updateProgressSteps(currentStep, 'error');
                resetUI(true);
            }
            break;
    }
});

// Handle face recognition status updates
window.api.onRecognitionStatus(async (event, status) => {
    // Handle recognition status update
    
    try {
        switch (status.type) {
            case 'info':
                if (status.data.includes('Starting face recognition')) {
                    currentStep = 2;
                    updateProgressSteps(currentStep, 'active');
                    // Disable button without toggling state
                    controlButton.disabled = true;
                    controlButton.style.pointerEvents = 'none';
                    controlButton.style.opacity = '0.5';
                    startPrompt.innerHTML = '<span class="material-icons" style="font-size: 48px; margin-bottom: 16px; animation: spin 2s linear infinite;">face</span>Recognizing faces, please wait...';
                    startPrompt.style.display = 'flex';
                }
                // Process status data
                break;
                
            case 'error':
                console.error(status.data);
                console.error('Face recognition error:', status.data);
                updateProgressSteps(currentStep, 'error');
                console.error('Process failed. Click Start to try again.');
                resetUI(true);
                startPrompt.innerHTML = 'Please click on Start button to track visitors on the store';
                break;
                
            case 'success':
                // Move to phase 3 when recognition completes
                currentStep = 3;
                updateProgressSteps(currentStep, 'active');
                startPrompt.innerHTML = '<span class="material-icons" style="font-size: 48px; margin-bottom: 16px; animation: spin 2s linear infinite;">insights</span>Storing visitor insights...';
                // Handle status data
                
                // Fetch the updated count
                try {
                    const now = new Date();
                    const today = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
                    // Update metrics for current date
                    const response = await fetch(`${API_ENDPOINT_BASE_URL}/api/v1/analytics/stores/metrics/?store_id=${STORE_ID}&date=${today}`, { headers: {
                        'X-API-KEY': API_KEY,
                        'Content-Type': 'application/json'
                      }});
                    const data = await response.json();
                    
                    if (data.status === 'success') {
                        // If data exists and has unique_visitors, show that, otherwise show 0
                        visitorCount.textContent = data.data?.unique_visitors ?? 0;
                        updateProgressSteps(currentStep, 'completed');
                        startPrompt.innerHTML = 'Please click on Start button to track visitors on the store';
                        
                        // Enable button after successful count update
                        controlButton.disabled = false;
                        controlButton.style.pointerEvents = 'auto';
                        controlButton.style.opacity = '1';
                        controlButton.className = 'start-button';
                        controlButton.innerHTML = '<span class="material-icons">play_arrow</span>Start';
                        isRunning = false;
                    } else {
                        throw new Error('Invalid response format');
                    }
                } catch (error) {
                    console.error('Failed to fetch count:', error);
                    updateProgressSteps(currentStep, 'error');
                    resetUI(true);
                }
                break;
                
            default:
                // Handle unknown status type
                // Process status data
        }
        
    } catch (error) {
        console.error('Error handling recognition status:', error);
        resetUI(true);
    }
});

// Start detection process
async function startProcess() {
    try {
        // Start Python process
        currentStep = 1;
        updateProgressSteps(currentStep, 'active');
        startPrompt.innerHTML = '<span class="material-icons" style="font-size: 48px; margin-bottom: 16px; animation: spin 2s linear infinite;">person_search</span>Detecting visitors in store...';
        
        await window.api.startPythonProcess();
        // Python process started
        
        startTime = Date.now();
        runtimeInterval = setInterval(updateRuntime, 1000);
        toggleControlButton();
        
        // Camera stream started
    } catch (error) {
        console.error('Failed to start process:', error);
        updateProgressSteps(currentStep, 'error');
        resetUI(true);
        throw error;
    }
}

// Stop detection process
async function stopProcess() {
    try {
        if (isRunning) {
            // Stop Python process
            
            // Keep video feed visible until process stops
            videoImage.style.display = 'block';
            
            // Update to phase 2
            currentStep = 2;
            updateProgressSteps(currentStep, 'active');
            startPrompt.innerHTML = '<span class="material-icons" style="font-size: 48px; margin-bottom: 16px; animation: spin 2s linear infinite;">face</span>Recognizing faces from captured frames...';
            startPrompt.style.display = 'flex';
            
            // Stop camera stream
            
            await window.api.stopPythonProcess();
            // Python process stopped
            
            videoImage.style.display = 'none';
        }
    } catch (error) {
        console.error('Failed to stop process:', error);
        updateProgressSteps(currentStep, 'error');
        console.error('Failed to stop process. Click Start to try again.');
        resetUI(true);
        throw error;
    }
}

// Handle fullscreen
document.querySelector('.stream-controls .icon-button[title="Fullscreen"]').addEventListener('click', () => {
    const streamContainer = document.querySelector('.stream-container');
    if (document.fullscreenElement) {
        document.exitFullscreen();
    } else {
        streamContainer.requestFullscreen();
    }
});
