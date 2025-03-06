"""FPS calculation utility"""

import time

class FPSTracker:
    def __init__(self):
        """Initialize FPS tracker"""
        self.prev_time = 0
        self.fps = 0
        
    def update(self):
        """Calculate and update FPS"""
        current_time = time.time()
        if self.prev_time == 0:
            self.prev_time = current_time
            return 0
            
        # Calculate FPS
        self.fps = 1 / (current_time - self.prev_time)
        self.prev_time = current_time
        return self.fps
        
    def get_fps(self):
        """Get current FPS value"""
        return self.fps
