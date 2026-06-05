import requests
from urllib.parse import urlparse


def is_valid_url(url):
    """
    Vérifie si l'URL est valide.
    Exemple valide : https://example.com
    """
    parsed = urlparse(url)
    return all([parsed.scheme, parsed.netloc])


def fetch_page_html(url):
    """
    Récupère le HTML d'une page web.
    Retourne un dictionnaire contenant :
    - success : True/False
    - html : le contenu HTML si succès
    - error : message d'erreur si problème
    """

    if not is_valid_url(url):
        return {
            "success": False,
            "html": None,
            "error": "URL invalide."
        }

    try:
        headers = {
            "User-Agent": (
              "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
              "AppleWebKit/537.36 (KHTML, like Gecko) "
              "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
            "Connection": "keep-alive",
        }

        response = requests.get(url, headers=headers, timeout=15)

        if response.status_code == 200:
            return {
                "success": True,
                "html": response.text,
                "error": None
            }
        else:
            return {
                "success": False,
                "html": None,
                "error": f"Erreur HTTP : {response.status_code}"
            }

    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "html": None,
            "error": str(e)
        }