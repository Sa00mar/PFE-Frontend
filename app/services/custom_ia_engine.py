from app.services.test_generator import generate_rule_based_tests
from app.services.gemini_generator import generate_tests_with_gemini
from app.services.page_classifier import classify_site_structure
from app.services.test_enricher import enrich_security_and_seo_tests
from app.services.page_filtre import extract_test_credentials_from_relevant_data
from app.services.gemini_generator import enforce_detected_login_credentials


def generate_tests_with_custom_engine(
    page_type,
    relevant_data,
    url,
    analysis_scope="single_page",
    target_feature="",
    test_types=None,
):
    """
    Chef d'orchestre de la génération des cas de test.

    Rôle :
    1. Recevoir le type de page + les données DOM + les features détectées.
    2. Respecter le scope choisi par l'utilisateur.
    3. Respecter les types de tests demandés.
    4. Détecter la fonctionnalité métier principale.
    5. Envoyer le contexte enrichi à Gemini.
    6. Si Gemini échoue, utiliser le fallback par règles.
    """

    print("\n==================== CUSTOM IA ENGINE ====================")

    if relevant_data is None:
        relevant_data = {}

    if test_types is None:
        test_types = ["functional", "ui"]

    # Sécurisation du scope
    if analysis_scope not in ["single_page", "full_site", "specific_feature"]:
        analysis_scope = "single_page"

    if analysis_scope != "specific_feature":
        target_feature = ""

    relevant_data["analysis_scope"] = analysis_scope
    relevant_data["target_feature"] = target_feature
    relevant_data["test_types"] = test_types

    relevant_data["url"] = url
    relevant_data["analysis_url"] = url

    test_credentials = extract_test_credentials_from_relevant_data(relevant_data)

    if test_credentials:
        relevant_data["test_credentials"] = test_credentials
        print("Credentials de test détectés :", test_credentials)
    else:
        print("Aucun credential de test détecté.")

    print("Scope reçu :", analysis_scope)
    print("Fonctionnalité cible :", target_feature if target_feature else "Aucune")
    print("Types de tests demandés :", test_types)

    features = relevant_data.get("features", [])

    print("\nFeatures reçues :")
    for feature in features:
        print("-", feature)

    print("\n=== MAIN FEATURE DETECTION ===")

    main_feature = detect_main_feature(
        page_type=page_type,
        relevant_data=relevant_data,
        url=url,
        analysis_scope=analysis_scope,
        target_feature=target_feature,
    )

    relevant_data["main_feature"] = main_feature

    print("Main feature :", main_feature)

    priority_profile = build_feature_priority_profile(
        main_feature=main_feature, analysis_scope=analysis_scope, test_types=test_types
    )

    relevant_data["priority_profile"] = priority_profile

    print("Priority profile :", priority_profile)

    print("\n=== SITE STRUCTURE ANALYSIS ===")

    pages = relevant_data.get("pages", [])

    site_structure = classify_site_structure(pages, url)

    relevant_data["site_structure"] = site_structure

    print("Site structure :", site_structure)

    # Important :
    # On ne force plus full_site automatiquement.
    # On respecte toujours le choix utilisateur.
    if analysis_scope == "single_page":
        print("[SCOPE] Analyse limitée à la page actuelle.")

    elif analysis_scope == "full_site":
        print("[SCOPE] Analyse complète du site.")

    elif analysis_scope == "specific_feature":
        print("[SCOPE] Analyse centrée sur la fonctionnalité :", target_feature)

    print("\n=== SEMANTIC ACTIONS DETECTED ===")
    for action in relevant_data.get("semantic_actions", []):
        print(action)

    gemini_result = generate_tests_with_gemini(
        page_type=page_type,
        relevant_data=relevant_data,
        url=url,
        analysis_scope=analysis_scope,
        target_feature=target_feature,
        test_types=test_types,
    )

    if gemini_result["success"] and gemini_result["test_cases"]:
        print(f"[SUCCESS] {len(gemini_result['test_cases'])} tests générés par Gemini")

        return {
            "success": True,
            "source": "gemini_ai",
            "test_cases": gemini_result["test_cases"],
            "error": None,
        }

    print("[FALLBACK] Gemini a échoué. Utilisation du générateur par règles.")
    print("[GEMINI ERROR] :", gemini_result.get("error"))

    fallback_tests = generate_rule_based_tests(page_type, relevant_data)

    if test_credentials:
        fallback_tests = [
            enforce_detected_login_credentials(test, test_credentials)
            for test in fallback_tests
        ]

    if "ui" in test_types:
        has_ui_test = any(
            "ui" in str(test.get("type", "")).lower() for test in fallback_tests
        )
        if not has_ui_test:
            fallback_tests.insert(
                0,
                {
                    "name": "TC_UI_AUTO_001_LoadPage",
                    "type": "ui",
                    "priority": "high",
                    "steps": [
                        f"Accéder à l'URL : {url}",
                        "Vérifier que la page se charge correctement.",
                        "Vérifier que les éléments principaux sont visibles.",
                    ],
                    "expected_result": "La page doit se charger correctement sans erreur visible.",
                    "selenium_script": f'driver.get("{url}")\nassert driver.title.strip() != ""',
                    "cypress_script": f'cy.visit("{url}")\ncy.title().should("not.be.empty")',
                },
            )
    fallback_tests = enrich_security_and_seo_tests(
        fallback_tests, relevant_data, url, test_types
    )
    return {
        "success": True,
        "source": "rule_based_fallback",
        "test_cases": fallback_tests,
        "error": gemini_result.get("error"),
    }


