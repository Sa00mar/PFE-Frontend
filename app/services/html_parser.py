# pyrefly: ignore [missing-import]
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

    soup = BeautifulSoup(html, "html.parser")

    # ---------------- VISIBLE TEXT ----------------
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    visible_text = soup.get_text(" ", strip=True)

    # ---------------- TITLE ----------------
    title = (
        soup.title.string.strip() if soup.title and soup.title.string else "No title"
    )

    # ---------------- INPUTS ----------------
    inputs = []
    text_inputs = []
    email_inputs = []
    password_inputs = []
    radio_inputs = []
    checkbox_inputs = []
    other_inputs = []

    for input_tag in soup.find_all("input"):
        input_data = {
            "tag": "input",
            "type": input_tag.get("type") or "text",
            "id": input_tag.get("id"),
            "name": input_tag.get("name"),
            "class": " ".join(input_tag.get("class", [])),
            "placeholder": input_tag.get("placeholder"),
            "value": input_tag.get("value"),
            "aria_label": input_tag.get("aria-label"),
            "required": input_tag.has_attr("required"),
            "maxlength": input_tag.get("maxlength"),
            "minlength": input_tag.get("minlength"),
            "pattern": input_tag.get("pattern"),
            "autocomplete": input_tag.get("autocomplete"),
            "disabled": input_tag.has_attr("disabled"),
            "readonly": input_tag.has_attr("readonly"),
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
    for button_tag in soup.find_all("button"):
        buttons.append(
            {
                "tag": "button",
                "type": button_tag.get("type"),
                "id": button_tag.get("id"),
                "name": button_tag.get("name"),
                "class": " ".join(button_tag.get("class", [])),
                "text": button_tag.get_text(strip=True),
                "aria_label": button_tag.get("aria-label"),
            }
        )

    # ---------------- FORMS ----------------
    forms = []

    for form_tag in soup.find_all("form"):
        form_inputs = []
        for input_tag in form_tag.find_all("input"):
            form_inputs.append(
                {
                    "tag": "input",
                    "type": input_tag.get("type") or "text",
                    "id": input_tag.get("id"),
                    "name": input_tag.get("name"),
                    "class": " ".join(input_tag.get("class", [])),
                    "placeholder": input_tag.get("placeholder"),
                    "value": input_tag.get("value"),
                    "aria_label": input_tag.get("aria-label"),
                    "required": input_tag.has_attr("required"),
                    "maxlength": input_tag.get("maxlength"),
                    "minlength": input_tag.get("minlength"),
                    "pattern": input_tag.get("pattern"),
                    "autocomplete": input_tag.get("autocomplete"),
                    "disabled": input_tag.has_attr("disabled"),
                    "readonly": input_tag.has_attr("readonly"),
                }
            )

        form_buttons = []
        for button_tag in form_tag.find_all("button"):
            form_buttons.append(
                {
                    "tag": "button",
                    "type": button_tag.get("type"),
                    "id": button_tag.get("id"),
                    "name": button_tag.get("name"),
                    "class": " ".join(button_tag.get("class", [])),
                    "text": button_tag.get_text(strip=True),
                    "aria_label": button_tag.get("aria-label"),
                }
            )

        form_textareas = []
        for textarea_tag in form_tag.find_all("textarea"):
            form_textareas.append(
                {
                    "tag": "textarea",
                    "id": textarea_tag.get("id"),
                    "name": textarea_tag.get("name"),
                    "class": " ".join(textarea_tag.get("class", [])),
                    "placeholder": textarea_tag.get("placeholder"),
                    "text": textarea_tag.get_text(strip=True),
                    "aria_label": textarea_tag.get("aria-label"),
                    "required": textarea_tag.has_attr("required"),
                    "maxlength": textarea_tag.get("maxlength"),
                    "minlength": textarea_tag.get("minlength"),
                    "disabled": textarea_tag.has_attr("disabled"),
                    "readonly": textarea_tag.has_attr("readonly"),
                }
            )

        form_selects = []
        for select_tag in form_tag.find_all("select"):
            options = []

            for option_tag in select_tag.find_all("option"):
                options.append(
                    {
                        "value": option_tag.get("value"),
                        "text": option_tag.get_text(strip=True),
                    }
                )

            form_selects.append(
                {
                    "tag": "select",
                    "id": select_tag.get("id"),
                    "name": select_tag.get("name"),
                    "class": " ".join(select_tag.get("class", [])),
                    "aria_label": select_tag.get("aria-label"),
                    "required": select_tag.has_attr("required"),
                    "disabled": select_tag.has_attr("disabled"),
                    "options": options,
                }
            )

        forms.append(
            {
                "tag": "form",
                "id": form_tag.get("id"),
                "name": form_tag.get("name"),
                "class": " ".join(form_tag.get("class", [])),
                "method": form_tag.get("method"),
                "action": form_tag.get("action"),
                "aria_label": form_tag.get("aria-label"),
                "inputs": form_inputs,
                "buttons": form_buttons,
                "textareas": form_textareas,
                "selects": form_selects,
                "fields_count": len(form_inputs)
                + len(form_textareas)
                + len(form_selects),
                "buttons_count": len(form_buttons),
            }
        )
    # --------------- LINKS ----------------
    links = []
    for link_tag in soup.find_all("a"):
        href = link_tag.get("href")
        text = link_tag.get_text(strip=True)

        if not href:
            continue
        if href.startswith("#"):
            continue
        if href.startswith("javascript"):
            continue
        if href.startswith("mailto"):
            continue
        if href.startswith("tel"):
            continue

        links.append(
            {
                "tag": "a",
                "id": link_tag.get("id"),
                "class": " ".join(link_tag.get("class", [])),
                "href": href,
                "text": text,
                "aria_label": link_tag.get("aria-label"),
                "target": link_tag.get("target"),
                "is_clickable": bool(href),
                "has_visible_text": bool(text),
                "role": link_tag.get("role"),
            }
        )

    # ---------------- TEXTAREAS ----------------
    textareas = []
    for textarea_tag in soup.find_all("textarea"):
        textareas.append(
            {
                "tag": "textarea",
                "id": textarea_tag.get("id"),
                "name": textarea_tag.get("name"),
                "class": " ".join(textarea_tag.get("class", [])),
                "placeholder": textarea_tag.get("placeholder"),
                "text": textarea_tag.get_text(strip=True),
                "aria_label": textarea_tag.get("aria-label"),
            }
        )

    # ---------------- SELECTS ----------------
    selects = []
    for select_tag in soup.find_all("select"):
        options = []

        for option_tag in select_tag.find_all("option"):
            options.append(
                {
                    "value": option_tag.get("value"),
                    "text": option_tag.get_text(strip=True),
                }
            )

        selects.append(
            {
                "tag": "select",
                "id": select_tag.get("id"),
                "name": select_tag.get("name"),
                "class": " ".join(select_tag.get("class", [])),
                "aria_label": select_tag.get("aria-label"),
                "options": options,
            }
        )

    return {
        "title": title,
        "visible_text": visible_text,
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
        "selects": selects,
    }
