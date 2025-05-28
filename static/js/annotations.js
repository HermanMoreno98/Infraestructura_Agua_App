// Variables globales para las anotaciones
let isDrawing = false;
let startX, startY;
let currentBox = null;
let boxes = [];
const imageContainer = document.getElementById('imageContainer');
const mainImage = document.getElementById('mainImage');
const boxesInfo = document.getElementById('boxesInfo');
const boxControlsTemplate = document.getElementById('boxControlsTemplate');

function updateNoBoxesMessage() {
    const noBoxesMessage = boxesInfo.querySelector('.no-boxes-message');
    if (boxes.length === 0) {
        if (!noBoxesMessage) {
            const message = document.createElement('div');
            message.className = 'no-boxes-message';
            message.textContent = 'No hay cajas de anotación creadas';
            boxesInfo.appendChild(message);
        }
    } else if (noBoxesMessage) {
        noBoxesMessage.remove();
    }
}

function getMousePosition(e) {
    const rect = imageContainer.getBoundingClientRect();
    return {
        x: e.clientX - rect.left,
        y: e.clientY - rect.top
    };
}

function createBox(x, y, width, height) {
    const box = document.createElement('div');
    box.className = 'bounding-box';
    box.style.left = x + 'px';
    box.style.top = y + 'px';
    box.style.width = width + 'px';
    box.style.height = height + 'px';
    
    const deleteBtn = document.createElement('button');
    deleteBtn.className = 'delete-btn';
    deleteBtn.innerHTML = '×';
    deleteBtn.onclick = (e) => {
        e.stopPropagation();
        removeBox(box);
    };
    box.appendChild(deleteBtn);
    
    return box;
}

function createCustomSelect(wrapper, boxIndex) {
    const searchInput = wrapper.querySelector('.select-search');
    const optionsContainer = wrapper.querySelector('.select-options');
    const addButton = wrapper.querySelector('.add-component-btn');
    
    function updateOptions(filter = '') {
        optionsContainer.innerHTML = '';
        const filteredComponents = components.filter(c => 
            c.name.toLowerCase().includes(filter.toLowerCase())
        );
        
        filteredComponents.forEach(component => {
            const option = document.createElement('div');
            option.className = 'select-option';
            option.textContent = component.name;
            option.onclick = () => {
                searchInput.value = component.name;
                optionsContainer.style.display = 'none';
                // Actualizar la anotación
                const box = boxes[boxIndex];
                box.component = component.name;
                updateAnnotationsInput();
            };
            optionsContainer.appendChild(option);
        });
    }
    
    searchInput.onfocus = () => {
        updateOptions(searchInput.value);
        optionsContainer.style.display = 'block';
    };
    
    searchInput.onblur = () => {
        setTimeout(() => {
            optionsContainer.style.display = 'none';
        }, 200);
    };
    
    searchInput.oninput = () => {
        updateOptions(searchInput.value);
        optionsContainer.style.display = 'block';
    };
    
    addButton.onclick = () => {
        document.getElementById('addComponentModal').style.display = 'block';
        const input = document.getElementById('newComponentName');
        input.value = searchInput.value;
        input.dataset.boxIndex = boxIndex;
    };
}

function addBoxControls(boxIndex) {
    const controls = boxControlsTemplate.content.cloneNode(true);
    controls.querySelector('.box-number').textContent = boxIndex + 1;
    
    const boxInfo = controls.querySelector('.box-info');
    boxInfo.dataset.boxIndex = boxIndex;
    
    boxesInfo.appendChild(controls);
    
    // Inicializar el select personalizado
    const wrapper = boxInfo.querySelector('.select-wrapper');
    createCustomSelect(wrapper, boxIndex);
    
    updateNoBoxesMessage();
}

