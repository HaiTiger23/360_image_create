import os
import secrets
import cv2
from flask import Flask, render_template, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from main import stitch_images, crop_content, convert_to_equirectangular, set_gpano_metadata, fill_black_holes
from advanced_stitch import stitch_images_advanced

import numpy as np

app = Flask(__name__)
# ... (rest of config)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 * 1024 # 16GB max upload (images can be large)

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'files[]' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    files = request.files.getlist('files[]')
    
    if not files or files[0].filename == '':
        return jsonify({'error': 'No selected file'}), 400

    # Create a unique session folder for this upload batch
    session_id = secrets.token_hex(8)
    session_folder = os.path.join(app.config['UPLOAD_FOLDER'], session_id)
    os.makedirs(session_folder, exist_ok=True)
    
    saved_paths = []
    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            path = os.path.join(session_folder, filename)
            file.save(path)
            saved_paths.append(path)
    
    if not saved_paths:
          return jsonify({'error': 'No valid images saved'}), 400

    # Trigger stitching
    output_filename = 'result_360.jpg'
    output_path = os.path.join(session_folder, output_filename)
    
    # Try Advanced Stitching first (for Spherical warp)
    horizon_y = None
    try:
        ret = stitch_images_advanced(saved_paths)
        if len(ret) == 3:
            success, result_or_msg, horizon_y = ret
        else:
            success, result_or_msg = ret
    except Exception as e:
        print(f"Advanced stitching invocation failed: {e}")
        success = False
        result_or_msg = str(e)
    
    if not success:
        print(f"Advanced stitching failed ({result_or_msg}), falling back to simple stitching...")
        success, result_or_msg = stitch_images(saved_paths)
        horizon_y = None
    
    if success:
        img = result_or_msg
        
        try:
            if not isinstance(img, np.ndarray):
                 print(f"Error: Stitched result is not a numpy array. It is {type(img)}: {img}")
                 return jsonify({'success': False, 'message': "Stitching returned invalid data"}), 500
            
            # 1. Crop valid content (remove outer black borders)
            img, crop_y_shift = crop_content(img)
             
            # If we cropped, the horizon_y index shifts!
            if horizon_y is not None:
                horizon_y -= crop_y_shift
             
            # 2. Embed into strict 2:1 Equirectangular Canvas (Fixes geometry)
            img = convert_to_equirectangular(img, horizon_y)
             
            # 3. Fill holes (Top/Bottom and internal gaps)
            img = fill_black_holes(img)
             
            # Save with HIGHEST QUALITY (100)
            cv2.imwrite(output_path, img, [int(cv2.IMWRITE_JPEG_QUALITY), 100])
             
            # 4. Inject Metadata
            try:
                set_gpano_metadata(output_path, img.shape[1], img.shape[0])
            except Exception as e:
                print(f"Metadata injection failed: {e}")
            
            # 5. Cleanup: Delete original uploaded images
            print("Cleaning up uploaded files...")
            for p in saved_paths:
                try:
                    if os.path.exists(p):
                        os.remove(p)
                except Exception as e:
                    print(f"Failed to delete {p}: {e}")

        except Exception as e:
            print(f"Post-processing failed: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'message': f"Post-processing failed: {str(e)}"}), 500
        
        # Return the URL to the result
        result_url = f"/result/{session_id}/{output_filename}"
        return jsonify({'success': True, 'message': "Stitching & Stretching successful!", 'image_url': result_url})
    else:
        return jsonify({'success': False, 'message': result_or_msg}), 500

@app.route('/result/<session_id>/<filename>')
def uploaded_file(session_id, filename):
    return send_from_directory(os.path.join(app.config['UPLOAD_FOLDER'], session_id), filename)

if __name__ == '__main__':
    app.run(debug=True, port=5001)
