function validateUrlBtn(btn) {
    const urlInput = document.getElementById('urlInput');
    if(!urlInput.checkValidity()) {
        urlInput.reportValidity();
        return;
    }
    
    const originalContent = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-circle-notch fa-spin text-primary me-2"></i> Vérif...';
    btn.disabled = true;
    
    setTimeout(() => {
        btn.innerHTML = '<i class="fas fa-check text-success me-2"></i> Valide';
        btn.classList.add('border-success', 'bg-success', 'bg-opacity-10');
        setTimeout(() => {
            btn.innerHTML = originalContent;
            btn.disabled = false;
            btn.classList.remove('border-success', 'bg-success', 'bg-opacity-10');
        }, 2500);
    }, 1000);
}

function startAnalysis() {
    const urlInput = document.getElementById('urlInput');
    if(!urlInput.checkValidity()) {
        urlInput.reportValidity();
        return;
    }

    // Cacher fomulaire, Afficher le loader
    document.getElementById('step-form').classList.add('d-none');
    document.getElementById('step-loader').classList.remove('d-none');
    
    // MAJ de l'URL dans le loader
    document.getElementById('targetUrlDisplay').textContent = urlInput.value;

    // Simulation de la durée d'analyse IA (~3.5 secondes)
    setTimeout(() => {
        // Cacher le loader, afficher le message de succès avec les boutons
        document.getElementById('step-loader').classList.add('d-none');
        document.getElementById('step-success').classList.remove('d-none');
    }, 3500);
}

function resetForm() {
    document.getElementById('urlInput').value = '';
    document.getElementById('step-success').classList.add('d-none');
    document.getElementById('step-form').classList.remove('d-none');
}

function runAllDirectly() {
    const btn = document.getElementById('btn-run-all');
    if (!btn) return;
    
    const originalContent = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-circle-notch fa-spin me-2"></i> Démarrage des tests...';
    btn.disabled = true;
    
    setTimeout(() => {
        btn.innerHTML = '<i class="fas fa-check-circle me-2"></i> Exécution en cours !';
        btn.classList.replace('btn-custom-primary', 'btn-success');
        
        setTimeout(() => {
            // Automatic redirection to results page
            window.location.href = '/test_results';
        }, 1500);
    }, 1500);
}

// --- Event Listeners for Modern Structure ---
document.addEventListener('DOMContentLoaded', function() {
    const btnViewResults = document.getElementById('btn-view-results');
    const btnRunAll = document.getElementById('btn-run-all');
    const btnReset = document.getElementById('btn-reset');

    if (btnViewResults) {
        btnViewResults.addEventListener('click', () => {
            window.location.href = '/analysis_result';
        });
    }

    if (btnRunAll) {
        btnRunAll.addEventListener('click', runAllDirectly);
    }

    if (btnReset) {
        btnReset.addEventListener('click', resetForm);
    }
});
