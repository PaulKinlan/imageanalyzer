const dropArea = document.getElementById('drop-area');
const fileElem = document.getElementById('fileElem');
const gallery = document.getElementById('gallery');
const results = document.getElementById('results');
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

function handleFiles(event) {
    const files = event.target ? event.target.files : event;
    [...files].forEach((file, index) => {
        uploadFile(file, index);
        previewFile(file);
    });
}

function previewFile(file) {
    const reader = new FileReader();
    reader.readAsDataURL(file);
    reader.onloadend = function() {
        const img = document.createElement('img');
        img.src = reader.result;
        img.classList.add('w-full', 'h-32', 'object-cover', 'rounded');
        gallery.appendChild(img);
    }
}

function uploadFile(file, index) {
    if (index >= 10) {
        showError('You can only upload up to 10 images at a time.');
        return;
    }

    if (!file.type.startsWith('image/')) {
        showError('Please upload only image files.');
        return;
    }

    const formData = new FormData();
    formData.append('file', file);
    formData.append('index', index);

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
            displayResult(file.name, data.description, index);
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

function displayResult(fileName, analysisResult, index) {
    const resultDiv = document.createElement('div');
    resultDiv.classList.add('mt-4', 'p-4', 'bg-gray-100', 'rounded');
    resultDiv.innerHTML = `
        <h3 class="font-bold">Image ${index + 1}: ${fileName}</h3>
        <p>${analysisResult}</p>
    `;
    results.appendChild(resultDiv);
    error.classList.add('hidden');
}

function showError(message) {
    error.textContent = message;
    error.classList.remove('hidden');
}
