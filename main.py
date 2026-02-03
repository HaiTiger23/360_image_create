import cv2
import os
import numpy as np

def stitch_images(image_paths):
    """
    Stitch list of images into a panorama using OpenCV.
    Args:
        image_paths (list): List of file paths to images.
    Returns:
        bool: True if successful, False otherwise.
        var: Result Image (numpy array) or Error message (str).
    """
    if not image_paths or len(image_paths) < 2:
        return False, "Need at least 2 images to stitch."

    print("Loading images for switching...")
    images = []
    for path in image_paths:
        img = cv2.imread(path)
        if img is not None:
            images.append(img)
    
    if len(images) < 2:
        return False, "Could not load enough valid images."

    # Use standard stitcher
    stitcher = cv2.Stitcher_create() if hasattr(cv2, 'Stitcher_create') else cv2.createStitcher(False)
    status, result = stitcher.stitch(images)
    
    if status == cv2.Stitcher_OK:
        return True, result
    else:
        return False, f"Stitching failed code: {status}"

def crop_content(img):
    """
    Crops the image to the bounding box of non-black pixels.
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 1, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if contours:
        # Find limiting bounding box of all content
        x_min, y_min = float('inf'), float('inf')
        x_max, y_max = float('-inf'), float('-inf')
        
        for c in contours:
            x, y, w, h = cv2.boundingRect(c)
            x_min = min(x_min, x)
            y_min = min(y_min, y)
            x_max = max(x_max, x + w)
            y_max = max(y_max, y + h)
            
        return img[int(y_min):int(y_max), int(x_min):int(x_max)]
        
    return img

def fill_black_holes(img):
    """
    Fills black regions (0,0,0) with a blurred version of the surrounding content.
    Optimized for performance using downscaling.
    """
    # 1. Create mask of black pixels
    # Gray conversion
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # Binary mask: 0 where pixel is > 0 (content), 255 where pixel is 0 (black)
    _, mask = cv2.threshold(gray, 1, 255, cv2.THRESH_BINARY_INV)
    
    if np.count_nonzero(mask) == 0:
        return img
    
    h, w = img.shape[:2]
    small_h, small_w = h // 10, w // 10
    small_h = max(small_h, 32)
    small_w = max(small_w, 32)
    
    small_img = cv2.resize(img, (small_w, small_h), interpolation=cv2.INTER_LINEAR)
    small_mask = cv2.resize(mask, (small_w, small_h), interpolation=cv2.INTER_NEAREST)
    
    print("Inpainting background...")
    try:
         inpainted = cv2.inpaint(small_img, small_mask, 3, cv2.INPAINT_TELEA)
    except:
         # Minimal fallback if inpaint fails (e.g. empty mask check failed?)
         return img

    blurred = cv2.GaussianBlur(inpainted, (21, 21), 0)
    background = cv2.resize(blurred, (w, h), interpolation=cv2.INTER_CUBIC)
    
    mask_3c = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
    img_content = cv2.bitwise_and(img, cv2.bitwise_not(mask_3c))
    bg_content = cv2.bitwise_and(background, mask_3c)
    result = cv2.add(img_content, bg_content)
    
    return result

def stretch_to_360(img):
    """
    Stretches the image to a 2:1 aspect ratio (Equirectangular).
    """
    height, width = img.shape[:2]
    target_width = width
    target_height = int(width / 2)
    
    if height > target_height:
        target_height = height
        target_width = height * 2
        
    print(f"Stretching {width}x{height} to {target_width}x{target_height} for 360 format.")
    resized = cv2.resize(img, (target_width, target_height), interpolation=cv2.INTER_LANCZOS4)
    return resized

def set_gpano_metadata(image_path, width, height):
    """
    Injects Google Photo Sphere XMP metadata into the JPEG file.
    """
    full_width = width
    full_height = int(width / 2)
    
    xmp_data = f'''<x:xmpmeta xmlns:x="adobe:ns:meta/">
    <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
        <rdf:Description rdf:about="" xmlns:GPano="http://ns.google.com/photos/1.0/panorama/">
            <GPano:UsePanoramaViewer>True</GPano:UsePanoramaViewer>
            <GPano:ProjectionType>equirectangular</GPano:ProjectionType>
            <GPano:FullPanoWidthPixels>{full_width}</GPano:FullPanoWidthPixels>
            <GPano:FullPanoHeightPixels>{full_height}</GPano:FullPanoHeightPixels>
            <GPano:CroppedAreaImageWidthPixels>{width}</GPano:CroppedAreaImageWidthPixels>
            <GPano:CroppedAreaImageHeightPixels>{height}</GPano:CroppedAreaImageHeightPixels>
            <GPano:CroppedAreaLeftPixels>0</GPano:CroppedAreaLeftPixels>
            <GPano:CroppedAreaTopPixels>{int((full_height - height) / 2)}</GPano:CroppedAreaTopPixels>
        </rdf:Description>
    </rdf:RDF>
</x:xmpmeta>'''

    header = b"http://ns.adobe.com/xap/1.0/\x00"
    payload = header + xmp_data.encode('utf-8')
    length = len(payload) + 2
    
    marker = b'\xFF\xE1' + length.to_bytes(2, byteorder='big') + payload
    
    with open(image_path, 'rb') as f:
        data = f.read()
        
    if data[:2] != b'\xFF\xD8':
        print("Error: Not a valid JPEG file (missing SOI).")
        return

    # Check for APP0 (JFIF)
    pos = 2
    if data[pos:pos+2] == b'\xFF\xE0':
        # Get length of APP0
        length = int.from_bytes(data[pos+2:pos+4], byteorder='big')
        pos += 2 + length
    
    # Insert XMP at pos
    new_data = data[:pos] + marker + data[pos:]
    
    with open(image_path, 'wb') as f:
        f.write(new_data)
    print(f"Metadata injected successfully at offset {pos}.")
