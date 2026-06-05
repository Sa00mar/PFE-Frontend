from app.services.test_generator import generate_rule_based_tests
from app.services.gemini_generator import generate_tests_with_gemini
from app.services.page_classifier import classify_site_structure

def generate_tests_with_custom_engine(page_type, relevant_data, url):
    """
    Chef d'orchestre de la génération des cas de test.

    Rôle :
    1. Recevoir le type de page + les données DOM + les features détectées.
    2. Envoyer ces données à Gemini.
    3. Si Gemini réussit, retourner les tests IA.
    4. Si Gemini échoue, utiliser le fallback par règles.
    """

    print("\n==================== CUSTOM IA ENGINE ====================")

    features = relevant_data.get("features", [])

    print("Features reçues :")
    for feature in features:
        print("-", feature)
    
    print("\n=== MAIN FEATURE DETECTION ===")
    main_feature = detect_main_feature(page_type, relevant_data, url)
    relevant_data["main_feature"] = main_feature
    print("Main feature :", main_feature)
    
    priority_profile = build_feature_priority_profile(main_feature)
    relevant_data["priority_profile"] = priority_profile
    print("Priority profile :", priority_profile)

    
    
    print("\n=== SITE STRUCTURE ANALYSIS ===")

    pages = relevant_data.get("pages", [])

    if page_type == "multi_page_analysis" and len(pages) > 3:
        relevant_data["analysis_scope"] = "full_site"
        relevant_data["main_feature"] = "site_overview"
        main_feature = "site_overview"
        priority_profile = {
            "page_ui": 40,
            "business_features": 30,
            "internal_navigation": 20,
            "global_navigation": 10
        }
        relevant_data["priority_profile"] = priority_profile

        print("Analysis scope forced :", relevant_data["analysis_scope"])
        print("Main feature forced :", main_feature)
        print("Priority profile forced :", priority_profile)
        
    site_structure = classify_site_structure(
    pages,
    url
    )
    relevant_data["site_structure"] = site_structure
    print("Site structure :", site_structure)

    gemini_result = generate_tests_with_gemini(
        page_type,
        relevant_data,
        url
    )

    if gemini_result["success"] and gemini_result["test_cases"]:
        print(f"[SUCCESS] {len(gemini_result['test_cases'])} tests générés par Gemini")

        return {
            "success": True,
            "source": "gemini_ai",
            "test_cases": gemini_result["test_cases"],
            "error": None
        }

    print("[FALLBACK] Gemini a échoué. Utilisation du générateur par règles.")
    print("[GEMINI ERROR] :", gemini_result.get("error"))
 
    fallback_tests = generate_rule_based_tests(page_type, relevant_data)

    return {
        "success": True,
        "source": "rule_based_fallback",
        "test_cases": fallback_tests,
        "error": gemini_result.get("error")
    }
def build_feature_priority_profile(main_feature):
    """
    Définit le poids métier des catégories de tests.
    """

    if main_feature == "authentication":
        return {
            "primary_feature": 70,
            "navigation": 20,
            "footer": 10
        }

    if main_feature == "contact_form":
        return {
            "primary_feature": 75,
            "navigation": 15,
            "footer": 10
        }

    if main_feature == "registration":
        return {
            "primary_feature": 75,
            "navigation": 15,
            "footer": 10
        }

    return {
        "primary_feature": 60,
        "navigation": 25,
        "footer": 15
    }

def detect_main_feature(page_type, relevant_data, url):
    """
    Détecte la fonctionnalité métier principale à partir :
    - de l'URL
    - du type de page
    - des champs détectés
    - des formulaires détectés
    """

    url_lower = (url or "").lower()
    inputs = relevant_data.get("inputs", [])
    forms = relevant_data.get("forms", [])

    input_text = " ".join([
        f"{item.get('type', '')} {item.get('name', '')} {item.get('id', '')} {item.get('placeholder', '')}"
        for item in inputs
    ]).lower()

    has_password = "password" in input_text
    has_user_identifier = (
        "user" in input_text
        or "email" in input_text
        or "login" in input_text
    )

    has_message_field = (
        "message" in input_text
        or "comment" in input_text
        or "subject" in input_text
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

    if (
        page_type == "form_page"
        and has_message_field
    ) or "contact" in url_lower:
        return "contact_form"

    if "search" in url_lower:
        return "search"

    if (
        "cart" in url_lower
        or "checkout" in url_lower
        or "payment" in url_lower
    ):
        return "ecommerce"

    if forms:
        return "form_submission"

    return "generic"

