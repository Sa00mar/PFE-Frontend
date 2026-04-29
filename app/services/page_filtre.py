def is_not_noise(item):
    name = (item.get("name") or "").lower()
    item_id = (item.get("id") or "").lower()
    item_class = (item.get("class") or "").lower()
    value = (item.get("value") or "").lower()
    text = (item.get("text") or "").lower()

    return not (
        "newsletter" in name or
        "newsletter" in item_id or
        "newsletter" in item_class or
        "newsletter" in value or
        "newsletter" in text or
        "search" in name or
        "search" in item_id or
        "search" in item_class or
        "search store" in value
    )


def is_button_input(item):
    input_type = (item.get("type") or "").lower()
    return input_type in ["submit", "button"]


def is_real_input(item):
    input_type = (item.get("type") or "").lower()
    return input_type not in ["submit", "button", "hidden"]


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

            if "log in" in value or "login" in value or "login" in item_class:
                relevant["buttons"].append(item)

        # BUTTONS (<button>)
        for item in parsed_data.get("buttons", []):
            text = (item.get("text") or "").lower()
            item_class = (item.get("class") or "").lower()

            if not is_not_noise(item):
                continue

            if "log in" in text or "login" in text or "login" in item_class:
                relevant["buttons"].append(item)

        # FORMS
        for form in parsed_data.get("forms", []):
            action = (form.get("action") or "").lower()

            if "login" in action:
                relevant["forms"].append(form)

        # LINKS
        for link in parsed_data.get("links", []):
            text = (link.get("text") or "").lower()
            href = (link.get("href") or "").lower()

            if (
                "forgot" in text or
                "forgot" in href or
                "register" in text or
                "register" in href
            ):
                relevant["links"].append(link)

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
                relevant["buttons"].append(item)

        # BUTTONS (input submit/button)
        for item in parsed_data.get("other_inputs", []):
            if is_button_input(item) and is_not_noise(item):
                relevant["buttons"].append(item)

        relevant["forms"] = parsed_data.get("forms", [])
        relevant["textareas"] = parsed_data.get("textareas", [])
        relevant["selects"] = parsed_data.get("selects", [])

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

        relevant["forms"] = parsed_data.get("forms", [])

    # ================= DEFAULT =================
    else:

        relevant["inputs"] = [
            item for item in parsed_data.get("inputs", [])
            if is_real_input(item) and is_not_noise(item)
        ]

        for item in parsed_data.get("buttons", []):
            if is_not_noise(item):
                relevant["buttons"].append(item)

        for item in parsed_data.get("other_inputs", []):
            if is_button_input(item) and is_not_noise(item):
                relevant["buttons"].append(item)

        relevant["links"] = parsed_data.get("links", [])
        relevant["forms"] = parsed_data.get("forms", [])
        relevant["textareas"] = parsed_data.get("textareas", [])
        relevant["selects"] = parsed_data.get("selects", [])

    # 🔥 SUPPRESSION DES DOUBLONS (IMPORTANT)
    relevant["buttons"] = remove_duplicate_buttons(relevant["buttons"])

    return relevant