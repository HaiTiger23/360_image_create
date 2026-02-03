import cv2
import sys

try:
    s = cv2.Stitcher_create()
    print("Stitcher methods:", dir(s))
except Exception as e:
    print(f"Stitcher error: {e}")

print(f"cv2.PyRotationWarper exists: {hasattr(cv2, 'PyRotationWarper')}")
if hasattr(cv2, 'PyRotationWarper'):
     try:
         w = cv2.PyRotationWarper('spherical', 1000)
         print("PyRotationWarper('spherical') created successfully")
     except Exception as e:
         print(f"PyRotationWarper error: {e}")
