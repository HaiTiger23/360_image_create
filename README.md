# 360 Image Stitcher

A web-based tool to stitch multiple overlapping images into a seamless 360-degree equirectangular panorama compatible with Google Photos and Facebook.

## Features

- **Advanced Stitching**: Uses OpenCV's spherical warping to create correct 360 geometry.
- **Auto-Correction**: Automatically crops black borders and fills missing zenith/nadir areas with "Smart Blur".
- **Google Photos Ready**: Injects correct XMP metadata so platforms recognize the image as interactive 360 content.
- **Optimized**: Handles large datasets and cleans up uploads automatically.

## Installation

1. Clone the repository.
2. Create time a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   *(Note: Ensure you have `opencv-python`, `flask`, `numpy`)*

## Usage

1. Start the server:
   ```bash
   ./venv/bin/python app.py
   ```
2. Open your browser to `http://127.0.0.1:5001`.
3. Drag and drop your overlapping photos (e.g., from a drone or camera rotation).
4. Wait for the processing to complete.
5. Download the result and upload to Google Photos!

## Troubleshooting

- **"Not enough images"**: Ensure images have at least 30-50% overlap.
- **Port Error**: If port 5001 is busy, kill the process or change the port in `app.py`.
