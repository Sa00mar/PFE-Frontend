import re
from urllib.parse import urljoin


# ==========================================================
# OUTILS GÉNÉRIQUES
# ==========================================================


def normalize_text(value):
    return (value or "").strip()


def escape_python_string(value):
    return str(value or "").replace("\\", "\\\\").replace('"', '\\"')


def escape_css_value(value):
    return str(value or "").replace("\\", "\\\\").replace('"', '\\"')


def get_analysis_url(relevant_data):
    """
    Récupère l'URL principale de l'analyse de façon générique.
    """

    if not relevant_data:
        return ""

    if relevant_data.get("url"):
        return relevant_data.get("url")

    if relevant_data.get("analysis_url"):
        return relevant_data.get("analysis_url")

    pages = relevant_data.get("pages", [])
    if pages and pages[0].get("url"):
        return pages[0].get("url")

    return ""


def get_element_identity(element):
    """
    Retourne un texte global pour comprendre le rôle d'un élément.
    Fonction générique : input, button, textarea, select, link.
    """
    return " ".join(
        [
            str(element.get("id") or ""),
            str(element.get("name") or ""),
            str(element.get("type") or ""),
            str(element.get("text") or ""),
            str(element.get("value") or ""),
            str(element.get("placeholder") or ""),
            str(element.get("aria_label") or ""),
            str(element.get("class") or ""),
            str(element.get("href") or ""),
        ]
    ).lower()


def make_variable_name(element, default_name="element"):
    """
    Crée un nom de variable lisible pour le script Selenium.
    """
    identity = get_element_identity(element)
    tag = (element.get("tag") or "").lower()

    if tag == "a":
        text = normalize_text(element.get("text"))
        if text:
            clean = re.sub(r"[^a-zA-Z0-9]+", "_", text.lower()).strip("_")
            return f"{clean}_link"
        return "navigation_link"

    if "password" in identity or "passwd" in identity:
        return "password_field"

    if "email" in identity:
        return "email_field"

    if "username" in identity or "user" in identity or "login" in identity:
        return "username_field"

    if "first" in identity and "name" in identity:
        return "first_name_field"

    if "last" in identity and "name" in identity:
        return "last_name_field"

    if "message" in identity or "comment" in identity:
        return "message_field"

    if "search" in identity:
        return "search_field"

    if "submit" in identity:
        return "submit_button"

    if tag == "button":
        return "action_button"

    if tag == "textarea":
        return "message_field"

    if tag == "select":
        return "select_field"

    return default_name


def get_test_value_for_field(field, test_credentials=None, mode="valid"):
    """
    Donne une valeur de test selon le type du champ.
    Si des credentials sont détectés, on les utilise.
    Sinon on utilise des valeurs neutres.
    """
    if test_credentials is None:
        test_credentials = {}

    field_type = (field.get("type") or "").lower()
    identity = get_element_identity(field)

    if mode == "invalid":
        if "email" in identity or field_type == "email":
            return "invalid-email"
        if "password" in identity or field_type == "password":
            return "InvalidSecretValue"
        if "username" in identity or "user" in identity or "login" in identity:
            return "invalid_user"
        if "phone" in identity or "tel" in identity:
            return "abc123"
        return "invalid_value"

    if "password" in identity or field_type == "password":
        return test_credentials.get("password", "SecureTestValue!A9")

    if "email" in identity or field_type == "email":
        return test_credentials.get("email", "test@example.com")

    if "username" in identity or "user" in identity or "login" in identity:
        return test_credentials.get("username", "test_user")

    if "first" in identity and "name" in identity:
        return "John"

    if "last" in identity and "name" in identity:
        return "Doe"

    if "phone" in identity or "tel" in identity:
        return "12345678"

    if "search" in identity:
        return "test"

    if "message" in identity or "comment" in identity:
        return "Ceci est un message de test automatique."

    return "Test Automation"


# ==========================================================
# FILTRAGE DES CHAMPS
# ==========================================================


def is_testable_field(field):
    """
    Vérifie si un input est réellement testable.
    """
    if not field:
        return False

    field_type = (field.get("type") or "text").lower()

    ignored_types = [
        "hidden",
        "submit",
        "button",
        "reset",
        "image",
        "file",
    ]

    if field_type in ignored_types:
        return False

    if field.get("disabled") or field.get("readonly"):
        return False

    return True


def is_required_or_important_field(field):
    """
    Détecte un champ important pour créer des tests négatifs.
    """
    if not field:
        return False

    if field.get("required"):
        return True

    identity = get_element_identity(field)

    important_words = [
        "username",
        "user",
        "login",
        "email",
        "password",
        "name",
        "message",
        "search",
    ]

    return any(word in identity for word in important_words)


