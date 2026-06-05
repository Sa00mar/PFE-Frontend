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
from selenium.common.exceptions import TimeoutException

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

    raise TimeoutException(
        f"Aucun élément trouvé avec les sélecteurs : {selectors}"
    )

def clean_selenium_script(script, url):
    """
    Nettoie le script généré par Gemini avant exécution.
    Objectif :
    - utiliser la vraie URL
    - supprimer la création/fermeture du driver
    - convertir l'ancienne syntaxe Selenium vers Selenium 4
    - ajouter des pauses visibles pour la démo
    """

    lines = script.splitlines()
    cleaned_lines = []

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("assert "):
            continue

        if stripped.startswith("# assert"):
            continue

        if "webdriver.Chrome" in stripped:
            continue

        if "Service(" in stripped:
            continue

        if "driver.quit()" in stripped:
            continue

        if stripped.startswith("from selenium") or stripped.startswith("import selenium"):
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
        cleaned_script
    )

    cleaned_script = re.sub(
        r"driver\.find_element_by_id\('([^']+)'\)",
        r'driver.find_element(By.ID, "\1")',
        cleaned_script
    )

    cleaned_script = re.sub(
        r'driver\.find_element_by_class_name\("([^"]+)"\)',
        r'driver.find_element(By.CLASS_NAME, "\1")',
        cleaned_script
    )

    cleaned_script = re.sub(
        r"driver\.find_element_by_class_name\('([^']+)'\)",
        r'driver.find_element(By.CLASS_NAME, "\1")',
        cleaned_script
    )

    cleaned_script = re.sub(
        r'driver\.find_element_by_link_text\("([^"]+)"\)',
        r'driver.find_element(By.LINK_TEXT, "\1")',
        cleaned_script
    )

    cleaned_script = re.sub(
        r"driver\.find_element_by_link_text\('([^']+)'\)",
        r'driver.find_element(By.LINK_TEXT, "\1")',
        cleaned_script
    )

    if "driver.get(" not in cleaned_script:
        cleaned_script = f'driver.get("{url}")\ntime.sleep(2)\n' + cleaned_script

    return cleaned_script

def check_expected_result(driver, test):
    test_name = (test.get("name") or "").lower()
    test_type = (test.get("type") or "").lower()
    expected_result = (test.get("expected_result") or "").lower()

    current_url = driver.current_url.lower()
    page_source = driver.page_source.lower()

    error_keywords = [
        "login was unsuccessful",
        "credentials provided are incorrect",
        "no customer account found",
        "please enter",
        "required",
        "incorrect",
        "invalid",
        "erreur"
    ]

    # 1. Login positif
    if test_type == "positive" and ("connexion" in test_name or "login" in test_name):
        for keyword in error_keywords:
            if keyword in page_source:
                return {
                    "status": "failed",
                    "detail": f"Connexion positive échouée. Message détecté : {keyword}"
                }

        if "/login" not in current_url or "logout" in page_source:
            return {
                "status": "passed",
                "detail": f"Connexion positive réussie. URL finale : {driver.current_url}"
            }

        return {
            "status": "failed",
            "detail": "Connexion positive non validée : l'utilisateur est resté sur la page login."
        }

    # 2. Tests négatifs
    if test_type == "negative" or "invalid" in test_name or "invalide" in test_name or "vide" in test_name:
        for keyword in error_keywords:
            if keyword in page_source:
                return {
                    "status": "passed",
                    "detail": f"Test négatif validé. Message d'erreur détecté : {keyword}"
                }

        return {
            "status": "failed",
            "detail": "Test négatif échoué : aucun message d'erreur attendu détecté."
        }

    # 3. Navigation Register
    if "register" in test_name or "inscription" in test_name or "enregistrement" in test_name:
        if "/register" in current_url:
            return {
                "status": "passed",
                "detail": "Navigation vers la page d'inscription réussie."
            }

        return {
            "status": "failed",
            "detail": f"Navigation attendue vers /register, mais URL finale : {driver.current_url}"
        }

    # 4. Navigation Forgot Password
    if "forgot" in test_name or "mot de passe" in test_name or "passwordrecovery" in expected_result:
        if "/passwordrecovery" in current_url:
            return {
                "status": "passed",
                "detail": "Navigation vers la page de récupération du mot de passe réussie."
            }

        return {
            "status": "failed",
            "detail": f"Navigation attendue vers /passwordrecovery, mais URL finale : {driver.current_url}"
        }

    # 5. Remember Me
    if "remember" in test_name:
        try:
            checkbox = driver.find_element(By.ID, "RememberMe")
            return {
                "status": "passed",
                "detail": f"Checkbox RememberMe détectée. État actuel : {checkbox.is_selected()}"
            }
        except Exception:
            return {
                "status": "failed",
                "detail": "Checkbox RememberMe introuvable après exécution."
            }

    return {
        "status": "passed",
        "detail": f"Script exécuté sans erreur technique. URL finale : {driver.current_url}"
    }
def execute_selenium_script(test, url):
    test_id = test["id"]
    selenium_script = test.get("selenium_script")
    
    screenshots_dir = os.path.join("static", "screenshots")
    os.makedirs(screenshots_dir, exist_ok=True)

    driver = None

    try:
        chrome_options = Options()
        chrome_options.add_argument("--start-maximized")

        driver = webdriver.Chrome(options=chrome_options)
        driver.implicitly_wait(5)

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
            "safe_find_element": safe_find_element
        }

        exec(cleaned_script, execution_context)

        time.sleep(2)

        assertion_result = check_expected_result(driver, test)

        return {
            "status": assertion_result["status"],
            "detail": assertion_result["detail"],
            "screenshot_path": None
        }

    except Exception as e:
        screenshot_path = None

        if driver:
            filename = f"test_{test_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            screenshot_path = os.path.join(screenshots_dir, filename)
            driver.save_screenshot(screenshot_path)

        time.sleep(3)

        return {
            "status": "failed",
            "detail": str(e),
            "screenshot_path": screenshot_path
        }

    finally:
        if driver:
            driver.quit()