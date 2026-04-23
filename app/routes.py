from flask import Blueprint, render_template, request, redirect, url_for, session
from app.models import get_user_by_login, create_user, create_analysis 
from .models import get_analysis_status
import threading
import time
from app.models import update_analysis_status
from app.models import get_analysis_by_id
from app.services.page_fetcher import fetch_page_html
from flask import jsonify
from app.services.html_parser import parse_html
from app.services.page_classifier import classify_page
from app.services.page_filtre import filter_relevant_elements
main = Blueprint('main', __name__)

# ---------------- HOME ----------------
@main.route('/')
def index():
    return redirect(url_for('main.login'))


# ---------------- LOGIN ----------------
@main.route('/login', methods=['GET', 'POST'])
def login():
    error = None

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = get_user_by_login(email, password)

        if user:
            session['user_id'] = user[0]      # id
            session['username'] = user[1]     # username

            return redirect(url_for('main.home'))
        else:
            error = "Login incorrect"

    return render_template('login.html', error=error)


# ---------------- REGISTER ----------------
@main.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    success = None

   
    if request.method == 'POST':
       firstname = request.form.get('firstname')
       lastname = request.form.get('lastname')
       email = request.form.get('email')
       password = request.form.get('password')
       confirm_password = request.form.get('confirm_password')

       username = f"{firstname} {lastname}"

       if not all([firstname, lastname, email, password, confirm_password]):
          error = "Tous les champs sont obligatoires"

       elif password != confirm_password:
           error = "Les mots de passe ne correspondent pas"

       elif len(password) < 6:
           error = "Mot de passe trop court"

       else:
           create_user(username, email, password)
           return redirect(url_for('main.login'))
    
    return render_template('register.html', error=error, success=success)


# ---------------- HOME ----------------
@main.route('/home')
def home():
    if 'user_id' not in session:
        return redirect(url_for('main.login'))

    return render_template('home.html')


# ---------------- LOGOUT ----------------
@main.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect(url_for('main.login'))

# ---------------- NewTest ----------------
@main.route('/new_test', methods=['GET', 'POST'])
def new_test():
    if 'user_id' not in session:
        return redirect(url_for('main.login'))

    if request.method == 'POST':
        url = request.form.get('url')
        if not url:
            return render_template('new_test.html', error="URL obligatoire")

        user_id = session['user_id']

        # INSERT DATABASE
        analysis_id = create_analysis(user_id, url, "pending")
        # START BACKGROUND PROCESS
        threading.Thread(
            target=process_analysis,
            args=(analysis_id, url)
        ).start()
        return redirect(url_for('main.loading', analysis_id=analysis_id))

    return render_template('new_test.html')
# ---------------- MyTests ----------------
@main.route('/my_tests')
def my_tests():
    if 'user_id' not in session:
        return redirect(url_for('main.login'))

    return render_template('my_tests.html')

# ---------------- Settings ----------------
@main.route('/settings')
def settings():
    if 'user_id' not in session:
        return redirect(url_for('main.login'))

    return render_template('settings.html')


# ---------------- analysis_result ----------------
@main.route('/analysis_result/<int:analysis_id>')
def analysis_result(analysis_id):
    # sécurité
    if 'user_id' not in session:
        return redirect(url_for('main.login'))

    # afficher résultat avec ID
    return render_template('analysis_result.html', analysis_id=analysis_id)


# ---------------- test_results ----------------
@main.route('/test_results/<int:analysis_id>')
def test_results(analysis_id):
    if 'user_id' not in session:
        return redirect(url_for('main.login'))

    analysis = get_analysis_by_id(analysis_id)

    if not analysis:
        return "Analysis not found", 404

    data = {
        "id": analysis[0],
        "url": analysis[1],
        "status": analysis[2],
        "created_at": analysis[3],
        "stats": {
            "pass": 0,
            "fail": 0,
            "warning": 0,
            "total": 0
        },
        "results": []
    }

    return render_template('test_results.html', data=data)

# ---------------- Loading ----------------
@main.route('/loading/<int:analysis_id>')
def loading(analysis_id):
    return render_template('loading.html', analysis_id=analysis_id)

# ---------------- CheckStatusS ----------------
@main.route('/check_status/<int:analysis_id>')
def check_status(analysis_id):
    status = get_analysis_status(analysis_id)
    return {"status": status}

def process_analysis(analysis_id, url):
    result = fetch_page_html(url)

    if result["success"]:
        html = result["html"]

        print(f"[INFO] HTML récupéré pour analysis_id={analysis_id}")

        parsed_data = parse_html(html)
        page_type = classify_page(parsed_data)

        relevant_data = filter_relevant_elements(parsed_data, page_type)

        print("\nPAGE TYPE :", page_type)
        pretty_print_relevant_data(relevant_data)
        update_analysis_status(analysis_id, "completed")
    else:
        print(f"[ERROR] Échec récupération page pour analysis_id={analysis_id}")
        print(result["error"])

        update_analysis_status(analysis_id, "failed")

# ---------------- validateUrl ----------------
@main.route('/validate_url', methods=['POST'])
def validate_url():
    if 'user_id' not in session:
        return jsonify({
            "success": False,
            "message": "Utilisateur non connecté."
        }), 401

    url = request.form.get('url')

    if not url:
        return jsonify({
            "success": False,
            "message": "URL obligatoire."
        }), 400

    result = fetch_page_html(url)

    if result["success"]:
        return jsonify({
            "success": True,
            "message": "URL valide et page accessible."
        })
    else:
        return jsonify({
            "success": False,
            "message": result["error"]
        }), 400

# ---------------- clarifier texte output ----------------

def pretty_print_elements(title, elements):
    print("\n" + "="*20 + f" {title} " + "="*20)

    if not elements:
        print("Aucun élément trouvé")
        return

    for i, el in enumerate(elements, start=1):
        print(f"[{i}] ", end="")

        # afficher les infos principales
        info = []

        if el.get("type"):
            info.append(f"type={el.get('type')}")

        if el.get("name"):
            info.append(f"name={el.get('name')}")

        if el.get("id"):
            info.append(f"id={el.get('id')}")

        if el.get("text"):
            info.append(f"text={el.get('text')}")

        if el.get("href"):
            info.append(f"href={el.get('href')}")
        if el.get("method"):
            info.append(f"method={el.get('method')}")

        if el.get("action"):
            info.append(f"action={el.get('action')}")

        if el.get("value"):
            info.append(f"value={el.get('value')}")

        if el.get("class"):
            info.append(f"class={el.get('class')}")

        print(" | ".join(info))
        
# ---------------- clarification output ----------------

def pretty_print_relevant_data(relevant_data):
    print("\n" + "=" * 20 + " RELEVANT ELEMENTS " + "=" * 20)

    pretty_print_elements("RELEVANT INPUTS", relevant_data["inputs"])
    pretty_print_elements("RELEVANT BUTTONS", relevant_data["buttons"])
    pretty_print_elements("RELEVANT LINKS", relevant_data["links"])
    pretty_print_elements("RELEVANT FORMS", relevant_data["forms"])
    pretty_print_elements("RELEVANT TEXTAREAS", relevant_data["textareas"])
    pretty_print_elements("RELEVANT SELECTS", relevant_data["selects"])