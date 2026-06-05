def detect_features(relevant_data):
    """
    Détecte les grandes fonctionnalités métier présentes dans les pages analysées.
    Exemple : authentication, search, shopping_cart, newsletter, poll...
    """

    features = []

    links = relevant_data.get("links", [])
    buttons = relevant_data.get("buttons", [])
    inputs = relevant_data.get("inputs", [])
    forms = relevant_data.get("forms", [])
    pages = relevant_data.get("pages", [])

    all_text_parts = []

    for item in links + buttons + inputs + forms:
        all_text_parts.append(str(item.get("text", "")))
        all_text_parts.append(str(item.get("href", "")))
        all_text_parts.append(str(item.get("id", "")))
        all_text_parts.append(str(item.get("name", "")))
        all_text_parts.append(str(item.get("class", "")))
        all_text_parts.append(str(item.get("value", "")))
        all_text_parts.append(str(item.get("action", "")))

    for page in pages:
        all_text_parts.append(str(page.get("url", "")))
        all_text_parts.append(str(page.get("page_type", "")))

    all_text = " ".join(all_text_parts).lower()

    # Authentification
    if any(word in all_text for word in ["login", "log in", "register", "password", "account"]):
        features.append("authentication")

    # Recherche
    if any(word in all_text for word in ["search", "small-searchterms"]):
        features.append("search")

    # Panier
    if any(word in all_text for word in ["cart", "shopping cart", "add to cart", "ico-cart"]):
        features.append("shopping_cart")

    # Wishlist
    if any(word in all_text for word in ["wishlist", "ico-wishlist"]):
        features.append("wishlist")

    # Newsletter
    if any(word in all_text for word in ["newsletter", "subscribe", "newsletter-email"]):
        features.append("newsletter")

    # Sondage / poll
    if any(word in all_text for word in ["poll", "vote", "pollanswers"]):
        features.append("poll")

    # Catégories
    if any(word in all_text for word in ["books", "computers", "electronics", "apparel", "jewelry", "gift cards"]):
        features.append("categories")

    # Produits
    if any(word in all_text for word in ["product", "product-item", "product-box", "price"]):
        features.append("products")

    # Tri / filtre
    if any(word in all_text for word in ["orderby", "viewmode", "price", "filter", "sort"]):
        features.append("sorting_filtering")

    # Footer / liens informationnels
    if any(word in all_text for word in ["about us", "contact us", "sitemap", "privacy", "conditions"]):
        features.append("footer_navigation")

    return list(set(features))