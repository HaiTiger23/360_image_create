import cv2
import sys

print(f"OpenCV Version: {cv2.__version__}")
try:
    print(f"cv2.detail available: {hasattr(cv2, 'detail')}")
    if hasattr(cv2, 'detail'):
        print(dir(cv2.detail))
except Exception as e:
    print(f"Error checking cv2.detail: {e}")

try:
    s = cv2.Stitcher_create()
    print(f"Stitcher works. Pano Confidence default: {s.panoConfidenceThresh()}")
except Exception as e:
    print(f"Stitcher error: {e}")
