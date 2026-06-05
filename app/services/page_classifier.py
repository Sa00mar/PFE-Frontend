from urllib.parse import urlparse

def classify_page(parsed_data):
    """
    Détecte le type fonctionnel de la page à partir des éléments DOM.
    """

    text_inputs = parsed_data.get("text_inputs", [])
    email_inputs = parsed_data.get("email_inputs", [])
    password_inputs = parsed_data.get("password_inputs", [])
    radio_inputs = parsed_data.get("radio_inputs", [])
    checkbox_inputs = parsed_data.get("checkbox_inputs", [])
    textareas = parsed_data.get("textareas", [])
    selects = parsed_data.get("selects", [])
    buttons = parsed_data.get("buttons", [])
    forms = parsed_data.get("forms", [])
    links = parsed_data.get("links", [])

    link_texts = " ".join([(l.get("text") or "").lower() for l in links])
    link_hrefs = " ".join([(l.get("href") or "").lower() for l in links])

    has_home_navigation = any(keyword in link_texts or keyword in link_hrefs for keyword in [
        "login",
        "log in",
        "register",
        "shopping cart",
        "wishlist",
        "books",
        "computers",
        "electronics",
        "apparel",
        "digital downloads",
        "jewelry",
        "gift cards"
    ])

    has_search = any(
        "search" in ((i.get("name") or "") + (i.get("id") or "") + (i.get("class") or "") + (i.get("value") or "")).lower()
        for i in text_inputs
    )

    # ---------------- LOGIN PAGE ----------------
    if len(password_inputs) > 0 and (len(text_inputs) > 0 or len(email_inputs) > 0):
        return "login_page"

    # ---------------- HOME PAGE ----------------
    if has_home_navigation or has_search:
        return "home_page"

    # ---------------- CHOICE FORM PAGE ----------------
    if len(radio_inputs) > 0 or len(checkbox_inputs) > 0:
        return "choice_form_page"

    # ---------------- SIMPLE FORM PAGE ----------------
    if len(forms) > 0 and (
        len(text_inputs) > 0 or
        len(email_inputs) > 0 or
        len(textareas) > 0 or
        len(selects) > 0
    ):
        return "form_page"

    # ---------------- BUTTON ONLY PAGE ----------------
    if len(buttons) > 0 and len(forms) == 0:
        return "action_page"

    return "unknown"

def normalize_value(value):
    return (value or "").strip().lower()


def get_domain(url):
    return urlparse(url or "").netloc.lower()


def classify_site_structure(pages, main_url):
    """
    Classe les pages analysées dans un site multipages.

    Rôle :
    - identifier les pages métier principales
    - identifier les pages secondaires
    - identifier les pages utilitaires
    - identifier les liens/pages externes
    """

    main_domain = get_domain(main_url)

    site_structure = {
        "main_pages": [],
        "secondary_pages": [],
        "utility_pages": [],
        "external_pages": []
    }

    for page in pages:
        url = normalize_value(page.get("url"))
        page_type = normalize_value(page.get("page_type"))
        title = page.get("title")

        if not url:
            continue

        page_domain = get_domain(url)

        page_info = {
            "url": page.get("url"),
            "title": title,
            "page_type": page.get("page_type")
        }

        if page_domain and main_domain and page_domain != main_domain:
            site_structure["external_pages"].append(page_info)
            continue

        if (
           "privacy" in url
           or "policy" in url
           or "terms" in url
           or "cookies" in url
           or "conditions" in url
        ):
          site_structure["utility_pages"].append(page_info)

        elif (
            page_type in ["home_page", "login_page", "form_page", "action_page"]
            or "login" in url
            or "signin" in url
            or "register" in url
            or "signup" in url
            or "contact" in url
            or "cart" in url
            or "checkout" in url
            or "payment" in url
        ):
           site_structure["main_pages"].append(page_info)
    
    

        else:
            site_structure["secondary_pages"].append(page_info)

    return site_structure