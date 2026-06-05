def is_not_noise(item):
    name = (item.get("name") or "").lower()
    item_id = (item.get("id") or "").lower()
    item_class = (item.get("class") or "").lower()
    value = (item.get("value") or "").lower()
    text = (item.get("text") or "").lower()

    # On garde search et newsletter parce qu'ils sont utiles pour les tests home_page.
    return not (
        "csrf" in name or
        "token" in name or
        "hidden" in name or
        "script" in text or
        "style" in text
    )


def is_button_input(item):
    input_type = (item.get("type") or "").lower()
    return input_type in ["submit", "button"]


def is_real_input(item):
    input_type = (item.get("type") or "").lower()
    return input_type not in ["submit", "button", "hidden"]

def is_cta_button(item):
    text = (
        item.get("text")
        or item.get("value")
        or ""
    ).lower()

    cta_keywords = [
        "read more",
        "learn more",
        "enroll",
        "subscribe",
        "buy",
        "start",
        "join",
        "add to cart",
        "checkout",
        "get xpath",
        "submit"
    ]

    return any(keyword in text for keyword in cta_keywords)


def is_pagination_link(item):
    text = (item.get("text") or "").lower()

    return (
        text.isdigit()
        or text in ["next", "previous", "prev"]
    )


def is_navigation_link(item):
    href = (item.get("href") or "").lower()

    return any(word in href for word in [
        "login",
        "practice",
        "course",
        "blog",
        "contact"
    ])

def remove_duplicate_buttons(buttons):
    """
    Supprime les boutons dupliqués (ex: plusieurs "Add to cart")
    """
    unique_buttons = []
    seen = set()

    for btn in buttons:
        text = (btn.get("text") or "").strip().lower()
        value = (btn.get("value") or "").strip().lower()
        item_id = (btn.get("id") or "").strip().lower()
        item_class = (btn.get("class") or "").strip().lower()

        # priorité au texte ou value
        label = text or value

        if label:
            key = label
        else:
            key = f"{item_id}-{item_class}"

        if key not in seen:
            seen.add(key)
            unique_buttons.append(btn)

    return unique_buttons


def filter_relevant_elements(parsed_data, page_type):

    relevant = {
        "inputs": [],
        "buttons": [],
        "links": [],
        "forms": [],
        "textareas": [],
        "selects": []
    }

    # ================= LOGIN PAGE =================
    if page_type == "login_page":

        # TEXT INPUTS
        for item in parsed_data.get("text_inputs", []):
            name = (item.get("name") or "").lower()
            item_id = (item.get("id") or "").lower()
            item_class = (item.get("class") or "").lower()

            if not is_not_noise(item):
                continue

            if (
                "email" in name or "user" in name or "login" in name or
                "email" in item_id or "user" in item_id or "login" in item_id or
                "email" in item_class or "user" in item_class or "login" in item_class
            ):
                relevant["inputs"].append(item)

        # PASSWORD
        for item in parsed_data.get("password_inputs", []):
            if is_not_noise(item):
                relevant["inputs"].append(item)

        # CHECKBOX
        for item in parsed_data.get("checkbox_inputs", []):
            name = (item.get("name") or "").lower()
            item_id = (item.get("id") or "").lower()

            if is_not_noise(item) and ("remember" in name or "remember" in item_id):
                relevant["inputs"].append(item)

        # BUTTONS (input type submit/button)
        for item in parsed_data.get("other_inputs", []):
            value = (item.get("value") or "").lower()
            item_class = (item.get("class") or "").lower()

            if not is_not_noise(item):
                continue

            if not is_button_input(item):
                continue

            relevant["buttons"].append(item)
        # BUTTONS (<button>)
        for item in parsed_data.get("buttons", []):
            text = (item.get("text") or "").lower()
            item_class = (item.get("class") or "").lower()

            if not is_not_noise(item):
                continue

            if is_not_noise(item):
                relevant["buttons"].append(item)

        # FORMS
        for form in parsed_data.get("forms", []):
            if not is_not_noise(form):
                continue
            relevant["forms"].append(form)

        # LINKS
        for link in parsed_data.get("links", []):
            if not is_not_noise(link):
                continue
            href = (link.get("href")or"").lower()

            if "logout" in href:
                continue
            relevant["links"].append(link)

    
    # ================= HOME PAGE =================

    elif page_type == "home_page":

        # Inputs utiles : search, newsletter, radio poll
        for item in (
            parsed_data.get("text_inputs", []) +
            parsed_data.get("email_inputs", []) +
            parsed_data.get("radio_inputs", []) +
            parsed_data.get("checkbox_inputs", [])
        ):
            if is_real_input(item) and is_not_noise(item):
                relevant["inputs"].append(item)

        # Boutons utiles : Search, Vote, Add to cart, Subscribe
        for item in parsed_data.get("buttons", []):
            if is_not_noise(item):
                if is_cta_button(item):
                   item["semantic_type"] = "cta_button"

                relevant["buttons"].append(item)

        for item in parsed_data.get("other_inputs", []):
            if is_button_input(item) and is_not_noise(item):
                relevant["buttons"].append(item)

        # Liens utiles : menu, login, register, cart, wishlist, catégories
        # Garder les vrais liens internes utiles
        for link in parsed_data.get("links", []):

           if not is_not_noise(link):
              continue

           href = (link.get("href") or "").lower()

       # ignorer logout
           if "logout" in href:
            continue

           if is_navigation_link(link) or is_pagination_link(link):
              link["semantic_type"] = "navigation"
              relevant["links"].append(link)
           else:
              relevant["links"].append(link)

        relevant["forms"] = parsed_data.get("forms", [])
        relevant["textareas"] = parsed_data.get("textareas", [])
        relevant["selects"] = parsed_data.get("selects", [])


