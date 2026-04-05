/**
 * ANALYSIS RESULT PAGE SCRIPTS
 */

document.addEventListener('DOMContentLoaded', function() {
    const selectAllCheckbox = document.getElementById('selectAll');
    const elementCheckboxes = document.querySelectorAll('.element-checkbox');
    const selectionCountSpan = document.getElementById('selectionCount');
    const btnRunSelected = document.getElementById('btn-run-selected');
    const btnRunAll = document.getElementById('btn-run-all');
    
    // Create Loader Overlay (if not in HTML)
    if (!document.getElementById('analysisLoader')) {
        const loader = document.createElement('div');
        loader.id = 'analysisLoader';
        loader.className = 'loader-overlay d-none';
        loader.innerHTML = `
            <div class="loader-content">
                <div class="spinner-border text-primary" role="status" style="width: 3.5rem; height: 3.5rem;">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <h3 class="mt-4 text-white fw-bold">Exécution des tests en cours...</h3>
                <p class="text-white-50">Analyse des scénarios et capture des résultats.</p>
            </div>
        `;
        document.body.appendChild(loader);
    }

    // --- 1. Selection Logic ---
    function updateCount() {
        const checkedCount = document.querySelectorAll('.element-checkbox:checked').length;
        selectionCountSpan.textContent = `${checkedCount} élément${checkedCount > 1 ? 's' : ''} sélectionné${checkedCount > 1 ? 's' : ''}`;
    }

    selectAllCheckbox.addEventListener('change', function() {
        elementCheckboxes.forEach(cb => {
            cb.checked = selectAllCheckbox.checked;
        });
        updateCount();
    });

    elementCheckboxes.forEach(cb => {
        cb.addEventListener('change', updateCount);
    });

    // --- 2. Execution Logic with Loader ---
    function runTests(selectedOnly = true) {
        const analysisLoader = document.getElementById('analysisLoader');
        analysisLoader.classList.remove('d-none');
        
        // Simuler un délai d'exécution (mock)
        setTimeout(() => {
            analysisLoader.classList.add('d-none');
            // Rediriger vers la page des résultats après exécution fictive
            window.location.href = '/test_results';
        }, 3000);
    }

    btnRunSelected.addEventListener('click', () => runTests(true));
    btnRunAll.addEventListener('click', () => runTests(false));

    // --- 3. Redirects ---
    const btnReAnalyze = document.getElementById('btn-re-analyze');
    if (btnReAnalyze) {
        btnReAnalyze.addEventListener('click', () => {
            window.location.href = '/new_test';
        });
    }
});

// Reuse loader CSS
const loaderStyle = document.createElement('style');
loaderStyle.textContent = `
.loader-overlay {
    position: fixed;
    inset: 0;
    background: rgba(15, 23, 42, 0.9);
    backdrop-filter: blur(10px);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 10000;
    flex-direction: column;
}
.loader-content { text-align: center; color: white; }
`;
document.head.appendChild(loaderStyle);
