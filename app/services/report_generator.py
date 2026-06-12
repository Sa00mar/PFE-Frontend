import os
import base64
import mimetypes
from datetime import datetime
from html import escape
import subprocess
import shutil


def safe_text(value):
    """
    Évite les erreurs si une valeur est None.
    Sécurise aussi l'affichage HTML.
    """
    if value is None:
        return ""
    return escape(str(value))


def image_to_base64_src(screenshot_path):
    """
    Convertit une capture d'écran locale en image base64.
    Objectif : rendre le rapport HTML autonome et partageable.
    """

    if not screenshot_path:
        return None

    # La base de ton projet contient le dossier static/
    normalized_path = screenshot_path.replace("\\", "/").lstrip("/")

    if normalized_path.startswith("static/"):
        full_path = normalized_path
    else:
        full_path = os.path.join("static", normalized_path)

    if not os.path.exists(full_path):
        print("[REPORT WARNING] Capture introuvable :", full_path)
        return None

    mime_type, _ = mimetypes.guess_type(full_path)

    if not mime_type:
        mime_type = "image/png"

    with open(full_path, "rb") as image_file:
        encoded = base64.b64encode(image_file.read()).decode("utf-8")

    return f"data:{mime_type};base64,{encoded}"


def format_steps(steps):
    """
    Transforme les étapes du test en liste HTML.
    Compatible avec :
    - liste Python
    - texte simple
    - None
    """

    if not steps:
        return "<p class='empty-text'>Aucune étape renseignée.</p>"

    if isinstance(steps, list):
        items = "".join(f"<li>{safe_text(step)}</li>" for step in steps)
        return f"<ol>{items}</ol>"

    steps_text = str(steps)

    # Si les étapes sont stockées sous forme de texte séparé par des retours ligne
    lines = [line.strip() for line in steps_text.split("\n") if line.strip()]

    if not lines:
        return "<p class='empty-text'>Aucune étape renseignée.</p>"

    items = "".join(f"<li>{safe_text(line)}</li>" for line in lines)
    return f"<ol>{items}</ol>"


def status_badge(status):
    """
    Retourne un badge HTML selon le statut du test.
    """

    status = (status or "unknown").lower()

    if status == "passed" or status == "pass":
        return "<span class='badge badge-pass'>PASS</span>"

    if status == "failed" or status == "fail":
        return "<span class='badge badge-fail'>FAIL</span>"

    if status == "pending":
        return "<span class='badge badge-pending'>PENDING</span>"

    return f"<span class='badge badge-unknown'>{safe_text(status)}</span>"


def classify_failure_type(test):
    """
    Classe un échec pour aider le développeur à comprendre
    si le problème vient du site ou du script généré.
    """

    status = str(test.get("status", "")).lower()
    message = str(test.get("execution_message") or test.get("detail") or "").lower()

    if status not in ["failed", "fail"]:
        return ""

    technical_keywords = [
        "syntaxerror",
        "indentationerror",
        "expected an indented block",
        "invalid syntax",
        "nameerror",
        "undefined name",
        "element not interactable",
        "no such element",
        "timeout",
        "selenium",
        "webdriver",
        "stacktrace",
    ]

    if any(keyword in message for keyword in technical_keywords):
        return "Échec technique du script généré"

    return "Échec fonctionnel potentiel du site"


def calculate_statistics(tests):
    """
    Calcule les statistiques globales des tests exécutés.
    """

    total = len(tests)

    passed = len(
        [
            test
            for test in tests
            if str(test.get("status", "")).lower() in ["pass", "passed"]
        ]
    )

    failed = len(
        [
            test
            for test in tests
            if str(test.get("status", "")).lower() in ["fail", "failed"]
        ]
    )

    pending = len(
        [test for test in tests if str(test.get("status", "")).lower() == "pending"]
    )

    success_rate = 0

    if total > 0:
        success_rate = round((passed / total) * 100, 2)

    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "pending": pending,
        "success_rate": success_rate,
    }


