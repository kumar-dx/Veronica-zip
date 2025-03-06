"""Video stream setup and management"""

import cv2
import os
import time
import queue
import json
import threading
import numpy as np
from config.camera_config import CAMERA_CONFIG, RTSP_ENV_OPTIONS

class StreamHandler:
    def __init__(self, stream_url):
        """Initialize stream handler"""
        self.stream_url = stream_url
        self.cap = None
        # Frame handling
        self.frame_queue = queue.Queue(maxsize=240)  # 8 second buffer at 30 FPS
        self.running = False
        self.frame_thread = None
        self.watchdog_thread = None
        self.last_frame = None
        self.frame_count = 0
        self.last_frame_count = 0
        self.network_errors = 0
        self.max_network_errors = 20  # Allow more network errors before reconnecting
        
        # Timing and monitoring
        self.start_time = time.time()
        self.last_frame_time = 0
        self.last_fps_check = 0
        self.current_fps = 0
        
        # Health monitoring
        self.frame_timeout = 60.0  # 1 minute timeout for frozen stream
        self.health_check_interval = 5.0  # Check health every 5 seconds
        self.min_acceptable_fps = 5  # Minimum acceptable FPS
        
        # Reconnection strategy
        self.base_reconnect_delay = CAMERA_CONFIG.get("retry_delay", 5)
        self.max_reconnect_delay = CAMERA_CONFIG["stream_settings"]["timeout"] / 1000  # Convert to seconds
        self.connection_attempts = 0
        self.last_reconnect_time = 0
        self.consecutive_failures = 0
        self.max_consecutive_failures = CAMERA_CONFIG["stream_settings"]["max_reconnects"]
        
        # Memory management
        self.last_memory_check = 0
        self.memory_check_interval = 60  # Check memory every minute
        self.last_gc_time = 0
        self.gc_interval = 300  # Force GC every 5 minutes
        
    def setup_stream(self):
        """Configure and setup the video stream"""
        print(json.dumps({
            "type": "info",
            "data": f"Attempting to connect to: {self.stream_url}"
        }), flush=True)
        
        try:
            # Set RTSP options before creating capture if using RTSP
            if 'rtsp://' in self.stream_url:
                os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = RTSP_ENV_OPTIONS
                
            # Open stream with minimal buffering
            self.cap = cv2.VideoCapture(self.stream_url)
            
            # Configure capture properties for stability
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, CAMERA_CONFIG["stream_settings"]["buffer_size"])
            self.cap.set(cv2.CAP_PROP_FPS, 30)  # Target 30 FPS
            
            # Set codec based on stream type
            if 'rtsp://' in self.stream_url:
                self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'H264'))
            else:
                self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
                
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            
            if not self.cap.isOpened():
                print(json.dumps({
                    "type": "error",
                    "data": "Failed to open stream"
                }), flush=True)
                return False
            
            # Read test frame
            ret, frame = self.cap.read()
            if not ret or frame is None:
                print(json.dumps({
                    "type": "error",
                    "data": "Failed to read test frame"
                }), flush=True)
                self.release()
                return False
                
            print(json.dumps({
                "type": "info",
                "data": f"Successfully connected. Frame size: {frame.shape}"
            }), flush=True)
            self.last_frame = frame  # Store first valid frame
            self.last_frame_time = time.time()
            
            # Start monitoring threads
            self.running = True
            self.frame_thread = threading.Thread(target=self._read_frames)
            self.watchdog_thread = threading.Thread(target=self._monitor_health)
            self.frame_thread.daemon = True
            self.watchdog_thread.daemon = True
            self.frame_thread.start()
            self.watchdog_thread.start()
            
            return True
            
        except Exception as e:
            print(json.dumps({
                "type": "error",
                "data": f"Error setting up stream: {str(e)}"
            }), flush=True)
            return False
            
    def _monitor_health(self):
        """Monitor stream health and performance"""
        last_frame_count = 0
        last_check_time = time.time()
        
        while self.running:
            try:
                current_time = time.time()
                
                # Check stream health
                if current_time - self.last_frame_time > self.frame_timeout:
                    print(json.dumps({
                        "type": "error",
                        "data": "Stream frozen - initiating recovery"
                    }), flush=True)
                    self._attempt_reconnect()
                    
                # Calculate and monitor FPS
                if current_time - last_check_time >= 5.0:  # Every 5 seconds
                    frames = self.frame_count - last_frame_count
                    fps = frames / 5.0  # 5 second window
                    
                    print(json.dumps({
                        "type": "info",
                        "data": f"Current FPS: {fps:.1f}"
                    }), flush=True)
                    
                    if fps < self.min_acceptable_fps:
                        print(json.dumps({
                            "type": "warning",
                            "data": f"Low FPS detected: {fps:.1f}"
                        }), flush=True)
                        
                    last_frame_count = self.frame_count
                    last_check_time = current_time
                    
                # Memory management
                if current_time - self.last_memory_check >= self.memory_check_interval:
                    self._manage_memory()
                    self.last_memory_check = current_time
                    
                # Periodic garbage collection
                if current_time - self.last_gc_time >= self.gc_interval:
                    import gc
                    gc.collect()
                    self.last_gc_time = current_time
                    
            except Exception as e:
                print(json.dumps({
                    "type": "error",
                    "data": f"Health monitor error: {str(e)}"
                }), flush=True)
                
            time.sleep(1.0)  # Check health every second
            
    def _manage_memory(self):
        """Manage memory usage"""
        try:
            # Clear frame queue if it's too full
            if self.frame_queue.qsize() > 60:  # More than 2 seconds of frames
                while self.frame_queue.qsize() > 30:  # Keep 1 second buffer
                    try:
                        self.frame_queue.get_nowait()
                    except queue.Empty:
                        break
                        
            # Release memory from any deleted frames
            import gc
            gc.collect()
            
        except Exception as e:
            print(json.dumps({
                "type": "error",
                "data": f"Memory management error: {str(e)}"
            }), flush=True)
            
    def _read_frames(self):
        """Background thread for continuous frame reading"""
        consecutive_errors = 0
        max_errors = 10  # Increased error tolerance
        frame_interval = 1.0 / 30  # Target 30 FPS
        
        while self.running:
            if not self._check_stream_health():
                time.sleep(0.1)
                continue
                
            frame_start = time.time()
            
            try:
                ret, frame = self.cap.read()
                
                if not ret or frame is None:
                    consecutive_errors += 1
                    self.network_errors += 1
                    print(json.dumps({
                        "type": "error",
                        "data": f"Frame read error {consecutive_errors}/{max_errors} (Network errors: {self.network_errors})"
                    }), flush=True)
                    
                    if consecutive_errors >= max_errors or self.network_errors >= self.max_network_errors:
                        print(json.dumps({
                            "type": "warning",
                            "data": "Too many errors, attempting reconnection..."
                        }), flush=True)
                        self._attempt_reconnect()
                        consecutive_errors = 0
                        self.network_errors = 0
                    time.sleep(0.1)
                    continue
                    
                # Process frame
                consecutive_errors = 0
                self.last_frame_time = time.time()
                self.last_frame = frame
                self.frame_count += 1
                
                # Update frame queue with error handling
                try:
                    if self.frame_queue.full():
                        try:
                            self.frame_queue.get_nowait()  # Remove oldest frame
                        except queue.Empty:
                            pass
                    self.frame_queue.put_nowait(frame)
                except queue.Full:
                    pass  # Skip if queue is still full
                    
                # Adaptive frame rate control
                frame_time = time.time() - frame_start
                if frame_time < frame_interval:
                    sleep_time = max(0.001, frame_interval - frame_time)
                    time.sleep(sleep_time)
                    
            except Exception as e:
                print(json.dumps({
                    "type": "error",
                    "data": f"Frame processing error: {str(e)}"
                }), flush=True)
                consecutive_errors += 1
                if consecutive_errors >= max_errors:
                    self._attempt_reconnect()
                    consecutive_errors = 0
            
    def _check_stream_health(self):
        """Check if the stream is healthy"""
        if self.cap is None or not self.cap.isOpened():
            return False
        
        current_time = time.time()
        if current_time - self.last_frame_time > self.frame_timeout:
            print(json.dumps({
                "type": "error",
                "data": "Stream appears frozen - no frames received recently"
            }), flush=True)
            return False
            
        return True

    def _calculate_reconnect_delay(self):
        """Calculate reconnect delay using exponential backoff"""
        delay = min(self.base_reconnect_delay * (2 ** self.connection_attempts), self.max_reconnect_delay)
        return delay

    def _attempt_reconnect(self):
        """Attempt to reconnect to the stream with exponential backoff"""
        current_time = time.time()
        
        # Ensure minimum time between reconnection attempts
        if current_time - self.last_reconnect_time < self.base_reconnect_delay:
            return False
            
        delay = self._calculate_reconnect_delay()
        print(json.dumps({
            "type": "info",
            "data": f"Attempting to reconnect (attempt {self.connection_attempts + 1}) in {delay} seconds..."
        }), flush=True)
        time.sleep(delay)
        
        try:
            if self.cap is not None:
                self.cap.release()
                
            # Clear any existing frames
            while not self.frame_queue.empty():
                try:
                    self.frame_queue.get_nowait()
                except queue.Empty:
                    break
                    
            # Force garbage collection before reconnecting
            import gc
            gc.collect()
            
            # Set RTSP options before creating capture if using RTSP
            if 'rtsp://' in self.stream_url:
                os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = RTSP_ENV_OPTIONS
                
            # Reopen stream with same settings as initial setup
            self.cap = cv2.VideoCapture(self.stream_url)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, CAMERA_CONFIG["stream_settings"]["buffer_size"])
            self.cap.set(cv2.CAP_PROP_FPS, 30)  # Target 30 FPS
            
            # Set codec based on stream type
            if 'rtsp://' in self.stream_url:
                self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'H264'))
            else:
                self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
                
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            
            if not self.cap.isOpened():
                print(json.dumps({
                    "type": "error",
                    "data": f"Reconnection attempt {self.connection_attempts + 1} failed"
                }), flush=True)
                self.connection_attempts += 1
                self.last_reconnect_time = current_time
                return False
                
            ret, frame = self.cap.read()
            if not ret or frame is None:
                print(json.dumps({
                    "type": "error",
                    "data": f"Failed to read frame after reconnection attempt {self.connection_attempts + 1}"
                }), flush=True)
                self.connection_attempts += 1
                self.last_reconnect_time = current_time
                return False
                
            print(json.dumps({
                "type": "info",
                "data": "Successfully reconnected to stream"
            }), flush=True)
            self.connection_attempts = 0  # Reset counter on successful connection
            self.last_reconnect_time = current_time
            self.last_frame_time = current_time
            return True
            
        except Exception as e:
            print(json.dumps({
                "type": "error",
                "data": f"Error during reconnection attempt {self.connection_attempts + 1}: {str(e)}"
            }), flush=True)
            self.connection_attempts += 1
            self.last_reconnect_time = current_time
            return False
            
    def read_frame(self):
        """Read the latest frame"""
        if not self.running:
            return False, None
            
        try:
            # Try to get latest frame from queue
            frame = self.frame_queue.get_nowait()
            return True, frame
        except queue.Empty:
            # If queue is empty but we have a last frame, use it
            if self.last_frame is not None:
                return True, self.last_frame.copy()
            return False, None
            
    def release(self):
        """Release resources"""
        self.running = False
        
        # Stop monitoring threads
        if self.frame_thread is not None:
            self.frame_thread.join(timeout=2.0)
        if self.watchdog_thread is not None:
            self.watchdog_thread.join(timeout=2.0)
            
        # Release capture device
        if self.cap is not None:
            self.cap.release()
            self.cap = None
            
        # Clear queues
        while not self.frame_queue.empty():
            try:
                self.frame_queue.get_nowait()
            except queue.Empty:
                break
