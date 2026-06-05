def get_field_label(field):
    return (
        field.get("placeholder")
        or field.get("name")
        or field.get("id")
        or field.get("aria_label")
        or "champ détecté"
    )


def build_valid_form_steps(inputs, textareas, buttons):
    steps = []

    for field in inputs:
        field_type = (field.get("type") or "text").lower()
        label = get_field_label(field)

        if field_type == "email":
            steps.append(f"Saisir une adresse email valide dans le champ '{label}'.")
        elif field_type == "password":
            steps.append(f"Saisir un mot de passe valide dans le champ '{label}'.")
        elif field_type in ["checkbox", "radio"]:
            steps.append(f"Sélectionner l'option '{label}'.")
        else:
            steps.append(f"Saisir une valeur valide dans le champ '{label}'.")

    for textarea in textareas:
        label = get_field_label(textarea)
        steps.append(f"Saisir un message valide dans la zone de texte '{label}'.")

    if buttons:
        button = buttons[0]
        button_label = (
            button.get("text")
            or button.get("value")
            or button.get("id")
            or "bouton principal"
        )
        steps.append(f"Cliquer sur le bouton '{button_label}'.")
    else:
        steps.append("Soumettre le formulaire.")

    return steps


def build_selector(field):
    if field.get("id"):
        return f'(By.ID, "{field.get("id")}")'
    if field.get("name"):
        return f'(By.NAME, "{field.get("name")}")'
    if field.get("placeholder"):
        return f'(By.CSS_SELECTOR, "[placeholder=\'{field.get("placeholder")}\']")'
    return None


def build_form_selenium_script(inputs, textareas, buttons):
    lines = [
        "from selenium.webdriver.common.by import By",
        "",
    ]

    for field in inputs:
        selector = build_selector(field)

        if not selector:
            continue

        field_type = (field.get("type") or "text").lower()

        lines.append(f"element = safe_find_element(driver, [{selector}])")

        if field_type == "email":
            lines.append('element.send_keys("test@example.com")')
        elif field_type == "password":
            lines.append('element.send_keys("Password123")')
        elif field_type in ["checkbox", "radio"]:
            lines.append("element.click()")
        else:
            lines.append('element.send_keys("Test Automation")')

        lines.append("")

    for textarea in textareas:
        selector = build_selector(textarea)

        if not selector:
            continue

        lines.append(f"element = safe_find_element(driver, [{selector}])")
        lines.append('element.send_keys("Message de test automatique.")')
        lines.append("")

    if buttons:
        button = buttons[0]
        selector = build_selector(button)

        if selector:
            lines.append(f"button = safe_find_element(driver, [{selector}])")
            lines.append("button.click()")

    return "\n".join(lines)


def build_link_tests(links, page_url=None, global_links=None):
    if global_links is None:
        global_links = set()
    tests = []
    seen = set()

    for index, link in enumerate(links[:10], start=1):
        text = link.get("text") or link.get("aria_label") or ""
        href = link.get("href") or ""

        if not href:
            continue

        normalized_href = normalize_url(href)

        if (
            "udemy.com" in href
            or "linkedin.com" in href 
            or "selenium.dev" in href
        ):
            continue

        if not text.strip():
            continue

        normalized_text = text.strip().lower()
        if normalized_text == "lien détecté":
            continue

        key = (text.strip().lower(), href.strip().lower())

        if key in seen:
            continue

        seen.add(key)

        if normalized_href in global_links:
           continue
        priority = "medium"
        

        tests.append({
            "name": f"Navigation depuis {page_url or 'page'} - {text[:40]}",
            "type": "navigation",
            "priority": priority,
            "steps": [
                f"Naviguer vers la page source : {page_url or 'page analysée'}.",
                f"Cliquer sur le lien '{text}'."
            ],
            "expected_result": f"L'utilisateur doit être redirigé vers : {href}.",
            "selenium_script": "",
            "cypress_script": ""
        })

    return tests

def normalize_text(value):
    return (value or "").strip().lower()


def get_test_unique_key(test):
    """
    Crée une clé unique pour éviter les tests dupliqués.
    """
    test_name = normalize_text(test.get("name"))
    test_type = normalize_text(test.get("type"))
    expected_result = normalize_text(test.get("expected_result"))

    return f"{test_type}|{test_name}|{expected_result}"


def remove_duplicate_tests(test_cases):
    """
    Supprime les cas de test répétés dans l'analyse multi-pages.
    """
    unique_tests = []
    seen = set()

    for test in test_cases:
        key = get_test_unique_key(test)

        if key in seen:
            continue

        seen.add(key)
        unique_tests.append(test)

    return unique_tests

def normalize_url(value):
    return (value or "").strip().lower().rstrip("/")