def generate_summary_text(stats, tests=None):
    """
    Génère un résumé exécutif automatique selon les résultats.
    """

    tests = tests or []

    technical_failures = [
        test
        for test in tests
        if str(test.get("status", "")).lower() in ["fail", "failed"]
        and classify_failure_type(test) == "Échec technique du script généré"
    ]

    functional_failures_count = stats["failed"] - len(technical_failures)

    if stats["total"] == 0:
        return (
            "Aucun test n'a été exécuté pour cette analyse. "
            "Le rapport ne permet donc pas encore d'évaluer la qualité de la page testée."
        )

    if stats["failed"] == 0 and stats["pending"] == 0:
        return (
            "L'exécution des tests est globalement réussie. "
            "Tous les cas de test exécutés ont été validés avec succès. "
            "Aucune anomalie bloquante n'a été détectée pendant l'exécution automatisée."
        )

    if stats["failed"] == 0 and stats["pending"] > 0:
        return (
            "L'exécution des tests est globalement satisfaisante. "
            "Aucun test n'a échoué. Cependant, certains tests sont marqués PENDING "
            "car ils nécessitent une intervention humaine ou sont bloqués par un élément "
            "non automatisable, comme un captcha ou un reCAPTCHA."
        )

    if functional_failures_count == 0 and technical_failures:
        return (
            "L'exécution des tests est globalement exploitable. "
            "Les tests fonctionnels principaux ont été exécutés, mais certains échecs "
            "semblent liés à des erreurs techniques dans les scripts générés. "
            "Ces cas doivent être vérifiés avant d'être considérés comme de véritables anomalies du site."
        )

    return (
        "L'exécution des tests a détecté une ou plusieurs anomalies potentielles. "
        "Les tests en échec doivent être analysés par l'équipe de développement afin "
        "d'identifier les causes et corriger les comportements non conformes."
    )


def generate_recommendations(stats):
    """
    Génère des recommandations selon les résultats.
    """

    recommendations = []

    if stats["failed"] > 0:
        recommendations.append(
            "Analyser les tests en échec et vérifier les messages exacts d'exécution."
        )
        recommendations.append(
            "Reproduire manuellement les scénarios en échec pour confirmer le comportement."
        )
        recommendations.append(
            "Vérifier les sélecteurs des éléments HTML utilisés dans les scripts Selenium/Cypress."
        )

    if stats["pending"] > 0:
        recommendations.append(
            "Prévoir un environnement de test sans captcha/reCAPTCHA pour permettre l'automatisation complète."
        )
        recommendations.append(
            "Utiliser des clés de test reCAPTCHA dans l'environnement QA si le formulaire doit être testé automatiquement."
        )

    if stats["failed"] == 0:
        recommendations.append(
            "Continuer à exécuter ces tests après chaque modification de la page afin d'éviter les régressions."
        )

    recommendations.append(
        "Conserver les captures d'écran comme preuve visuelle de l'exécution."
    )

    recommendations.append(
        "Mettre à jour les scripts de test si la structure HTML de la page change."
    )

    return recommendations


def generate_test_details_html(tests):
    """
    Génère la section détaillée de tous les cas de test.
    """

    html = ""

    for index, test in enumerate(tests, start=1):
        screenshot_path = test.get("screenshot_path")
        selenium_script = test.get("selenium_script")
        cypress_script = test.get("cypress_script")

        screenshot_html = "<p class='empty-text'>Aucune capture disponible.</p>"

        if screenshot_path:
            screenshot_src = image_to_base64_src(screenshot_path)
            if screenshot_src:
                screenshot_html = (
                    f"<img class='screenshot' src='{screenshot_src}' "
                    f"alt='Capture du test'>"
                )
            else:
                screenshot_html = "<p class='empty-text'>Capture renseignée mais fichier introuvable.</p>"

        selenium_html = "<p class='empty-text'>Aucun script Selenium disponible.</p>"

        if selenium_script:
            selenium_html = f"<pre><code>{safe_text(selenium_script)}</code></pre>"

        cypress_html = "<p class='empty-text'>Aucun script Cypress disponible.</p>"

        if cypress_script:
            cypress_html = f"<pre><code>{safe_text(cypress_script)}</code></pre>"

        html += f"""
        <div class="test-card">
            <div class="test-header">
                <div>
                    <h3>{index}. {safe_text(test.get("name"))}</h3>
                    <p class="test-id">ID : {safe_text(test.get("id"))}</p>
                </div>
                {status_badge(test.get("status"))}
            </div>

            <div class="test-meta">
                <span><strong>Type :</strong> {safe_text(test.get("type"))}</span>
                <span><strong>Priorité :</strong> {safe_text(test.get("priority"))}</span>
                <span><strong>Version :</strong> {safe_text(test.get("version"))}</span>
            </div>

            <h4>Étapes du test</h4>
            {format_steps(test.get("steps"))}

            <h4>Résultat attendu</h4>
            <p>{safe_text(test.get("expected_result"))}</p>

            <h4>Résultat réel / message d'exécution</h4>
            <p>{safe_text(test.get("execution_message") or test.get("detail"))}</p>

            <h4>Capture d'écran</h4>
            {screenshot_html}

            <details open>
                <summary>Voir le script Selenium</summary>
                {selenium_html}
            </details>

            <details open>
                <summary>Voir le script Cypress</summary>
                {cypress_html}
            </details>
        </div>
        """

    return html


