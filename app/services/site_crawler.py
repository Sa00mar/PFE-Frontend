from urllib.parse import urljoin, urlparse
from app.services.page_fetcher import fetch_page_html
from app.services.html_parser import parse_html


IMPORTANT_KEYWORDS = [
    "login",
    "register",
    "cart",
    "wishlist",
    "books",
    "computers",
    "electronics",
    "apparel",
    "shoes",
    "digital",
    "jewelry",
    "gift",
    "contact",
    "about",
    "search"
]


def is_internal_link(base_url, href):
    if not href:
        return False

    full_url = urljoin(base_url, href)

    base_domain = urlparse(base_url).netloc
    link_domain = urlparse(full_url).netloc

    return base_domain == link_domain


def is_important_link(href, text):
    value = f"{href} {text}".lower()

    return any(keyword in value for keyword in IMPORTANT_KEYWORDS)

def score_link(url, text):
    value = f"{url} {text}".lower()
    score = 0

    # Liens avec texte visible
    if text.strip():
        score += 2

    # Pages simples sans paramètres
    if not urlparse(url).query:
        score += 2

    # Pages HTML classiques
    if not url.lower().endswith((".pdf", ".jpg", ".png", ".zip", ".css", ".js")):
        score += 2

    # Profondeur raisonnable
    path_parts = [p for p in urlparse(url).path.split("/") if p]
    if 0 <= len(path_parts) <= 3:
        score += 2

    # Actions utilisateur fréquentes, mais générales
    action_words = [
        "login", "sign", "contact", "blog", "course", "practice",
        "test","table","exception","exceptions",
        "read", "more", "next", "previous", "learn", "start",
        "enroll", "subscribe"
    ]

    if any(word in value for word in action_words):
        score += 3
    
    business_keywords = [
        "practice-test",
        "test-login",
        "test-exceptions",
        "test-table",
        "checkout",
        "cart",
        "dashboard",
        "account",
        "product",
        "detail"
    ]
    if any(keyword in value for keyword in business_keywords):
        score += 8
    return score

def extract_important_links(base_url, parsed_data, max_links=12):
    links = parsed_data.get("links", [])
    selected_links = []
    seen = set()

    for link in links:
        href = link.get("href")
        text = link.get("text") or ""

        if not is_internal_link(base_url, href):
            continue

        

        full_url = urljoin(base_url, href)

        if full_url in seen:
            continue

        seen.add(full_url)
        selected_links.append({
            "url": full_url,
            "text": text,
            "href": href
        })

    selected_links = sorted(
       selected_links,
       key=lambda link: score_link(link["url"], link["text"]),
       reverse=True
    )
    return selected_links[:max_links]

   
def crawl_important_pages(start_url, max_pages=12, max_depth=2):
    """
    Crawler intelligent multi-niveaux.

    Il analyse :
    - la page principale
    - les pages importantes de niveau 1
    - les pages métier importantes de niveau 2
    """

    crawled_pages = []
    visited = set()
    queue = [{
        "url": start_url,
        "depth": 0,
        "source": "main_page",
        "link_text": ""
    }]

    while queue and len(crawled_pages) < max_pages:
        current = queue.pop(0)

        current_url = current["url"]
        depth = current["depth"]

        if current_url in visited:
            continue

        if depth > max_depth:
            continue

        visited.add(current_url)

        result = fetch_page_html(current_url)

        if not result["success"]:
            continue

        html = result["html"]
        parsed_data = parse_html(html)

        crawled_pages.append({
            "url": current_url,
            "html": html,
            "parsed_data": parsed_data,
            "source": current["source"],
            "link_text": current.get("link_text", ""),
            "depth": depth
        })

        if len(crawled_pages) >= max_pages:
            break

        child_links = extract_important_links(
            current_url,
            parsed_data,
            max_links=12
        )

        for link in child_links:
            child_url = link["url"]

            if child_url in visited:
                continue

            if len(crawled_pages) + len(queue) >= max_pages:
                break

            queue.append({
                "url": child_url,
                "depth": depth + 1,
                "source": "linked_page",
                "link_text": link["text"]
            })

    return {
        "success": True,
        "pages": crawled_pages,
        "error": None
    }
