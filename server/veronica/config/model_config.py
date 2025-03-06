"""YOLO model configuration settings"""
from config.performance_config import DETECTION_SETTINGS

# Capture settings
CAPTURE_CONFIG = {
    "interval": 5,  # seconds between captures
    "output_dir": "detected_persons",  # directory to save images
    "min_confidence": DETECTION_SETTINGS["confidence"]["min_capture"]  # minimum confidence threshold for capture
}

# Model settings
MODEL_CONFIG = {
    "model_path": "yolov8m.pt",
    "confidence": DETECTION_SETTINGS["confidence"]["min_detection"],  # Detection confidence threshold
    "iou": 0.45,        # IoU threshold
    "max_det": 100,     # Maximum detections per image
    "classes": [0],     # Only detect people (class 0 in COCO)
    "agnostic": False,  # Class-specific NMS
    "verbose": False    # Disable verbose output
}

# Visualization settings
VISUALIZATION_CONFIG = {
    "box_color": (0, 255, 0),  # Green
    "box_thickness": 2,
    "font": {
        "face": "FONT_HERSHEY_SIMPLEX",
        "scale": 0.5,
        "thickness": 2,
        "color": (0, 255, 0)  # Green
    }
}