# ================= FORM PAGE =================

    elif page_type == "form_page":

        # INPUTS (sans boutons)
        relevant["inputs"] = [
            item for item in parsed_data.get("inputs", [])
            if is_real_input(item) and is_not_noise(item)
        ]

        # BUTTONS (<button>)
        for item in parsed_data.get("buttons", []):
            if is_not_noise(item):
                if is_cta_button(item):
                    item["semantic_type"] = "cta_button"
                relevant["buttons"].append(item)

        # BUTTONS (input submit/button)
        for item in parsed_data.get("other_inputs", []):
            if is_button_input(item) and is_not_noise(item):
                relevant["buttons"].append(item)

        relevant["forms"] = parsed_data.get("forms", [])
        relevant["textareas"] = parsed_data.get("textareas", [])
        relevant["selects"] = parsed_data.get("selects", [])
        for link in parsed_data.get("links", []):
            if not is_not_noise(link):
               continue

            href = (link.get("href") or "").lower()

            if "logout" in href:
                continue

            if is_navigation_link(link) or is_pagination_link(link):
               link["semantic_type"] = "navigation"

            relevant["links"].append(link)

    # ================= CHOICE FORM =================
    elif page_type == "choice_form_page":

        relevant["inputs"] = [
            item for item in (
                parsed_data.get("radio_inputs", []) +
                parsed_data.get("checkbox_inputs", [])
            )
            if is_not_noise(item)
        ]

        for item in parsed_data.get("buttons", []):
            if is_not_noise(item):
                relevant["buttons"].append(item)

        for item in parsed_data.get("other_inputs", []):
            if is_button_input(item) and is_not_noise(item):
                relevant["buttons"].append(item)
        
        for link in parsed_data.get("links", []):
            if not is_not_noise(link):
                continue
            href = (link.get("href") or "").lower()
            if "logout" in href:
                continue
            text = (link.get("text") or "").lower()
            if (
                is_navigation_link(link)
                or is_pagination_link(link)
                or text in ["view", "details", "detail"]
                or "view" in text
                or "details" in text
                or "detail" in text
            ):
                link["semantic_type"] = "detail_or_navigation"
            relevant["links"].append(link)    
        relevant["forms"] = parsed_data.get("forms", [])

    # ================= DEFAULT =================
    else:

        relevant["inputs"] = [
            item for item in parsed_data.get("inputs", [])
            if is_real_input(item) and is_not_noise(item)
        ]

        for item in parsed_data.get("buttons", []):
            if is_not_noise(item):
                if is_cta_button(item):
                    item["semantic_type"] = "cta_button"
                relevant["buttons"].append(item)


        for item in parsed_data.get("other_inputs", []):
            if is_button_input(item) and is_not_noise(item):
                relevant["buttons"].append(item)

        for link in parsed_data.get("links", []):
            if not is_not_noise(link):
               continue

            href = (link.get("href") or "").lower()

            if "logout" in href:
                continue

            if is_navigation_link(link) or is_pagination_link(link):
               link["semantic_type"] = "navigation"

            relevant["links"].append(link)
            
        relevant["forms"] = parsed_data.get("forms", [])
        relevant["textareas"] = parsed_data.get("textareas", [])
        relevant["selects"] = parsed_data.get("selects", [])

    # 🔥 SUPPRESSION DES DOUBLONS (IMPORTANT)
    relevant["buttons"] = remove_duplicate_buttons(relevant["buttons"])

    return relevant