# ==========================================================
# CONSTRUCTION DES SÉLECTEURS
# ==========================================================


def build_selectors(element):
    """
    Retourne une liste de sélecteurs Selenium possibles.
    Exemple :
    [(By.ID, "username"), (By.NAME, "username")]
    """
    if not element:
        return []

    selectors = []
    tag = (element.get("tag") or "").lower()

    element_id = normalize_text(element.get("id"))
    element_name = normalize_text(element.get("name"))
    element_class = normalize_text(element.get("class"))
    element_text = normalize_text(element.get("text"))
    element_href = normalize_text(element.get("href"))
    element_type = normalize_text(element.get("type"))

    if element_id:
        selectors.append(f'(By.ID, "{escape_python_string(element_id)}")')

    if element_name:
        selectors.append(f'(By.NAME, "{escape_python_string(element_name)}")')

    if tag == "a":
        if element_text:
            selectors.append(f'(By.LINK_TEXT, "{escape_python_string(element_text)}")')
        if element_href:
            selectors.append(
                f'(By.CSS_SELECTOR, "a[href=\\"{escape_css_value(element_href)}\\"]")'
            )

    elif tag == "button":
        if element_type:
            selectors.append(
                f'(By.CSS_SELECTOR, "button[type=\\"{escape_css_value(element_type)}\\"]")'
            )
        if element_text:
            safe_text = escape_python_string(element_text)
            selectors.append(
                f'(By.XPATH, "//button[contains(normalize-space(.), \\"{safe_text}\\")]")'
            )

    elif tag == "textarea":
        if element_name:
            selectors.append(
                f'(By.CSS_SELECTOR, "textarea[name=\\"{escape_css_value(element_name)}\\"]")'
            )

    elif tag == "select":
        if element_name:
            selectors.append(
                f'(By.CSS_SELECTOR, "select[name=\\"{escape_css_value(element_name)}\\"]")'
            )

    else:
        # input ou élément générique
        if element_name:
            selectors.append(
                f'(By.CSS_SELECTOR, "input[name=\\"{escape_css_value(element_name)}\\"]")'
            )
        if element_type:
            selectors.append(
                f'(By.CSS_SELECTOR, "input[type=\\"{escape_css_value(element_type)}\\"]")'
            )

    if element_class:
        first_class = element_class.split()[0]
        if first_class:
            selectors.append(f'(By.CLASS_NAME, "{escape_python_string(first_class)}")')

    # Supprimer doublons
    unique_selectors = []
    for selector in selectors:
        if selector not in unique_selectors:
            unique_selectors.append(selector)

    return unique_selectors


def build_selector(element):
    """
    Compatibilité avec l'ancien code.
    Retourne le meilleur sélecteur seul.
    """
    selectors = build_selectors(element)
    if selectors:
        return selectors[0]
    return None


def build_selector_list_text(element):
    """
    Retourne le texte à mettre dans safe_find_element(driver, [...]).
    """
    selectors = build_selectors(element)
    return ", ".join(selectors)


# ==========================================================
# DÉTECTION BOUTON PRINCIPAL
# ==========================================================


def find_main_submit_button(buttons):
    """
    Trouve le bouton principal d'action.
    Générique : submit, send, login, save, search, continue...
    """
    if not buttons:
        return None

    priority_words = [
        "submit",
        "send",
        "login",
        "connexion",
        "sign in",
        "save",
        "search",
        "continue",
        "confirm",
        "next",
        "create",
        "register",
    ]

    for button in buttons:
        identity = get_element_identity(button)
        if any(word in identity for word in priority_words):
            return button

    return buttons[0]


# ==========================================================
# SCRIPT SELENIUM GÉNÉRIQUE FORMULAIRE
# ==========================================================


