import os
import re
import time
from datetime import datetime

# pyrefly: ignore [missing-import]
from selenium import webdriver

# pyrefly: ignore [missing-import]
from selenium.webdriver.chrome.options import Options

# pyrefly: ignore [missing-import]
from selenium.webdriver.common.by import By

# pyrefly: ignore [missing-import]
from selenium.webdriver.common.keys import Keys

# pyrefly: ignore [missing-import]
from selenium.webdriver.support.ui import WebDriverWait

# pyrefly: ignore [missing-import]
from selenium.webdriver.support import expected_conditions as EC

# pyrefly: ignore [missing-import]
from selenium.common.exceptions import TimeoutException, NoAlertPresentException


def safe_find_element(driver, selectors, timeout=10):
    """
    Essaie plusieurs sélecteurs intelligemment.
    selectors = [
        (By.ID, "email"),
        (By.NAME, "email"),
        (By.CSS_SELECTOR, "input[type='email']")
    ]
    """

    for by, value in selectors:
        try:
            element = WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )

            return element

        except Exception:
            continue

    raise TimeoutException(f"Aucun élément trouvé avec les sélecteurs : {selectors}")


def remove_honeypot_interactions(script):
    """
    Supprime les interactions avec les champs cachés anti-spam / honeypot.
    Exemple : wpforms[hp], field-hp, honeypot.
    """

    lines = script.splitlines()
    cleaned = []
    honeypot_vars = set()

    for line in lines:
        lower = line.lower()

        # Détecter une variable qui pointe vers un champ honeypot
        match = re.match(r"\s*(\w+)\s*=\s*safe_find_element\(.*", line)

        if match and (
            "wpforms[hp]" in lower
            or "field-hp" in lower
            or "honeypot" in lower
            or "[hp]" in lower
        ):
            honeypot_vars.add(match.group(1))
            continue

        # Supprimer les actions sur ce champ
        should_skip = False

        for var in honeypot_vars:
            if re.match(rf"\s*{var}\.(clear|send_keys|click)\(", line):
                should_skip = True
                break

        if should_skip:
            continue

        cleaned.append(line)

    return "\n".join(cleaned)


def fix_empty_except_blocks(script):
    """
    Évite les erreurs Python quand le nettoyage supprime les assertions
    et laisse un bloc except vide.
    Exemple corrigé :
        except NoAlertPresentException:
            pass
    """

    lines = script.splitlines()
    fixed_lines = []

    for i, line in enumerate(lines):
        fixed_lines.append(line)

        stripped = line.strip()

        if stripped.startswith("except ") and stripped.endswith(":"):
            next_line = lines[i + 1] if i + 1 < len(lines) else ""

            if not next_line.strip() or next_line.lstrip().startswith("#"):
                indent = line[: len(line) - len(line.lstrip())] + "    "
                fixed_lines.append(indent + "pass")

    return "\n".join(fixed_lines)


