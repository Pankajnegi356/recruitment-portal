import cv2
import json
import time
import numpy as np
from collections import deque
import argparse
 
class EyeDetectionService:
    """Service class for processing individual frames from frontend"""
    def __init__(self, session_id: str, smoothing_window=5, confidence_threshold=3, simple_mode=False):
        """
        Initialize the eye detection service for session-based processing
       
        Args:
            session_id: Unique session identifier
            smoothing_window: Number of frames to average for gaze smoothing
            confidence_threshold: Minimum detections needed for stable gaze
            simple_mode: Use simple detection similar to original code
        """
        # Load Haar cascades with error handling
        try:
            self.face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            )
            self.eye_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + "haarcascade_eye_tree_eyeglasses.xml"
            )
           
            if self.face_cascade.empty() or self.eye_cascade.empty():
                raise ValueError("Failed to load Haar cascades")
               
        except Exception as e:
            print(f" Error loading cascades: {e}")
            raise
       
        # Configuration
        self.session_id = session_id
        self.smoothing_window = smoothing_window
        self.confidence_threshold = confidence_threshold
        self.simple_mode = simple_mode
       
        # Tracking variables
        self.eye_log = []
        self.gaze_history = deque(maxlen=smoothing_window)
        self.frame_count = 0
        
        # Violation tracking
        self.violation_start_time = None
        self.looking_away_duration = 0
        self.total_violations = 0
        self.last_violation_log = None
        
        # Thresholds for anti-cheating
        self.violation_threshold_seconds = 2.0  # Looking away for 2+ seconds is a violation
        self.max_violations = 5  # Maximum allowed violations
       
        # More lenient detection parameters
        self.face_params = {
            'scaleFactor': 1.05,
            'minNeighbors': 4,
            'minSize': (60, 60),
            'maxSize': (400, 400)
        }
       
        self.eye_params = {
            'scaleFactor': 1.05,
            'minNeighbors': 3,
            'minSize': (20, 20),
            'maxSize': (100, 100)
        }
       
        # Gaze thresholds (more refined)
        self.gaze_thresholds = {
            'left': (0.0, 0.35),
            'right': (0.65, 1.0),
            'up': (0.0, 0.35),
            'down': (0.65, 1.0),
            'center': (0.35, 0.65)
        }
        
        print(f"✅ EyeDetectionService initialized for session: {session_id}")
        
    def process_frame(self, frame):
        """Process a single frame and return analysis results"""
        try:
            self.frame_count += 1
            current_time = time.time()
            
            # Preprocess frame
            gray = self.preprocess_frame(frame)
            
            # Detect faces
            faces = self.face_cascade.detectMultiScale(gray, **self.face_params)
            
            analysis_result = {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "frame_number": self.frame_count,
                "face_detected": len(faces) > 0,
                "looking_forward": False,
                "gaze_direction": "unknown",
                "confidence": 0.0,
                "violation_detected": False,
                "violation_type": None,
                "violation_duration": 0.0
            }
            
            if len(faces) > 0:
                # Use the largest face
                face = max(faces, key=lambda f: f[2] * f[3])
                x, y, w, h = face
                
                roi_gray = gray[y:y+h, x:x+w]
                
                # Detect eyes
                eyes = self.eye_cascade.detectMultiScale(roi_gray, **self.eye_params)
                
                if len(eyes) >= 1:
                    # Sort eyes left to right and take up to two
                    eyes = sorted(eyes, key=lambda e: e[0])[:2]
                    
                    iris_positions = []
                    
                    for i, (ex, ey, ew, eh) in enumerate(eyes):
                        # Extract eye region with some padding
                        pad = 2
                        eye_y1 = max(0, ey - pad)
                        eye_y2 = min(roi_gray.shape[0], ey + eh + pad)
                        eye_x1 = max(0, ex - pad)
                        eye_x2 = min(roi_gray.shape[1], ex + ew + pad)
                        
                        eye_roi = roi_gray[eye_y1:eye_y2, eye_x1:eye_x2]
                        
                        # Detect iris
                        if self.simple_mode:
                            iris_rect = self.detect_iris_simple(eye_roi)
                        else:
                            iris_rect = self.detect_iris(eye_roi)
                        
                        if iris_rect:
                            ix, iy, iw, ih = iris_rect
                            
                            # Adjust coordinates back to original eye position
                            adj_ix = ix + eye_x1 - ex
                            adj_iy = iy + eye_y1 - ey
                            
                            # Calculate relative position
                            iris_center_x = (adj_ix + iw / 2) / ew
                            iris_center_y = (adj_iy + ih / 2) / eh
                            
                            # Clamp values to reasonable range
                            iris_center_x = max(0.0, min(1.0, iris_center_x))
                            iris_center_y = max(0.0, min(1.0, iris_center_y))
                            
                            iris_positions.append((iris_center_x, iris_center_y))
                    
                    # Calculate gaze direction
                    if iris_positions:
                        gaze_direction, looking_forward = self.calculate_gaze_direction(iris_positions)
                        confidence = self.calculate_confidence(iris_positions)
                        
                        analysis_result.update({
                            "looking_forward": looking_forward,
                            "gaze_direction": gaze_direction,
                            "confidence": round(confidence, 3)
                        })
                        
                        # Check for violations (looking away)
                        violation_info = self.check_violation(looking_forward, current_time)
                        analysis_result.update(violation_info)
                        
                        # Log data for session
                        log_entry = {
                            "timestamp": analysis_result["timestamp"],
                            "frame_number": self.frame_count,
                            "face_position": [int(x), int(y), int(w), int(h)],
                            "eyes": [{"pos": [int(ex), int(ey), int(ew), int(eh)],
                                    "iris_relative": iris_pos}
                                   for (ex, ey, ew, eh), iris_pos in zip(eyes, iris_positions)],
                            "gaze_direction": gaze_direction,
                            "looking_forward": looking_forward,
                            "confidence": round(confidence, 3)
                        }
                        
                        self.eye_log.append(log_entry)
            
            return analysis_result
            
        except Exception as e:
            print(f"❌ Error processing frame: {e}")
            return {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "frame_number": self.frame_count,
                "error": str(e),
                "face_detected": False,
                "looking_forward": False,
                "gaze_direction": "error",
                "confidence": 0.0,
                "violation_detected": False
            }
    
    def check_violation(self, looking_forward, current_time):
        """Check for anti-cheating violations"""
        violation_info = {
            "violation_detected": False,
            "violation_type": None,
            "violation_duration": 0.0
        }
        
        if not looking_forward:
            # User is looking away
            if self.violation_start_time is None:
                self.violation_start_time = current_time
            
            self.looking_away_duration = current_time - self.violation_start_time
            
            # Check if violation threshold is exceeded
            if self.looking_away_duration >= self.violation_threshold_seconds:
                violation_info.update({
                    "violation_detected": True,
                    "violation_type": "looking_away",
                    "violation_duration": round(self.looking_away_duration, 2)
                })
                
                # Log this as a new violation if it's been a while since the last log
                current_violation_key = f"looking_away_{int(self.looking_away_duration)}"
                if self.last_violation_log != current_violation_key:
                    self.total_violations += 1
                    self.last_violation_log = current_violation_key
                    print(f"🚨 VIOLATION DETECTED: Looking away for {self.looking_away_duration:.1f}s (Total: {self.total_violations})")
        else:
            # User is looking forward, reset violation tracking
            if self.violation_start_time is not None:
                print(f"✅ User looking forward again after {self.looking_away_duration:.1f}s away")
            self.violation_start_time = None
            self.looking_away_duration = 0
            self.last_violation_log = None
        
        return violation_info
    
    def get_session_summary(self):
        """Get summary of the eye tracking session"""
        total_frames = len(self.eye_log)
        looking_forward_frames = sum(1 for entry in self.eye_log if entry.get("looking_forward", False))
        
        return {
            "session_id": self.session_id,
            "total_frames": total_frames,
            "looking_forward_frames": looking_forward_frames,
            "looking_away_frames": total_frames - looking_forward_frames,
            "attention_percentage": round((looking_forward_frames / total_frames * 100) if total_frames > 0 else 0, 2),
            "total_violations": self.total_violations,
            "violation_threshold_seconds": self.violation_threshold_seconds,
            "max_violations": self.max_violations,
            "tracking_data": self.eye_log
        }
    
    def save_session_log(self, output_dir="eye_log"):
        """Save eye tracking log for this session"""
        import os
        
        try:
            # Create directory if it doesn't exist
            os.makedirs(output_dir, exist_ok=True)
            
            # Generate filename with session ID and timestamp
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"{output_dir}/eye_tracking_{self.session_id}_{timestamp}.json"
            
            session_summary = self.get_session_summary()
            
            # Add metadata
            log_data = {
                "metadata": {
                    "session_id": self.session_id,
                    "total_frames": len(self.eye_log),
                    "total_violations": self.total_violations,
                    "violation_threshold_seconds": self.violation_threshold_seconds,
                    "attention_percentage": session_summary["attention_percentage"],
                    "simple_mode": self.simple_mode,
                    "tracking_params": {
                        "smoothing_window": self.smoothing_window,
                        "confidence_threshold": self.confidence_threshold,
                        "gaze_thresholds": self.gaze_thresholds,
                        "face_params": self.face_params,
                        "eye_params": self.eye_params
                    },
                    "saved_at": time.strftime("%Y-%m-%d %H:%M:%S")
                },
                "session_summary": session_summary,
                "tracking_data": self.eye_log
            }
            
            with open(filename, "w") as f:
                json.dump(log_data, f, indent=2)
            
            print(f"✅ Eye tracking log saved: {filename}")
            return filename
            
        except Exception as e:
            print(f"❌ Error saving eye tracking log: {e}")
            return None
    
    def preprocess_frame(self, frame):
        """Preprocess frame for eye detection"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        # Light processing only - sometimes less is more
        gray = cv2.equalizeHist(gray)
        return gray
    
    def detect_iris_simple(self, eye_roi):
        """Simple iris detection - closest to original working code"""
        if eye_roi.size == 0:
            return None
       
        # Simple thresholding like original code
        _, thresh = cv2.threshold(eye_roi, 50, 255, cv2.THRESH_BINARY_INV)
        thresh = cv2.medianBlur(thresh, 5)
       
        # Find contours
        contours, _ = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            # Largest dark contour = iris (exactly like original)
            iris_contour = max(contours, key=cv2.contourArea)
            return cv2.boundingRect(iris_contour)
       
        return None
    
    def detect_iris(self, eye_roi, debug=False):
        """Robust iris detection with fallback methods"""
        if eye_roi.size == 0 or eye_roi.shape[0] < 20 or eye_roi.shape[1] < 20:
            return None
       
        # Method 1: Simple thresholding (similar to original but more robust)
        try:
            # Try multiple threshold values
            for threshold in [50, 60, 40, 70]:
                _, thresh = cv2.threshold(eye_roi, threshold, 255, cv2.THRESH_BINARY_INV)
                thresh = cv2.medianBlur(thresh, 5)
               
                # Find contours
                contours, _ = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
               
                if contours:
                    # Get largest contour
                    largest_contour = max(contours, key=cv2.contourArea)
                    area = cv2.contourArea(largest_contour)
                   
                    # More lenient area requirements
                    eye_area = eye_roi.shape[0] * eye_roi.shape[1]
                    min_area = max(20, eye_area * 0.02)  # At least 20 pixels or 2% of eye
                    max_area = eye_area * 0.8  # Up to 80% of eye area
                   
                    if min_area <= area <= max_area:
                        rect = cv2.boundingRect(largest_contour)
                        # Basic sanity check on dimensions
                        if rect[2] > 5 and rect[3] > 5:  # At least 5x5 pixels
                            return rect
           
            # Method 2: HoughCircles as fallback
            circles = cv2.HoughCircles(
                eye_roi,
                cv2.HOUGH_GRADIENT,
                dp=1,
                minDist=int(min(eye_roi.shape) * 0.3),
                param1=50,
                param2=30,
                minRadius=max(3, int(min(eye_roi.shape) * 0.1)),
                maxRadius=int(min(eye_roi.shape) * 0.4)
            )
           
            if circles is not None:
                circles = np.round(circles[0, :]).astype("int")
                # Take the first (most confident) circle
                x, y, r = circles[0]
                return (max(0, x-r), max(0, y-r), 2*r, 2*r)
           
            # Method 3: Simplest fallback - find darkest region
            if eye_roi.shape[0] > 10 and eye_roi.shape[1] > 10:
                # Find minimum value location
                min_val, _, min_loc, _ = cv2.minMaxLoc(eye_roi)
               
                # Create a small region around the darkest point
                h, w = eye_roi.shape
                size = min(h, w) // 3
                x = max(0, min_loc[0] - size//2)
                y = max(0, min_loc[1] - size//2)
                w = min(size, w - x)
                h = min(size, h - y)
               
                if w > 5 and h > 5:
                    return (x, y, w, h)
           
        except Exception as e:
            if debug:
                print(f"Iris detection error: {e}")
           
        return None
    
    def calculate_gaze_direction(self, iris_positions):
        """Calculate gaze direction with smoothing"""
        if len(iris_positions) < 1:
            return "unknown", False
       
        # Average both eyes if available
        avg_x = np.mean([pos[0] for pos in iris_positions])
        avg_y = np.mean([pos[1] for pos in iris_positions])
       
        # Add to history for smoothing
        self.gaze_history.append((avg_x, avg_y))
       
        if len(self.gaze_history) < self.confidence_threshold:
            return "calibrating", False
       
        # Calculate smoothed position
        smooth_x = np.mean([pos[0] for pos in self.gaze_history])
        smooth_y = np.mean([pos[1] for pos in self.gaze_history])
       
        # Determine gaze direction with hysteresis to reduce jitter
        horizontal_dir = "center"
        vertical_dir = "center"
       
        if smooth_x < self.gaze_thresholds['left'][1]:
            horizontal_dir = "left"
        elif smooth_x > self.gaze_thresholds['right'][0]:
            horizontal_dir = "right"
       
        if smooth_y < self.gaze_thresholds['up'][1]:
            vertical_dir = "up"
        elif smooth_y > self.gaze_thresholds['down'][0]:
            vertical_dir = "down"
       
        # Combine directions
        if horizontal_dir == "center" and vertical_dir == "center":
            gaze_direction = "forward"
            looking_forward = True
        elif horizontal_dir != "center" and vertical_dir == "center":
            gaze_direction = horizontal_dir
            looking_forward = False
        elif horizontal_dir == "center" and vertical_dir != "center":
            gaze_direction = vertical_dir
            looking_forward = False
        else:
            gaze_direction = f"{vertical_dir}-{horizontal_dir}"
            looking_forward = False
       
        return gaze_direction, looking_forward
    
    def calculate_confidence(self, iris_positions):
        """Calculate detection confidence based on consistency"""
        if len(self.gaze_history) < 2:
            return 0.0
       
        # Calculate variance in recent positions
        recent_x = [pos[0] for pos in list(self.gaze_history)[-5:]]
        recent_y = [pos[1] for pos in list(self.gaze_history)[-5:]]
       
        var_x = np.var(recent_x) if len(recent_x) > 1 else 1.0
        var_y = np.var(recent_y) if len(recent_y) > 1 else 1.0
       
        # Lower variance = higher confidence
        confidence = 1.0 / (1.0 + var_x + var_y)
        return min(confidence, 1.0)

class EyeTracker:
    def __init__(self, duration=20, smoothing_window=5, confidence_threshold=3, simple_mode=False):
        """
        Initialize the eye tracker
       
        Args:
            duration: Recording duration in seconds
            smoothing_window: Number of frames to average for gaze smoothing
            confidence_threshold: Minimum detections needed for stable gaze
            simple_mode: Use simple detection similar to original code
        """
        # Load Haar cascades with error handling
        try:
            self.face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            )
            self.eye_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + "haarcascade_eye_tree_eyeglasses.xml"
            )
           
            if self.face_cascade.empty() or self.eye_cascade.empty():
                raise ValueError("Failed to load Haar cascades")
               
        except Exception as e:
            print(f" Error loading cascades: {e}")
            raise
       
        # Configuration
        self.duration = duration
        self.smoothing_window = smoothing_window
        self.confidence_threshold = confidence_threshold
        self.simple_mode = simple_mode
       
        # Tracking variables
        self.eye_log = []
        self.gaze_history = deque(maxlen=smoothing_window)
        self.frame_count = 0
        self.fps_counter = deque(maxlen=30)
       
        # More lenient detection parameters
        self.face_params = {
            'scaleFactor': 1.05,
            'minNeighbors': 4,
            'minSize': (60, 60),
            'maxSize': (400, 400)
        }
       
        self.eye_params = {
            'scaleFactor': 1.05,
            'minNeighbors': 3,
            'minSize': (20, 20),
            'maxSize': (100, 100)
        }
       
        # Gaze thresholds (more refined)
        self.gaze_thresholds = {
            'left': (0.0, 0.35),
            'right': (0.65, 1.0),
            'up': (0.0, 0.35),
            'down': (0.65, 1.0),
            'center': (0.35, 0.65)
        }
       
        # More lenient detection parameters
        self.face_params = {
            'scaleFactor': 1.05,
            'minNeighbors': 4,
            'minSize': (60, 60),
            'maxSize': (400, 400)
        }
    def detect_iris_simple(self, eye_roi):
        """Simple iris detection - closest to your original working code"""
        if eye_roi.size == 0:
            return None
       
        # Simple thresholding like your original code
        _, thresh = cv2.threshold(eye_roi, 50, 255, cv2.THRESH_BINARY_INV)
        thresh = cv2.medianBlur(thresh, 5)
       
        # Find contours
        contours, _ = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            # Largest dark contour = iris (exactly like your original)
            iris_contour = max(contours, key=cv2.contourArea)
            return cv2.boundingRect(iris_contour)
       
        return None
       
        self.eye_params = {
            'scaleFactor': 1.05,
            'minNeighbors': 3,
            'minSize': (20, 20),
            'maxSize': (100, 100)
        }
       
        # Gaze thresholds (more refined)
        self.gaze_thresholds = {
            'left': (0.0, 0.35),
            'right': (0.65, 1.0),
            'up': (0.0, 0.35),
            'down': (0.65, 1.0),
            'center': (0.35, 0.65)
        }
   
    def preprocess_frame(self, frame):
        """Simpler preprocessing to avoid over-processing"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
       
        # Light processing only - sometimes less is more
        gray = cv2.equalizeHist(gray)
       
        return gray
   
    def detect_iris(self, eye_roi, debug=False):
        """Robust iris detection with fallback methods"""
        if eye_roi.size == 0 or eye_roi.shape[0] < 20 or eye_roi.shape[1] < 20:
            return None
       
        # Method 1: Simple thresholding (similar to original but more robust)
        try:
            # Try multiple threshold values
            for threshold in [50, 60, 40, 70]:
                _, thresh = cv2.threshold(eye_roi, threshold, 255, cv2.THRESH_BINARY_INV)
                thresh = cv2.medianBlur(thresh, 5)
               
                # Find contours
                contours, _ = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
               
                if contours:
                    # Get largest contour
                    largest_contour = max(contours, key=cv2.contourArea)
                    area = cv2.contourArea(largest_contour)
                   
                    # More lenient area requirements
                    eye_area = eye_roi.shape[0] * eye_roi.shape[1]
                    min_area = max(20, eye_area * 0.02)  # At least 20 pixels or 2% of eye
                    max_area = eye_area * 0.8  # Up to 80% of eye area
                   
                    if min_area <= area <= max_area:
                        rect = cv2.boundingRect(largest_contour)
                        # Basic sanity check on dimensions
                        if rect[2] > 5 and rect[3] > 5:  # At least 5x5 pixels
                            return rect
           
            # Method 2: HoughCircles as fallback
            circles = cv2.HoughCircles(
                eye_roi,
                cv2.HOUGH_GRADIENT,
                dp=1,
                minDist=int(min(eye_roi.shape) * 0.3),
                param1=50,
                param2=30,
                minRadius=max(3, int(min(eye_roi.shape) * 0.1)),
                maxRadius=int(min(eye_roi.shape) * 0.4)
            )
           
            if circles is not None:
                circles = np.round(circles[0, :]).astype("int")
                # Take the first (most confident) circle
                x, y, r = circles[0]
                return (max(0, x-r), max(0, y-r), 2*r, 2*r)
           
            # Method 3: Simplest fallback - find darkest region
            if eye_roi.shape[0] > 10 and eye_roi.shape[1] > 10:
                # Find minimum value location
                min_val, _, min_loc, _ = cv2.minMaxLoc(eye_roi)
               
                # Create a small region around the darkest point
                h, w = eye_roi.shape
                size = min(h, w) // 3
                x = max(0, min_loc[0] - size//2)
                y = max(0, min_loc[1] - size//2)
                w = min(size, w - x)
                h = min(size, h - y)
               
                if w > 5 and h > 5:
                    return (x, y, w, h)
           
        except Exception as e:
            if debug:
                print(f"Iris detection error: {e}")
           
        return None
   
    def calculate_gaze_direction(self, iris_positions):
        """Enhanced gaze direction calculation with smoothing"""
        if len(iris_positions) < 2:
            return "unknown", False
       
        # Average both eyes
        avg_x = np.mean([pos[0] for pos in iris_positions])
        avg_y = np.mean([pos[1] for pos in iris_positions])
       
        # Add to history for smoothing
        self.gaze_history.append((avg_x, avg_y))
       
        if len(self.gaze_history) < self.confidence_threshold:
            return "calibrating", False
       
        # Calculate smoothed position
        smooth_x = np.mean([pos[0] for pos in self.gaze_history])
        smooth_y = np.mean([pos[1] for pos in self.gaze_history])
       
        # Determine gaze direction with hysteresis to reduce jitter
        horizontal_dir = "center"
        vertical_dir = "center"
       
        if smooth_x < self.gaze_thresholds['left'][1]:
            horizontal_dir = "left"
        elif smooth_x > self.gaze_thresholds['right'][0]:
            horizontal_dir = "right"
       
        if smooth_y < self.gaze_thresholds['up'][1]:
            vertical_dir = "up"
        elif smooth_y > self.gaze_thresholds['down'][0]:
            vertical_dir = "down"
       
        # Combine directions
        if horizontal_dir == "center" and vertical_dir == "center":
            gaze_direction = "forward"
            looking_forward = True
        elif horizontal_dir != "center" and vertical_dir == "center":
            gaze_direction = horizontal_dir
            looking_forward = False
        elif horizontal_dir == "center" and vertical_dir != "center":
            gaze_direction = vertical_dir
            looking_forward = False
        else:
            gaze_direction = f"{vertical_dir}-{horizontal_dir}"
            looking_forward = False
       
        return gaze_direction, looking_forward
   
    def draw_enhanced_annotations(self, frame, face_rect, eyes, gaze_info, fps):
        """Enhanced visual annotations"""
        x, y, w, h = face_rect
        gaze_direction, looking_forward, confidence = gaze_info
       
        # Face rectangle with confidence color
        color = (0, 255, 0) if looking_forward else (0, 165, 255)  # Green if forward, orange otherwise
        cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
       
        # Gaze direction with confidence indicator
        confidence_text = f"●" if confidence > 0.8 else "◐" if confidence > 0.5 else "○"
        gaze_text = f"{confidence_text} Gaze: {gaze_direction}"
       
        # Text background for better readability
        text_size = cv2.getTextSize(gaze_text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
        cv2.rectangle(frame, (x, y - 30), (x + text_size[0] + 10, y - 5), (0, 0, 0), -1)
        cv2.putText(frame, gaze_text, (x + 5, y - 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
       
        # FPS display
        cv2.putText(frame, f"FPS: {fps:.1f}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
       
        # Frame counter
        cv2.putText(frame, f"Frame: {self.frame_count}", (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
       
        return frame
   
    def calculate_confidence(self, iris_positions):
        """Calculate detection confidence based on consistency"""
        if len(self.gaze_history) < 2:
            return 0.0
       
        # Calculate variance in recent positions
        recent_x = [pos[0] for pos in list(self.gaze_history)[-5:]]
        recent_y = [pos[1] for pos in list(self.gaze_history)[-5:]]
       
        var_x = np.var(recent_x) if len(recent_x) > 1 else 1.0
        var_y = np.var(recent_y) if len(recent_y) > 1 else 1.0
       
        # Lower variance = higher confidence
        confidence = 1.0 / (1.0 + var_x + var_y)
        return min(confidence, 1.0)
   
    def run(self, output_file="eye_log_improved.json"):
        """Main tracking loop"""
        print("Starting improved eye tracking...")
        print("Press 'q' to quit, 'r' to reset gaze history, 's' to save current log")
       
        # Try different camera indices if default fails
        cap = None
        for camera_idx in [0, 1, 2]:
            print(f"Trying camera index {camera_idx}...")
            cap = cv2.VideoCapture(camera_idx)
            if cap.isOpened():
                print(f" Camera {camera_idx} opened successfully")
                break
            else:
                print(f" Camera {camera_idx} failed to open")
                cap.release()
                cap = None
       
        if cap is None:
            print(" Error: Could not open any camera")
            return
       
        # Set camera properties for better performance
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS, 30)
       
        # Test if we can read a frame
        ret, test_frame = cap.read()
        if not ret:
            print(" Error: Could not read test frame from camera")
            cap.release()
            return
        else:
            print(f" Camera working - frame size: {test_frame.shape}")
       
        start_time = time.time()
       
        try:
            while True:
                frame_start = time.time()
                ret, frame = cap.read()
               
                if not ret:
                    print(" Error: Could not read frame")
                    break
               
                self.frame_count += 1
               
                # Preprocess frame
                gray = self.preprocess_frame(frame)
               
                # Detect faces
                faces = self.face_cascade.detectMultiScale(gray, **self.face_params)
               
                current_fps = 0
                if self.fps_counter:
                    current_fps = len(self.fps_counter) / sum(self.fps_counter)
               
                if len(faces) > 0:
                    # Use the largest face
                    face = max(faces, key=lambda f: f[2] * f[3])
                    x, y, w, h = face
                   
                    roi_gray = gray[y:y+h, x:x+w]
                    roi_color = frame[y:y+h, x:x+w]
                   
                    # Detect eyes
                    eyes = self.eye_cascade.detectMultiScale(roi_gray, **self.eye_params)
                   
                    if len(eyes) >= 1:  # Accept even single eye detection
                        # Sort eyes left to right and take up to two
                        eyes = sorted(eyes, key=lambda e: e[0])[:2]
                       
                        iris_positions = []
                        debug_info = []
                       
                        for i, (ex, ey, ew, eh) in enumerate(eyes):
                            # Draw eye rectangle
                            cv2.rectangle(roi_color, (ex, ey), (ex+ew, ey+eh), (255, 0, 0), 2)
                           
                            # Extract eye region with some padding
                            pad = 2
                            eye_y1 = max(0, ey - pad)
                            eye_y2 = min(roi_gray.shape[0], ey + eh + pad)
                            eye_x1 = max(0, ex - pad)
                            eye_x2 = min(roi_gray.shape[1], ex + ew + pad)
                           
                            eye_roi = roi_gray[eye_y1:eye_y2, eye_x1:eye_x2]
                           
                            # Detect iris with debug info
                            if self.simple_mode:
                                iris_rect = self.detect_iris_simple(eye_roi)
                            else:
                                iris_rect = self.detect_iris(eye_roi, debug=True)
                           
                            if iris_rect:
                                ix, iy, iw, ih = iris_rect
                               
                                # Adjust coordinates back to original eye position
                                adj_ix = ix + eye_x1 - ex
                                adj_iy = iy + eye_y1 - ey
                               
                                # Draw iris
                                cv2.rectangle(roi_color, (ex + adj_ix, ey + adj_iy),
                                            (ex + adj_ix + iw, ey + adj_iy + ih), (0, 0, 255), 2)
                               
                                # Calculate relative position
                                iris_center_x = (adj_ix + iw / 2) / ew
                                iris_center_y = (adj_iy + ih / 2) / eh
                               
                                # Clamp values to reasonable range
                                iris_center_x = max(0.0, min(1.0, iris_center_x))
                                iris_center_y = max(0.0, min(1.0, iris_center_y))
                               
                                iris_positions.append((iris_center_x, iris_center_y))
                                debug_info.append(f"Eye {i+1}: ({iris_center_x:.2f}, {iris_center_y:.2f})")
                            else:
                                debug_info.append(f"Eye {i+1}: No iris detected")
                       
                        # Show debug info
                        for j, info in enumerate(debug_info):
                            cv2.putText(frame, info, (10, 120 + j*20),
                                      cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 0), 1)
                       
                        # Calculate gaze direction
                        if iris_positions:
                            gaze_direction, looking_forward = self.calculate_gaze_direction(iris_positions)
                            confidence = self.calculate_confidence(iris_positions)
                        else:
                            gaze_direction, looking_forward = "no_iris", False
                            confidence = 0.0
                       
                        # Enhanced annotations
                        frame = self.draw_enhanced_annotations(
                            frame, face, eyes, (gaze_direction, looking_forward, confidence), current_fps
                        )
                       
                        # Log data
                        self.eye_log.append({
                            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                            "frame_number": self.frame_count,
                            "face_position": [int(x), int(y), int(w), int(h)],
                            "eyes": [{"pos": [int(ex), int(ey), int(ew), int(eh)],
                                    "iris_relative": iris_pos}
                                   for (ex, ey, ew, eh), iris_pos in zip(eyes, iris_positions)],
                            "gaze_direction": gaze_direction,
                            "looking_forward": looking_forward,
                            "confidence": round(confidence, 3),
                            "fps": round(current_fps, 1)
                        })
                    else:
                        # No eyes detected
                        cv2.putText(frame, "No eyes detected", (x, y - 10),
                                  cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                else:
                    # No face detected
                    cv2.putText(frame, "No face detected", (10, 90),
                              cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
               
                # Display frame
                cv2.imshow("Enhanced Eye Tracking", frame)
               
                # Handle key presses
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break
                elif key == ord('r'):
                    self.gaze_history.clear()
                    print(" Gaze history reset")
                elif key == ord('s'):
                    self.save_log(output_file)
                    print(f" Log saved to {output_file}")
               
                # Check time limit
                if time.time() - start_time > self.duration:
                    print(" Time limit reached, stopping...")
                    break
               
                # Calculate FPS
                frame_time = time.time() - frame_start
                self.fps_counter.append(frame_time)
       
        except KeyboardInterrupt:
            print("\n Interrupted by user")
       
        finally:
            cap.release()
            cv2.destroyAllWindows()
           
            # Save final log
            self.save_log(output_file)
            print(f"✅ Final eye log saved with {len(self.eye_log)} entries to {output_file}")
   
    def save_log(self, filename):
        """Save tracking log to JSON file"""
        try:
            with open(filename, "w") as f:
                json.dump({
                    "metadata": {
                        "total_frames": len(self.eye_log),
                        "duration_seconds": self.duration,
                        "simple_mode": self.simple_mode,
                        "tracking_params": {
                            "smoothing_window": self.smoothing_window,
                            "confidence_threshold": self.confidence_threshold,
                            "gaze_thresholds": getattr(self, 'gaze_thresholds', {}),
                            "face_params": getattr(self, 'face_params', {}),
                            "eye_params": getattr(self, 'eye_params', {})
                        }
                    },
                    "tracking_data": self.eye_log
                }, f, indent=2)
        except Exception as e:
            print(f"❌ Error saving log: {e}")
            import traceback
            traceback.print_exc()
 
def main():
    parser = argparse.ArgumentParser(description="Enhanced Eye Tracking System")
    parser.add_argument("--duration", "-d", type=int, default=20, help="Recording duration in seconds")
    parser.add_argument("--smoothing", "-s", type=int, default=5, help="Smoothing window size")
    parser.add_argument("--output", "-o", type=str, default="eye_log_improved.json", help="Output file name")
    parser.add_argument("--simple", action="store_true", help="Use simple detection mode (like original)")
   
    args = parser.parse_args()
   
    tracker = EyeTracker(
        duration=args.duration,
        smoothing_window=args.smoothing,
        confidence_threshold=3,
        simple_mode=args.simple
    )
   
    print(f" Detection mode: {'Simple' if args.simple else 'Advanced'}")
    tracker.run(args.output)
 
if __name__ == "__main__":
    main()