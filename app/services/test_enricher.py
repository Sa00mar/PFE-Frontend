import json

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


def enrich_missing_tests(test_cases, semantic_actions):
    """
    Ajoute seulement quelques tests detail_navigation oubliés par Gemini.
    Évite d'ajouter trop de bruit.
    """

    existing_text = json.dumps(test_cases, ensure_ascii=False).lower()

    existing_names = {
        (test.get("name") or "").lower()
        for test in test_cases
    }
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
        "locators"
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

            test_cases.append({
                "name": test_name,
                "type": "detail_navigation",
                "priority": "medium",
                "steps": [
                    f"Naviguer vers la page : {page_url}",
                    f"Cliquer sur le lien ou bouton '{label}'."
                ],
                "expected_result": "L'utilisateur doit être redirigé vers une page de détail ou un contenu associé.",
                "selenium_script": "",
                "cypress_script": ""
            })
            existing_names.add(test_name.lower())

            existing_text += " " + label_lower
            added_count += 1

    return test_cases