/**
 * Full-Screen Floating Signature Pad
 * Large signature capture with clear/redo functionality
 */

let signatureCanvas;
let signatureCtx;
let isDrawing = false;
let lastX = 0;
let lastY = 0;
let signatureData = null;

function openSignaturePad() {
    // Create modal overlay
    const modal = document.createElement('div');
    modal.id = 'signatureModal';
    modal.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0, 0, 0, 0.95);
        z-index: 9999;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 20px;
    `;
    
    // Create signature container
    const container = document.createElement('div');
    container.style.cssText = `
        background: white;
        border-radius: 15px;
        padding: 20px;
        width: 95%;
        max-width: 1200px;
        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5);
    `;
    
    // Create header
    const header = document.createElement('div');
    header.style.cssText = `
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 15px;
        padding-bottom: 15px;
        border-bottom: 2px solid #e5e7eb;
    `;
    header.innerHTML = `
        <h3 style="margin: 0; color: #1e3a5f;">
            <i class="bi bi-pen"></i> Sign Here
        </h3>
        <button onclick="closeSignaturePad()" style="
            background: #dc2626;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 600;
        ">
            <i class="bi bi-x-lg"></i> Close
        </button>
    `;
    
    // Create canvas
    signatureCanvas = document.createElement('canvas');
    signatureCanvas.id = 'signatureCanvas';
    signatureCanvas.style.cssText = `
        border: 3px solid #1e3a5f;
        border-radius: 10px;
        cursor: crosshair;
        touch-action: none;
        background: white;
        width: 100%;
        display: block;
    `;
    
    // Set canvas size
    const canvasWidth = Math.min(1160, window.innerWidth - 80);
    const canvasHeight = Math.min(600, window.innerHeight - 250);
    signatureCanvas.width = canvasWidth;
    signatureCanvas.height = canvasHeight;
    
    // Create instruction text
    const instruction = document.createElement('p');
    instruction.style.cssText = `
        text-align: center;
        color: #6b7280;
        margin: 15px 0;
        font-size: 14px;
    `;
    instruction.textContent = 'Draw your signature above using mouse or touch';
    
    // Create button container
    const buttonContainer = document.createElement('div');
    buttonContainer.style.cssText = `
        display: flex;
        gap: 10px;
        justify-content: center;
        margin-top: 15px;
    `;
    
    // Clear button
    const clearBtn = document.createElement('button');
    clearBtn.innerHTML = '<i class="bi bi-arrow-counterclockwise"></i> Clear';
    clearBtn.style.cssText = `
        background: #f59e0b;
        color: white;
        border: none;
        padding: 12px 24px;
        border-radius: 8px;
        cursor: pointer;
        font-weight: 600;
        font-size: 16px;
    `;
    clearBtn.onclick = clearSignature;
    
    // Save button
    const saveBtn = document.createElement('button');
    saveBtn.innerHTML = '<i class="bi bi-check-circle"></i> Save Signature';
    saveBtn.style.cssText = `
        background: #10b981;
        color: white;
        border: none;
        padding: 12px 24px;
        border-radius: 8px;
        cursor: pointer;
        font-weight: 600;
        font-size: 16px;
    `;
    saveBtn.onclick = saveSignature;
    
    buttonContainer.appendChild(clearBtn);
    buttonContainer.appendChild(saveBtn);
    
    // Assemble modal
    container.appendChild(header);
    container.appendChild(instruction);
    container.appendChild(signatureCanvas);
    container.appendChild(buttonContainer);
    modal.appendChild(container);
    document.body.appendChild(modal);
    
    // Initialize canvas
    signatureCtx = signatureCanvas.getContext('2d');
    signatureCtx.strokeStyle = '#000000';
    signatureCtx.lineWidth = 3;
    signatureCtx.lineCap = 'round';
    signatureCtx.lineJoin = 'round';
    
    // Add event listeners
    signatureCanvas.addEventListener('mousedown', startDrawing);
    signatureCanvas.addEventListener('mousemove', draw);
    signatureCanvas.addEventListener('mouseup', stopDrawing);
    signatureCanvas.addEventListener('mouseout', stopDrawing);
    
    // Touch events for mobile
    signatureCanvas.addEventListener('touchstart', handleTouchStart);
    signatureCanvas.addEventListener('touchmove', handleTouchMove);
    signatureCanvas.addEventListener('touchend', stopDrawing);
}

function closeSignaturePad() {
    const modal = document.getElementById('signatureModal');
    if (modal) {
        modal.remove();
    }
}

function startDrawing(e) {
    isDrawing = true;
    const rect = signatureCanvas.getBoundingClientRect();
    lastX = e.clientX - rect.left;
    lastY = e.clientY - rect.top;
}

function draw(e) {
    if (!isDrawing) return;
    
    const rect = signatureCanvas.getBoundingClientRect();
    const currentX = e.clientX - rect.left;
    const currentY = e.clientY - rect.top;
    
    signatureCtx.beginPath();
    signatureCtx.moveTo(lastX, lastY);
    signatureCtx.lineTo(currentX, currentY);
    signatureCtx.stroke();
    
    lastX = currentX;
    lastY = currentY;
}

function stopDrawing() {
    isDrawing = false;
}

function handleTouchStart(e) {
    e.preventDefault();
    const touch = e.touches[0];
    const rect = signatureCanvas.getBoundingClientRect();
    lastX = touch.clientX - rect.left;
    lastY = touch.clientY - rect.top;
    isDrawing = true;
}

function handleTouchMove(e) {
    e.preventDefault();
    if (!isDrawing) return;
    
    const touch = e.touches[0];
    const rect = signatureCanvas.getBoundingClientRect();
    const currentX = touch.clientX - rect.left;
    const currentY = touch.clientY - rect.top;
    
    signatureCtx.beginPath();
    signatureCtx.moveTo(lastX, lastY);
    signatureCtx.lineTo(currentX, currentY);
    signatureCtx.stroke();
    
    lastX = currentX;
    lastY = currentY;
}

function clearSignature() {
    signatureCtx.clearRect(0, 0, signatureCanvas.width, signatureCanvas.height);
}

function saveSignature() {
    // Check if canvas is empty
    const imageData = signatureCtx.getImageData(0, 0, signatureCanvas.width, signatureCanvas.height);
    const pixels = imageData.data;
    let isEmpty = true;
    
    for (let i = 0; i < pixels.length; i += 4) {
        if (pixels[i + 3] !== 0) {
            isEmpty = false;
            break;
        }
    }
    
    if (isEmpty) {
        alert('Please draw your signature first');
        return;
    }
    
    // Convert canvas to base64
    signatureData = signatureCanvas.toDataURL('image/png');
    
    // Update hidden input
    const signatureInput = document.getElementById('ci_signature');
    if (signatureInput) {
        signatureInput.value = signatureData;
    }
    
    // Update preview
    const preview = document.getElementById('signaturePreview');
    if (preview) {
        preview.innerHTML = `
            <img src="${signatureData}" style="max-width: 300px; border: 2px solid #10b981; border-radius: 8px; padding: 10px; background: white;">
            <p style="color: #10b981; margin-top: 10px;">
                <i class="bi bi-check-circle-fill"></i> Signature captured
            </p>
        `;
    }
    
    closeSignaturePad();
    alert('Signature saved successfully!');
}
