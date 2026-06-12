import json
from urllib.parse import urlparse


def safe_test_name(value):
    value = (value or "").strip().lower()

    cleaned = ""

    for char in value:
        if char.isalnum():
            cleaned += char
        elif char in [" ", "-", "_"]:
            cleaned += "_"

    while "__" in cleaned:
        cleaned = cleaned.replace("__", "_")

    return cleaned.strip("_")[:60]


def has_test_type(test_cases, target_type):
    """
    Vérifie si une liste contient déjà un test d'un type donné.
    """
    target_type = target_type.lower()

    for test in test_cases:
        test_type = str(test.get("type", "")).lower()

        if target_type in test_type:
            return True

    return False


def count_test_type(test_cases, target_type):
    """
    Compte le nombre de tests d'un type donné.
    """
    target_type = target_type.lower()
    count = 0

    for test in test_cases:
        test_type = str(test.get("type", "")).lower()

        if target_type in test_type:
            count += 1

    return count


def get_all_inputs(relevant_data):
    """
    Récupère les inputs depuis une page simple ou plusieurs pages.
    """
    inputs = []

    inputs.extend(relevant_data.get("inputs", []))

    for page in relevant_data.get("pages", []):
        inputs.extend(page.get("inputs", []))

    return inputs


def get_all_links(relevant_data):
    """
    Récupère les liens depuis une page simple ou plusieurs pages.
    """
    links = []

    links.extend(relevant_data.get("links", []))

    for page in relevant_data.get("pages", []):
        links.extend(page.get("links", []))

    return links


def get_all_images(relevant_data):
    """
    Récupère les images si elles existent dans les données analysées.
    """
    images = []

    images.extend(relevant_data.get("images", []))

    for page in relevant_data.get("pages", []):
        images.extend(page.get("images", []))

    return images


def get_page_titles(relevant_data):
    """
    Récupère les titres des pages analysées.
    """
    titles = []

    if relevant_data.get("title"):
        titles.append(relevant_data.get("title"))

    for page in relevant_data.get("pages", []):
        title = page.get("title")

        if title:
            titles.append(title)

    return titles


def is_https_url(url):
    return str(url or "").lower().startswith("https://")


def get_domain(url):
    try:
        parsed = urlparse(url)
        return parsed.netloc.lower().replace("www.", "")
    except Exception:
        return ""


def enrich_missing_tests(test_cases, semantic_actions):
    """
    Ajoute seulement quelques tests detail_navigation oubliés par Gemini.
    Évite d'ajouter trop de bruit.
    """

    existing_text = json.dumps(test_cases, ensure_ascii=False).lower()

    existing_names = {(test.get("name") or "").lower() for test in test_cases}

    added_count = 0
    max_auto_tests = 10

    ignored_keywords = [
        "open menu",
        "close menu",
        "aperçu",
        "preview",
        "introduction",
        "sessions",
        "environment",
        "fundamentals",
        "basics",
        "methods",
        "locators",
    ]

    for action in semantic_actions:
        if action.get("type") != "detail_navigation":
            continue

        page_url = action.get("page_url", "page analysée")

        for label in action.get("sample_labels", []):
            label_lower = label.lower()

            if added_count >= max_auto_tests:
                return test_cases

            if label_lower in existing_text:
                continue

            if any(word in label_lower for word in ignored_keywords):
                continue

            label_clean = safe_test_name(label)

            if not label_clean:
                continue

            label_clean = label_clean[:30]

            test_name = f"TC_DETAIL_AUTO_{label_clean}"

            if test_name.lower() in existing_names:
                continue

            test_cases.append(
                {
                    "name": test_name,
                    "type": "detail_navigation",
                    "priority": "medium",
                    "steps": [
                        f"Naviguer vers la page : {page_url}",
                        f"Cliquer sur le lien ou bouton '{label}'.",
                    ],
                    "expected_result": "L'utilisateur doit être redirigé vers une page de détail ou un contenu associé.",
                    "selenium_script": "",
                    "cypress_script": "",
                }
            )

            existing_names.add(test_name.lower())
            existing_text += " " + label_lower
            added_count += 1

    return test_cases