def detect_semantic_actions(relevant_data):
    """
    Détecte des actions métier générales à partir de la structure DOM.
    Sans dépendre d'un site précis.
    """

    actions = []

    inputs = relevant_data.get("inputs", [])
    buttons = relevant_data.get("buttons", [])
    links = relevant_data.get("links", [])
    forms = relevant_data.get("forms", [])
    textareas = relevant_data.get("textareas", [])
    selects = relevant_data.get("selects", [])

    # 1. Formulaire détecté
    if forms or inputs or textareas:
        actions.append({
            "type": "form_interaction",
            "reason": "La page contient des champs ou un formulaire.",
            "elements_count": len(inputs) + len(textareas)
        })

    # 2. Soumission possible
    if (forms or inputs or textareas) and buttons:
        actions.append({
            "type": "submit_action",
            "reason": "La page contient des champs et au moins un bouton d'action.",
            "elements_count": len(buttons)
        })

    # 3. Filtres détectés
    if selects:
        select_filters = []
        for select in selects:
            label = (
                select.get("aria_label")
                or select.get("name")
                or select.get("id")
                or "select_filter"
            )
            options = []
            for option in select.get("options", []):
                text = option.get("text")
                if text:
                    options.append(text)
            select_filters.append({
                "label": label,
                "options": options[:20]
            })

        actions.append({
            "type": "select_filter_action",
            "reason": "La page contient une ou plusieurs listes déroulantes.",
            "elements_count": len(selects),
            "filters": select_filters
        })

    checkbox_count = sum(
        1 for item in inputs
        if (item.get("type") or "").lower() == "checkbox"
    )

    radio_count = sum(
        1 for item in inputs
        if (item.get("type") or "").lower() == "radio"
    )

    radio_options = []
    checkbox_options = []

    for item in inputs:
        input_type = (item.get("type") or "").lower()
        label = (
            item.get("aria_label")
            or item.get("value")
            or item.get("name")
            or item.get("id")
            or "option"
        )
        if input_type == "radio":
            radio_options.append(label)
        elif input_type == "checkbox":
            checkbox_options.append(label)
    if checkbox_count > 0 or radio_count > 0:
        actions.append({
            "type": "choice_filter_action",
            "reason": "La page contient des radio buttons ou des checkboxes.",
            "radio_count": radio_count,
            "checkbox_count": checkbox_count,
            "radio_options": radio_options[:20],
            "checkbox_options": checkbox_options[:20]
        })

    # 4. Navigation interne détectée
    internal_links = [
        link for link in links
        if link.get("href")
    ]
    link_labels = []
    for link in internal_links:
        text = (link.get("text") or "").strip()
        if text:
            link_labels.append(text)


    if internal_links:
        actions.append({
            "type": "navigation_action",
            "reason": "La page contient des liens navigables.",
            "elements_count": len(internal_links),
            "sample_labels": link_labels[:15]
        })
    
    detail_labels = []
    for link in internal_links:
        text = (link.get("text") or "").strip()
        normalized_text = text.lower()
        if any(keyword in normalized_text for keyword in [
            "view",
            "details",
            "detail",
            "read more",
            "learn more",
            "enroll",
            "open",
            "see more"
        ]):
           detail_labels.append(text)
    if detail_labels:
        actions.append({
            "type": "detail_navigation",
            "reason": "La page contient des liens qui mènent probablement vers des détails, articles, cours ou contenus approfondis.",
            "elements_count": len(detail_labels),
            "sample_labels": detail_labels[:15]
        })

    # 5. Navigation répétée type tableau/liste
    link_texts = {}

    for link in links:
        text = (link.get("text") or "").strip().lower()

        if not text:
            continue

        link_texts[text] = link_texts.get(text, 0) + 1

    repeated_links = [
        text for text, count in link_texts.items()
        if count >= 2
    ]

    if repeated_links:
        actions.append({
            "type": "repeated_detail_navigation",
            "reason": "La page contient plusieurs liens similaires, probablement une liste ou un tableau.",
            "repeated_labels": repeated_links[:5]
        })

    # 6. Actions utilisateur par boutons
    button_labels = []
    for btn in buttons:
        label = (
            btn.get("text")
            or btn.get("value")
            or ""
        ).strip()
        if label:
            button_labels.append(label)
    if buttons:
        actions.append({
            "type": "button_action",
            "reason": "La page contient des boutons cliquables.",
            "elements_count": len(buttons),
            "sample_labels": button_labels[:10]
        })
     
        normalized_button_labels = [
            (
                btn.get("text")
                or btn.get("value")
                or ""
            ).strip().lower()
            for btn in buttons
        ]
        
        workflow_keywords = [
            "add",
            "edit",
            "create",
            "new",
            "update"
        ]
        if any(label in workflow_keywords for label in normalized_button_labels):

            actions.append({
                "type": "multi_step_workflow",
                "reason": "La page contient une action pouvant déclencher un workflow dynamique.",
                "trigger_buttons": button_labels[:10]
            })

    # 7. Plusieurs boutons = workflow possible
    if len(buttons) >= 2:
        actions.append({
            "type": "multi_step_interaction",
            "reason": "La page contient plusieurs boutons, ce qui peut indiquer un workflow utilisateur.",
            "elements_count": len(buttons)
        })

    return actions