def build_feature_priority_profile(
    main_feature, analysis_scope="single_page", test_types=None
):
    """
    Définit le poids métier des catégories de tests selon :
    - la fonctionnalité principale
    - le scope choisi
    - les types de tests demandés
    """

    if test_types is None:
        test_types = ["functional", "ui"]

    profile = {}

    # Priorité selon le scope
    if analysis_scope == "single_page":
        profile["primary_feature"] = 70
        profile["page_ui"] = 20
        profile["navigation"] = 10

    elif analysis_scope == "full_site":
        profile["business_features"] = 45
        profile["internal_navigation"] = 25
        profile["page_ui"] = 20
        profile["global_navigation"] = 10

    elif analysis_scope == "specific_feature":
        profile["target_feature"] = 85
        profile["related_validations"] = 10
        profile["ui"] = 5

    # Priorité selon les types de tests
    if "security" in test_types:
        profile["security"] = 20

    if "seo" in test_types:
        profile["seo"] = 15

    # Ajustement selon la fonctionnalité métier
    if main_feature == "authentication":
        profile["authentication"] = 80

    elif main_feature == "contact_form":
        profile["contact_form"] = 75

    elif main_feature == "registration":
        profile["registration"] = 75

    elif main_feature == "search":
        profile["search"] = 70

    elif main_feature == "ecommerce":
        profile["ecommerce"] = 75

    return profile


def detect_main_feature(
    page_type, relevant_data, url, analysis_scope="single_page", target_feature=""
):
    """
    Détecte la fonctionnalité métier principale à partir :
    - du scope choisi
    - de la fonctionnalité cible
    - de l'URL
    - du type de page
    - des champs détectés
    - des formulaires détectés
    """

    # Si l'utilisateur choisit une fonctionnalité précise,
    # elle devient la fonctionnalité principale.
    if analysis_scope == "specific_feature" and target_feature:
        return target_feature.lower().strip().replace(" ", "_")

    url_lower = (url or "").lower()
    inputs = relevant_data.get("inputs", [])
    forms = relevant_data.get("forms", [])

    input_text = " ".join(
        [
            f"{item.get('type', '')} {item.get('name', '')} {item.get('id', '')} {item.get('placeholder', '')}"
            for item in inputs
        ]
    ).lower()

    has_password = "password" in input_text

    has_user_identifier = (
        "user" in input_text or "email" in input_text or "login" in input_text
    )

    has_message_field = (
        "message" in input_text or "comment" in input_text or "subject" in input_text
    )

    if (
        page_type == "login_page"
        or "login" in url_lower
        or "signin" in url_lower
        or (has_password and has_user_identifier)
    ):
        return "authentication"

    if (
        "register" in url_lower
        or "signup" in url_lower
        or "create-account" in url_lower
    ):
        return "registration"

    if (page_type == "form_page" and has_message_field) or "contact" in url_lower:
        return "contact_form"

    if "search" in url_lower:
        return "search"

    if "cart" in url_lower or "checkout" in url_lower or "payment" in url_lower:
        return "ecommerce"

    if forms:
        return "form_submission"

    if analysis_scope == "full_site":
        return "site_overview"

    return "generic"