def clean_selenium_script(script, url):
    """
    Nettoie le script généré par Gemini avant exécution.
    """

    lines = script.splitlines()
    cleaned_lines = []
    skip_assert_block = False
    bracket_balance = 0

    for line in lines:
        stripped = line.strip()

        # Supprimer les assert simples ou multi-lignes
        if stripped.startswith("assert ") or stripped.startswith("# assert"):
            skip_assert_block = True
            bracket_balance = (
                stripped.count("[")
                + stripped.count("(")
                - stripped.count("]")
                - stripped.count(")")
            )

            if bracket_balance <= 0:
                skip_assert_block = False

            continue

        if skip_assert_block:
            bracket_balance += stripped.count("[") + stripped.count("(")
            bracket_balance -= stripped.count("]") + stripped.count(")")

            if bracket_balance <= 0:
                skip_assert_block = False

            continue

        if "webdriver.Chrome" in stripped:
            continue

        if "Service(" in stripped:
            continue

        if "driver.quit()" in stripped:
            continue

        if stripped.startswith("from selenium") or stripped.startswith(
            "import selenium"
        ):
            continue

        line = line.replace("http://your-app-url/login", url)
        line = line.replace("http://localhost/login", url)
        line = line.replace("YOUR_LOGIN_PAGE_URL", url)

        cleaned_lines.append(line)

        if "driver.get(" in stripped:
            cleaned_lines.append("time.sleep(2)")

        if ".send_keys(" in stripped:
            cleaned_lines.append("time.sleep(2)")

        if ".click()" in stripped:
            cleaned_lines.append("time.sleep(2)")

    cleaned_script = "\n".join(cleaned_lines)

    # Conversion ancienne syntaxe Selenium vers Selenium 4
    cleaned_script = re.sub(
        r'driver\.find_element_by_id\("([^"]+)"\)',
        r'driver.find_element(By.ID, "\1")',
        cleaned_script,
    )

    cleaned_script = re.sub(
        r"driver\.find_element_by_id\('([^']+)'\)",
        r'driver.find_element(By.ID, "\1")',
        cleaned_script,
    )

    cleaned_script = re.sub(
        r'driver\.find_element_by_class_name\("([^"]+)"\)',
        r'driver.find_element(By.CLASS_NAME, "\1")',
        cleaned_script,
    )

    cleaned_script = re.sub(
        r"driver\.find_element_by_class_name\('([^']+)'\)",
        r'driver.find_element(By.CLASS_NAME, "\1")',
        cleaned_script,
    )

    cleaned_script = re.sub(
        r'driver\.find_element_by_link_text\("([^"]+)"\)',
        r'driver.find_element(By.LINK_TEXT, "\1")',
        cleaned_script,
    )

    cleaned_script = re.sub(
        r"driver\.find_element_by_link_text\('([^']+)'\)",
        r'driver.find_element(By.LINK_TEXT, "\1")',
        cleaned_script,
    )

    if "driver.get(" not in cleaned_script:
        cleaned_script = f'driver.get("{url}")\ntime.sleep(2)\n' + cleaned_script

    cleaned_script = remove_honeypot_interactions(cleaned_script)
    cleaned_script = fix_empty_except_blocks(cleaned_script)

    return cleaned_script


def has_captcha(driver):
    """
    Détecte la présence d'un captcha ou reCAPTCHA dans la page.
    """

    captcha_selectors = [
        "iframe[src*='recaptcha']",
        ".g-recaptcha",
        "[class*='recaptcha']",
        "[id*='recaptcha']",
        "[name*='recaptcha']",
        "iframe[src*='captcha']",
        "[class*='captcha']",
        "[id*='captcha']",
        "textarea[name='g-recaptcha-response']",
        "[name='g-recaptcha-response']",
        "iframe[title*='reCAPTCHA']",
        "iframe[title*='recaptcha']",
    ]

    for selector in captcha_selectors:
        elements = driver.find_elements(By.CSS_SELECTOR, selector)

        if elements:
            return True

    page_source = driver.page_source.lower()

    return (
        "recaptcha" in page_source
        or "g-recaptcha" in page_source
        or "captcha" in page_source
        or "je ne suis pas un robot" in page_source
        or "i'm not a robot" in page_source
    )


