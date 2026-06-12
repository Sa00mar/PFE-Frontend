from app.services.report_generator import generate_html_report


analysis = {
    "id": 186,
    "url": "https://practicetestautomation.com/contact/",
    "page_type": "contact",
    "main_feature": "Formulaire de contact",
    "analysis_scope": "single_page",
    "version": "v4",
    "executed_at": "2026-06-10 19:24:12",
}


tests = [
    {
        "id": 2608,
        "name": "Soumission valide du formulaire",
        "type": "positive",
        "priority": "high",
        "version": "v4",
        "status": "pending",
        "steps": [
            "Remplir les champs obligatoires avec des valeurs valides.",
            "Cliquer sur le bouton principal du formulaire.",
            "Vérifier que l'action est exécutée correctement.",
        ],
        "expected_result": "Le formulaire doit être soumis correctement avec des données valides.",
        "execution_message": "Test non automatisé complètement : un captcha/reCAPTCHA est présent.",
        "screenshot_path": "screenshots/test_2608_20260610_192412.png",
        "selenium_script": "driver.get('https://practicetestautomation.com/contact/')",
        "cypress_script": "cy.visit('https://practicetestautomation.com/contact/')",
    }
]


generate_html_report(
    analysis=analysis, tests=tests, output_path="static/reports/report_test.html"
)

print("Rapport généré avec succès : static/reports/report_test.html")
