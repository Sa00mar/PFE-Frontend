/**
 * TEST DETAILS PAGE SCRIPTS
 */

function copySelector(elementId) {
    const text = document.getElementById(elementId).textContent;
    navigator.clipboard.writeText(text).then(() => {
        const btn = document.querySelector('.btn-copy');
        const icon = btn.querySelector('i');
        
        // Success Feedback
        icon.className = 'fas fa-check text-success';
        setTimeout(() => {
            icon.className = 'far fa-copy';
        }, 2000);
    });
}

function rerunElement(elementId) {
    const loader = document.getElementById('rerunLoader');
    if (!loader) return;
    loader.classList.remove('d-none');
    
    // Simuler un délai d'exécution de test (mock)
    setTimeout(() => {
        loader.classList.add('d-none');
        alert('Le test pour cet élément ' + elementId + ' a été ré-exécuté avec succès !');
        window.location.reload();
    }, 2500);
}

// --- Modern Event Listeners ---
document.addEventListener('DOMContentLoaded', function() {
    const btnRerunElement = document.getElementById('btn-rerun-element');
    const btnCopy = document.querySelector('.btn-copy-modern');

    if (btnRerunElement) {
        btnRerunElement.addEventListener('click', function() {
            const elementId = this.getAttribute('data-test-id');
            rerunElement(elementId);
        });
    }

    if (btnCopy) {
        btnCopy.addEventListener('click', function() {
            const selectorCode = document.querySelector('.selector-box-modern code');
            if (selectorCode) {
                navigator.clipboard.writeText(selectorCode.textContent).then(() => {
                    const icon = this.querySelector('i');
                    const originalClass = icon.className;
                    
                    // Success Feedback
                    icon.className = 'fas fa-check text-success';
                    setTimeout(() => {
                        icon.className = originalClass;
                    }, 2000);
                });
            }
        });
    }
});
