/**
 * ANALYSIS RESULT PAGE SCRIPTS
 */

document.addEventListener('DOMContentLoaded', function () {
    const selectAllCheckbox = document.getElementById('selectAll');
    const selectionCountSpan = document.getElementById('selectionCount');
    const btnRunSelected = document.getElementById('btn-run-selected');
    const btnRunAll = document.getElementById('btn-run-all');
    const btnReAnalyze = document.getElementById('btn-re-analyze');

    // Loader
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
                <p class="text-white-50">Traitement des cas de test sélectionnés.</p>
            </div>
        `;
        document.body.appendChild(loader);
    }

    function getTestCheckboxes() {
        return document.querySelectorAll('.element-checkbox');
    }

    function updateCount() {
        const checkedCount = document.querySelectorAll('.element-checkbox:checked').length;

        if (selectionCountSpan) {
            selectionCountSpan.textContent =
                `${checkedCount} test${checkedCount > 1 ? 's' : ''} sélectionné${checkedCount > 1 ? 's' : ''}`;
        }
    }

    if (selectAllCheckbox) {
        selectAllCheckbox.addEventListener('change', function () {
            getTestCheckboxes().forEach(cb => {
                cb.checked = selectAllCheckbox.checked;
            });
            updateCount();
        });
    }

    getTestCheckboxes().forEach(cb => {
        cb.addEventListener('change', updateCount);
    });

    function runTests(selectedOnly = true) {
        const analysisLoader = document.getElementById('analysisLoader');
        analysisLoader.classList.remove('d-none');

        let selectedIds = [];

        if (selectedOnly) {
            selectedIds = Array.from(document.querySelectorAll('.element-checkbox:checked'))
                .map(cb => parseInt(cb.value))
                .filter(id => !isNaN(id));

            if (selectedIds.length === 0) {
                analysisLoader.classList.add('d-none');
                alert("Veuillez sélectionner au moins un test.");
                return;
            }
        }

        fetch(`/run_tests/${analysisId}`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                selected_only: selectedOnly,
                selected_ids: selectedIds
            })
        })
            .then(response => response.json())
            .then(data => {
                analysisLoader.classList.add('d-none');

                if (data.success) {
                    window.location.href = `/test_results/${analysisId}`;
                } else {
                    alert("Erreur lors de l'exécution des tests.");
                }
            })
            .catch(error => {
                analysisLoader.classList.add('d-none');
                console.error(error);
                alert("Erreur backend lors de l'exécution.");
            });
    }

    if (btnRunSelected) {
        btnRunSelected.addEventListener('click', () => runTests(true));
    }

    if (btnRunAll) {
        btnRunAll.addEventListener('click', () => runTests(false));
    }

    if (btnReAnalyze) {
        btnReAnalyze.addEventListener('click', () => {
            window.location.href = '/new_test';
        });
    }

    updateCount();
});

// Loader CSS
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
.loader-content {
    text-align: center;
    color: white;
}
`;
document.head.appendChild(loaderStyle);