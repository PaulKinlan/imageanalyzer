const dropArea = document.getElementById('drop-area');
const fileElem = document.getElementById('fileElem');
const gallery = document.getElementById('gallery');
const result = document.getElementById('result');
const description = document.getElementById('description');
const error = document.getElementById('error');

if (dropArea) {
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach(eventName => {
        dropArea.addEventListener(eventName, highlight, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, unhighlight, false);
    });

    function highlight() {
        dropArea.classList.add('highlight');
    }

    function unhighlight() {
        dropArea.classList.remove('highlight');
    }

    dropArea.addEventListener('drop', handleDrop, false);
    fileElem.addEventListener('change', handleFiles, false);
}

function handleDrop(e) {
    const dt = e.dataTransfer;
    const files = dt.files;
    handleFiles(files);
}

function handleFiles(files) {
    if (files instanceof FileList) {
        ([...files]).forEach(uploadFile);
    } else if (files.target && files.target.files) {
        ([...files.target.files]).forEach(uploadFile);
    }
}

function uploadFile(file) {
    if (!file.type.startsWith('image/')) {
        showError('Please upload an image file.');
        return;
    }

    const formData = new FormData();
    formData.append('file', file);

    fetch('/upload', {
        method: 'POST',
        body: formData
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.json();
    })
    .then(data => {
        if (data.error) {
            showError(data.error);
        } else {
            displayResult(file, data.description);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        if (error.message === 'Network response was not ok') {
            showError('You need to be logged in to upload images.');
        } else {
            showError('An error occurred while uploading the image.');
        }
    });
}

function displayResult(file, analysisResult) {
    gallery.innerHTML = '';
    const img = document.createElement('img');
    img.src = URL.createObjectURL(file);
    img.onload = () => URL.revokeObjectURL(img.src);
    gallery.appendChild(img);

    description.textContent = analysisResult;
    result.classList.remove('hidden');
    error.classList.add('hidden');
}

function showError(message) {
    error.textContent = message;
    error.classList.remove('hidden');
    result.classList.add('hidden');
}