def check_expected_result(driver, test):
    test_name = (test.get("name") or "").lower()
    test_type = (test.get("type") or "").lower()
    expected_result = (test.get("expected_result") or "").lower()

    current_url = driver.current_url.lower()
    page_source = driver.page_source.lower()

    positive_login_error_keywords = [
        "login was unsuccessful",
        "credentials provided are incorrect",
        "no customer account found",
        "incorrect",
        "invalid",
        "erreur",
    ]

    # 1. Login positif
    if test_type == "positive" and ("connexion" in test_name or "login" in test_name):
        for keyword in positive_login_error_keywords:
            if keyword in page_source:
                return {
                    "status": "failed",
                    "detail": f"Connexion positive échouée. Message détecté : {keyword}",
                }

        if "/login" not in current_url or "logout" in page_source:
            return {
                "status": "passed",
                "detail": f"Connexion positive réussie. URL finale : {driver.current_url}",
            }

        return {
            "status": "failed",
            "detail": "Connexion positive non validée : l'utilisateur est resté sur la page login.",
        }

    # 2. Tests négatifs

    # 2. Tests négatifs : login + formulaire
    if (
        test_type == "negative"
        or "invalid" in test_name
        or "invalide" in test_name
        or "vide" in test_name
        or "empty" in test_name
    ):
        error_keywords = [
            # erreurs login
            "login was unsuccessful",
            "credentials provided are incorrect",
            "no customer account found",
            "incorrect",
            "invalid",
            "erreur",
            # erreurs formulaire
            "required",
            "this field is required",
            "please enter",
            "obligatoire",
            "champ obligatoire",
            "invalid email",
            "enter a valid email",
            "please enter a valid email",
        ]

        for keyword in error_keywords:
            if keyword in page_source:
                return {
                    "status": "passed",
                    "detail": f"Test négatif validé. Message d'erreur détecté : {keyword}",
                }

        validation_errors = driver.find_elements(
            By.CSS_SELECTOR,
            ".wpforms-error, label.wpforms-error, .error, .invalid-feedback, [role='alert']",
        )

        visible_errors = [
            error.text.strip()
            for error in validation_errors
            if error.is_displayed() and error.text.strip()
        ]

        if visible_errors:
            return {
                "status": "passed",
                "detail": f"Message(s) de validation détecté(s) : {visible_errors[:3]}",
            }

        return {
            "status": "failed",
            "detail": "Test négatif échoué : aucun message d'erreur détecté.",
        }

        for keyword in positive_login_error_keywords:
            if keyword in page_source:
                return {
                    "status": "passed",
                    "detail": f"Test négatif validé. Message d'erreur détecté : {keyword}",
                }

        return {
            "status": "failed",
            "detail": "Test négatif échoué : aucun message d'erreur attendu détecté.",
        }

    # 3. Navigation Register
    if (
        "register" in test_name
        or "inscription" in test_name
        or "enregistrement" in test_name
    ):
        if "/register" in current_url:
            return {
                "status": "passed",
                "detail": "Navigation vers la page d'inscription réussie.",
            }

        return {
            "status": "failed",
            "detail": f"Navigation attendue vers /register, mais URL finale : {driver.current_url}",
        }

    # 4. Navigation Forgot Password
    if (
        "forgot" in test_name
        or "mot de passe" in test_name
        or "passwordrecovery" in expected_result
    ):
        if "/passwordrecovery" in current_url:
            return {
                "status": "passed",
                "detail": "Navigation vers la page de récupération du mot de passe réussie.",
            }

        return {
            "status": "failed",
            "detail": f"Navigation attendue vers /passwordrecovery, mais URL finale : {driver.current_url}",
        }

    # 5. Remember Me
    if "remember" in test_name:
        try:
            checkbox = driver.find_element(By.ID, "RememberMe")
            return {
                "status": "passed",
                "detail": f"Checkbox RememberMe détectée. État actuel : {checkbox.is_selected()}",
            }
        except Exception:
            return {
                "status": "failed",
                "detail": "Checkbox RememberMe introuvable après exécution.",
            }

    # 6. Test sécurité : XSS
    if "security" in test_type and (
        "xss" in test_name
        or "script injecté" in expected_result
        or "script injected" in expected_result
    ):
        try:
            alert = WebDriverWait(driver, 3).until(EC.alert_is_present())
            alert_text = alert.text
            alert.accept()

            return {
                "status": "failed",
                "detail": f"Faille XSS détectée : une alerte JavaScript s'est ouverte : {alert_text}",
            }
        except TimeoutException:
            page_source = driver.page_source.lower()
            security_block_keywords = [
                "a potentially unsafe operation has been detected",
                "your access to this service has been limited",
                "block technical data",
                "request has been blocked",
                "unsafe operation",
                "wordfence",
                "firewall",
                "forbidden",
                "403",
            ]

            for keyword in security_block_keywords:
                if keyword in page_source:
                    return {
                        "status": "passed",
                        "detail": (
                            "Test XSS sécurisé : aucune alerte JavaScript détectée. "
                            "La requête dangereuse a été bloquée par une protection du site."
                        ),
                    }
            return {
                "status": "passed",
                "detail": "Aucune alerte JavaScript détectée après tentative XSS. Le script injecté n'a pas été exécuté.",
            }

    # 6. Test UI : chargement de page
    if test_type == "ui" or "loadpage" in test_name or "pageload" in test_name:
        if driver.title and driver.title.strip():
            return {
                "status": "passed",
                "detail": f"Page chargée correctement. Titre détecté : {driver.title}",
            }

        return {
            "status": "failed",
            "detail": "La page est chargée, mais aucun titre valide n'a été détecté.",
        }

    # 7. Test sécurité : HTTPS
    if "security" in test_type and (
        "https" in test_name
        or "https" in expected_result
        or "connexion sécurisée" in expected_result
    ):
        if driver.current_url.lower().startswith("https://"):
            return {
                "status": "passed",
                "detail": f"Connexion HTTPS validée. URL finale : {driver.current_url}",
            }

        return {
            "status": "failed",
            "detail": f"Connexion non sécurisée. URL finale : {driver.current_url}",
        }

    # 8. Test SEO : titre de page
    if "seo" in test_type and (
        "title" in test_name
        or "titre" in expected_result
        or "balise title" in expected_result
    ):
        if driver.title and driver.title.strip():
            return {
                "status": "passed",
                "detail": f"Balise title détectée : {driver.title}",
            }

        return {"status": "failed", "detail": "Aucune balise title valide détectée."}

    # 9. Test SEO : lisibilité URL
    if "seo" in test_type and (
        "url" in test_name
        or "url lisible" in expected_result
        or "descriptive" in expected_result
    ):
        current_url = driver.current_url.lower()

        if len(current_url) <= 120 and "?" not in current_url:
            return {
                "status": "passed",
                "detail": f"URL lisible et simple : {driver.current_url}",
            }

        return {
            "status": "failed",
            "detail": f"URL trop complexe ou contenant des paramètres : {driver.current_url}",
        }

    # 10. Test sécurité / SEO : liens
    if "links" in test_name or "liens" in expected_result or "href" in expected_result:
        links = driver.find_elements(By.TAG_NAME, "a")

        invalid_links = []

        for link in links:
            href = link.get_attribute("href")
            text = (link.text or "").strip()

            if not href or href.strip() in ["#", "javascript:void(0)"]:
                invalid_links.append(text or "lien sans texte")

        if not invalid_links:
            return {
                "status": "passed",
                "detail": f"{len(links)} liens vérifiés. Aucun lien vide ou invalide détecté.",
            }

        return {
            "status": "failed",
            "detail": f"Liens invalides détectés : {invalid_links[:5]}",
        }
    # 11.Test formulaire : champ obligatoire vide
    if (
        "missing" in test_name
        or "required" in expected_result
        or "obligatoire" in expected_result
        or "champ" in expected_result
        or ("champ" in expected_result and "vide" in test_name)
    ):
        error_keywords = [
            "required",
            "obligatoire",
            "please enter",
            "this field is required",
            "champ obligatoire",
        ]

        for keyword in error_keywords:
            if keyword in page_source:
                return {
                    "status": "passed",
                    "detail": f"Validation formulaire détectée. Message trouvé : {keyword}",
                }

        validation_errors = driver.find_elements(
            By.CSS_SELECTOR,
            ".wpforms-error, label.wpforms-error, .error, .invalid-feedback",
        )

        visible_errors = [
            error.text.strip()
            for error in validation_errors
            if error.is_displayed() and error.text.strip()
        ]

        if visible_errors:
            return {
                "status": "passed",
                "detail": f"Message(s) de validation détecté(s) : {visible_errors[:3]}",
            }

        return {
            "status": "failed",
            "detail": "Aucun message de validation détecté pour le champ obligatoire.",
        }
        # 12. Test formulaire positif bloqué par captcha
    if is_positive_form_submit_test(test):
        if has_captcha(driver):
            return {
                "status": "pending",
                "detail": (
                    "Test non automatisé complètement : un captcha/reCAPTCHA est présent. "
                    "Intervention manuelle du testeur requise."
                ),
            }

        success_keywords = [
            "thank you",
            "thanks",
            "thanks for contacting",
            "merci",
            "success",
            "successful",
            "confirmation",
            "message sent",
            "envoyé",
            "we will be in touch",
        ]

        for keyword in success_keywords:
            if keyword in page_source:
                return {
                    "status": "passed",
                    "detail": f"Soumission réussie détectée. Indice trouvé : {keyword}",
                }

        return {
            "status": "failed",
            "detail": "Aucun message de confirmation détecté après soumission du formulaire.",
        }

    # 13. Test navigation : vérifier l'URL finale
    if (
        "navigation" in test_type
        or "navigate" in test_name
        or "navigateto" in test_name
        or "redirigé vers" in expected_result
    ):
        expected_urls = re.findall(
            r"https?://[^\s\)\]\.]+(?:/[^\s\)\]]*)?", expected_result
        )

        if expected_urls:
            expected_url = expected_urls[0].rstrip(".,")
            current_url_clean = driver.current_url.rstrip("/")

            if expected_url.rstrip("/") in current_url_clean:
                return {
                    "status": "passed",
                    "detail": f"Navigation réussie vers l'URL attendue : {driver.current_url}",
                }

            return {
                "status": "failed",
                "detail": (
                    f"Navigation incorrecte. URL attendue : {expected_url}, "
                    f"URL finale : {driver.current_url}"
                ),
            }

        return {
            "status": "passed",
            "detail": f"Navigation exécutée. URL finale : {driver.current_url}",
        }

    return {
        "status": "passed",
        "detail": f"Script exécuté sans erreur technique. URL finale : {driver.current_url}",
    }


