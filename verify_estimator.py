import cv2
import numpy as np

print(f"OpenCV: {cv2.__version__}")
try:
    est = cv2.detail_HomographyBasedEstimator()
    print("Estimator created.")
    print(f"Methods: {dir(est)}")
    
    # Check if 'estimate' exists or 'apply'
    if hasattr(est, 'estimate'):
        print("Has 'estimate' method.")
    if hasattr(est, 'apply'):
        print("Has 'apply' method.")
except Exception as e:
    print(f"Error: {e}")
