import os
import json
import re
from urllib.parse import urlparse

# pyrefly: ignore [missing-import]
from dotenv import load_dotenv

# pyrefly: ignore [missing-import]
from google import genai
from app.services.test_enricher import (
    enrich_missing_tests,
    enrich_security_and_seo_tests,
)

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


def clean_json_response(content):
    """
    Nettoie la réponse Gemini pour garder uniquement le premier tableau JSON valide.
    """

    content = content.strip()

    if content.startswith("```json"):
        content = content.replace("```json", "", 1).strip()

    if content.startswith("```"):
        content = content.replace("```", "", 1).strip()

    if content.endswith("```"):
        content = content[:-3].strip()

    start = content.find("[")
    end = content.rfind("]")

    if start != -1 and end != -1 and end > start:
        content = content[start : end + 1]

    return content


def normalize_test_case(test):
    """
    Normalise les champs pour rester compatible avec la base actuelle.
    """

    return {
        "name": test.get("name") or test.get("title") or "Cas de test généré",
        "type": str(test.get("type", "functional")).lower(),
        "priority": str(test.get("priority", "medium")).lower(),
        "steps": test.get("steps", []),
        "expected_result": test.get("expected_result", ""),
        "selenium_script": test.get("selenium_script", ""),
        "cypress_script": test.get("cypress_script", ""),
    }


def is_positive_login_test(test):
    name = (test.get("name") or "").lower()
    test_type = (test.get("type") or "").lower()
    expected = (test.get("expected_result") or "").lower()

    return ("login" in name or "connexion" in name or "auth" in name) and (
        test_type == "positive"
        or "success" in name
        or "successful" in name
        or "succès" in expected
        or "connecté avec succès" in expected
    )


def enforce_detected_login_credentials(test, test_credentials):
    """
    Corrige uniquement les scripts Selenium/Cypress des tests positifs de login.
    Ne met aucune valeur en dur.
    Utilise seulement les credentials détectés automatiquement.
    """

    if not test or not test_credentials:
        return test

    username = test_credentials.get("username")
    password = test_credentials.get("password")

    if not username or not password:
        return test

    test_text = " ".join(
        [
            str(test.get("name", "")),
            str(test.get("type", "")),
            str(test.get("expected_result", "")),
            " ".join([str(step) for step in test.get("steps", [])]),
        ]
    ).lower()

    is_login_test = (
        "login" in test_text
        or "connexion" in test_text
        or "authentification" in test_text
    )

    is_positive_test = (
        "positive" in test_text
        or "succès" in test_text
        or "success" in test_text
        or "valides" in test_text
    )

    is_negative_test = (
        "invalid" in test_text
        or "incorrect" in test_text
        or "vide" in test_text
        or "empty" in test_text
        or "erreur" in test_text
        or "negative" in test_text
    )

    if not is_login_test or not is_positive_test or is_negative_test:
        return test

    selenium_script = test.get("selenium_script") or ""
    cypress_script = test.get("cypress_script") or ""

    if selenium_script:
        selenium_script = re.sub(
            r'(username_field\.send_keys\()\s*["\'][^"\']*["\']\s*(\))',
            rf'\1"{username}"\2',
            selenium_script,
            flags=re.IGNORECASE,
        )

        selenium_script = re.sub(
            r'(password_field\.send_keys\()\s*["\'][^"\']*["\']\s*(\))',
            rf'\1"{password}"\2',
            selenium_script,
            flags=re.IGNORECASE,
        )

        test["selenium_script"] = selenium_script

    if cypress_script:
        cypress_script = re.sub(
            r'(cy\.get\([\'"]#?username[\'"]\)\.type\()\s*["\'][^"\']*["\']\s*(\))',
            rf'\1"{username}"\2',
            cypress_script,
            flags=re.IGNORECASE,
        )

        cypress_script = re.sub(
            r'(cy\.get\([\'"]#?password[\'"]\)\.type\()\s*["\'][^"\']*["\']\s*(\))',
            rf'\1"{password}"\2',
            cypress_script,
            flags=re.IGNORECASE,
        )

        test["cypress_script"] = cypress_script

    return test