function updateAnnotation(select) {
    const boxInfo = select.closest('.box-info');
    const boxIndex = parseInt(boxInfo.dataset.boxIndex);
    const box = boxes[boxIndex];
    
    if (select.classList.contains('component-select')) {
        box.component = select.value;
    } else if (select.classList.contains('estado-select')) {
        box.estado = select.value;
    } else if (select.classList.contains('estado-operativo-select')) {
        box.estado_operativo = select.value;
    } else if (select.classList.contains('analisis-input')) {
        box.analisis = select.value;
    }
    
    updateAnnotationsInput();
}

function removeBox(box) {
    const index = Array.from(imageContainer.children).indexOf(box) - 1;
    box.remove();
    boxes.splice(index, 1);
    boxesInfo.innerHTML = '';
    
    boxes.forEach((_, i) => addBoxControls(i));
    updateAnnotationsInput();
    updateNoBoxesMessage();
}

function updateAnnotationsInput() {
    const annotations = boxes.map(box => ({
        x: parseInt(box.style.left),
        y: parseInt(box.style.top),
        width: parseInt(box.style.width),
        height: parseInt(box.style.height),
        component: box.component || '',
        estado: box.estado || '',
        estado_operativo: box.estado_operativo || '',
        analisis: box.analisis || ''
    }));
    document.getElementById('annotationsInput').value = JSON.stringify(annotations);
}

// Event listeners para dibujar cajas
imageContainer.addEventListener('mousedown', (e) => {
    if (e.target === mainImage) {
        isDrawing = true;
        const pos = getMousePosition(e);
        startX = pos.x;
        startY = pos.y;
        currentBox = createBox(startX, startY, 0, 0);
        imageContainer.appendChild(currentBox);
    }
});

document.addEventListener('mousemove', (e) => {
    if (!isDrawing) return;
    
    const pos = getMousePosition(e);
    const width = pos.x - startX;
    const height = pos.y - startY;
    
    if (width > 0) {
        currentBox.style.width = width + 'px';
    } else {
        currentBox.style.left = pos.x + 'px';
        currentBox.style.width = -width + 'px';
    }
    
    if (height > 0) {
        currentBox.style.height = height + 'px';
    } else {
        currentBox.style.top = pos.y + 'px';
        currentBox.style.height = -height + 'px';
    }
});

document.addEventListener('mouseup', () => {
    if (isDrawing) {
        isDrawing = false;
        if (parseInt(currentBox.style.width) < 5 || parseInt(currentBox.style.height) < 5) {
            currentBox.remove();
        } else {
            boxes.push(currentBox);
            addBoxControls(boxes.length - 1);
            updateAnnotationsInput();
        }
        currentBox = null;
    }
});

// Event listener para mover cajas
imageContainer.addEventListener('mousedown', (e) => {
    const box = e.target.closest('.bounding-box');
    if (!box) return;
    
    let isDragging = true;
    const rect = box.getBoundingClientRect();
    const offsetX = e.clientX - rect.left;
    const offsetY = e.clientY - rect.top;
    
    function onMouseMove(e) {
        if (!isDragging) return;
        
        const pos = getMousePosition(e);
        box.style.left = (pos.x - offsetX) + 'px';
        box.style.top = (pos.y - offsetY) + 'px';
        updateAnnotationsInput();
    }
    
    function onMouseUp() {
        isDragging = false;
        document.removeEventListener('mousemove', onMouseMove);
        document.removeEventListener('mouseup', onMouseUp);
    }
    
    document.addEventListener('mousemove', onMouseMove);
    document.addEventListener('mouseup', onMouseUp);
});

// Validación del formulario
function validateForm() {
    const annotations = JSON.parse(document.getElementById('annotationsInput').value || '[]');
    if (annotations.length === 0) {
        window.location.href = '/';
        return false;
    }
    const feedback = document.getElementById('feedback');
    feedback.style.display = 'block';
    setTimeout(() => {
        feedback.style.display = 'none';
    }, 1000);
    return true;
}

// Inicializar el mensaje de no hay cajas
updateNoBoxesMessage(); 