def build_generic_form_selenium_script(
    inputs=None,
    textareas=None,
    selects=None,
    buttons=None,
    test_credentials=None,
    mode="valid",
    empty_field_keyword=None,
):
    """
    Génère un script Selenium générique pour :
    - login
    - contact
    - inscription
    - recherche
    - formulaire classique
    - tests négatifs
    """

    inputs = inputs or []
    textareas = textareas or []
    selects = selects or []
    buttons = buttons or []
    test_credentials = test_credentials or {}

    lines = [
        "from selenium.webdriver.common.by import By",
        "",
    ]

    used_variables = {}

    def unique_variable_name(base_name):
        count = used_variables.get(base_name, 0)
        used_variables[base_name] = count + 1

        if count == 0:
            return base_name

        return f"{base_name}_{count + 1}"

    # INPUTS
    for field in inputs:
        if not is_testable_field(field):
            continue

        selector_text = build_selector_list_text(field)
        if not selector_text:
            continue

        variable_name = unique_variable_name(make_variable_name(field, "input_field"))
        identity = get_element_identity(field)

        lines.append(f"{variable_name} = safe_find_element(driver, [{selector_text}])")
        lines.append(f"{variable_name}.clear()")

        if empty_field_keyword and empty_field_keyword in identity:
            lines.append("")
            continue

        value = get_test_value_for_field(
            field,
            test_credentials=test_credentials,
            mode=mode,
        )

        lines.append(f'{variable_name}.send_keys("{escape_python_string(value)}")')
        lines.append("")

    # TEXTAREAS
    for textarea in textareas:
        selector_text = build_selector_list_text(textarea)
        if not selector_text:
            continue

        variable_name = unique_variable_name(
            make_variable_name(textarea, "textarea_field")
        )
        identity = get_element_identity(textarea)

        lines.append(f"{variable_name} = safe_find_element(driver, [{selector_text}])")
        lines.append(f"{variable_name}.clear()")

        if empty_field_keyword and empty_field_keyword in identity:
            lines.append("")
            continue

        lines.append(
            f'{variable_name}.send_keys("Ceci est un message de test automatique.")'
        )
        lines.append("")

    # SELECTS
    for select in selects:
        selector_text = build_selector_list_text(select)
        if not selector_text:
            continue

        variable_name = unique_variable_name(make_variable_name(select, "select_field"))
        lines.append(f"{variable_name} = safe_find_element(driver, [{selector_text}])")
        lines.append("# Sélection automatique à compléter si nécessaire")
        lines.append("")

    # BOUTON PRINCIPAL
    submit_button = find_main_submit_button(buttons)

    if submit_button:
        selector_text = build_selector_list_text(submit_button)

        if selector_text:
            lines.append(
                f"submit_button = safe_find_element(driver, [{selector_text}])"
            )
        else:
            lines.append(
                "submit_button = safe_find_element(driver, [(By.CSS_SELECTOR, \"button[type='submit'], input[type='submit']\")])"
            )

        lines.append("submit_button.click()")

    return "\n".join(lines).strip()


# ==========================================================
# SCRIPT CYPRESS GÉNÉRIQUE FORMULAIRE
# ==========================================================


def build_generic_form_cypress_script(
    url,
    inputs=None,
    textareas=None,
    buttons=None,
    test_credentials=None,
    mode="valid",
    empty_field_keyword=None,
):
    inputs = inputs or []
    textareas = textareas or []
    buttons = buttons or []
    test_credentials = test_credentials or {}

    lines = [
        f'cy.visit("{escape_python_string(url)}")',
    ]

    for field in inputs:
        if not is_testable_field(field):
            continue

        field_id = normalize_text(field.get("id"))
        field_name = normalize_text(field.get("name"))
        identity = get_element_identity(field)

        selector = ""

        if field_id:
            selector = f"#{field_id}"
        elif field_name:
            selector = f"input[name='{field_name}']"

        if not selector:
            continue

        lines.append(f'cy.get("{selector}").clear()')

        if empty_field_keyword and empty_field_keyword in identity:
            continue

        value = get_test_value_for_field(
            field,
            test_credentials=test_credentials,
            mode=mode,
        )

        lines.append(f'cy.get("{selector}").type("{escape_python_string(value)}")')

    for textarea in textareas:
        textarea_id = normalize_text(textarea.get("id"))
        textarea_name = normalize_text(textarea.get("name"))

        selector = ""

        if textarea_id:
            selector = f"#{textarea_id}"
        elif textarea_name:
            selector = f"textarea[name='{textarea_name}']"

        if selector:
            lines.append(
                f'cy.get("{selector}").clear().type("Ceci est un message de test automatique.")'
            )

    submit_button = find_main_submit_button(buttons)

    if submit_button:
        button_id = normalize_text(submit_button.get("id"))
        button_text = normalize_text(submit_button.get("text"))

        if button_id:
            lines.append(f'cy.get("#{button_id}").click()')
        elif button_text:
            lines.append(
                f'cy.contains("button", "{escape_python_string(button_text)}").click()'
            )
        else:
            lines.append(
                "cy.get(\"button[type='submit'], input[type='submit']\").click()"
            )

    return "\n".join(lines).strip()


# ==========================================================
# SCRIPT NAVIGATION
# ==========================================================


