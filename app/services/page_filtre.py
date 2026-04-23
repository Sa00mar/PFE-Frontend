def filter_relevant_elements(parsed_data, page_type):
    """
    Filtre les éléments les plus utiles selon le type de page.
    """

    relevant = {
        "inputs": [],
        "buttons": [],
        "links": [],
        "forms": [],
        "textareas": [],
        "selects": []
    }

    if page_type == "login_page":
        # garder les champs texte/email liés au login
        for item in parsed_data.get("text_inputs", []):
            name = (item.get("name") or "").lower()
            item_id = (item.get("id") or "").lower()

            if "email" in name or "user" in name or "login" in name or \
               "email" in item_id or "user" in item_id or "login" in item_id:
                relevant["inputs"].append(item)

        # garder password
        for item in parsed_data.get("password_inputs", []):
            relevant["inputs"].append(item)

        # garder checkbox remember me
        for item in parsed_data.get("checkbox_inputs", []):
            name = (item.get("name") or "").lower()
            item_id = (item.get("id") or "").lower()

            if "remember" in name or "remember" in item_id:
                relevant["inputs"].append(item)

        # garder boutons utiles parmi les autres inputs
        for item in parsed_data.get("other_inputs", []):
            value = (item.get("value") or "").lower()
            item_class = (item.get("class") or "").lower()

            if "log in" in value or "login" in value or "login" in item_class:
                relevant["buttons"].append(item)

        # garder formulaires login
        for form in parsed_data.get("forms", []):
            action = (form.get("action") or "").lower()
            if "login" in action:
                relevant["forms"].append(form)

        # garder liens forgot password / register
        for link in parsed_data.get("links", []):
            text = (link.get("text") or "").lower()
            href = (link.get("href") or "").lower()

            if "forgot" in text or "forgot" in href or "register" in text or "register" in href:
                relevant["links"].append(link)

    elif page_type == "form_page":
        relevant["inputs"] = parsed_data.get("inputs", [])
        relevant["buttons"] = parsed_data.get("buttons", []) + parsed_data.get("other_inputs", [])
        relevant["forms"] = parsed_data.get("forms", [])
        relevant["textareas"] = parsed_data.get("textareas", [])
        relevant["selects"] = parsed_data.get("selects", [])

    elif page_type == "choice_form_page":
        relevant["inputs"] = (
            parsed_data.get("radio_inputs", []) +
            parsed_data.get("checkbox_inputs", [])
        )
        relevant["buttons"] = parsed_data.get("buttons", []) + parsed_data.get("other_inputs", [])
        relevant["forms"] = parsed_data.get("forms", [])

    else:
        relevant["inputs"] = parsed_data.get("inputs", [])
        relevant["buttons"] = parsed_data.get("buttons", []) + parsed_data.get("other_inputs", [])
        relevant["links"] = parsed_data.get("links", [])
        relevant["forms"] = parsed_data.get("forms", [])
        relevant["textareas"] = parsed_data.get("textareas", [])
        relevant["selects"] = parsed_data.get("selects", [])

    return relevant