def post_process_generated_tests(test_cases, main_feature, dom_text):
    """
    Nettoie et stabilise les cas de test générés par Gemini.
    """

    unique_tests = []
    seen_keys = set()

    for test in test_cases:
        name = (test.get("name") or "").strip().lower()
        test_type = (test.get("type") or "").strip().lower()
        expected = (test.get("expected_result") or "").strip().lower()

        semantic_key = f"{test_type}|{name}|{expected}"

        if semantic_key in seen_keys:
            continue

        seen_keys.add(semantic_key)

        if main_feature == "authentication" and name.startswith("tc_auth"):
            test["priority"] = "high"

        if "footer" in name or "privacy" in name or "copyright" in name:
            test["priority"] = "low"
        elif "nav" in name:
            test["priority"] = "medium"

        if "toggle" in name or "menu" in name:
            test["type"] = "functional"
            test["priority"] = "low"

        unique_tests.append(test)

    return unique_tests


def ensure_ui_load_test(test_cases, main_feature, url):

    has_ui_test = any(test.get("type", "").lower() == "ui" for test in test_cases)

    if has_ui_test:
        return test_cases

    test_cases.insert(
        0,
        {
            "name": "TC_UI_001_LoadPage",
            "type": "ui",
            "priority": "high",
            "steps": [f"Accéder à l'URL : {url}"],
            "expected_result": "La page se charge correctement et les éléments principaux sont visibles.",
            "selenium_script": "",
            "cypress_script": "",
        },
    )

    print("[AUTO] UI Load Test ajouté automatiquement")

    return test_cases


def ensure_security_tests(test_cases, url, test_types):
    """
    Ajoute des tests sécurité généraux si l'utilisateur a demandé security
    et si Gemini n'a pas généré assez de tests sécurité.
    """

    if "security" not in test_types:
        return test_cases

    security_tests = [
        test for test in test_cases if "security" in str(test.get("type", "")).lower()
    ]

    if len(security_tests) >= 2:
        return test_cases

    existing_names = {str(test.get("name", "")).lower() for test in test_cases}

    if "tc_security_auto_001_verify_https_usage" not in existing_names:
        test_cases.append(
            {
                "name": "TC_SECURITY_AUTO_001_VerifyHTTPSUsage",
                "type": "security",
                "priority": "high",
                "steps": [
                    f"Accéder à l'URL : {url}",
                    "Vérifier que l'URL commence par https://",
                ],
                "expected_result": "La page doit être chargée via HTTPS afin d'assurer une connexion sécurisée.",
                "selenium_script": "",
                "cypress_script": "",
            }
        )

    if (
        "tc_security_auto_002_check_sensitive_information_exposure"
        not in existing_names
    ):
        test_cases.append(
            {
                "name": "TC_SECURITY_AUTO_002_CheckSensitiveInformationExposure",
                "type": "security",
                "priority": "medium",
                "steps": [
                    f"Accéder à l'URL : {url}",
                    "Inspecter les textes visibles de la page.",
                    "Vérifier qu'aucune information sensible n'est affichée publiquement.",
                ],
                "expected_result": "La page ne doit pas afficher d'informations sensibles comme des mots de passe, tokens, clés API ou messages techniques internes.",
                "selenium_script": "",
                "cypress_script": "",
            }
        )

    return test_cases


def get_domain(value):
    """
    Retourne le domaine normalisé d'une URL.
    """
    try:
        parsed = urlparse(value)
        domain = parsed.netloc.lower()

        if domain.startswith("www."):
            domain = domain[4:]

        return domain
    except Exception:
        return ""


def is_external_url(candidate_url, base_url):
    """
    Vérifie si candidate_url pointe vers un domaine externe.
    """
    base_domain = get_domain(base_url)
    candidate_domain = get_domain(candidate_url)

    if not base_domain or not candidate_domain:
        return False

    return candidate_domain != base_domain and not candidate_domain.endswith(
        "." + base_domain
    )


