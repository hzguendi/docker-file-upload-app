document.addEventListener('DOMContentLoaded', function() {
    const dropArea = document.getElementById('drop-area');
    const fileInput = document.getElementById('file-input');
    const fileInfo = document.getElementById('file-info');
    const uploadForm = document.getElementById('upload-form');
    const uploadButton = document.querySelector('.upload-button');
    const progressContainer = document.getElementById('progress-container');
    const progressBar = document.getElementById('progress-bar');
    const statusMessage = document.getElementById('status-message');

    // Prevent default drag behaviors
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, preventDefaults, false);
        document.body.addEventListener(eventName, preventDefaults, false);
    });

    // Highlight drop area when dragging over it
    ['dragenter', 'dragover'].forEach(eventName => {
        dropArea.addEventListener(eventName, highlight, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, unhighlight, false);
    });

    // Handle dropped files
    dropArea.addEventListener('drop', handleDrop, false);

    // Handle selected files
    fileInput.addEventListener('change', handleFiles);

    // Handle form submission
    uploadForm.addEventListener('submit', handleUpload);

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    function highlight() {
        dropArea.classList.add('highlight');
    }

    function unhighlight() {
        dropArea.classList.remove('highlight');
    }

    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        
        if (files.length > 0) {
            fileInput.files = files;
            handleFiles();
        }
    }

    function handleFiles() {
        const file = fileInput.files[0];
        if (!file) return;
        
        displayFileInfo(file);
        validateFile(file);
    }

    function displayFileInfo(file) {
        const fileSizeMB = (file.size / (1024 * 1024)).toFixed(2);
        
        fileInfo.innerHTML = `
            <p><strong>File name:</strong> ${file.name}</p>
            <p><strong>File type:</strong> ${file.type || 'Unknown'}</p>
            <p><strong>Size:</strong> ${fileSizeMB} MB</p>
        `;
        
        fileInfo.classList.add('show');
    }

    function validateFile(file) {
        // Get max file size from page
        const maxSizeEl = document.querySelector('.restrictions strong');
        const maxSizeText = maxSizeEl ? maxSizeEl.textContent : '100 MB';
        const maxSize = parseFloat(maxSizeText.replace(' MB', ''));
        
        // Check file size
        const fileSizeMB = file.size / (1024 * 1024);
        if (fileSizeMB > maxSize) {
            showStatus(`File size exceeds the maximum allowed size of ${maxSize} MB`, 'error');
            uploadButton.disabled = true;
            return false;
        }
        
        // Check file extension
        const blacklistedExtensions = getBlacklistedExtensions();
        const whitelistedExtensions = getWhitelistedExtensions();
        const fileExt = '.' + file.name.split('.').pop().toLowerCase();
        
        if (blacklistedExtensions.includes(fileExt)) {
            showStatus(`File type ${fileExt} is not allowed`, 'error');
            uploadButton.disabled = true;
            return false;
        }
        
        if (whitelistedExtensions.length > 0 && !whitelistedExtensions.includes(fileExt)) {
            showStatus(`Only ${whitelistedExtensions.join(', ')} files are allowed`, 'error');
            uploadButton.disabled = true;
            return false;
        }
        
        // Clear previous status
        clearStatus();
        uploadButton.disabled = false;
        return true;
    }
    
    function getBlacklistedExtensions() {
        const blacklistEl = document.querySelectorAll('.restrictions strong')[1];
        if (!blacklistEl) return [];
        
        const blacklistText = blacklistEl.textContent;
        return blacklistText.split(', ').map(ext => ext.trim());
    }
    
    function getWhitelistedExtensions() {
        const whitelistEl = document.querySelectorAll('.restrictions strong')[2];
        if (!whitelistEl) return [];
        
        const whitelistText = whitelistEl.textContent;
        return whitelistText.split(', ').map(ext => ext.trim());
    }

    function handleUpload(e) {
        e.preventDefault();
        
        const file = fileInput.files[0];
        if (!file) {
            showStatus('Please select a file first', 'error');
            return;
        }
        
        if (!validateFile(file)) {
            return;
        }
        
        uploadFile(file);
    }

    function uploadFile(file) {
        const xhr = new XMLHttpRequest();
        const formData = new FormData();
        
        formData.append('file', file);
        
        xhr.open('POST', '/upload', true);
        
        // Set up authentication from browser's authentication dialog
        xhr.withCredentials = true;
        
        // Track upload progress
        xhr.upload.addEventListener('progress', function(e) {
            if (e.lengthComputable) {
                const percentComplete = (e.loaded / e.total) * 100;
                progressContainer.classList.add('show');
                progressBar.style.width = percentComplete + '%';
            }
        }, false);
        
        // Handle response
        xhr.onload = function() {
            if (xhr.status >= 200 && xhr.status < 300) {
                showStatus('File uploaded successfully!', 'success');
                uploadForm.reset();
                fileInfo.classList.remove('show');
                setTimeout(() => {
                    progressContainer.classList.remove('show');
                    progressBar.style.width = '0%';
                }, 2000);
            } else {
                let errorMessage = 'Upload failed';
                try {
                    const response = JSON.parse(xhr.responseText);
                    errorMessage = response.detail || errorMessage;
                } catch (e) {
                    // Use default error message
                }
                showStatus(errorMessage, 'error');
            }
        };
        
        xhr.onerror = function() {
            showStatus('Network error occurred', 'error');
        };
        
        xhr.send(formData);
        showStatus('Uploading...', '');
    }

    function showStatus(message, type) {
        statusMessage.textContent = message;
        statusMessage.className = 'status-message';
        
        if (type) {
            statusMessage.classList.add(type);
        }
    }
    
    function clearStatus() {
        statusMessage.textContent = '';
        statusMessage.className = 'status-message';
    }
});