def generate_filtered_tests_html(tests, status):
    """
    Génère une section filtrée : FAIL ou PENDING.
    """

    filtered_tests = [
        test for test in tests if str(test.get("status", "")).lower() in status
    ]

    if not filtered_tests:
        return "<p class='empty-text'>Aucun test dans cette catégorie.</p>"

    html = ""

    for test in filtered_tests:
        test_status = str(test.get("status", "")).lower()

        failure_type_html = ""

        if test_status in ["fail", "failed"]:
            failure_type_html = (
                f"<p><strong>Type d'échec :</strong> "
                f"{safe_text(classify_failure_type(test))}</p>"
            )

        html += f"""
        <div class="small-test-card">
            <div class="test-header">
                <div>
                    <h3>{safe_text(test.get("name"))}</h3>
                    <p class="test-id">ID : {safe_text(test.get("id"))}</p>
                </div>
                {status_badge(test.get("status"))}
            </div>

            {failure_type_html}

            <p><strong>Cause / message :</strong> {safe_text(test.get("execution_message") or test.get("detail"))}</p>
            <p><strong>Recommandation :</strong> Vérifier ce scénario manuellement et analyser le comportement de la page.</p>
        </div>
        """

    return html


def generate_html_report(analysis, tests, output_path):
    """
    Génère un rapport HTML complet.

    analysis : dictionnaire contenant les informations de l'analyse
    tests : liste de dictionnaires contenant les tests et résultats
    output_path : chemin du fichier HTML à générer
    """

    stats = calculate_statistics(tests)
    summary_text = generate_summary_text(stats, tests)
    recommendations = generate_recommendations(stats)

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    recommendations_html = "".join(
        f"<li>{safe_text(recommendation)}</li>" for recommendation in recommendations
    )

    tests_details_html = generate_test_details_html(tests)
    failed_tests_html = generate_filtered_tests_html(tests, ["fail", "failed"])
    pending_tests_html = generate_filtered_tests_html(tests, ["pending"])

    html_content = f"""
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>Rapport d'exécution des tests</title>

    <style>
        body {{
            font-family: Arial, sans-serif;
            background: #f4f7fb;
            color: #1f2937;
            margin: 0;
            padding: 0;
        }}

        .container {{
            max-width: 1100px;
            margin: 40px auto;
            background: white;
            padding: 40px;
            border-radius: 18px;
            box-shadow: 0 10px 30px rgba(15, 23, 42, 0.08);
        }}

        .cover {{
            text-align: center;
            padding: 60px 20px;
            border-bottom: 4px solid #2563eb;
            margin-bottom: 40px;
        }}

        .cover h1 {{
            font-size: 34px;
            color: #0f172a;
            margin-bottom: 10px;
        }}

        .cover p {{
            font-size: 16px;
            color: #64748b;
        }}

        h2 {{
            color: #0f172a;
            border-left: 6px solid #2563eb;
            padding-left: 12px;
            margin-top: 45px;
        }}

        h3 {{
            margin-bottom: 6px;
            color: #0f172a;
        }}

        h4 {{
            margin-bottom: 8px;
            color: #334155;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 16px;
            margin-bottom: 20px;
        }}

        th, td {{
            padding: 12px 14px;
            border: 1px solid #e2e8f0;
            text-align: left;
        }}

        th {{
            background: #f1f5f9;
            color: #0f172a;
        }}

        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 18px;
            margin-top: 20px;
        }}

        .stat-card {{
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            padding: 18px;
            border-radius: 14px;
            text-align: center;
        }}

        .stat-card strong {{
            display: block;
            font-size: 28px;
            color: #0f172a;
        }}

        .badge {{
            display: inline-block;
            padding: 8px 16px;
            border-radius: 999px;
            font-weight: bold;
            font-size: 13px;
        }}

        .badge-pass {{
            background: #dcfce7;
            color: #15803d;
        }}

        .badge-fail {{
            background: #fee2e2;
            color: #b91c1c;
        }}

        .badge-pending {{
            background: #fef3c7;
            color: #b45309;
        }}

        .badge-unknown {{
            background: #e5e7eb;
            color: #374151;
        }}

        .test-card, .small-test-card {{
            border: 1px solid #e2e8f0;
            border-radius: 16px;
            padding: 22px;
            margin-top: 22px;
            background: #ffffff;
            box-shadow: 0 4px 14px rgba(15, 23, 42, 0.04);
        }}

        .test-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 20px;
        }}

        .test-id {{
            color: #64748b;
            margin-top: 0;
        }}

        .test-meta {{
            display: flex;
            flex-wrap: wrap;
            gap: 18px;
            background: #f8fafc;
            padding: 12px;
            border-radius: 10px;
            margin: 15px 0;
        }}

        .screenshot {{
            max-width: 100%;
            border: 1px solid #cbd5e1;
            border-radius: 12px;
            margin-top: 10px;
        }}

        pre {{
            background: #0f172a;
            color: #e5e7eb;
            padding: 18px;
            border-radius: 12px;
            overflow-x: auto;
            font-size: 13px;
        }}

        details {{
            margin-top: 14px;
        }}

        summary {{
            cursor: pointer;
            font-weight: bold;
            color: #2563eb;
        }}

        .empty-text {{
            color: #94a3b8;
            font-style: italic;
        }}

        .footer {{
            margin-top: 50px;
            padding-top: 20px;
            border-top: 1px solid #e2e8f0;
            text-align: center;
            color: #64748b;
            font-size: 13px;
        }}

        @media print {{
            body {{
                background: white;
            }}

            .container {{
                box-shadow: none;
                margin: 0;
                max-width: 100%;
            }}

            .test-card {{
                page-break-inside: avoid;
            }}
        }}
    </style>
</head>

<body>
    <div class="container">

        <section class="cover">
            <h1>Rapport d'exécution des tests web</h1>
            <p>Généré par TestFlow - Moteur intelligent de génération et d'exécution de tests</p>
            <p><strong>URL testée :</strong> {safe_text(analysis.get("url"))}</p>
            <p><strong>Date de génération :</strong> {generated_at}</p>
        </section>

        <section>
            <h2>1. Résumé exécutif</h2>
            <p>{safe_text(summary_text)}</p>
        </section>

        <section>
            <h2>2. Informations générales de l'analyse</h2>

            <table>
                <tr>
                    <th>Élément</th>
                    <th>Valeur</th>
                </tr>
                <tr>
                    <td>ID analyse</td>
                    <td>{safe_text(analysis.get("id"))}</td>
                </tr>
                <tr>
                    <td>URL testée</td>
                    <td>{safe_text(analysis.get("url"))}</td>
                </tr>
                <tr>
                    <td>Type de page détecté</td>
                    <td>{safe_text(analysis.get("page_type"))}</td>
                </tr>
                <tr>
                    <td>Fonctionnalité principale</td>
                    <td>{safe_text(analysis.get("main_feature"))}</td>
                </tr>
                <tr>
                    <td>Scope d'analyse</td>
                    <td>{safe_text(analysis.get("analysis_scope"))}</td>
                </tr>
                <tr>
                   <td>Types de tests générés</td>
                   <td>{safe_text(analysis.get("test_types"))}</td>
                </tr>
                <tr>
                    <td>Version</td>
                    <td>{safe_text(analysis.get("version"))}</td>
                </tr>
                <tr>
                    <td>Version d'exécution</td>
                    <td>{safe_text(analysis.get("execution_version"))}</td>
                </tr>
                <tr>
                    <td>Date d'exécution</td>
                    <td>{safe_text(analysis.get("executed_at"))}</td>
                </tr>
            </table>
        </section>

        <section>
            <h2>3. Statistiques globales</h2>

            <div class="stats-grid">
                <div class="stat-card">
                    <strong>{stats["total"]}</strong>
                    Total
                </div>

                <div class="stat-card">
                    <strong>{stats["passed"]}</strong>
                    PASS
                </div>

                <div class="stat-card">
                    <strong>{stats["failed"]}</strong>
                    FAIL
                </div>

                <div class="stat-card">
                    <strong>{stats["pending"]}</strong>
                    PENDING
                </div>
            </div>

            <table>
                <tr>
                    <th>Statut</th>
                    <th>Nombre</th>
                    <th>Pourcentage</th>
                </tr>
                <tr>
                    <td>PASS</td>
                    <td>{stats["passed"]}</td>
                    <td>{stats["success_rate"]}%</td>
                </tr>
                <tr>
                    <td>FAIL</td>
                    <td>{stats["failed"]}</td>
                    <td>{round((stats["failed"] / stats["total"]) * 100, 2) if stats["total"] else 0}%</td>
                </tr>
                <tr>
                    <td>PENDING</td>
                    <td>{stats["pending"]}</td>
                    <td>{round((stats["pending"] / stats["total"]) * 100, 2) if stats["total"] else 0}%</td>
                </tr>
            </table>
        </section>

        <section>
            <h2>4. Détail complet des cas de test</h2>
            {tests_details_html}
        </section>

        <section>
            <h2>5. Tests échoués</h2>
            {failed_tests_html}
        </section>

        <section>
            <h2>6. Tests en attente / PENDING</h2>
            {pending_tests_html}
        </section>

        <section>
            <h2>7. Recommandations</h2>
            <ul>
                {recommendations_html}
            </ul>
        </section>

        <section>
            <h2>8. Conclusion</h2>
            <p>
                Ce rapport fournit une vision détaillée de l'exécution des tests générés
                automatiquement. Il peut être utilisé par l'équipe de développement pour
                identifier les anomalies, vérifier les comportements attendus et prioriser
                les corrections nécessaires.
            </p>
        </section>

        <div class="footer">
            Rapport généré automatiquement par TestFlow - {generated_at}
        </div>

    </div>
</body>
</html>
"""

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as file:
        file.write(html_content)

    return output_path