def get_test_value(test, *keys):
    for key in keys:
        value = test.get(key)
        if value:
            return str(value)
    return ""


def is_positive_form_submit_test(test):
    """
    Détecte un test positif de soumission de formulaire.
    """

    test_name = get_test_value(test, "name", "test_name", "title").lower()
    test_type = get_test_value(test, "type", "test_type", "category").lower()
    expected_result = get_test_value(
        test,
        "expected_result",
        "expected",
        "resultat_attendu",
        "expectedResult",
    ).lower()

    steps = test.get("steps") or []
    steps_text = " ".join([str(step) for step in steps]).lower()

    full_text = f"{test_name} {test_type} {expected_result} {steps_text}"

    has_form_submit = any(
        word in full_text
        for word in [
            "soumission",
            "soumettre",
            "submit",
            "envoyer",
            "envoi",
            "formulaire",
            "form",
            "contact",
            "message",
        ]
    )

    has_positive_meaning = any(
        word in full_text
        for word in [
            "positive",
            "positif",
            "valide",
            "valid",
            "succès",
            "success",
            "réussi",
            "réussie",
        ]
    )

    negative_text = f"{test_name} {test_type} {expected_result}"

    has_negative_meaning = any(
        word in negative_text
        for word in [
            "negative",
            "négatif",
            "invalide",
            "invalid",
            "vide",
            "empty",
            "required",
            "erreur",
            "error",
            "incorrect",
        ]
    )

    return has_form_submit and has_positive_meaning and not has_negative_meaning