def build_navigation_selenium_script(source_url, link):
    """
    Génère un script Selenium générique pour cliquer sur un lien.
    """
    if not link:
        return ""

    selector_text = build_selector_list_text(link)

    if not selector_text:
        return ""

    return "\n".join(
        [
            "from selenium.webdriver.common.by import By",
            "",
            f'driver.get("{escape_python_string(source_url)}")',
            f"navigation_link = safe_find_element(driver, [{selector_text}])",
            "navigation_link.click()",
        ]
    )


def build_navigation_cypress_script(source_url, link):
    """
    Génère un script Cypress générique pour cliquer sur un lien.
    """
    if not link:
        return ""

    text = normalize_text(link.get("text"))
    href = normalize_text(link.get("href"))

    lines = [
        f'cy.visit("{escape_python_string(source_url)}")',
    ]

    if text:
        lines.append(f'cy.contains("a", "{escape_python_string(text)}").click()')
    elif href:
        lines.append(f"cy.get(\"a[href='{escape_python_string(href)}']\").click()")

    return "\n".join(lines)


# ==========================================================
# SCRIPTS UI
# ==========================================================


def build_ui_selenium_script(url):
    return "\n".join(
        [
            f'driver.get("{escape_python_string(url)}")',
            'assert driver.title.strip() != ""',
        ]
    )


def build_ui_cypress_script(url):
    return "\n".join(
        [
            f'cy.visit("{escape_python_string(url)}")',
            'cy.title().should("not.be.empty")',
        ]
    )


# ==========================================================
# GÉNÉRATION DES TESTS RULE-BASED
# ==========================================================


