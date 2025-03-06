"""File handling utilities"""

import os
import cv2
import json
from datetime import datetime
from utils.s3_utils import S3Uploader
from config.model_config import CAPTURE_CONFIG

# Initialize S3 uploader
s3_uploader = S3Uploader()

# Ensure temp directory exists
temp_dir = "./"
os.makedirs(temp_dir, exist_ok=True)

def generate_filename(person_id, confidence):
    """Generate a standardized filename for person images"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    return f"person_id{person_id}_{timestamp}_{confidence:.2f}.jpg"

def log_message(msg_type, data):
    """Standardized logging function"""
    print(json.dumps({
        "type": msg_type,
        "data": data
    }), flush=True)

def save_image_to_disk(image, filepath):
    """Save image to disk and ensure directory exists"""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    # print("filepath from save image to disk", filepath)
    return cv2.imwrite(filepath, image)

def save_person_image(image, confidence, person_id):
    """
    Save detected person image based on environment:
    - Production: Save only to S3
    - Development: Save locally and optionally to S3
    
    Args:
        image: OpenCV image array
        confidence: Detection confidence score
        person_id: Unique identifier for the person
        
    Returns:
        str: S3 URL or local filepath if successful, None otherwise
    """
    try:
        filename = generate_filename(person_id, confidence)
        # print("filename from save person image", filename)
        is_production = os.getenv("ENVIRONMENT", "dev").lower() == "prod"
        
        # Production: Use temp directory and S3 only
        if is_production:
            if not s3_uploader.enabled:
                return None
                
            temp_path = os.path.join(temp_dir, filename)
            
            if not save_image_to_disk(image, temp_path):
                log_message("error", f"Failed to save temporary file: {temp_path}")
                return None
            
            try:
                s3_url = s3_uploader.upload_file(temp_path)  # Uses daily prefix automatically
                if s3_url:
                    log_message("info", f"Uploaded to S3: {s3_url}")
                return s3_url
            finally:
                # Clean up temporary file
                try:
                    os.unlink(temp_path)
                except Exception as e:
                    log_message("error", f"Failed to remove temporary file: {str(e)}")
        
        # Development: Save locally and optionally to S3
        else:
            local_path = os.path.join(CAPTURE_CONFIG["output_dir"], filename)
            
            # Save locally
            if not save_image_to_disk(image, local_path):
                log_message("error", f"Failed to save image locally: {local_path}")
                return None
                
            log_message("info", f"Saved locally to: {local_path}")
            
            # Upload to S3 if enabled (for testing)
            # if s3_uploader.enabled:
            #     s3_url = s3_uploader.upload_file(local_path)  # Uses daily prefix automatically
            #     if s3_url:
            #         log_message("info", f"Uploaded to S3: {s3_url}")
            
            return local_path
            
    except Exception as e:
        log_message("error", f"Error saving image: {str(e)}")
        return None
