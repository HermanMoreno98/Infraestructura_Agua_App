// Funcionalidad para el manejo de componentes
function closeModal() {
    document.getElementById('addComponentModal').style.display = 'none';
}

async function saveNewComponent() {
    const input = document.getElementById('newComponentName');
    const name = input.value.trim();
    const boxIndex = parseInt(input.dataset.boxIndex);
    
    if (!name) {
        alert('Por favor ingrese un nombre para el componente');
        return;
    }
    
    try {
        const response = await fetch('/add_component', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ name }),
        });
        
        const data = await response.json();
        
        if (data.success) {
            components.push(data.component);
            components.sort((a, b) => a.name.localeCompare(b.name));
            
            // Actualizar el valor en el select
            const box = boxes[boxIndex];
            const searchInput = document.querySelector(`[data-box-index="${boxIndex}"] .select-search`);
            searchInput.value = name;
            box.component = name;
            updateAnnotationsInput();
            
            closeModal();
        } else {
            alert(data.error || 'Error al agregar el componente');
        }
    } catch (error) {
        alert('Error al agregar el componente');
        console.error('Error:', error);
    }
}

// Cerrar modal al hacer clic fuera
window.onclick = function(event) {
    const modal = document.getElementById('addComponentModal');
    if (event.target == modal) {
        closeModal();
    }
}; 