def extract_urls_from_text(text):
    """
    Extrait les URLs présentes dans un texte.
    """
    return re.findall(r"https?://[^\s\)\]\}\'\"]+", text)


def detect_external_like_pages(relevant_data, base_url):
    """
    Détecte les pages qui appartiennent au domaine principal,
    mais dont le contenu pointe majoritairement vers des domaines externes.

    Exemple générique :
    - page de redirection partenaire
    - page de cours externe intégrée
    - page de promotion externe
    - page contenant surtout des liens vers une autre plateforme
    """

    external_like_pages = set()

    for page in relevant_data.get("pages", []):
        page_url = page.get("url", "")
        links = page.get("links", [])

        if not page_url or not isinstance(links, list):
            continue

        total_links = 0
        external_links = 0
        external_domains = set()

        for link in links:
            if not isinstance(link, dict):
                continue

            href = link.get("href") or link.get("url") or ""

            if not href:
                continue

            domain = get_domain(href)

            if not domain:
                continue

            total_links += 1

            if is_external_url(href, base_url):
                external_links += 1
                external_domains.add(domain)

        if total_links == 0:
            continue

        external_ratio = external_links / total_links

        # Règle générique :
        # si beaucoup de liens sortent vers un autre domaine,
        # la page est considérée comme une page externe/partenaire.
        if external_ratio >= 0.50 and len(external_domains) >= 1:
            external_like_pages.add(page_url.lower())

        # Autre cas :
        # si une page contient beaucoup de liens vers le même domaine externe.
        if len(external_domains) == 1 and external_links >= 5:
            external_like_pages.add(page_url.lower())

    return external_like_pages


def filter_external_platform_tests(test_cases, base_url, relevant_data):
    """
    Supprime les tests qui ciblent des pages ou fonctionnalités externes
    au site principal analysé.

    Cette version est générique :
    - aucun nom de site externe n'est écrit en dur
    - aucune URL spécifique n'est écrite en dur
    - le filtrage se base sur les domaines détectés automatiquement
    """

    filtered_tests = []

    external_like_pages = detect_external_like_pages(relevant_data, base_url)

    for test in test_cases:
        test_text = json.dumps(test, ensure_ascii=False).lower()

        urls = extract_urls_from_text(test_text)

        contains_external_url = any(
            is_external_url(candidate_url, base_url) for candidate_url in urls
        )

        targets_external_like_page = any(
            page_url in test_text for page_url in external_like_pages
        )

        if contains_external_url:
            print("[FILTER] Test avec URL externe supprimé :", test.get("name"))
            continue

        if targets_external_like_page:
            print(
                "[FILTER] Test sur page externe/partenaire supprimé :", test.get("name")
            )
            continue

        filtered_tests.append(test)

    return filtered_tests


