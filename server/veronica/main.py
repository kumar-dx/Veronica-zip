"""Main entry point for person detection system"""

import os
import time
import sys
import json
import base64
import cv2
import numpy as np
from config.camera_config import CAMERA_CONFIG, get_stream_url, RTSP_ENV_OPTIONS
from core.stream_handler import StreamHandler
from models.yolo_model import YOLOModel
from core.frame_processor import FrameProcessor

def setup_environment():
    """Setup environment variables and configuration"""
    # Validate S3 configuration
    from config.s3_config import validate_s3_config
    validate_s3_config()
    
    # Validate camera configuration
    if not all([CAMERA_CONFIG["username"], CAMERA_CONFIG["password"], CAMERA_CONFIG["ip"]]):
        print(json.dumps({
            "type": "error",
            "data": "Missing required camera configuration. Please check your .env file."
        }), flush=True)
        sys.exit(1)

def encode_frame(frame):
    """Encode frame as base64 string"""
    # Resize frame to reduce data size
    height, width = frame.shape[:2]
    max_dimension = 800
    if height > max_dimension or width > max_dimension:
        scale = max_dimension / max(height, width)
        frame = cv2.resize(frame, None, fx=scale, fy=scale)
    
    # Encode frame
    _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
    jpg_as_text = base64.b64encode(buffer).decode()
    return jpg_as_text

def send_frame(frame):
    """Send frame data to Electron"""
    try:
        encoded_frame = encode_frame(frame)
        message = {
            "type": "frame",
            "data": encoded_frame
        }
        # Send as a single line to ensure atomic writes
        print(json.dumps(message), flush=True)
    except Exception as e:
        print(json.dumps({"type": "error", "data": str(e)}), flush=True)

def run_stream(stream_url):
    """Run the video stream with person detection"""
    stream = StreamHandler(stream_url)
    
    if not stream.setup_stream():
        print(json.dumps({"type": "error", "data": "Failed to setup stream"}), flush=True)
        return False
    
    try:
        # Initialize YOLO model and frame processor
        print(json.dumps({"type": "info", "data": "Initializing YOLO model..."}), flush=True)
        model = YOLOModel()
        processor = FrameProcessor(model)
        print(json.dumps({"type": "info", "data": "Model initialized successfully"}), flush=True)
        
        while True:
            ret, frame = stream.read_frame()
            if ret and frame is not None:
                # Process frame for person detection
                processed_frame, person_count = processor.process_frame(frame)
                if processed_frame is not None:
                    send_frame(processed_frame)
                    
                    # Send person count info
                    print(json.dumps({
                        "type": "info",
                        "data": f"Detected {person_count} people"
                    }), flush=True)
                    
            time.sleep(1/30)  # Limit to ~30 FPS
            
    except KeyboardInterrupt:
        print(json.dumps({"type": "info", "data": "Stream stopped by user"}), flush=True)
    except Exception as e:
        print(json.dumps({"type": "error", "data": str(e)}), flush=True)
    finally:
        stream.release()
    
    return True

def try_stream(stream_type, max_attempts=None):
    """Attempt to run stream of a specific type"""
    if max_attempts is None:
        max_attempts = CAMERA_CONFIG.get("max_retries", 3)
    
    stream_url = get_stream_url(stream_type)
    attempt = 0
    retry_delay = CAMERA_CONFIG.get("retry_delay", 5)
    
    while attempt < max_attempts:
        try:
            print(json.dumps({
                "type": "info", 
                "data": f"Attempt {attempt + 1}/{max_attempts} for {stream_type} stream..."
            }), flush=True)
            
            if run_stream(stream_url):
                return True
            
        except KeyboardInterrupt:
            print(json.dumps({
                "type": "info",
                "data": "User interrupted program"
            }), flush=True)
            return True
            
        except Exception as e:
            print(json.dumps({
                "type": "error",
                "data": f"Error on attempt {attempt + 1}: {str(e)}"
            }), flush=True)
            
            attempt += 1
            if attempt < max_attempts:
                time.sleep(retry_delay)
                retry_delay = min(retry_delay * 1.5, 30)
            else:
                print(json.dumps({
                    "type": "error",
                    "data": f"Failed to establish stable connection after {max_attempts} attempts"
                }), flush=True)
    
    return False

def main():
    """Main function"""
    setup_environment()
    
    total_attempts = CAMERA_CONFIG.get("max_retries", 3) * 2
    
    for stream_type in ["main", "sub"]:
        print(json.dumps({
            "type": "info",
            "data": f"Trying {stream_type} stream..."
        }), flush=True)
        
        if try_stream(stream_type, total_attempts):
            print(json.dumps({
                "type": "info",
                "data": f"Successfully ran {stream_type} stream"
            }), flush=True)
            return
        
        print(json.dumps({
            "type": "error",
            "data": f"Failed to establish stable connection on {stream_type} stream"
        }), flush=True)
    
    print(json.dumps({
        "type": "error",
        "data": "Failed to establish stable connection on any stream"
    }), flush=True)
    sys.exit(1)

if __name__ == "__main__":
    main()
