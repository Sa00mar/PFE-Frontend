import time
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from app.services.html_parser import parse_html


def score_link(link):

    score = 0

    parsed = urlparse(link)

    # privilégier les pages simples
    if not parsed.query:
        score += 2

    # éviter les fichiers inutiles
    if not link.lower().endswith((
        ".pdf",
        ".jpg",
        ".png",
        ".zip",
        ".css",
        ".js"
    )):
        score += 2

    # éviter URLs trop longues
    if len(link) < 120:
        score += 1

    # profondeur raisonnable
    path_parts = [p for p in parsed.path.split("/") if p]

    if 1 <= len(path_parts) <= 3:
        score += 2

    return score

def crawl_authenticated_pages(url, login_email=None, login_password=None, max_pages=20):
    """
    Analyse authentifiée avec connexion manuelle assistée.

    Pourquoi ce mode ?
    - Certains sites comme Glovo, Facebook, Google, etc. n'affichent pas
      directement les champs email/password.
    - Ils utilisent souvent des popups, OAuth, captcha, double authentification
      ou protection anti-bot.
    - Donc Selenium ouvre le site, puis l'utilisateur se connecte manuellement.
    - Après l'attente, le crawler récupère le HTML de la session connectée.

    Sécurité :
    - Les identifiants ne sont pas sauvegardés.
    - Les identifiants ne sont pas envoyés à Gemini.
    - Les identifiants ne sont pas affichés dans les logs.
    """

    driver = None

    try:
        chrome_options = Options()
        chrome_options.add_argument("--start-maximized")

        driver = webdriver.Chrome(options=chrome_options)
        driver.implicitly_wait(5)

        # ==================================================
        # 1. OUVRIR LE SITE
        # ==================================================

        driver.get(url)

        print(
            "[INFO] Connexion manuelle : vous avez 60 secondes pour vous connecter."
        )

        # L'utilisateur fait le login manuellement dans la fenêtre Chrome.
        time.sleep(60)

        # ==================================================
        # 2. RÉCUPÉRER LA PAGE APRÈS CONNEXION
        # ==================================================

        html = driver.page_source

        if not html:
           return {
              "success": False,
               "pages": [],
               "error": "HTML vide après tentative de connexion"
            }

        parsed_data = parse_html(html)

        pages = [{
            "url": driver.current_url,
            "html": html,
            "parsed_data": parsed_data,
            "source": "authenticated_manual_login"
        }]

        print("[INFO] Page connectée récupérée :", driver.current_url)

        # ==================================================
        # 3. EXTRAIRE DES LIENS INTERNES APRÈS CONNEXION
        # ==================================================



        soup = BeautifulSoup(html, "html.parser")
        links = soup.find_all("a", href=True)

        visited = set()
        visited.add(driver.current_url)

        base_domain = urlparse(driver.current_url).netloc

        internal_links = []

        for link in links:
            href = link.get("href")

            if not href:
                continue

            next_url = urljoin(driver.current_url, href)
            parsed_next = urlparse(next_url)

            # Garder seulement les liens du même domaine
            if parsed_next.netloc != base_domain:
                continue

            # Éviter les ancres, logout, fichiers inutiles
            if "#" in next_url:
                continue

            if any(word in next_url.lower() for word in [
                "logout",
                "signout",
                "facebook",
                "instagram",
                "twitter",
                "linkedin",
                "youtube"
            ]):
                continue

            if next_url not in visited:
                internal_links.append(next_url)
        

        internal_links = sorted(
           internal_links,
           key=score_link,
           reverse=True
        )
        # Limiter le nombre de pages pour éviter une analyse trop longue
        internal_links = internal_links[:max_pages - 1]

        # ==================================================
        # 4. VISITER QUELQUES PAGES CONNECTÉES
        # ==================================================

        for next_url in internal_links:

            try:
                driver.get(next_url)
                time.sleep(3)

                page_html = driver.page_source

                if not page_html:
                   print("[WARNING] HTML vide pour la page :", next_url)
                   continue

                page_parsed = parse_html(page_html)

                pages.append({
                    "url": driver.current_url,
                    "html": page_html,
                    "parsed_data": page_parsed,
                    "source": "authenticated_internal_link"
                })

                visited.add(driver.current_url)

                print("[INFO] Page connectée explorée :", driver.current_url)

                if len(pages) >= max_pages:
                    break

            except Exception as page_error:
                print("[WARNING] Page ignorée :", next_url, "|", str(page_error))
                continue

        return {
            "success": True,
            "pages": pages,
            "error": None
        }

    except Exception as e:

        return {
            "success": False,
            "pages": [],
            "error": str(e)
        }

    finally:

        if driver:
            driver.quit()