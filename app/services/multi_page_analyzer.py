from app.services.page_classifier import classify_page
from app.services.page_filtre import filter_relevant_elements, detect_semantic_actions


def merge_relevant_data(all_pages):
    """
    Fusionne les éléments pertinents détectés dans plusieurs pages.
    """

    merged = {
        "pages": [],
        "inputs": [],
        "buttons": [],
        "links": [],
        "forms": [],
        "textareas": [],
        "selects": [],
        "semantic_actions": [],
        "visible_text": "",
    }

    for page in all_pages:
        url = page["url"]
        parsed_data = page["parsed_data"]

        page_type = classify_page(parsed_data)
        relevant_data = filter_relevant_elements(parsed_data, page_type)

        # Important : garder le texte visible pour détecter les credentials de test
        relevant_data["visible_text"] = parsed_data.get("visible_text", "")
        merged["visible_text"] += " " + parsed_data.get("visible_text", "")

        semantic_actions = detect_semantic_actions(relevant_data)

        merged["pages"].append(
            {
                "url": url,
                "page_type": page_type,
                "source": page.get("source"),
                "link_text": page.get("link_text"),
                "title": parsed_data.get("title"),
                "visible_text": parsed_data.get("visible_text", ""),
                "inputs": relevant_data.get("inputs", []),
                "buttons": relevant_data.get("buttons", []),
                "links": relevant_data.get("links", []),
                "forms": relevant_data.get("forms", []),
                "textareas": relevant_data.get("textareas", []),
                "selects": relevant_data.get("selects", []),
                "semantic_actions": semantic_actions,
            }
        )

        for key in ["inputs", "buttons", "links", "forms", "textareas", "selects"]:
            for item in relevant_data.get(key, []):
                item_copy = dict(item)
                item_copy["page_url"] = url
                item_copy["page_type"] = page_type
                merged[key].append(item_copy)

        for action in semantic_actions:
            action_copy = dict(action)
            action_copy["page_url"] = url
            action_copy["page_type"] = page_type
            merged["semantic_actions"].append(action_copy)

    merged["visible_text"] = " ".join(merged["visible_text"].split())

    return merged
