"""Frame processing and person detection logic"""

import numpy as np
import time
import json
from utils.visualization import draw_detection_box, draw_stats
from utils.file_utils import save_person_image
from config.model_config import CAPTURE_CONFIG
from config.performance_config import FRAME_SETTINGS, DETECTION_SETTINGS

class FrameProcessor:
    def __init__(self, model):
        """Initialize frame processor"""
        self.model = model
        self.min_confidence = DETECTION_SETTINGS["confidence"]["min_detection"]  # Minimum confidence threshold
        self.last_person_count = 0  # Track last count for smoother display
        self.captured_ids = set()  # Track IDs that have been captured
        self.last_capture_time = time.time()  # Track last capture time
        self.frame_count = 0  # Track total frames processed
        self.last_gc_time = time.time()  # Track last garbage collection
        self.gc_interval = FRAME_SETTINGS["garbage_collection"]["interval"]  # Force GC interval from config
        
    def process_frame(self, frame):
        """Process a single frame for person detection"""
        if not self._validate_frame(frame):
            return None, 0
            
        # Create a copy of the frame for visualization
        try:
            display_frame = frame.copy()
        except Exception as e:
            print(json.dumps({
                "type": "error",
                "data": f"Error copying frame: {str(e)}"
            }), flush=True)
            return None, 0
            
        try:
            # Run inference
            results = self.model.detect(frame)
            
            # Process detections (results is a list of [x1, y1, x2, y2, conf, class_id])
            person_count = 0
            
            for detection in results:
                x1, y1, x2, y2, conf, class_id, track_id = detection
                # Only process if it's a person with sufficient confidence
                if int(class_id) == 0 and float(conf) >= self.min_confidence:
                    if self._process_detection_from_list(detection, display_frame):
                        person_count += 1
            
            # Update last known count
            self.last_person_count = person_count
            
            # Draw statistics
            draw_stats(display_frame, 0, person_count, 0)
            
            # Increment frame count and check for garbage collection
            self.frame_count += 1
            current_time = time.time()
            if current_time - self.last_gc_time >= self.gc_interval:
                import gc
                gc.collect()
                self.last_gc_time = current_time
            
            # Log person count periodically
            if self.frame_count % FRAME_SETTINGS["logging"]["frame_interval"] == 0:  # Log based on configured interval
                print(json.dumps({
                    "type": "info",
                    "data": f"Current person count: {person_count}"
                }), flush=True)
            
            return display_frame, person_count
            
        except Exception as e:
            print(json.dumps({
                "type": "error",
                "data": f"Error processing frame: {str(e)}"
            }), flush=True)
            return display_frame, self.last_person_count
            
    def _validate_frame(self, frame):
        """Validate frame data"""
        if frame is None:
            print(json.dumps({
                "type": "error",
                "data": "Received empty frame"
            }), flush=True)
            return False
            
        if not isinstance(frame, np.ndarray):
            print(json.dumps({
                "type": "error",
                "data": f"Invalid frame type: {type(frame)}"
            }), flush=True)
            return False
            
        height, width = frame.shape[:2]
        if height == 0 or width == 0:
            print(json.dumps({
                "type": "error",
                "data": "Invalid frame dimensions"
            }), flush=True)
            return False
            
        return True

    def _process_detection(self, box, display_frame):
        """Process a single detection with tracking ID"""
        try:
            conf = float(box.conf)
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            # Get tracking ID if available, otherwise use -1
            track_id = int(box.id[0]) if hasattr(box, 'id') and box.id is not None else -1
            
            # Get frame dimensions for bounds checking
            height, width = display_frame.shape[:2]
            
            # Ensure coordinates are within frame bounds
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(width-1, x2), min(height-1, y2)
            
            if x2 <= x1 or y2 <= y1:
                return False
                
            # Draw detection box with track ID
            draw_detection_box(display_frame, x1, y1, x2, y2, conf, track_id)
            
            # Handle image capture if needed
            if track_id >= 0:  # Only capture if we have a valid track ID
                current_time = time.time()
                if (current_time - self.last_capture_time >= CAPTURE_CONFIG["interval"] and 
                    track_id not in self.captured_ids and
                    conf >= CAPTURE_CONFIG["min_confidence"]):
                    try:
                        # Extract person image from frame
                        person_img = display_frame[y1:y2, x1:x2].copy()
                        # Save image
                        if save_person_image(person_img, conf, track_id):
                            self.captured_ids.add(track_id)
                            self.last_capture_time = current_time
                            print(json.dumps({
                                "type": "info",
                                "data": f"Captured person with ID {track_id} (confidence: {conf:.2f})"
                            }), flush=True)
                    except Exception as e:
                        print(json.dumps({
                            "type": "error",
                            "data": f"Error capturing person image: {str(e)}"
                        }), flush=True)
            
            return True
            
        except Exception as e:
            print(json.dumps({
                "type": "error",
                "data": f"Error processing detection: {str(e)}"
            }), flush=True)
            return False
            
    def _process_detection_from_list(self, detection, display_frame):
        """Process a single detection from list format [x1, y1, x2, y2, conf, class_id, track_id]"""
        try:
            x1, y1, x2, y2, conf, _, track_id = detection
            
            # Get frame dimensions for bounds checking
            height, width = display_frame.shape[:2]
            
            # Ensure coordinates are within frame bounds and convert to int
            x1, y1 = max(0, int(x1)), max(0, int(y1))
            x2, y2 = min(width-1, int(x2)), min(height-1, int(y2))
            
            if x2 <= x1 or y2 <= y1:
                return False
                
            # Draw detection box with track ID
            draw_detection_box(display_frame, x1, y1, x2, y2, conf, track_id)
            
            # Handle image capture if we have a valid track ID
            if track_id >= 0:
                current_time = time.time()
                if (current_time - self.last_capture_time >= CAPTURE_CONFIG["interval"] and 
                    track_id not in self.captured_ids and
                    conf >= CAPTURE_CONFIG["min_confidence"]):
                    try:
                        # Extract person image from frame
                        person_img = display_frame[y1:y2, x1:x2].copy()
                        # Save image
                        if save_person_image(person_img, conf, track_id):
                            self.captured_ids.add(track_id)
                            self.last_capture_time = current_time
                            print(json.dumps({
                                "type": "info",
                                "data": f"Captured person with ID {track_id} (confidence: {conf:.2f})"
                            }), flush=True)
                    except Exception as e:
                        print(json.dumps({
                            "type": "error",
                            "data": f"Error capturing person image: {str(e)}"
                        }), flush=True)
            
            return True
            
        except Exception as e:
            print(json.dumps({
                "type": "error",
                "data": f"Error processing detection from list: {str(e)}"
            }), flush=True)
            return False
