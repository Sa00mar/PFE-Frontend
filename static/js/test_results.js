/**
 * TEST RESULTS PAGE SCRIPTS
 */

/**
 * TEST RESULTS PAGE SCRIPTS
 */

document.addEventListener('DOMContentLoaded', function () {
    const searchInput = document.getElementById('testSearch');
    const filterBtns = document.querySelectorAll('.filter-btn');
    const testCards = document.querySelectorAll('.test-card-modern');

    let currentFilter = 'all';
    let currentSearch = '';

    function applyFilters() {
        testCards.forEach(card => {
            const status = card.getAttribute('data-status');
            const name = (card.getAttribute('data-name') || '').toLowerCase();

            const matchesStatus = currentFilter === 'all' || status === currentFilter;
            const matchesSearch = name.includes(currentSearch);

            if (matchesStatus && matchesSearch) {
                card.style.display = 'block';
                card.style.opacity = '1';
                card.style.transform = 'scale(1)';
            } else {
                card.style.display = 'none';
                card.style.opacity = '0';
                card.style.transform = 'scale(0.98)';
            }
        });
    }

    filterBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            filterBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            currentFilter = btn.getAttribute('data-filter');
            applyFilters();
        });
    });

    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            currentSearch = e.target.value.toLowerCase();
            applyFilters();
        });
    }
});

// --- 3. Modal Management ---
window.openModal = function (testData) {
    const modalElement = document.getElementById('testDetailsModal');
    const modal = new bootstrap.Modal(modalElement);

    // Fill Modal Data
    document.getElementById('modalTitle').textContent = `Détails du test: ${testData.name}`;

    const screenshot = document.getElementById('modalScreenshot');
    screenshot.style.opacity = '0';
    screenshot.src = testData.screenshot;
    screenshot.onload = () => screenshot.style.opacity = '1';

    document.getElementById('modalName').textContent = testData.name;
    document.getElementById('modalType').textContent = testData.type;
    document.getElementById('modalAction').textContent = testData.action;
    document.getElementById('modalSelector').textContent = testData.xpath;

    // Status Badge in Modal
    const statusPill = document.getElementById('modalStatusBadge');
    statusPill.textContent = testData.status;
    statusPill.className = `status-pill ${testData.status}`;
    statusPill.style.background = testData.status === 'PASS' ? '#00c853' : '#ff1744';

    // Error Section
    const errorContainer = document.getElementById('modalErrorContainer');
    if (testData.status === 'FAIL') {
        errorContainer.classList.remove('d-none');
        document.getElementById('modalError').textContent = testData.error || 'Erreur non spécifiée lors de l\'exécution.';
    } else {
        errorContainer.classList.add('d-none');
    }

    modal.show();
};

// --- 5. Global Actions ---
function downloadReport() {
    // Simulation du téléchargement
    const btn = document.querySelector('.btn-download');
    const originalText = btn.innerHTML;

    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Génération...';
    btn.disabled = true;

    setTimeout(() => {
        alert('Le rapport de test (PDF) a été généré et le téléchargement va commencer.');
        btn.innerHTML = originalText;
        btn.disabled = false;
    }, 2000);
}

function rerunFullTest() {
    // Simulation d'une ré-exécution globale
    if (confirm('Voulez-vous vraiment relancer l\'intégralité de ce scénario de test ?')) {
        const btn = document.querySelector('.btn-rerun-all');
        const originalText = btn.innerHTML;

        btn.innerHTML = '<i class="fas fa-sync fa-spin"></i> Exécution...';
        btn.disabled = true;

        setTimeout(() => {
            alert('La ré-exécution complète est terminée. Les résultats ont été mis à jour.');
            btn.innerHTML = originalText;
            btn.disabled = false;
            window.location.reload();
        }, 3000);
    }
}
