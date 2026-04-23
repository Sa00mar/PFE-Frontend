
function validateUrlBtn(btn) {
    const urlInput = document.getElementById('urlInput');
    const messageBox = document.getElementById('urlValidationMessage');

    if (messageBox) {
        messageBox.textContent = '';
        messageBox.className = 'mt-2 small';
    }

    if (!urlInput.checkValidity()) {
        urlInput.reportValidity();
        return;
    }

    const originalContent = btn.innerHTML;

    btn.innerHTML = '<i class="fas fa-circle-notch fa-spin text-primary me-2"></i> Vérif...';
    btn.disabled = true;

    const formData = new FormData();
    formData.append('url', urlInput.value);

    fetch('/validate_url', {
        method: 'POST',
        body: formData
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                btn.innerHTML = '<i class="fas fa-check text-success me-2"></i> Valide';
                btn.classList.add('border-success', 'bg-success', 'bg-opacity-10');

                if (messageBox) {
                    messageBox.textContent = data.message;
                    messageBox.classList.add('text-success');
                }
            } else {
                btn.innerHTML = '<i class="fas fa-times text-danger me-2"></i> Invalide';
                btn.classList.add('border-danger', 'bg-danger', 'bg-opacity-10');

                if (messageBox) {
                    messageBox.textContent = data.message;
                    messageBox.classList.add('text-danger');
                }
            }

            setTimeout(() => {
                btn.innerHTML = originalContent;
                btn.disabled = false;
                btn.classList.remove(
                    'border-success',
                    'bg-success',
                    'bg-opacity-10',
                    'border-danger',
                    'bg-danger'
                );
            }, 1500);
        })
        .catch(error => {
            console.error('Erreur:', error);

            btn.innerHTML = '<i class="fas fa-times text-danger me-2"></i> Erreur';
            btn.classList.add('border-danger', 'bg-danger', 'bg-opacity-10');

            if (messageBox) {
                messageBox.textContent = "Erreur lors de la validation de l'URL.";
                messageBox.classList.add('text-danger');
            }

            setTimeout(() => {
                btn.innerHTML = originalContent;
                btn.disabled = false;
                btn.classList.remove('border-danger', 'bg-danger', 'bg-opacity-10');
            }, 1500);
        });
}

// ==========================
// FORM SUBMIT (IMPORTANT)
// ==========================
document.addEventListener('DOMContentLoaded', function () {

    const form = document.getElementById('analysisForm');

    form.addEventListener('submit', function () {

        const btn = document.getElementById('btn-launch');

        btn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i> Analyse en cours...';
        btn.disabled = true;

        // PAS fetch → on laisse Flask gérer redirect
    });

});


// ==========================
// EVENT BUTTONS ANALYSIS RESULT PAGE
// ==========================
const btnViewResults = document.getElementById('btn-view-results');
const btnRunAll = document.getElementById('btn-run-all');
const btnReset = document.getElementById('btn-reset');

if (btnViewResults) {
    btnViewResults.addEventListener('click', () => {
        window.location.href = `/analysis_result/${analysisId}`;
    });
}

if (btnRunAll) {
    btnRunAll.addEventListener('click', function () {

        const btn = this;
        btn.innerHTML = '<i class="fas fa-circle-notch fa-spin me-2"></i> Exécution...';
        btn.disabled = true;

        setTimeout(() => {
            btn.innerHTML = '<i class="fas fa-check-circle me-2"></i> Terminé';

            setTimeout(() => {
                window.location.href = '/test_results';
            }, 1200);

        }, 1500);
    });
}

if (btnReset) {
    btnReset.addEventListener('click', () => {
        document.getElementById('urlInput').value = '';
        document.getElementById('step-success')?.classList.add('d-none');
        document.getElementById('step-form')?.classList.remove('d-none');
    });
}