def find_chrome_executable():
    """
    Trouve l'exécutable Chrome sur Windows.
    """

    possible_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ]

    for path in possible_paths:
        if os.path.exists(path):
            return path

    chrome_from_path = shutil.which("chrome") or shutil.which("google-chrome")

    if chrome_from_path:
        return chrome_from_path

    return None


def generate_pdf_report(analysis, tests, html_output_path, pdf_output_path):
    """
    Génère d'abord le rapport HTML, puis le convertit en PDF avec Chrome headless.
    Cette solution évite les problèmes WeasyPrint/GTK sur Windows.
    """

    generate_html_report(
        analysis=analysis,
        tests=tests,
        output_path=html_output_path,
    )

    chrome_path = find_chrome_executable()

    if not chrome_path:
        raise RuntimeError(
            "Google Chrome est introuvable. Impossible de générer le PDF."
        )

    html_abs_path = os.path.abspath(html_output_path)
    pdf_abs_path = os.path.abspath(pdf_output_path)

    html_url = "file:///" + html_abs_path.replace("\\", "/")

    command = [
        chrome_path,
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--disable-extensions",
        "--disable-background-networking",
        "--no-pdf-header-footer",
        "--print-to-pdf-no-header",
        f"--print-to-pdf={pdf_abs_path}",
        html_url,
    ]

    subprocess.run(command, check=True)

    if not os.path.exists(pdf_abs_path):
        raise RuntimeError("Le fichier PDF n'a pas été généré.")

    return pdf_output_path
