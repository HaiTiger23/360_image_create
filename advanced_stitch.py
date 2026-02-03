import cv2
import sys
import numpy as np

def stitch_images_advanced(img_names):
    """
    Advanced stitching with Spherical Warping.
    Returns:
        success (bool)
        result (numpy array or error message string)
    """
    # Constants
    try:
        # Standard parameters
        work_megapix = 0.6
        seam_megapix = 0.1
        compose_megapix = -1 # Keep original resolution
        conf_thresh = 0.15 # EXTREMELY PERMISSIVE to include top/bottom
        wave_correct = cv2.detail.WAVE_CORRECT_HORIZ
        warp_type = 'spherical' # FORCE SPHERICAL for 360 look
        blend_type = 'multiband'
        blend_strength = 5

        # 1. Loading Images
        print("Loading images specifically for stitching...")
        full_img_list = []
        for name in img_names:
            img = cv2.imread(name)
            if img is not None:
                full_img_list.append(img)
            else:
                print(f"Failed to load {name}")
        
        if len(full_img_list) < 2:
            return False, "Not enough images"

        # 2. Resize for Feature Finding
        work_imgs = []
        images = []
        is_work_scale_set = False
        is_seam_scale_set = False
        is_compose_scale_set = False
        
        for full_img in full_img_list:
            if not is_work_scale_set:
                work_scale = min(1.0, np.sqrt(work_megapix * 1e6 / (full_img.shape[0] * full_img.shape[1])))
                is_work_scale_set = True
            
            img = cv2.resize(src=full_img, dsize=None, fx=work_scale, fy=work_scale, interpolation=cv2.INTER_LINEAR_EXACT)
            work_imgs.append(img)
            images.append(full_img) # Keep ref

        # 3. Feature Finding
        print("Finding features...")
        finder = cv2.SIFT_create() if hasattr(cv2, 'SIFT_create') else cv2.ORB_create() 
        features = []
        for img in work_imgs:
            if hasattr(cv2.detail, 'computeImageFeatures2'):
                 features.append(cv2.detail.computeImageFeatures2(finder, img))
            else:
                 features.append(cv2.detail.computeImageFeatures(finder, img))

        # 4. Matching
        print("Matching features...")
        matcher = cv2.detail.BestOf2NearestMatcher_create(False, 0.15)
        matches = matcher.apply2(features)
        matcher.collectGarbage()

        # 5. Estimating Cameras
        print("Estimating camera parameters...")
        estimator = cv2.detail_HomographyBasedEstimator()
        b, cameras = estimator.apply(features, matches, None)
        
        if not b:
             return False, "Homography estimation failed."
             
        print(f"DEBUG: Stitched {len(cameras)} out of {len(full_img_list)} input images.")

        print("Adjusting bundle...")
        adjuster = cv2.detail_BundleAdjusterRay()
        adjuster.setConfThresh(conf_thresh)
        b, cameras = adjuster.apply(features, matches, cameras)
        if not b:
             return False, "Camera adjustment failed."

        # Wave Correction (Leveling)
        rmats = []
        for cam in cameras:
            rmats.append(np.copy(cam.R).astype(np.float32))
        rmats = cv2.detail.waveCorrect(rmats, wave_correct)
        for idx, cam in enumerate(cameras):
            cam.R = rmats[idx]

        # 6. Compositing Setup
        print("Preparing composite...")
        # Scale cameras
        if not is_compose_scale_set:
             compose_scale = 1.0
             is_compose_scale_set = True
             
        # Compute warped image scale
        focals = [cam.focal for cam in cameras]
        warped_image_scale = np.median(focals)
        
        # Warper
        warper_creator = cv2.PyRotationWarper(warp_type, warped_image_scale * compose_scale)
        
        # Image Processing Loop
        # Pre-calculate sizes
        corners = []
        sizes = []
        masks_warped = []
        images_warped = []
        
        for idx, full_img in enumerate(full_img_list):
            K = cameras[idx].K().astype(np.float32)
            
            roi = warper_creator.warp(full_img, K, cameras[idx].R, cv2.INTER_LINEAR, cv2.BORDER_REFLECT)
            corners.append(roi[0])
            images_warped.append(roi[1])
            sizes.append((roi[1].shape[1], roi[1].shape[0])) # w, h
            
            # Create mask
            mask = np.ones((full_img.shape[0], full_img.shape[1]), dtype=np.uint8) * 255
            roi_mask = warper_creator.warp(mask, K, cameras[idx].R, cv2.INTER_NEAREST, cv2.BORDER_CONSTANT)
            masks_warped.append(roi_mask[1])

        # Blender
        dest_sz = cv2.detail.resultRoi(corners, sizes)
        blend_width = np.sqrt(dest_sz[2] * dest_sz[3]) * blend_strength / 100
        
        blender = cv2.detail.Blender_createDefault(cv2.detail.Blender_MULTI_BAND)
        blender.prepare(dest_sz)
        
        print("Blending...")
        for i in range(len(images_warped)):
            img_warped = images_warped[i]
            mask_warped = masks_warped[i]
            corner = corners[i]
            
            img_warped_s = img_warped.astype(np.int16)
            blender.feed(img_warped_s, mask_warped, corner)
        
        result, result_mask = blender.blend(None, None)
        
        # Post-Processing
        # Convert back to uint8
        result = cv2.convertScaleAbs(result)
        
        print("Advanced Stitching Complete.")
        
        # Calculate horizon offset relative to the top of the image
        # In spherical warping, y=0 is the horizon.
        # The image starts at dest_sz[1] (y_min).
        # So the horizon is at index 0 - dest_sz[1] = -dest_sz[1]
        horizon_y = -dest_sz[1]
        
        # Return the actual image array and the horizon offset
        return True, result, horizon_y

    except Exception as e:
        print(f"Advanced stitching error: {e}")
        import traceback
        traceback.print_exc()
        return False, f"Advanced stitching failed: {str(e)}", 0
