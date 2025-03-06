"""Camera configuration settings"""
import os
import requests
from typing import Dict, Optional
from dotenv import load_dotenv
from config.performance_config import STREAM_SETTINGS, RTSP_SETTINGS, get_rtsp_options

# Load environment variables
load_dotenv()

def fetch_camera_config_from_api() -> Optional[Dict]:
    url = f"{os.getenv('API_ENDPOINT_BASE_URL')}/api/v1/analytics/stores/"
    params = {"store_id": os.getenv("STORE_ID")}
    
    try:
        response = requests.get(url, params=params, headers={'Content-Type': 'application/json', 'X-API-KEY': os.getenv('API_KEY')})
        response.raise_for_status()
        data = response.json()
        return data["data"]["camera_config"]
    except Exception as e:
        print(f"Error fetching camera config from API: {e}")
        return None

# Try to get config from API first
api_config = fetch_camera_config_from_api()

# Camera connection settings
if api_config:
    CAMERA_CONFIG = {
        "ip": api_config["ip"],
        "rtsp_port": int(api_config["rtsp_port"]),
        "username": api_config["username"],
        "password": api_config["password"],
        "max_retries": int(api_config["max_retries"]),
        "retry_delay": int(api_config["retry_delay"]),
        "stream_urls": {
            "main": "rtsp://{username}:{password}@{ip}:{port}" + api_config["main_stream_path"],
            "sub": "rtsp://{username}:{password}@{ip}:{port}" + api_config["sub_stream_path"]
        },
        "stream_settings": {
            "buffer_size": STREAM_SETTINGS["buffer"]["size"],
            "max_delay": STREAM_SETTINGS["timing"]["max_delay"],
            "timeout": STREAM_SETTINGS["timing"]["timeout"],
            "reorder_queue_size": STREAM_SETTINGS["buffer"]["reorder_queue_size"],
            "reconnect_interval": STREAM_SETTINGS["timing"]["reconnect_interval"],
            "max_reconnects": STREAM_SETTINGS["timing"]["max_reconnects"]
        }
    }
    RTSP_ENV_OPTIONS = api_config["rtsp_env_options"]
else:
    pass

def get_stream_url(stream_type="main"):
    """Get formatted stream URL"""
    # For development/testing, use webcam if no camera credentials
    if not all([CAMERA_CONFIG["username"], CAMERA_CONFIG["password"], CAMERA_CONFIG["ip"]]):
        return 0  # Use default webcam
        
    config = CAMERA_CONFIG
    url = config["stream_urls"][stream_type].format(
        username=config["username"],
        password=config["password"],
        ip=config["ip"],
        port=config["rtsp_port"]
    )
    return url
