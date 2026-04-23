from bs4 import BeautifulSoup


def parse_html(html):
    """
    Analyse le HTML et extrait les informations utiles :
    - titre
    - inputs
    - buttons
    - forms
    - links
    - textareas
    - selects

    Et classe les inputs par type :
    - text_inputs
    - email_inputs
    - password_inputs
    - radio_inputs
    - checkbox_inputs
    - other_inputs
    """

    soup = BeautifulSoup(html, 'html.parser')

    # ---------------- TITLE ----------------
    title = soup.title.string.strip() if soup.title and soup.title.string else "No title"

    # ---------------- INPUTS ----------------
    inputs = []
    text_inputs = []
    email_inputs = []
    password_inputs = []
    radio_inputs = []
    checkbox_inputs = []
    other_inputs = []

    for input_tag in soup.find_all('input'):
        input_data = {
            "tag": "input",
            "type": input_tag.get("type"),
            "id": input_tag.get("id"),
            "name": input_tag.get("name"),
            "class": " ".join(input_tag.get("class", [])),
            "placeholder": input_tag.get("placeholder"),
            "value": input_tag.get("value"),
            "aria_label": input_tag.get("aria-label")
        }

        inputs.append(input_data)

        input_type = (input_tag.get("type") or "text").lower()

        if input_type == "text":
            text_inputs.append(input_data)
        elif input_type == "email":
            email_inputs.append(input_data)
        elif input_type == "password":
            password_inputs.append(input_data)
        elif input_type == "radio":
            radio_inputs.append(input_data)
        elif input_type == "checkbox":
            checkbox_inputs.append(input_data)
        else:
            other_inputs.append(input_data)

    # ---------------- BUTTONS ----------------
    buttons = []
    for button_tag in soup.find_all('button'):
        buttons.append({
            "tag": "button",
            "type": button_tag.get("type"),
            "id": button_tag.get("id"),
            "name": button_tag.get("name"),
            "class": " ".join(button_tag.get("class", [])),
            "text": button_tag.get_text(strip=True),
            "aria_label": button_tag.get("aria-label")
        })

    # ---------------- FORMS ----------------
    forms = []
    for form_tag in soup.find_all('form'):
        forms.append({
            "tag": "form",
            "id": form_tag.get("id"),
            "name": form_tag.get("name"),
            "class": " ".join(form_tag.get("class", [])),
            "method": form_tag.get("method"),
            "action": form_tag.get("action"),
            "aria_label": form_tag.get("aria-label")
        })

    # ---------------- LINKS ----------------
    links = []
    for link_tag in soup.find_all('a'):
        links.append({
            "tag": "a",
            "id": link_tag.get("id"),
            "class": " ".join(link_tag.get("class", [])),
            "href": link_tag.get("href"),
            "text": link_tag.get_text(strip=True),
            "aria_label": link_tag.get("aria-label")
        })

    # ---------------- TEXTAREAS ----------------
    textareas = []
    for textarea_tag in soup.find_all('textarea'):
        textareas.append({
            "tag": "textarea",
            "id": textarea_tag.get("id"),
            "name": textarea_tag.get("name"),
            "class": " ".join(textarea_tag.get("class", [])),
            "placeholder": textarea_tag.get("placeholder"),
            "text": textarea_tag.get_text(strip=True),
            "aria_label": textarea_tag.get("aria-label")
        })

    # ---------------- SELECTS ----------------
    selects = []
    for select_tag in soup.find_all('select'):
        options = []

        for option_tag in select_tag.find_all('option'):
            options.append({
                "value": option_tag.get("value"),
                "text": option_tag.get_text(strip=True)
            })

        selects.append({
            "tag": "select",
            "id": select_tag.get("id"),
            "name": select_tag.get("name"),
            "class": " ".join(select_tag.get("class", [])),
            "aria_label": select_tag.get("aria-label"),
            "options": options
        })

    return {
        "title": title,
        "inputs": inputs,
        "text_inputs": text_inputs,
        "email_inputs": email_inputs,
        "password_inputs": password_inputs,
        "radio_inputs": radio_inputs,
        "checkbox_inputs": checkbox_inputs,
        "other_inputs": other_inputs,
        "buttons": buttons,
        "forms": forms,
        "links": links,
        "textareas": textareas,
        "selects": selects
    }