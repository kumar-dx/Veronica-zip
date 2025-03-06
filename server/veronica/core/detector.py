"""Main person detector implementation"""

import cv2
import time
from models.yolo_model import YOLOModel
from core.stream_handler import StreamHandler
from core.frame_processor import FrameProcessor
from utils.fps_tracker import FPSTracker
from config.camera_config import CAMERA_CONFIG
from config.performance_config import FRAME_SETTINGS

class PersonDetector:
    def __init__(self, stream_url):
        """Initialize the person detector"""
        self.stream_url = stream_url
        
        # Initialize components
        self.model = YOLOModel()
        self.stream_handler = StreamHandler(stream_url)
        self.frame_processor = FrameProcessor(self.model)
        self.fps_tracker = FPSTracker()
        
        # Frame retry settings from config
        self.frame_retry_delay = FRAME_SETTINGS["retry"]["delay"]
        self.max_consecutive_failures = FRAME_SETTINGS["retry"]["max_consecutive_failures"]
        
    def run(self):
        """Main processing loop"""
        # Setup video stream
        if not self.stream_handler.setup_stream():
            print("Failed to setup stream initially")
            return
        
        print("Press 'q' to quit")
        consecutive_failures = 0
        
        try:
            while True:
                # Read frame
                ret, frame = self.stream_handler.read_frame()
                
                if not ret or frame is None:
                    consecutive_failures += 1
                    print(f"Failed to read frame (attempt {consecutive_failures}/{self.max_consecutive_failures})")
                    
                    if consecutive_failures >= self.max_consecutive_failures:
                        print("Too many consecutive frame failures, attempting to reset stream...")
                        if not self.reset_stream():
                            print("Failed to reset stream after multiple attempts")
                            break
                        consecutive_failures = 0
                    
                    time.sleep(self.frame_retry_delay)
                    continue
                
                # Reset failure counter on successful frame read
                consecutive_failures = 0
                
                try:
                    # Process frame
                    processed_frame, person_count = self.frame_processor.process_frame(frame)
                    
                    # Update FPS
                    fps = self.fps_tracker.update()
                    
                    if processed_frame is not None:
                        # Update FPS display
                        cv2.putText(processed_frame, f"FPS: {fps:.1f}", (10, 30), 
                                  cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                        
                        # Display the frame
                        cv2.imshow('Person Detection', processed_frame)
                    else:
                        # Display original frame if processing failed
                        cv2.imshow('Person Detection', frame)
                    
                except Exception as e:
                    print(f"Error processing frame: {str(e)}")
                    # Continue to next frame on processing error
                    continue
                
                # Break on 'q' press
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    print("User requested quit")
                    break
                    
        except Exception as e:
            print(f"Critical error in main loop: {str(e)}")
        finally:
            self.cleanup()
            
    def reset_stream(self):
        """Attempt to reset the stream connection"""
        print("Resetting stream connection...")
        self.cleanup()
        
        # Wait before attempting reconnection
        time.sleep(CAMERA_CONFIG.get("retry_delay", 5))
        
        # Reinitialize stream handler
        self.stream_handler = StreamHandler(self.stream_url)
        return self.stream_handler.setup_stream()
            
    def cleanup(self):
        """Clean up resources"""
        self.stream_handler.release()
        cv2.destroyAllWindows()