def generate_tests_with_gemini(
    page_type,
    relevant_data,
    url,
    analysis_scope="single_page",
    target_feature="",
    test_types=None,
):
    """
    Génère des cas de test avec Gemini à partir :
    - du type de page,
    - des données DOM multi-pages,
    - des features détectées,
    - de l'URL analysée.
    """

    features = relevant_data.get("features", [])
    main_feature = relevant_data.get("main_feature", "generic")
    priority_profile = relevant_data.get("priority_profile", {})
    site_structure = relevant_data.get("site_structure", {})
    semantic_actions = relevant_data.get("semantic_actions", [])

    test_credentials = relevant_data.get("test_credentials", {})

    if test_types is None:
        test_types = relevant_data.get("test_types", ["functional", "ui"])

    if not analysis_scope:
        analysis_scope = relevant_data.get("analysis_scope", "single_page")

    if not target_feature:
        target_feature = relevant_data.get("target_feature", "")

    if analysis_scope not in ["single_page", "full_site", "specific_feature"]:
        analysis_scope = "single_page"

    if analysis_scope != "specific_feature":
        target_feature = ""

    relevant_data["analysis_scope"] = analysis_scope
    relevant_data["target_feature"] = target_feature
    relevant_data["test_types"] = test_types

    prompt = f"""
Tu es un expert QA Automation senior spécialisé en tests web, Selenium et Cypress.

Ta mission :
Générer des cas de test web professionnels, pertinents et exécutables à partir d'une analyse DOM multi-pages.

Tu dois respecter strictement :
- le scope d'analyse choisi
- les types de tests demandés
- les éléments réellement détectés dans le DOM
- les données de test visibles dans la page
- le domaine principal analysé

==================================================
CONTEXTE D'ANALYSE
==================================================

URL PRINCIPALE ANALYSÉE :
{url}

TYPE DE PAGE :
{page_type}

SCOPE D'ANALYSE :
{analysis_scope}

FONCTIONNALITÉ CIBLE DEMANDÉE :
{target_feature if target_feature else "Aucune fonctionnalité précise demandée"}

TYPES DE TESTS DEMANDÉS :
{json.dumps(test_types, ensure_ascii=False, indent=2)}

FONCTIONNALITÉ MÉTIER PRINCIPALE :
{main_feature}

FONCTIONNALITÉS MÉTIER DÉTECTÉES :
{json.dumps(features, ensure_ascii=False, indent=2)}

PAGES ANALYSÉES :
{json.dumps(relevant_data.get("pages", []), ensure_ascii=False, indent=2)}

ÉLÉMENTS DOM DÉTECTÉS :
{json.dumps(relevant_data, ensure_ascii=False, indent=2)}

IDENTIFIANTS DE TEST DÉTECTÉS :
{json.dumps(test_credentials, ensure_ascii=False, indent=2)}

PROFIL DE PRIORITÉ MÉTIER :
{json.dumps(priority_profile, ensure_ascii=False, indent=2)}

STRUCTURE DU SITE ANALYSÉ :
{json.dumps(site_structure, ensure_ascii=False, indent=2)}

ACTIONS FONCTIONNELLES DÉTECTÉES :
{json.dumps(semantic_actions, ensure_ascii=False, indent=2)}

==================================================
RÈGLES GÉNÉRALES OBLIGATOIRES
==================================================

- Utilise uniquement les fonctionnalités réellement détectées.
- Utilise uniquement les ids, names, classes, hrefs, textes visibles et attributs présents dans les données fournies.
- Ne crée jamais une fonctionnalité absente du DOM.
- Ne crée jamais un bouton, champ, message, lien ou workflow qui n'existe pas dans les données analysées.
- Ne génère pas deux cas de test qui vérifient exactement le même comportement avec les mêmes données.
- Chaque cas de test doit avoir un objectif clair et distinct.
- Les étapes doivent être simples, claires et exécutables.
- Les résultats attendus doivent être basés sur un comportement observable :
  - redirection
  - changement d'URL
  - élément visible
  - élément masqué
  - bouton activé ou désactivé
  - validation HTML5
  - message exact si détecté
- Si un message exact est présent dans le DOM, utilise-le exactement sans le reformuler.
- Si aucun message exact n'est détecté, n'invente pas un texte précis. Utilise un résultat attendu générique basé sur le comportement observable.

==================================================
RÈGLES DE SCOPE
==================================================

CAS 1 : SCOPE = single_page

- Génère entre 8 et 15 cas de test maximum.
- Centre les tests sur l'URL PRINCIPALE ANALYSÉE.
- Les pages secondaires servent seulement comme contexte.
- Ne teste pas les fonctionnalités internes des pages secondaires.
- Priorité :
  1. fonctionnalité métier principale
  2. scénario positif principal
  3. scénarios négatifs importants
  4. validations de champs
  5. navigation visible depuis la page principale

Navigation secondaire autorisée :
- liens principaux du header/navbar visibles sur la page principale
- logo cliquable si détecté
- liens footer importants visibles, comme Privacy Policy ou lien copyright
- ces tests doivent être générés une seule fois
- priorité medium pour header/logo
- priorité low pour footer

CAS 2 : SCOPE = specific_feature

- Génère uniquement des tests liés à la fonctionnalité cible :
{target_feature if target_feature else "Aucune"}
- Ignore les fonctionnalités non liées.
- Ne génère pas de tests globaux du site.
- Ne génère pas de tests de navigation sauf si nécessaire pour atteindre la fonctionnalité.
- Génère entre 6 et 12 cas de test.
- Priorité :
  1. scénario positif de la fonctionnalité ciblée
  2. scénarios négatifs
  3. validations de champs
  4. comportements limites

CAS 3 : SCOPE = full_site

- Génère entre 25 et 80 cas de test selon la richesse du site.
- Couvre les pages principales détectées.
- Pour chaque page importante :
  1. générer un test UI de chargement
  2. générer les tests métier liés aux éléments principaux
  3. générer les tests de formulaire si un vrai formulaire existe
  4. générer les tests positifs et négatifs utiles
  5. générer les tests de boutons importants
- La navigation globale header/footer doit être testée une seule fois pour tout le site.
- Ne répète pas le même lien global depuis chaque page.

==================================================
RÈGLES SELON LA FONCTIONNALITÉ MÉTIER PRINCIPALE
==================================================

Si main_feature = authentication :

- Le premier cas doit être un test UI de chargement de la page login.
- Génère principalement des tests d'authentification.
- Inclure si les éléments existent :
  1. chargement de la page login
  2. connexion avec identifiants valides
  3. connexion avec username/email invalide
  4. connexion avec password invalide
  5. connexion avec username/email vide
  6. connexion avec password vide
  7. connexion avec champs vides
  8. vérification de redirection ou succès observable
  9. vérification du bouton/lien logout si détecté

Si main_feature = contact_form :

- Génère principalement des tests de formulaire de contact.
- Inclure si les champs existent :
  1. chargement de la page contact
  2. soumission valide
  3. email invalide
  4. champ obligatoire vide
  5. message vide
  6. validation des erreurs visibles

Si main_feature = registration :

- Génère principalement des tests d'inscription.
- Inclure si les champs existent :
  1. inscription valide
  2. email invalide
  3. mot de passe faible
  4. confirmation différente
  5. champs requis vides

Si main_feature = search :

- Génère principalement des tests de recherche.
- Inclure si le champ existe :
  1. recherche valide
  2. recherche vide
  3. recherche sans résultat
  4. recherche avec caractères spéciaux

Si main_feature = ecommerce :

- Génère principalement des tests panier/checkout.
- Inclure seulement les actions détectées :
  1. ajout au panier
  2. modification quantité
  3. suppression produit
  4. checkout
  5. paiement invalide

==================================================
RÈGLES SUR LES ACTIONS FONCTIONNELLES DÉTECTÉES
==================================================

Pour chaque action dans ACTIONS FONCTIONNELLES DÉTECTÉES :

- Si type = form_interaction :
  générer des tests de saisie et validation.

- Si type = submit_action :
  générer des tests de soumission.

- Si type = navigation_action :
  générer des tests de navigation vers les liens internes importants.

- Si type = repeated_detail_navigation :
  générer un test distinct pour chaque lien métier significatif.

- Si type = button_action :
  générer un test distinct pour chaque bouton métier détecté.

- Si type = select_filter_action :
  générer un scénario de filtrage pour les options importantes détectées.

- Si type = choice_filter_action :
  générer un scénario couvrant les radios, checkboxes et reset si détectés.

- Si type = multi_step_interaction ou multi_step_workflow :
  générer un scénario utilisateur multi-étapes uniquement avec les boutons et éléments détectés.

Si sample_labels existe :
- utilise sample_labels pour nommer les tests
- génère plusieurs tests si plusieurs éléments importants existent
- ne fusionne pas plusieurs boutons ou liens métier dans un seul test

==================================================
RÈGLES SUR LES LIENS EXTERNES
==================================================

- Le moteur doit rester centré sur le domaine principal analysé.
- Ne génère pas de tests pour les fonctionnalités internes d'un domaine externe.
- Si un lien visible mène vers un domaine externe, tu peux vérifier uniquement que le lien existe ou redirige, mais tu ne dois pas tester la page externe.
- Ne teste pas les boutons, formulaires, recherche, panier, inscription ou connexion d'un site externe.
- Les liens internes du domaine principal sont autorisés.

==================================================
RÈGLES SELON LES TYPES DE TESTS DEMANDÉS
==================================================

Tu dois respecter strictement TYPES DE TESTS DEMANDÉS.

Si "functional" n'est pas dans test_types :
- ne génère pas de tests fonctionnels métier.

Si "ui" n'est pas dans test_types :
- ne génère pas de tests purement UI.

Si "security" est dans test_types :
- génère au moins 2 tests sécurité.
- Si des champs texte existent, teste XSS simple et injection SQL simple.
- Si un champ password existe, vérifie qu'il est masqué.
- Si aucun champ n'existe, génère des tests sécurité généraux :
  - HTTPS
  - absence d'informations sensibles visibles
  - liens internes non vides
  - absence de redirection inattendue

Si "security" n'est pas dans test_types :
- ne génère aucun test sécurité.

Si "seo" est dans test_types :
- génère au moins 2 tests SEO.
- Vérifie selon les éléments détectés :
  - title
  - URL lisible
  - H1
  - href vide
  - image sans alt

Si "seo" n'est pas dans test_types :
- ne génère aucun test SEO.

==================================================
RÈGLES SUR LES DONNÉES DE TEST
==================================================

- Si des données de test sont visibles dans la page ou dans les données analysées, utilise-les exactement sans les modifier.
- Ne remplace jamais une valeur détectée par une valeur générique.
- Si IDENTIFIANTS DE TEST DÉTECTÉS contient un username/email/login et un password :
  - utilise ces valeurs exactes pour le scénario positif de login
  - utilise ces valeurs exactes dans le script Selenium
  - utilise ces valeurs exactes dans le script Cypress
  - ne les modifie pas
  - ne les reformule pas
  - ne les remplace pas par des valeurs génériques
- Les valeurs génériques sont autorisées seulement si aucune donnée réelle adaptée n'est détectée.
- Pour les tests négatifs, tu peux utiliser des valeurs invalides afin de provoquer une erreur.
- Si aucune donnée réelle n'est détectée, utilise des valeurs génériques adaptées :
  - username : test_user
  - email : test@example.com
  - password : SecureTestValueA9!
  - search : test
  - message : Ceci est un message de test
- Ne crée jamais de données spécifiques à un site particulier.

==================================================
RÈGLES POUR LES SCRIPTS SELENIUM
==================================================

- Les scripts Selenium doivent être en Python.
- Utilise l'URL réelle : {url}
- Utilise prioritairement safe_find_element(driver, selectors).
- Ne crée pas la fonction safe_find_element : elle existe déjà.
- Utilise plusieurs sélecteurs fiables quand ils existent.
- Utilise driver.find_element seulement si un seul sélecteur fiable existe.
- Les sélecteurs autorisés :
  - By.ID
  - By.NAME
  - By.CLASS_NAME
  - By.CSS_SELECTOR
  - By.LINK_TEXT
  - By.XPATH
- N'utilise jamais :
  - find_element_by_id
  - find_element_by_class_name
  - find_element_by_link_text
- Mets des assertions simples quand c'est possible.
- Ne mets pas driver.quit().
- Ne crée pas de configuration webdriver.
- Ne crée pas d'import inutile si l'environnement l'a déjà.

Exemple de style attendu :

element = safe_find_element(driver, [
    (By.ID, "id_detecte"),
    (By.NAME, "name_detecte"),
    (By.CSS_SELECTOR, "selecteur_detecte")
])
element.send_keys("valeur_adaptee")

button = safe_find_element(driver, [
    (By.ID, "id_bouton_detecte"),
    (By.CSS_SELECTOR, "selecteur_bouton_detecte")
])
button.click()

RÈGLES SPÉCIALES POUR LES TESTS XSS :
- Pour les tests de sécurité XSS sur un formulaire, ne pas exiger obligatoirement un message de succès après soumission.
- Vérifier uniquement qu'aucune alerte JavaScript ne s'exécute.
- Si un captcha/reCAPTCHA bloque la soumission, le test doit être considéré comme pending et non fail.
- Ne jamais générer un bloc try/except vide.
- Dans un bloc except, toujours mettre au minimum pass.
- Ne pas ajouter une assertion obligatoire du type "Thank you" pour valider un test XSS.


==================================================
RÈGLES POUR LES SCRIPTS CYPRESS
==================================================

- Les scripts Cypress doivent être en JavaScript.
- Utilise cy.visit avec l'URL réelle.
- Utilise les vrais sélecteurs détectés.
- Ne crée pas de sélecteurs inexistants.
- Ajoute des vérifications simples quand c'est possible :
  - should('be.visible')
  - should('include')
  - should('contain')
  - should('not.be.empty')

==================================================
FORMAT OBLIGATOIRE DE SORTIE
==================================================

Retourne uniquement un JSON valide.
Aucun texte avant le JSON.
Aucun texte après le JSON.
Pas de ```json.
Pas de commentaire.

Le format exact doit être :

[
  {{
    "name": "TC_EXAMPLE_001_TestName",
    "type": "positive | negative | functional | navigation | validation | ui | security | seo",
    "priority": "high | medium | low",
    "steps": [
      "Étape 1",
      "Étape 2"
    ],
    "expected_result": "Résultat attendu clair et vérifiable",
    "selenium_script": "Script Selenium Python complet ou partiel mais exécutable",
    "cypress_script": "Script Cypress JavaScript complet ou partiel mais exécutable"
  }}
]

Chaque objet doit contenir obligatoirement :
- name
- type
- priority
- steps
- expected_result
- selenium_script
- cypress_script
"""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash", contents=prompt
        )

        content = response.text.strip()
        content = clean_json_response(content)

        test_cases = json.loads(content)

        if not isinstance(test_cases, list):
            raise ValueError("La réponse Gemini n'est pas une liste JSON.")

        normalized_tests = []

        # Convertir relevant_data en texte pour faciliter la recherche
        dom_text = json.dumps(relevant_data).lower()

        for test in test_cases:
            if not isinstance(test, dict):
                continue

            normalized_test = normalize_test_case(test)

            normalized_test = enforce_detected_login_credentials(
                normalized_test, test_credentials
            )

            test_text = json.dumps(normalized_test).lower()

            # ==================================================
            # FILTRE ANTI-FAUX ÉLÉMENTS
            # ==================================================

            forbidden_fake_elements = ["toggle-navigation", "open menu"]

            fake_detected = False

            for fake_element in forbidden_fake_elements:
                # Si Gemini génère un élément absent du DOM
                if fake_element in test_text and fake_element not in dom_text:
                    print(f"[FILTER] Faux élément détecté supprimé : {fake_element}")

                    fake_detected = True
                    break

            if fake_detected:
                continue

            normalized_tests.append(normalized_test)

        normalized_tests = post_process_generated_tests(
            normalized_tests, main_feature, dom_text
        )
        if "ui" in test_types:
            normalized_tests = ensure_ui_load_test(normalized_tests, main_feature, url)

        if analysis_scope in ["single_page", "specific_feature"]:
            semantic_actions = [
                action for action in semantic_actions if action.get("page_url") == url
            ]

        normalized_tests = enrich_missing_tests(normalized_tests, semantic_actions)

        normalized_tests = filter_external_platform_tests(
            normalized_tests, url, relevant_data
        )

        normalized_tests = enrich_security_and_seo_tests(
            normalized_tests, relevant_data, url, test_types
        )

        return {
            "success": True,
            "source": "gemini_ai",
            "test_cases": normalized_tests,
            "error": None,
        }

    except Exception as e:
        return {
            "success": False,
            "source": "gemini_ai",
            "test_cases": [],
            "error": str(e),
        }