def generate_rule_based_tests(page_type, relevant_data):
    """
    Génère des cas de test génériques à partir des éléments détectés.
    Cette version évite les scripts vides autant que possible.
    """

    if relevant_data is None:
        relevant_data = {}

    url = relevant_data.get("url") or relevant_data.get("page_url") or ""

    inputs = relevant_data.get("inputs", [])
    buttons = relevant_data.get("buttons", [])
    links = relevant_data.get("links", [])
    textareas = relevant_data.get("textareas", [])
    selects = relevant_data.get("selects", [])
    test_credentials = relevant_data.get("test_credentials", {})

    tests = []

    # ======================================================
    # 1. TEST UI DE CHARGEMENT
    # ======================================================

    url = get_analysis_url(relevant_data)
    tests.append(
        {
            "name": "TC_UI_AUTO_001_LoadPage",
            "type": "ui",
            "priority": "high",
            "steps": [
                f"Accéder à l'URL : {url}",
                "Vérifier que la page se charge correctement.",
                "Vérifier que le titre de la page est présent.",
            ],
            "expected_result": "La page doit se charger correctement sans erreur visible.",
            "selenium_script": build_ui_selenium_script(url),
            "cypress_script": build_ui_cypress_script(url),
        }
    )

    has_form_elements = bool(inputs or textareas or selects)

    # ======================================================
    # 2. TEST FORMULAIRE POSITIF
    # ======================================================
    if has_form_elements:
        is_authentication_page = (
            page_type == "login_page"
            or relevant_data.get("main_feature") in ["authentication", "login"]
            or any("password" in get_element_identity(field) for field in inputs)
        )

        if is_authentication_page:
            positive_name = "Login avec identifiants valides"
            positive_expected = "L'utilisateur doit être connecté avec succès."
        else:
            positive_name = "Soumission valide du formulaire"
            positive_expected = (
                "Le formulaire doit être soumis correctement avec des données valides."
            )

        tests.append(
            {
                "name": positive_name,
                "type": "positive",
                "priority": "high",
                "steps": [
                    "Remplir les champs obligatoires avec des valeurs valides.",
                    "Cliquer sur le bouton principal du formulaire.",
                    "Vérifier que l'action est exécutée correctement.",
                ],
                "expected_result": positive_expected,
                "selenium_script": build_generic_form_selenium_script(
                    inputs=inputs,
                    textareas=textareas,
                    selects=selects,
                    buttons=buttons,
                    test_credentials=test_credentials,
                    mode="valid",
                ),
                "cypress_script": build_generic_form_cypress_script(
                    url=url,
                    inputs=inputs,
                    textareas=textareas,
                    buttons=buttons,
                    test_credentials=test_credentials,
                    mode="valid",
                ),
            }
        )

        # ==================================================
        # 3. TESTS NÉGATIFS GÉNÉRIQUES
        # ==================================================
        important_fields = [
            field for field in inputs if is_required_or_important_field(field)
        ]

        # Limiter pour éviter trop de tests
        for index, field in enumerate(important_fields[:3], start=1):
            identity = get_element_identity(field)

            if "password" in identity:
                field_label = "mot de passe"
                empty_keyword = "password"
            elif "email" in identity:
                field_label = "email"
                empty_keyword = "email"
            elif "username" in identity or "user" in identity or "login" in identity:
                field_label = "identifiant"
                empty_keyword = "user"
            else:
                field_label = "champ obligatoire"
                empty_keyword = ""

            tests.append(
                {
                    "name": f"Validation champ vide - {field_label}",
                    "type": "negative",
                    "priority": "medium",
                    "steps": [
                        f"Laisser le champ {field_label} vide.",
                        "Remplir les autres champs si nécessaire.",
                        "Cliquer sur le bouton principal.",
                        "Vérifier qu'un message d'erreur ou une validation apparaît.",
                    ],
                    "expected_result": f"Un message d'erreur doit indiquer que le champ {field_label} est obligatoire ou invalide.",
                    "selenium_script": build_generic_form_selenium_script(
                        inputs=inputs,
                        textareas=textareas,
                        selects=selects,
                        buttons=buttons,
                        test_credentials=test_credentials,
                        mode="valid",
                        empty_field_keyword=empty_keyword,
                    ),
                    "cypress_script": build_generic_form_cypress_script(
                        url=url,
                        inputs=inputs,
                        textareas=textareas,
                        buttons=buttons,
                        test_credentials=test_credentials,
                        mode="valid",
                        empty_field_keyword=empty_keyword,
                    ),
                }
            )

        tests.append(
            {
                "name": "Soumission avec valeurs invalides",
                "type": "negative",
                "priority": "medium",
                "steps": [
                    "Remplir les champs avec des valeurs invalides.",
                    "Cliquer sur le bouton principal.",
                    "Vérifier que le système refuse les données invalides.",
                ],
                "expected_result": "Le système doit afficher un message d'erreur ou empêcher la soumission invalide.",
                "selenium_script": build_generic_form_selenium_script(
                    inputs=inputs,
                    textareas=textareas,
                    selects=selects,
                    buttons=buttons,
                    test_credentials=test_credentials,
                    mode="invalid",
                ),
                "cypress_script": build_generic_form_cypress_script(
                    url=url,
                    inputs=inputs,
                    textareas=textareas,
                    buttons=buttons,
                    test_credentials=test_credentials,
                    mode="invalid",
                ),
            }
        )

    # ======================================================
    # 4. TESTS NAVIGATION GÉNÉRIQUES
    # ======================================================
    navigation_links = []

    for link in links:
        text = normalize_text(link.get("text"))
        href = normalize_text(link.get("href"))

        if not href:
            continue

        if not text and not href:
            continue

        navigation_links.append(link)

    # Limiter pour ne pas générer trop de navigation
    for link in navigation_links[:8]:
        text = normalize_text(link.get("text")) or normalize_text(link.get("href"))
        source_url = link.get("page_url") or url
        expected_url = urljoin(source_url, normalize_text(link.get("href")))

        tests.append(
            {
                "name": f"Navigation - {text}",
                "type": "navigation",
                "priority": "low",
                "steps": [
                    f"Naviguer vers la page source : {source_url}.",
                    f"Cliquer sur le lien '{text}'.",
                    "Vérifier que la navigation se fait correctement.",
                ],
                "expected_result": f"L'utilisateur doit être redirigé vers : {expected_url}.",
                "selenium_script": build_navigation_selenium_script(source_url, link),
                "cypress_script": build_navigation_cypress_script(source_url, link),
            }
        )

    # ======================================================
    # 5. TEST BOUTON SIMPLE SI PAS DE FORMULAIRE
    # ======================================================
    if buttons and not has_form_elements:
        main_button = find_main_submit_button(buttons)

        if main_button:
            button_text = (
                normalize_text(main_button.get("text"))
                or normalize_text(main_button.get("value"))
                or "bouton principal"
            )

            selector_text = build_selector_list_text(main_button)

            selenium_script = ""

            if selector_text:
                selenium_script = "\n".join(
                    [
                        "from selenium.webdriver.common.by import By",
                        "",
                        f"action_button = safe_find_element(driver, [{selector_text}])",
                        "action_button.click()",
                    ]
                )

            tests.append(
                {
                    "name": f"Action bouton - {button_text}",
                    "type": "functional",
                    "priority": "medium",
                    "steps": [
                        f"Cliquer sur le bouton '{button_text}'.",
                        "Vérifier que l'action associée est exécutée.",
                    ],
                    "expected_result": "Le bouton doit déclencher l'action attendue sans erreur.",
                    "selenium_script": selenium_script,
                    "cypress_script": "",
                }
            )

    return tests
