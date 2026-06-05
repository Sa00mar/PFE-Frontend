import os
import json
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv
# pyrefly: ignore [missing-import]
from google import genai
from app.services.test_enricher import enrich_missing_tests

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
        content = content[start:end + 1]

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
        "cypress_script": test.get("cypress_script", "")
    }

def post_process_generated_tests(test_cases, main_feature,dom_text):
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

    has_ui_test = any(
        test.get("type", "").lower() == "ui"
        for test in test_cases
    )

    if has_ui_test:
        return test_cases

    test_cases.insert(0, {
        "name": "TC_UI_001_LoadPage",
        "type": "ui",
        "priority": "high",
        "steps": [
            f"Accéder à l'URL : {url}"
        ],
        "expected_result":
            "La page se charge correctement et les éléments principaux sont visibles.",
        "selenium_script": "",
        "cypress_script": ""
    })

    print("[AUTO] UI Load Test ajouté automatiquement")

    return test_cases


def generate_tests_with_gemini(page_type, relevant_data, url):
    """
    Génère des cas de test avec Gemini à partir :
    - du type de page,
    - des données DOM multi-pages,
    - des features détectées,
    - de l'URL analysée.
    """

    features = relevant_data.get("features", [])
    pages = relevant_data.get("pages", [])
    analysis_scope = relevant_data.get("analysis_scope")
    main_feature = relevant_data.get("main_feature", "generic")
    priority_profile = relevant_data.get("priority_profile", {})
    site_structure = relevant_data.get("site_structure", {})
    semantic_actions = relevant_data.get("semantic_actions", [])

    if not analysis_scope:
       if main_feature == "multi_page_analysis" and len(pages) > 3:
          analysis_scope = "full_site"
       elif page_type != "generic":
          analysis_scope = "single_interface"
       else:
          analysis_scope="single_interface"

    prompt = f"""
Tu es un expert QA Automation senior spécialisé en tests web, Selenium et Cypress.

Ta mission :
Générer des cas de test web professionnels à partir d'une analyse DOM multi-pages.

==================================================
URL PRINCIPALE ANALYSÉE
==================================================
{url}

==================================================
TYPE D'ANALYSE
==================================================
{page_type}

==================================================
SCOPE D'ANALYSE
==================================================
{analysis_scope}

==================================================
FONCTIONNALITÉ MÉTIER PRINCIPALE
==================================================
{main_feature}

==================================================
FONCTIONNALITÉS MÉTIER DÉTECTÉES
==================================================
{json.dumps(features, ensure_ascii=False, indent=2)}

==================================================
PAGES ANALYSÉES
==================================================
{json.dumps(relevant_data.get("pages", []), ensure_ascii=False, indent=2)}

==================================================
ÉLÉMENTS DOM DÉTECTÉS
==================================================
{json.dumps(relevant_data, ensure_ascii=False, indent=2)}

==================================================
PROFIL DE PRIORITÉ MÉTIER
==================================================
{priority_profile}
==================================================
STRUCTURE DU SITE ANALYSÉ
==================================================
{json.dumps(site_structure, ensure_ascii=False, indent=2)}
==================================================
ACTIONS FONCTIONNELLES DÉTECTÉES
==================================================
{json.dumps(semantic_actions, ensure_ascii=False, indent=2)}

OBJECTIF DE COUVERTURE
==================================================

OBJECTIF DE COUVERTURE
==================================================
RÈGLES DE COUVERTURE OBLIGATOIRES
==================================================

Pour chaque page fonctionnelle analysée :

- Générer au moins un test UI de chargement de page.
- Vérifier au minimum :
  - le chargement correct de l'URL
  - le titre de la page si détecté
  - la présence des éléments principaux détectés
  - l'absence d'erreur visible de chargement

Tu dois adapter la génération selon le SCOPE D'ANALYSE.

CAS 1 : SCOPE = single_interface
- Génère entre 8 et 20 cas de test.
- Centre la génération sur l'URL PRINCIPALE ANALYSÉE.
- Les pages secondaires servent seulement comme contexte.
- Ne génère pas un test UI pour chaque page secondaire.
- Ne génère pas des tests de formulaires présents sur des pages secondaires.
Inclure aussi quelques tests secondaires de navigation globale visibles sur la page principale :
- liens principaux de la navbar/header
- logo si présent
- liens footer importants comme Privacy Policy

Ces tests doivent être générés une seule fois, avec priorité medium ou low.
Ils peuvent représenter jusqu'à 40% du total si la page contient plusieurs liens de navigation visibles.

- Priorité :
  1. fonctionnalité métier principale de l'URL
  2. scénarios positifs
  3. scénarios négatifs
  4. validations de champs
  5. navigation métier directe 

RÈGLES SELON LA FONCTIONNALITÉ MÉTIER PRINCIPALE :

Si main_feature = authentication :
-Le premier cas de test doit être un test UI de chargement de la page de connexion.
- Génère principalement des tests d'authentification.
- Inclure au minimum :
  1. chargement de la page login
  2. login avec identifiants valides
  3. login avec username/email invalide
  4. login avec password invalide
  5. login avec username/email vide
  6. login avec password vide
  7. login avec champs vides
  8. vérification de la redirection ou du message de succès
  9. vérification du bouton logout si détecté

Après les tests d'authentification, ajoute les tests secondaires visibles sur la page principale :
- générer un test pour chaque lien principal de la navbar/header visible sur la page principale
- générer un test pour le logo s'il est cliquable
- générer un test pour chaque lien footer visible, y compris le nom du site/copyright et Privacy Policy
- ces tests doivent être générés une seule fois
- ces tests doivent avoir une priorité medium pour header/logo et low pour footer
- ne génère pas les fonctionnalités internes des pages secondaires

Ces tests doivent rester secondaires et ne doivent pas dominer les tests d'authentification.
Ne génère pas de tests de formulaires ou fonctionnalités internes des pages secondaires.

Si main_feature = contact_form :
- Génère principalement des tests de formulaire de contact.
- Inclure : soumission valide, email invalide, champs obligatoires vides, message vide.

Si main_feature = registration :
- Génère principalement des tests d'inscription.
- Inclure : inscription valide, email invalide, mot de passe faible, confirmation mot de passe différente, champs requis vides.

Si main_feature = search :
- Génère principalement des tests de recherche.
- Inclure : recherche valide, recherche vide, recherche sans résultat, recherche avec caractères spéciaux.

Si main_feature = ecommerce :
- Génère principalement des tests panier/checkout.
- Inclure : ajouter au panier, modifier quantité, supprimer produit, checkout, paiement invalide.

Pour le footer :

- Génère un test séparé pour chaque lien footer visible.
- Même si un lien footer pointe vers la même URL qu'un lien header ou logo, il doit être testé séparément car l'élément source est différent.
- Inclure notamment :
  1. le lien du nom du site/copyright s'il est cliquable
  2. Privacy Policy s'il est visible
- Les tests footer doivent avoir une priorité low.

CAS 2 : SCOPE = full_site
IMPORTANT :
Si SCOPE = full_site, ne concentre pas la génération uniquement sur main_feature.
main_feature sert seulement de contexte.
La génération doit couvrir les pages principales listées dans STRUCTURE DU SITE ANALYSÉ.
- Génère entre 25 et 80 cas de test selon la richesse du site.
- Analyse toutes les pages présentes dans relevant_data["pages"].
- Regroupe les cas de test par page ou par fonctionnalité métier.

Pour chaque page importante :
1. Générer un test UI de chargement.
2. Générer les tests métier liés aux éléments principaux de cette page.
3. Générer les tests de formulaire si un formulaire réel est détecté.
4. Générer les tests positifs et négatifs utiles uniquement si les champs nécessaires existent.
5. Générer les tests de boutons d'action importants.

Navigation globale :
- Générer les tests de header/navbar une seule fois pour tout le site.
- Générer les tests de footer une seule fois pour tout le site.
- Ne pas répéter Home, Contact, Blog, Courses, Privacy Policy depuis chaque page.
- Si le même lien apparaît dans plusieurs pages, le considérer comme navigation globale.

Navigation métier :
- Générer les tests pour les liens spécifiques à une page.
- Exemple : lien vers détail produit, article, exercice, checkout, dashboard, etc.
Actions fonctionnelles détectées :

IMPORTANT :

Lorsque navigation_action contient sample_labels :

- Générer un test pour chaque lien métier significatif.
- Utiliser sample_labels comme source principale.
- Ne pas se limiter à un seul lien.

Exemples :
- Read More
- View
- Enroll
- Article
- Course
- Product
- Detail
- Practice
- Login

Chaque lien métier important détecté doit produire son propre cas de test.

--------------------------------------------------

Lorsque button_action contient sample_labels :

- Générer un test distinct pour chaque bouton métier détecté.
- Utiliser les libellés présents dans sample_labels.

Exemples :

Si sample_labels contient :

[
 "Edit",
 "Save",
 "Add",
 "Remove"
]

alors générer :

TC_BUTTON_Edit
TC_BUTTON_Save
TC_BUTTON_Add
TC_BUTTON_Remove

Ne jamais fusionner plusieurs boutons métiers dans un seul test.

- Si type = detail_navigation :
  générer un test distinct pour chaque lien de détail détecté 
  Utiliser ces liens pour tester :
  - ouverture d'un détail
  - article
  - cours
  - produit
  - page d'information
  - contenu approfondi

Si plusieurs liens ont le même libellé mais des href différents, générer un test par href distinct.
Ne pas fusionner automatiquement les liens qui ont le même texte.

Lorsque sample_labels existe :
- Utiliser sample_labels pour nommer les tests.
- Ne pas générer seulement un test générique.
- Générer plusieurs tests si plusieurs labels métier importants sont détectés.

Pour chaque élément présent dans ACTIONS FONCTIONNELLES DÉTECTÉES :

Lorsque button_action contient sample_labels :

- Générer un test distinct pour chaque bouton métier détecté.
- Utiliser les libellés présents dans sample_labels.
- Ne pas fusionner plusieurs boutons dans un seul test.

- Générer au moins un cas de test pertinent.
- Si type = form_interaction :
  générer des tests de saisie et validation.

- Si type = submit_action :
  générer des tests de soumission.

- Si type = select_filter_action :
  utiliser filters[].label et filters[].options.
  Générer un scénario complet par filtre dropdown :
  1. sélectionner chaque option importante
  2. vérifier le changement observable
  3. tester le retour à l’option par défaut si elle existe

- Si type = choice_filter_action :
  ne génère pas seulement un test isolé pour une seule option.
  Génère un scénario complet de filtrage couvrant :
  1. chaque option radio détectée dans radio_options
  2. chaque option checkbox détectée dans checkbox_options
  3. quelques combinaisons pertinentes radio + checkbox sans générer toutes les combinaisons possibles
  4. le bouton reset si détecté

- Si type = navigation_action :
  générer des tests de navigation.

- Si type = repeated_detail_navigation :
  générer des tests d'ouverture de détails.


- Si type = button_action :
  générer des tests de clic sur les boutons.

- Si type = multi_step_interaction :
  générer un scénario utilisateur multi-étapes.
  Le scénario doit :
  1. cliquer sur le bouton ou l'action déclencheuse
  2. vérifier si de nouveaux éléments apparaissent
  3. vérifier les changements visibles dans l'interface
  4. tester les nouvelles actions disponibles si elles sont détectées
  5. vérifier que le workflow complet fonctionne correctement

- Si type = multi_step_workflow :
  générer un scénario multi-étapes basé uniquement sur les boutons détectés dans trigger_buttons.
  Cliquer sur l'action déclencheuse détectée.
  Vérifier si l'interface change : nouvel élément visible, champ activé/désactivé, bouton affiché/masqué, ligne ajoutée/supprimée ou contenu modifié.
  Si de nouveaux boutons/actions deviennent visibles après l'interaction, générer des étapes pour les tester.
  Ne jamais inventer une action non détectée explicitement.

Liens externes :
- Générer uniquement les liens externes importants pour le métier.
- Ignorer les liens externes publicitaires, sociaux ou partenaires sauf s'ils sont des CTA principaux.

Répartition recommandée :
- 40% tests UI et chargement des pages importantes
- 30% tests métier/formulaires
- 20% navigation interne métier
- 10% header/footer/liens globaux



==================================================
RÈGLES IMPORTANTES
==================================================

- Utilise uniquement les fonctionnalités réellement détectées.
- Utilise les vrais ids, names, classes, hrefs et textes visibles présents dans le DOM.
- Ne crée pas de fonctionnalités qui n'existent pas.
- Les résultats attendus doivent être dérivés uniquement des informations détectées dans le DOM, le HTML, les attributs, les textes visibles, les URLs, ou les données d'analyse fournies.
- Si un message exact est présent dans le DOM ou dans les données analysées, utilise exactement ce message sans le reformuler.
- Si aucun message exact n'est détecté, formule un expected_result générique basé sur le comportement observable : redirection, changement d'URL, élément visible, élément masqué, bouton activé/désactivé, validation HTML5.
- Ne crée jamais un message d'erreur textuel spécifique qui n'existe pas dans les données analysées.
- Ne suppose jamais un texte exact si ce texte n'est pas présent dans le DOM ou dans relevant_data.

- Évite les doublons sémantiques.
- Ne génère pas deux cas de test qui vérifient exactement le même comportement avec les mêmes données.
- Chaque cas de test doit avoir un objectif métier distinct.
- Évite les doublons.
Pour les scénarios négatifs :
- Si le message exact associé à ce scénario n'est pas clairement détecté, ne réutilise pas le message d'un autre scénario.
- Utilise un résultat observable générique : l'utilisateur reste sur la même page, aucune session n'est créée, ou un message d'erreur est affiché.
- Les étapes doivent être claires et exécutables.
- Les scripts Selenium doivent être en Python.
- Les scripts Cypress doivent être en JavaScript.
- Les scripts doivent être simples, lisibles et directement exploitables.
- Pour les scripts Selenium, utilise prioritairement safe_find_element(driver, selectors).
- Ne pas créer la fonction safe_find_element : elle existe déjà dans l'environnement d'exécution.
- Évite driver.find_element(...) quand plusieurs sélecteurs sont possibles.
- Utilise driver.find_element(...) seulement si un seul sélecteur fiable existe.
- Les scripts Selenium peuvent utiliser :
  By.ID
  By.NAME
  By.CLASS_NAME
  By.CSS_SELECTOR
  By.LINK_TEXT
- Exemple obligatoire :
from selenium.webdriver.common.by import By

element = safe_find_element(driver, [
    (By.ID, "username"),
    (By.NAME, "username"),
    (By.CSS_SELECTOR, "input[name='username']")
])
element.send_keys("student")

button = safe_find_element(driver, [
    (By.ID, "submit"),
    (By.NAME, "submit"),
    (By.CSS_SELECTOR, "button[type='submit']"),
    (By.CSS_SELECTOR, "input[type='submit']")
])
button.click()

- N'utilise jamais :
  find_element_by_id
  find_element_by_class_name
  find_element_by_link_text
- Mets des assertions simples dans les scripts quand c'est possible.
- Utilise l'URL réelle : {url}

==================================================
FORMAT OBLIGATOIRE
==================================================

Retourne uniquement un JSON valide.
Aucun texte avant.
Aucun texte après.
Pas de ```json.

Le format exact doit être :

[
  {{
    "name": "TC_AUTH_001_RegisterUserSuccessfully",
    "type": "positive | negative | functional | navigation | validation | ui",
    "priority": "high | medium | low",
    "steps": [
      "Étape 1",
      "Étape 2"
    ],
    "expected_result": "Résultat attendu clair",
    "selenium_script": "Script Selenium Python complet ou partiel mais exécutable",
    "cypress_script": "Script Cypress JavaScript complet ou partiel mais exécutable"
  }}
]

IMPORTANT :
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
            model="gemini-2.5-flash",
            contents=prompt
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

           test_text = json.dumps(normalized_test).lower()

    # ==================================================
    # FILTRE ANTI-FAUX ÉLÉMENTS
    # ==================================================

           forbidden_fake_elements = [
               "toggle-navigation",
              "open menu"
           ]

           fake_detected = False

           for fake_element in forbidden_fake_elements:

        # Si Gemini génère un élément absent du DOM
               if fake_element in test_text and fake_element not in dom_text:

                    print(
                        f"[FILTER] Faux élément détecté supprimé : {fake_element}"
                    )

                    fake_detected = True
                    break

           if fake_detected:
              continue

           normalized_tests.append(normalized_test)

        normalized_tests = post_process_generated_tests(
          normalized_tests,
          main_feature,
          dom_text
        )
        normalized_tests = ensure_ui_load_test(
          normalized_tests,
          main_feature,
          url
        )

        normalized_tests = enrich_missing_tests(
          normalized_tests,
          semantic_actions
        )

        return {
            "success": True,
            "source": "gemini_ai",
            "test_cases": normalized_tests,
            "error": None
        }

    except Exception as e:
        return {
            "success": False,
            "source": "gemini_ai",
            "test_cases": [],
            "error": str(e)
        }