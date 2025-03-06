"""YOLO model implementation for person detection"""

from ultralytics import YOLO
import cv2
import numpy as np
from config.model_config import MODEL_CONFIG

class YOLOModel:
    def __init__(self):
        """Initialize YOLO model"""
        self.model = YOLO(MODEL_CONFIG["model_path"])
        self.confidence_threshold = MODEL_CONFIG.get("confidence_threshold", 0.5)
        self.person_class_id = MODEL_CONFIG.get("person_class_id", 0)  # COCO dataset person class ID
        
    def detect(self, frame):
        """
        Detect people in the given frame
        Returns: List of detections [x1, y1, x2, y2, confidence, class_id]
        """
        try:
            # Run inference with tracking enabled
            results = self.model.track(frame, verbose=False, persist=True)[0]
            
            # Filter detections for persons with confidence above threshold
            detections = []
            if results.boxes and len(results.boxes) > 0:
                for box in results.boxes:
                    # Get box data
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    conf = float(box.conf)
                    class_id = int(box.cls)
                    track_id = int(box.id[0]) if box.id is not None else -1
                    
                    if class_id == self.person_class_id and conf >= self.confidence_threshold:
                        detections.append([x1, y1, x2, y2, conf, class_id, track_id])
            
            return detections
            
        except Exception as e:
            print(f"Error during detection: {str(e)}")
            return []
            
    def draw_detections(self, frame, detections):
        """Draw bounding boxes and labels on frame"""
        for det in detections:
            x1, y1, x2, y2, conf, _ = det
            
            # Draw bounding box
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            
            # Draw confidence label
            label = f"Person {conf:.2f}"
            cv2.putText(frame, label, (x1, y1 - 10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        return frame
