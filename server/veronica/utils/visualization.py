"""Visualization utilities for drawing on frames"""

import cv2
from config.model_config import VISUALIZATION_CONFIG as viz_config

def draw_detection_box(frame, x1, y1, x2, y2, confidence, track_id):
    """Draw bounding box and confidence text for a detected person with track ID"""
    # Draw bounding box
    cv2.rectangle(frame, (x1, y1), (x2, y2), 
                 viz_config["box_color"], 
                 viz_config["box_thickness"])
    
    # Draw confidence text with track ID
    text = f"ID-{track_id}: {confidence:.2f}" if track_id >= 0 else f"Person: {confidence:.2f}"
    cv2.putText(frame, text,
                (x1, y1-10), 
                getattr(cv2, viz_config["font"]["face"]),
                viz_config["font"]["scale"],
                viz_config["font"]["color"],
                viz_config["font"]["thickness"])

def draw_stats(frame, fps, person_count, _):
    """Draw statistics on frame"""
    # Draw FPS
    cv2.putText(frame, f"FPS: {fps:.1f}",
                (10, 30),
                getattr(cv2, viz_config["font"]["face"]),
                1, viz_config["font"]["color"], 2)
    
    # Draw person count
    cv2.putText(frame, f"Persons: {person_count}",
                (10, 70),
                getattr(cv2, viz_config["font"]["face"]),
                1, viz_config["font"]["color"], 2)
