import time
from urllib.parse import urljoin, urlparse, urlunparse

from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from app.services.html_parser import parse_html


def normalize_url_without_fragment(url):
    """
    Supprime l'ancre #section d'une URL pour éviter les doublons.
    """
    parsed = urlparse(url)
    return urlunparse(parsed._replace(fragment=""))


def score_link(link):
    """
    Donne un score simple aux liens internes importants.
    Plus le score est élevé, plus le lien est intéressant à analyser.
    """

    score = 0
    parsed = urlparse(link)

    if not parsed.query:
        score += 2

    if not link.lower().endswith(
        (
            ".pdf",
            ".jpg",
            ".jpeg",
            ".png",
            ".zip",
            ".css",
            ".js",
            ".svg",
            ".webp",
        )
    ):
        score += 2

    if len(link) < 120:
        score += 1

    path_parts = [p for p in parsed.path.split("/") if p]

    if 1 <= len(path_parts) <= 3:
        score += 2

    keywords = [
        "dashboard",
        "account",
        "profile",
        "cart",
        "checkout",
        "orders",
        "settings",
        "contact",
        "search",
        "product",
        "details",
        "admin",
    ]

    value = link.lower()

    if any(keyword in value for keyword in keywords):
        score += 3

    return score


def should_ignore_url(url):
    """
    Ignore les liens inutiles ou dangereux pour une session connectée.
    """

    value = url.lower()

    ignored_keywords = [
        "logout",
        "signout",
        "deconnexion",
        "déconnexion",
        "delete",
        "remove-account",
    ]

    if any(keyword in value for keyword in ignored_keywords):
        return True

    ignored_extensions = (
        ".pdf",
        ".jpg",
        ".jpeg",
        ".png",
        ".zip",
        ".css",
        ".js",
        ".svg",
        ".webp",
    )

    if value.endswith(ignored_extensions):
        return True

    return False


def crawl_authenticated_pages(
    url, analysis_scope="single_page", max_pages=None, wait_seconds=60
):
    """
    Analyse authentifiée avec connexion manuelle.

    Principe :
    1. Selenium ouvre Chrome.
    2. L'utilisateur se connecte lui-même manuellement.
    3. Le système attend quelques secondes.
    4. Le HTML de la page connectée est récupéré.
    5. Si le scope est full_site, quelques liens internes connectés sont explorés.

    Sécurité :
    - Aucun email n'est demandé dans l'interface.
    - Aucun mot de passe n'est envoyé au backend.
    - Aucun identifiant n'est stocké.
    """

    driver = None

    if max_pages is None:
        if analysis_scope == "full_site":
            max_pages = 12
        else:
            max_pages = 1

    try:
        chrome_options = Options()
        chrome_options.add_argument("--start-maximized")

        driver = webdriver.Chrome(options=chrome_options)
        driver.implicitly_wait(5)

        driver.get(url)

        print("\n==================== ANALYSE AVEC CONNEXION ====================")
        print("[INFO] Une fenêtre Chrome est ouverte.")
        print("[INFO] Connectez-vous manuellement dans Chrome.")
        print(
            f"[INFO] Le système attend {wait_seconds} secondes avant de récupérer la page."
        )
        print("================================================================\n")

        time.sleep(wait_seconds)

        html = driver.page_source

        if not html:
            return {
                "success": False,
                "pages": [],
                "error": "HTML vide après la connexion manuelle.",
            }

        current_url = driver.current_url
        parsed_data = parse_html(html)

        pages = [
            {
                "url": current_url,
                "html": html,
                "parsed_data": parsed_data,
                "source": "authenticated_manual_login",
                "link_text": "",
                "depth": 0,
            }
        ]

        print("[INFO] Page connectée récupérée :", current_url)

        if max_pages <= 1:
            return {
                "success": True,
                "pages": pages,
                "error": None,
            }

        soup = BeautifulSoup(html, "html.parser")
        links = soup.find_all("a", href=True)

        visited = {normalize_url_without_fragment(current_url)}
        base_domain = urlparse(current_url).netloc

        internal_links = []

        for link in links:
            href = link.get("href")
            text = link.get_text(strip=True)

            if not href:
                continue

            next_url = urljoin(current_url, href)
            next_url = normalize_url_without_fragment(next_url)

            parsed_next = urlparse(next_url)

            if parsed_next.netloc != base_domain:
                continue

            if should_ignore_url(next_url):
                continue

            if next_url in visited:
                continue

            internal_links.append(
                {
                    "url": next_url,
                    "text": text,
                }
            )

        internal_links = sorted(
            internal_links,
            key=lambda item: score_link(item["url"]),
            reverse=True,
        )

        internal_links = internal_links[: max_pages - 1]

        for link in internal_links:
            next_url = link["url"]

            try:
                driver.get(next_url)
                time.sleep(3)

                page_html = driver.page_source

                if not page_html:
                    print("[WARNING] HTML vide pour la page :", next_url)
                    continue

                page_parsed = parse_html(page_html)
                final_url = normalize_url_without_fragment(driver.current_url)

                if final_url in visited:
                    continue

                pages.append(
                    {
                        "url": final_url,
                        "html": page_html,
                        "parsed_data": page_parsed,
                        "source": "authenticated_internal_link",
                        "link_text": link.get("text", ""),
                        "depth": 1,
                    }
                )

                visited.add(final_url)

                print("[INFO] Page connectée explorée :", final_url)

                if len(pages) >= max_pages:
                    break

            except Exception as page_error:
                print("[WARNING] Page ignorée :", next_url, "|", str(page_error))
                continue

        return {
            "success": True,
            "pages": pages,
            "error": None,
        }

    except Exception as e:
        return {
            "success": False,
            "pages": [],
            "error": str(e),
        }

    finally:
        if driver:
            driver.quit()
