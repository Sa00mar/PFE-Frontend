import re


def clean_value(value):
    return (value or "").strip().lower()


def format_selector_label(selector_value):
    """
    Déduit un nom lisible à partir du sélecteur.
    Exemple :
    username -> Champ Username
    password -> Champ Mot de passe
    submit -> Bouton Submit
    """
    value = clean_value(selector_value)

    if not value:
        return "Élément détecté automatiquement"

    if "username" in value or "user" in value or "login" in value:
        return "Champ Username"

    if "email" in value:
        return "Champ Email"

    if "password" in value or "passwd" in value:
        return "Champ Mot de passe"

    if "submit" in value:
        return "Bouton Submit"

    if "button" in value or "btn" in value:
        return "Bouton"

    if "logout" in value or "log out" in value:
        return "Bouton Logout"

    if "message" in value or "comment" in value:
        return "Champ Message"

    if "first" in value and "name" in value:
        return "Champ First Name"

    if "last" in value and "name" in value:
        return "Champ Last Name"

    if "form" in value:
        return "Formulaire"

    return selector_value.replace("_", " ").replace("-", " ").title()


def format_variable_name(variable_name, selectors=None):
    """
    Transforme un nom technique en nom lisible.
    Si la variable est trop générique comme 'element',
    on utilise le sélecteur pour trouver le vrai élément testé.
    """

    if selectors is None:
        selectors = []

    name = clean_value(variable_name)

    generic_names = ["element", "field", "input", "el"]

    if not name or name in generic_names:
        if selectors:
            return format_selector_label(selectors[0][1])
        return "Élément détecté automatiquement"

    if "submit" in name and "button" in name:
        return "Bouton Submit"

    if "button" in name or "btn" in name:
        return "Bouton"

    if "username" in name or "user" in name or "login" in name:
        return "Champ Username"

    if "email" in name:
        return "Champ Email"

    if "password" in name:
        return "Champ Mot de passe"

    if "first" in name and "name" in name:
        return "Champ First Name"

    if "last" in name and "name" in name:
        return "Champ Last Name"

    if "message" in name:
        return "Champ Message"

    if "form" in name:
        return "Formulaire"

    if "link" in name:
        return "Lien de navigation"

    return variable_name.replace("_", " ").replace("-", " ").title()


def extract_selectors_from_script(selenium_script):
    """
    Extrait les éléments testés et les sélecteurs depuis selenium_script.
    """

    if not selenium_script:
        return {"element_name": None, "selector": None}

    detected_elements = []

    pattern = re.compile(
        r"(\w+)\s*=\s*safe_find_element\s*\(\s*driver\s*,\s*\[(.*?)\]\s*\)",
        re.DOTALL,
    )

    matches = pattern.findall(selenium_script)

    for variable_name, selectors_block in matches:
        selectors = re.findall(
            r'By\.(ID|NAME|CSS_SELECTOR|XPATH|LINK_TEXT|CLASS_NAME)\s*,\s*(?:"([^"]+)"|\'([^\']+)\')',
            selectors_block,
        )

        clean_selectors = []

        for selector_type, value_double, value_single in selectors:
            selector_value = value_double or value_single

            if selector_value:
                clean_selectors.append((selector_type, selector_value))

        if clean_selectors:
            element_label = format_variable_name(variable_name, clean_selectors)

            detected_elements.append(
                {
                    "variable_name": variable_name,
                    "element_label": element_label,
                    "selectors": clean_selectors,
                }
            )

    if not detected_elements:
        return {"element_name": None, "selector": None}

    element_names = []
    selector_lines = []
    seen_selector_lines = set()

    for item in detected_elements:
        element_label = item["element_label"]

        if element_label not in element_names:
            element_names.append(element_label)

        for selector_type, selector_value in item["selectors"]:
            line = f"{element_label} : By.{selector_type} = {selector_value}"

            if line in seen_selector_lines:
                continue

            seen_selector_lines.add(line)
            selector_lines.append(line)

    return {
        "element_name": " / ".join(element_names),
        "selector": "\n".join(selector_lines),
    }