def ensure_security_tests(test_cases, relevant_data, url, test_types):
    """
    Ajoute des tests sécurité génériques si security est demandé.
    """

    if "security" not in test_types:
        return test_cases

    security_count = count_test_type(test_cases, "security")

    if security_count >= 2:
        return test_cases

    inputs = get_all_inputs(relevant_data)
    links = get_all_links(relevant_data)

    has_password = any(
        (field.get("type") or "").lower() == "password" for field in inputs
    )

    has_text_input = any(
        (field.get("type") or "text").lower() in ["text", "email", "search", "password"]
        for field in inputs
    )

    existing_names = {str(test.get("name", "")).lower() for test in test_cases}

    if "tc_security_auto_001_verify_https_usage" not in existing_names:
        test_cases.append(
            {
                "name": "TC_SECURITY_AUTO_001_VerifyHTTPSUsage",
                "type": "security",
                "priority": "high",
                "steps": [
                    f"Accéder à l'URL : {url}",
                    "Vérifier que l'URL commence par https://.",
                ],
                "expected_result": "La page doit être chargée via HTTPS afin d'assurer une connexion sécurisée.",
                "selenium_script": f'driver.get("{url}")\nassert driver.current_url.startswith("https://")',
                "cypress_script": f'cy.visit("{url}")\ncy.url().should("include", "https://")',
            }
        )

    if (
        has_password
        and "tc_security_auto_002_verify_password_masking" not in existing_names
    ):
        test_cases.append(
            {
                "name": "TC_SECURITY_AUTO_002_VerifyPasswordMasking",
                "type": "security",
                "priority": "high",
                "steps": [
                    f"Accéder à l'URL : {url}",
                    "Identifier le champ mot de passe.",
                    "Vérifier que le champ est de type password.",
                ],
                "expected_result": "Le mot de passe saisi doit être masqué et le champ doit avoir le type password.",
                "selenium_script": (
                    f'driver.get("{url}")\n'
                    "password_fields = driver.find_elements(By.CSS_SELECTOR, \"input[type='password']\")\n"
                    "assert len(password_fields) > 0"
                ),
                "cypress_script": (
                    f'cy.visit("{url}")\n'
                    'cy.get("input[type=\'password\']").should("exist")'
                ),
            }
        )

    if (
        has_text_input
        and "tc_security_auto_003_check_xss_input_handling" not in existing_names
    ):
        test_cases.append(
            {
                "name": "TC_SECURITY_AUTO_003_CheckXSSInputHandling",
                "type": "security",
                "priority": "medium",
                "steps": [
                    f"Accéder à l'URL : {url}",
                    "Saisir une charge XSS simple dans un champ texte.",
                    "Soumettre le formulaire si un bouton est disponible.",
                    "Vérifier que le script n'est pas exécuté.",
                ],
                "expected_result": "L'application ne doit pas exécuter le script injecté et doit traiter l'entrée de manière sécurisée.",
                "selenium_script": "",
                "cypress_script": "",
            }
        )

    if links and "tc_security_auto_004_check_links_are_safe" not in existing_names:
        test_cases.append(
            {
                "name": "TC_SECURITY_AUTO_004_CheckLinksAreSafe",
                "type": "security",
                "priority": "medium",
                "steps": [
                    f"Accéder à l'URL : {url}",
                    "Vérifier que les liens importants ont un href valide.",
                    "Vérifier qu'aucun lien vide ou suspect n'est utilisé dans la navigation principale.",
                ],
                "expected_result": "Les liens visibles doivent avoir des destinations valides et ne doivent pas rediriger vers des destinations inattendues.",
                "selenium_script": "",
                "cypress_script": "",
            }
        )

    return test_cases


def ensure_seo_tests(test_cases, relevant_data, url, test_types):
    """
    Ajoute des tests SEO génériques si seo est demandé.
    """

    if "seo" not in test_types:
        return test_cases

    seo_count = count_test_type(test_cases, "seo")

    if seo_count >= 2:
        return test_cases

    links = get_all_links(relevant_data)
    images = get_all_images(relevant_data)

    existing_names = {str(test.get("name", "")).lower() for test in test_cases}

    if "tc_seo_auto_001_verify_title_presence" not in existing_names:
        test_cases.append(
            {
                "name": "TC_SEO_AUTO_001_VerifyTitlePresence",
                "type": "seo",
                "priority": "high",
                "steps": [
                    f"Accéder à l'URL : {url}",
                    "Vérifier la présence d'une balise title non vide.",
                ],
                "expected_result": "La page doit contenir un titre pertinent et non vide.",
                "selenium_script": f'driver.get("{url}")\nassert driver.title.strip() != ""',
                "cypress_script": f'cy.visit("{url}")\ncy.title().should("not.be.empty")',
            }
        )

    if "tc_seo_auto_002_verify_url_readability" not in existing_names:
        test_cases.append(
            {
                "name": "TC_SEO_AUTO_002_VerifyURLReadability",
                "type": "seo",
                "priority": "medium",
                "steps": [
                    f"Analyser l'URL : {url}",
                    "Vérifier que l'URL est lisible et descriptive.",
                ],
                "expected_result": "L'URL doit être lisible, descriptive et ne doit pas contenir une longue chaîne de paramètres inutiles.",
                "selenium_script": "",
                "cypress_script": "",
            }
        )

    if links and "tc_seo_auto_003_check_links_text" not in existing_names:
        test_cases.append(
            {
                "name": "TC_SEO_AUTO_003_CheckLinksText",
                "type": "seo",
                "priority": "medium",
                "steps": [
                    f"Accéder à l'URL : {url}",
                    "Vérifier que les liens importants ont un texte visible.",
                ],
                "expected_result": "Les liens importants doivent avoir un texte descriptif utile pour l'utilisateur et le référencement.",
                "selenium_script": "",
                "cypress_script": "",
            }
        )

    if images and "tc_seo_auto_004_check_images_alt" not in existing_names:
        test_cases.append(
            {
                "name": "TC_SEO_AUTO_004_CheckImagesAltAttributes",
                "type": "seo",
                "priority": "medium",
                "steps": [
                    f"Accéder à l'URL : {url}",
                    "Vérifier que les images importantes possèdent un attribut alt.",
                ],
                "expected_result": "Les images importantes doivent avoir un attribut alt non vide pour améliorer l'accessibilité et le SEO.",
                "selenium_script": "",
                "cypress_script": "",
            }
        )

    return test_cases


def enrich_security_and_seo_tests(test_cases, relevant_data, url, test_types):
    """
    Point d'entrée principal pour enrichir automatiquement les tests SEO/Sécurité.
    """

    test_cases = ensure_security_tests(test_cases, relevant_data, url, test_types)

    test_cases = ensure_seo_tests(test_cases, relevant_data, url, test_types)

    return test_cases