def detect_global_links(pages, min_occurrences=2):
    """
    Détecte automatiquement les liens globaux présents sur plusieurs pages.
    Exemple : menu header, footer, logo, privacy policy...
    """
    link_occurrences = {}

    for page in pages:
        page_url = page.get("url")

        for link in page.get("links", []):
            href = normalize_url(link.get("href"))
            text = normalize_text(link.get("text") or link.get("aria_label"))

            if not href:
                continue

            key = href

            if key not in link_occurrences:
                link_occurrences[key] = {
                    "href": href,
                    "texts": set(),
                    "pages": set()
                }

            if text:
                link_occurrences[key]["texts"].add(text)

            if page_url:
                link_occurrences[key]["pages"].add(page_url)

    global_links = set()

    for href, data in link_occurrences.items():
        if len(data["pages"]) >= min_occurrences:
            global_links.add(href)

    return global_links

def generate_rule_based_tests(page_type, relevant_data):
    """
    Génère des cas de test avec des règles simples.
    Ce module sert de fallback si l'IA externe ne répond pas.
    """

    test_cases = []

    if page_type == "login_page":
        inputs = relevant_data.get("inputs", [])
        links = relevant_data.get("links", [])

        has_email = any(
            "email" in (item.get("name") or "").lower()
            or "email" in (item.get("id") or "").lower()
            or "user" in (item.get("name") or "").lower()
            or "user" in (item.get("id") or "").lower()
            for item in inputs
        )

        has_password = any(
            "password" in (item.get("name") or "").lower()
            or "password" in (item.get("id") or "").lower()
            for item in inputs
        )

        has_remember_me = any(
            "remember" in (item.get("name") or "").lower()
            or "remember" in (item.get("id") or "").lower()
            for item in inputs
        )

        if has_email and has_password:
            test_cases.append({
                "name": "Login avec identifiants valides",
                "type": "positive",
                "priority": "high",
                "steps": [
                    "Saisir un identifiant valide",
                    "Saisir un mot de passe valide",
                    "Cliquer sur le bouton de connexion"
                ],
                "expected_result": "L'utilisateur doit être connecté avec succès.",
                "selenium_script": build_form_selenium_script(
                    inputs,
                    [],
                    relevant_data.get("buttons", [])
                ),
                "cypress_script": ""
            })

            test_cases.append({
                "name": "Login avec identifiant vide",
                "type": "negative",
                "priority": "high",
                "steps": [
                    "Laisser le champ identifiant vide",
                    "Saisir un mot de passe valide",
                    "Cliquer sur le bouton de connexion"
                ],
                "expected_result": "Un message d'erreur doit indiquer que l'identifiant est obligatoire.",
                "selenium_script": "",
                "cypress_script": ""
            })

            test_cases.append({
                "name": "Login avec mot de passe vide",
                "type": "negative",
                "priority": "high",
                "steps": [
                    "Saisir un identifiant valide",
                    "Laisser le champ mot de passe vide",
                    "Cliquer sur le bouton de connexion"
                ],
                "expected_result": "Un message d'erreur doit indiquer que le mot de passe est obligatoire.",
                "selenium_script": "",
                "cypress_script": ""
            })

            test_cases.append({
                "name": "Login avec identifiants invalides",
                "type": "negative",
                "priority": "medium",
                "steps": [
                    "Saisir un identifiant invalide",
                    "Saisir un mot de passe invalide",
                    "Cliquer sur le bouton de connexion"
                ],
                "expected_result": "Un message d'erreur doit indiquer que les identifiants sont incorrects.",
                "selenium_script": "",
                "cypress_script": ""
            })

        if has_remember_me:
            test_cases.append({
                "name": "Vérification de Remember Me",
                "type": "functional",
                "priority": "medium",
                "steps": [
                    "Saisir un identifiant valide",
                    "Saisir un mot de passe valide",
                    "Cocher Remember Me",
                    "Cliquer sur le bouton de connexion"
                ],
                "expected_result": "L'option Remember Me doit être prise en compte.",
                "selenium_script": "",
                "cypress_script": ""
            })

        test_cases.extend(
            build_link_tests(
                links,
                relevant_data.get("page_url"),
                relevant_data.get("global_links")
            )
        )

    elif page_type == "form_page":
        inputs = relevant_data.get("inputs", [])
        buttons = relevant_data.get("buttons", [])
        textareas = relevant_data.get("textareas", [])

        if inputs or textareas:
            test_cases.append({
                "name": "Soumission formulaire avec données valides",
                "type": "positive",
                "priority": "high",
                "steps": build_valid_form_steps(inputs, textareas, buttons),
                "expected_result": "Le formulaire doit être soumis avec succès ou afficher un message de confirmation.",
                "selenium_script": build_form_selenium_script(inputs, textareas, buttons),
                "cypress_script": ""
            })

            test_cases.append({
                "name": "Soumission avec champ obligatoire vide",
                "type": "negative",
                "priority": "high",
                "steps": [
                    "Laisser un champ obligatoire vide",
                    "Cliquer sur le bouton de soumission"
                ],
                "expected_result": "Un message d'erreur doit indiquer que le champ est obligatoire.",
                "selenium_script": "",
                "cypress_script": ""
            })

        if any((item.get("type") or "").lower() == "email" for item in inputs):
            test_cases.append({
                "name": "Validation du format email",
                "type": "negative",
                "priority": "medium",
                "steps": [
                    "Saisir une adresse email invalide",
                    "Soumettre le formulaire"
                ],
                "expected_result": "Un message d'erreur doit indiquer que le format email est incorrect.",
                "selenium_script": "",
                "cypress_script": ""
            })

        if any((item.get("type") or "").lower() == "radio" for item in inputs):
            test_cases.append({
                "name": "Sélection d'un bouton radio",
                "type": "functional",
                "priority": "medium",
                "steps": [
                    "Sélectionner une option radio",
                    "Soumettre le formulaire"
                ],
                "expected_result": "L'option sélectionnée doit être prise en compte.",
                "selenium_script": "",
                "cypress_script": ""
            })

        if any((item.get("type") or "").lower() == "checkbox" for item in inputs):
            test_cases.append({
                "name": "Sélection d'une case à cocher",
                "type": "functional",
                "priority": "medium",
                "steps": [
                    "Cocher une ou plusieurs cases",
                    "Soumettre le formulaire"
                ],
                "expected_result": "Les cases cochées doivent être prises en compte.",
                "selenium_script": "",
                "cypress_script": ""
            })

        if buttons:
            test_cases.append({
                "name": "Vérification du bouton d'action principal",
                "type": "functional",
                "priority": "medium",
                "steps": [
                    "Cliquer sur le bouton principal détecté"
                ],
                "expected_result": "L'action associée au bouton doit être exécutée correctement.",
                "selenium_script": "",
                "cypress_script": ""
            })

        test_cases.extend(
            build_link_tests(
                relevant_data.get("links", []),
                relevant_data.get("page_url"),
                relevant_data.get("global_links")
            )
        )

    elif page_type == "home_page":
        inputs = relevant_data.get("inputs", [])
        buttons = relevant_data.get("buttons", [])
        links = relevant_data.get("links", [])

        if inputs:
            test_cases.append({
                "name": "Interaction avec les champs de la page",
                "type": "functional",
                "priority": "medium",
                "steps": build_valid_form_steps(inputs, [], buttons),
                "expected_result": "Les champs détectés doivent accepter les données utilisateur.",
                "selenium_script": build_form_selenium_script(inputs, [], buttons),
                "cypress_script": ""
            })

        if buttons:
            test_cases.append({
                "name": "Vérification des boutons d'action de la page",
                "type": "functional",
                "priority": "medium",
                "steps": [
                    "Identifier les boutons d'action visibles.",
                    "Cliquer sur le bouton principal détecté."
                ],
                "expected_result": "L'action associée au bouton doit fonctionner correctement.",
                "selenium_script": "",
                "cypress_script": ""
            })

        test_cases.extend(
            build_link_tests(
                links,
                relevant_data.get("page_url"),
                relevant_data.get("global_links")
            )
        )

    elif page_type == "action_page":
        buttons = relevant_data.get("buttons", [])
        links = relevant_data.get("links", [])

        if buttons:
            test_cases.append({
                "name": "Vérification des actions disponibles",
                "type": "functional",
                "priority": "medium",
                "steps": [
                    "Identifier les boutons d'action visibles.",
                    "Cliquer sur le bouton principal détecté."
                ],
                "expected_result": "L'action associée au bouton doit être exécutée correctement.",
                "selenium_script": "",
                "cypress_script": ""
            })

        test_cases.extend(
            build_link_tests(
                links,
                relevant_data.get("page_url"),
                relevant_data.get("global_links")
            )
        )

    elif page_type == "multi_page_analysis":
        pages = relevant_data.get("pages", [])
        global_links = detect_global_links(pages)

        for page in pages:
            current_page_type = page.get("page_type")

            page_data = {
                "page_url": page.get("url"),
                "inputs": page.get("inputs", []),
                "buttons": page.get("buttons", []),
                "links": page.get("links", []),
                "forms": page.get("forms", []),
                "textareas": page.get("textareas", []),
                "selects": page.get("selects", []),
                "global_links": global_links
            }

            sub_tests = generate_rule_based_tests(
                current_page_type,
                page_data
            )

            test_cases.extend(sub_tests)

        test_cases = remove_duplicate_tests(test_cases)

    else:
        test_cases.extend(
            build_link_tests(
                relevant_data.get("links", []),
                relevant_data.get("page_url"),
                relevant_data.get("global_links")
            )
        )

    return remove_duplicate_tests(test_cases)