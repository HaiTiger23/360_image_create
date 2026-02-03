const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const fileList = document.getElementById('file-list');
const progressContainer = document.getElementById('progress-container');
const resultContainer = document.getElementById('result-container');
const errorMessage = document.getElementById('error-message');
const resultImage = document.getElementById('result-image');
const downloadLink = document.getElementById('download-link');

let filesToUpload = [];

// Drag & Drop events
['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
    dropZone.addEventListener(eventName, preventDefaults, false);
});

function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
}

['dragenter', 'dragover'].forEach(eventName => {
    dropZone.addEventListener(eventName, highlight, false);
});

['dragleave', 'drop'].forEach(eventName => {
    dropZone.addEventListener(eventName, unhighlight, false);
});

function highlight(e) {
    dropZone.classList.add('dragover');
}

function unhighlight(e) {
    dropZone.classList.remove('dragover');
}

dropZone.addEventListener('drop', handleDrop, false);

function handleDrop(e) {
    const dt = e.dataTransfer;
    const files = dt.files;
    handleFiles(files);
}

fileInput.addEventListener('change', function() {
    handleFiles(this.files);
});

function handleFiles(files) {
    filesToUpload = [...files];
    updateFileList();
    
    if (filesToUpload.length >= 2) {
        uploadAndStitch();
    } else {
        showError("Please select at least 2 images.");
    }
}

function updateFileList() {
    fileList.innerHTML = '';
    fileList.classList.remove('hidden');
    filesToUpload.forEach(file => {
        const item = document.createElement('div');
        item.className = 'file-item';
        // Add a small icon
        item.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"></path><polyline points="13 2 13 9 20 9"></polyline></svg> ${file.name}`;
        fileList.appendChild(item);
    });
}

function uploadAndStitch() {
    const formData = new FormData();
    filesToUpload.forEach(file => {
        formData.append('files[]', file);
    });

    // Show loading
    dropZone.classList.add('hidden');
    fileList.classList.add('hidden');
    progressContainer.classList.remove('hidden');
    errorMessage.classList.add('hidden');

    fetch('/upload', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        progressContainer.classList.add('hidden');
        if (data.success) {
            showResult(data.image_url);
        } else {
            showError(data.message || 'An error occurred during stitching.');
            // Show upload area again to retry
            dropZone.classList.remove('hidden');
        }
    })
    .catch(error => {
        progressContainer.classList.add('hidden');
        showError('Network error or server failed to respond.');
        dropZone.classList.remove('hidden');
        console.error('Error:', error);
    });
}

function showResult(imageUrl) {
    resultImage.src = imageUrl;
    downloadLink.href = imageUrl;
    resultContainer.classList.remove('hidden');
}

function showError(msg) {
    errorMessage.textContent = msg;
    errorMessage.classList.remove('hidden');
}
