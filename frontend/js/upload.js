const API_BASE = 'http://localhost:8000/api';

document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('uploadForm');
    const fileInput = document.getElementById('fileInput');
    const progressBar = document.getElementById('uploadProgress');
    const progressFill = document.getElementById('progressFill');
    const resultEl = document.getElementById('uploadResult');

    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        const file = fileInput.files[0];
        if (!file) {
            resultEl.textContent = 'Please select a PDF file.';
            resultEl.style.color = 'red';
            return;
        }

        const token = localStorage.getItem('token');
        if (!token) {
            window.location.href = 'index.html';
            return;
        }

        const formData = new FormData();
        formData.append('file', file);

        const xhr = new XMLHttpRequest();
        xhr.open('POST', `${API_BASE}/documents/upload`, true);
        xhr.setRequestHeader('Authorization', `Bearer ${token}`);

        xhr.upload.addEventListener('progress', function(e) {
            if (e.lengthComputable) {
                const percent = Math.round((e.loaded / e.total) * 100);
                progressFill.style.width = percent + '%';
                progressFill.textContent = percent + '%';
                progressBar.style.display = 'block';
            }
        });

        xhr.onload = function() {
            progressBar.style.display = 'none';
            if (xhr.status === 200) {
                const data = JSON.parse(xhr.responseText);
                resultEl.textContent = `✅ Upload successful! Document ID: ${data.document_id}`;
                resultEl.style.color = 'green';
                fileInput.value = '';
            } else {
                let detail = 'Upload failed';
                try {
                    const err = JSON.parse(xhr.responseText);
                    detail = err.detail || detail;
                } catch (e) {}
                resultEl.textContent = `❌ ${detail}`;
                resultEl.style.color = 'red';
            }
        };

        xhr.onerror = function() {
            progressBar.style.display = 'none';
            resultEl.textContent = '❌ Network error. Please try again.';
            resultEl.style.color = 'red';
        };

        xhr.send(formData);
    });
});