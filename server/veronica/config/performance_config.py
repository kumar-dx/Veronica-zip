"""Performance and system configuration settings"""

# Stream buffer and timing settings
STREAM_SETTINGS = {
    "buffer": {
        "size": 1000000,  # 1MB buffer for network jitter
        "reorder_queue_size": 100000  # Large reorder queue for packet reordering
    },
    "timing": {
        "max_delay": 500000,  # 500ms max delay
        "timeout": 5000000,  # 5s timeout
        "reconnect_interval": 5,  # Seconds between reconnection attempts
        "max_reconnects": 10  # Maximum reconnection attempts before switching streams
    }
}

# Frame processing settings
FRAME_SETTINGS = {
    "retry": {
        "delay": 0.5,  # seconds between retry attempts
        "max_consecutive_failures": 10  # maximum consecutive frame read failures
    },
    "garbage_collection": {
        "interval": 300  # Force garbage collection every 5 minutes
    },
    "logging": {
        "frame_interval": 30  # Log info every 30 frames
    }
}

# Detection thresholds
DETECTION_SETTINGS = {
    "confidence": {
        "min_detection": 0.5,  # Minimum confidence for detection
        "min_capture": 0.70  # Minimum confidence for capture (70%)
    }
}

# RTSP transport settings
RTSP_SETTINGS = {
    "transport": "tcp",
    "max_delay": 500000,  # 500ms max delay
    "reorder_queue_size": 100000,
    "buffer_size": 1000000,  # 1MB buffer
    "socket_timeout": 5000000,  # 5s socket timeout
    "flags": {
        "buffer": False,  # Disable input buffering
        "low_delay": True  # Minimize latency
    }
}

def get_rtsp_options():
    """Generate RTSP options string from settings"""
    return (
        f"rtsp_transport={RTSP_SETTINGS['transport']}|"
        f"max_delay={RTSP_SETTINGS['max_delay']}|"
        f"reorder_queue_size={RTSP_SETTINGS['reorder_queue_size']}|"
        f"buffer_size={RTSP_SETTINGS['buffer_size']}|"
        f"stimeout={RTSP_SETTINGS['socket_timeout']}|"
        f"fflags={'nobuffer' if not RTSP_SETTINGS['flags']['buffer'] else ''}|"
        f"flags={'low_delay' if RTSP_SETTINGS['flags']['low_delay'] else ''}"
    )
