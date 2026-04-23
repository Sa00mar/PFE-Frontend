def classify_page(parsed_data):
    """
    Détecte le type fonctionnel de la page
    à partir des éléments extraits du DOM.
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

    # ---------------- LOGIN PAGE ----------------
    if len(password_inputs) > 0 and (len(text_inputs) > 0 or len(email_inputs) > 0):
        return "login_page"

    # ---------------- SIMPLE FORM PAGE ----------------
    if len(forms) > 0 and (
        len(text_inputs) > 0 or
        len(email_inputs) > 0 or
        len(textareas) > 0 or
        len(selects) > 0
    ):
        return "form_page"

    # ---------------- CHOICE FORM PAGE ----------------
    if len(radio_inputs) > 0 or len(checkbox_inputs) > 0:
        return "choice_form_page"

    # ---------------- BUTTON ONLY PAGE ----------------
    if len(buttons) > 0 and len(forms) == 0:
        return "action_page"

    # ---------------- DEFAULT ----------------
    return "unknown"