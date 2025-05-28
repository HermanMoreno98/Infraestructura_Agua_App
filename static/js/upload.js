// Funcionalidad de carga de archivos
const dropZone = document.getElementById('dropZone');
const fileInput = document.getElementById('fileInput');
const progressBar = document.querySelector('.upload-progress-bar');
const progressContainer = document.querySelector('.upload-progress');

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
    dropZone.classList.add('border-primary');
}

function unhighlight(e) {
    dropZone.classList.remove('border-primary');
}

dropZone.addEventListener('drop', handleDrop, false);
fileInput.addEventListener('change', handleFileSelect, false);

function handleDrop(e) {
    const dt = e.dataTransfer;
    const file = dt.files[0];
    handleFile(file);
}

function handleFileSelect(e) {
    const file = e.target.files[0];
    handleFile(file);
}

function handleFile(file) {
    if (!file || !file.type.startsWith('image/')) {
        alert('Por favor, selecciona un archivo de imagen válido.');
        return;
    }

    uploadFile(file);
}

async function uploadFile(file) {
    const formData = new FormData();
    formData.append('file', file);

    progressContainer.style.display = 'block';
    progressBar.style.width = '0%';

    try {
        const response = await fetch('/upload', {
            method: 'POST',
            body: formData
        });

        progressBar.style.width = '100%';

        const data = await response.json();
        if (data.success) {
            // Actualizar los datos del formulario con la nueva imagen
            document.querySelector('input[name="image_name"]').value = data.filename;
            document.querySelector('input[name="image_id"]').value = data.image_id;
            document.querySelector('input[name="width"]').value = data.width;
            document.querySelector('input[name="height"]').value = data.height;

            // Actualizar la imagen inmediatamente
            document.getElementById('mainImage').src = `data:image/jpeg;base64,${data.image_data}`;
            
            // Actualizar la URL para reflejar la nueva imagen
            const newUrl = new URL(window.location);
            newUrl.searchParams.set('image_id', data.image_id);
            window.history.pushState({}, '', newUrl);

            // Limpiar cualquier anotación existente
            boxes.forEach(box => box.remove());
            boxes = [];
            boxesInfo.innerHTML = '';
            updateNoBoxesMessage();
            updateAnnotationsInput();

            // Mostrar mensaje de éxito
            const feedback = document.getElementById('feedback');
            feedback.textContent = '¡Imagen cargada correctamente!';
            feedback.style.display = 'block';
            setTimeout(() => {
                feedback.style.display = 'none';
            }, 2000);
        } else {
            alert(data.error || 'Error al subir la imagen');
        }
    } catch (error) {
        alert('Error al subir la imagen');
        console.error('Error:', error);
    } finally {
        setTimeout(() => {
            progressContainer.style.display = 'none';
            progressBar.style.width = '0%';
        }, 1000);
    }
} 