def save_test_screenshot(driver, test_id):
    screenshots_dir = os.path.join("static", "screenshots")
    os.makedirs(screenshots_dir, exist_ok=True)

    filename = f"test_{test_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"

    full_path = os.path.join(screenshots_dir, filename)
    driver.save_screenshot(full_path)

    return f"screenshots/{filename}"


def execute_selenium_script(test, url):
    test_id = test["id"]
    selenium_script = test.get("selenium_script")

    driver = None

    try:
        chrome_options = Options()
        chrome_options.add_argument("--start-maximized")

        driver = webdriver.Chrome(options=chrome_options)
        driver.implicitly_wait(5)

        if is_positive_form_submit_test(test):
            driver.get(url)
            time.sleep(2)

            if has_captcha(driver):
                detail_message = (
                    "Test non automatisé complètement : un captcha/reCAPTCHA est présent. "
                    "Intervention manuelle du testeur requise."
                )

                result = {
                    "status": "pending",
                    "detail": detail_message,
                    "screenshot_path": save_test_screenshot(driver, test_id),
                }

                print("[ASSERTION RESULT] :", result)

                return result

        cleaned_script = clean_selenium_script(selenium_script, url)

        print("\n========== SCRIPT SELENIUM NETTOYÉ ==========")
        print(cleaned_script)
        print("=============================================\n")

        execution_context = {
            "driver": driver,
            "By": By,
            "Keys": Keys,
            "WebDriverWait": WebDriverWait,
            "EC": EC,
            "time": time,
            "safe_find_element": safe_find_element,
            "TimeoutException": TimeoutException,
            "NoAlertPresentException": NoAlertPresentException,
        }

        exec(cleaned_script, execution_context)

        time.sleep(2)

        assertion_result = check_expected_result(driver, test)

        print("[ASSERTION RESULT] :", assertion_result)

        screenshot_path = save_test_screenshot(driver, test_id)

        return {
            "status": assertion_result["status"],
            "detail": assertion_result["detail"],
            "screenshot_path": screenshot_path,
        }

    except Exception as e:
        screenshot_path = None

        if driver:
            screenshot_path = save_test_screenshot(driver, test_id)

            if is_positive_form_submit_test(test) and has_captcha(driver):
                return {
                    "status": "pending",
                    "detail": (
                        "Test non automatisé complètement : un captcha/reCAPTCHA est présent. "
                        "Intervention manuelle du testeur requise."
                    ),
                    "screenshot_path": screenshot_path,
                }
        time.sleep(3)

        return {
            "status": "failed",
            "detail": str(e),
            "screenshot_path": screenshot_path,
        }

    finally:
        if driver:
            driver.quit()
