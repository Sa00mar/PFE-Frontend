from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    session,
    jsonify,
)
import threading

from app.models import (
    get_user_by_login,
    create_user,
    create_analysis,
    get_analysis_status,
    update_analysis_status,
    get_analysis_by_id,
    save_test_cases,
    get_test_cases_by_analysis,
    update_test_status,
    get_executed_results_by_analysis,
    get_next_version,
    create_result,
    delete_results_by_analysis,
)

from app.services.page_fetcher import fetch_page_html
from app.services.custom_ia_engine import generate_tests_with_custom_engine
from app.services.site_crawler import crawl_important_pages
from app.services.multi_page_analyzer import merge_relevant_data
from app.services.feature_detector import detect_features
from app.services.selenium_executor import execute_selenium_script

main = Blueprint("main", __name__)


# =========================================================
# HOME
# =========================================================


@main.route("/")
def index():
    return redirect(url_for("main.login"))


# =========================================================
# LOGIN
# =========================================================


@main.route("/login", methods=["GET", "POST"])
def login():

    error = None

    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        user = get_user_by_login(email, password)

        if user:
            session["user_id"] = user[0]
            session["username"] = user[1]

            return redirect(url_for("main.home"))

        error = "Login incorrect"

    return render_template("login.html", error=error)


# =========================================================
# REGISTER
# =========================================================


@main.route("/register", methods=["GET", "POST"])
def register():

    error = None
    success = None

    if request.method == "POST":
        firstname = request.form.get("firstname")
        lastname = request.form.get("lastname")
        email = request.form.get("email")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        username = f"{firstname} {lastname}"

        if not all([firstname, lastname, email, password, confirm_password]):
            error = "Tous les champs sont obligatoires"

        elif password != confirm_password:
            error = "Les mots de passe ne correspondent pas"

        elif len(password) < 6:
            error = "Mot de passe trop court"

        else:
            create_user(username, email, password)

            return redirect(url_for("main.login"))

    return render_template("register.html", error=error, success=success)


# =========================================================
# HOME PAGE
# =========================================================


@main.route("/home")
def home():

    if "user_id" not in session:
        return redirect(url_for("main.login"))

    return render_template("home.html")


# =========================================================
# LOGOUT
# =========================================================


@main.route("/logout", methods=["POST"])
def logout():

    session.clear()

    return redirect(url_for("main.login"))


# =========================================================
# NEW TEST
# =========================================================


@main.route("/new_test", methods=["GET", "POST"])
def new_test():

    if "user_id" not in session:
        return redirect(url_for("main.login"))

    if request.method == "POST":
        url = request.form.get("target_url")

        auth_required = request.form.get("auth_required")

        login_email = request.form.get("login_email")
        login_password = request.form.get("login_password")

        if not url:
            return render_template("new_test.html", error="URL obligatoire")

        user_id = session["user_id"]

        analysis_id = create_analysis(user_id, url, "pending")

        threading.Thread(
            target=process_analysis,
            args=(analysis_id, url, auth_required, login_email, login_password),
        ).start()

        return redirect(url_for("main.loading", analysis_id=analysis_id))

    return render_template("new_test.html")


# =========================================================
# MY TESTS
# =========================================================


@main.route("/my_tests")
def my_tests():

    if "user_id" not in session:
        return redirect(url_for("main.login"))

    return render_template("my_tests.html")


# =========================================================
# SETTINGS
# =========================================================


@main.route("/settings")
def settings():

    if "user_id" not in session:
        return redirect(url_for("main.login"))

    return render_template("settings.html")


# =========================================================
# ANALYSIS RESULT
# =========================================================


@main.route("/analysis_result/<int:analysis_id>")
def analysis_result(analysis_id):

    if "user_id" not in session:
        return redirect(url_for("main.login"))

    test_cases = get_test_cases_by_analysis(analysis_id)

    return render_template(
        "analysis_result.html", analysis_id=analysis_id, test_cases=test_cases
    )


# =========================================================
# TEST RESULTS
# =========================================================


@main.route("/test_results/<int:analysis_id>")
def test_results(analysis_id):

    if "user_id" not in session:
        return redirect(url_for("main.login"))

    analysis = get_analysis_by_id(analysis_id)

    if not analysis:
        return "Analysis not found", 404

    executed_results = get_executed_results_by_analysis(analysis_id)

    passed = sum(1 for test in executed_results if test["status"] == "passed")

    failed = sum(1 for test in executed_results if test["status"] == "failed")

    pending = sum(1 for test in executed_results if test["status"] == "pending")
    total = len(executed_results)

    data = {
        "id": analysis[0],
        "url": analysis[1],
        "status": analysis[2],
        "created_at": analysis[3],
        "stats": {"pass": passed, "fail": failed, "warning": pending, "total": total},
        "results": executed_results,
    }

    return render_template("test_results.html", data=data)


# =========================================================
# LOADING PAGE
# =========================================================


@main.route("/loading/<int:analysis_id>")
def loading(analysis_id):

    return render_template("loading.html", analysis_id=analysis_id)


# =========================================================
# CHECK STATUS
# =========================================================


@main.route("/check_status/<int:analysis_id>")
def check_status(analysis_id):

    status = get_analysis_status(analysis_id)

    return {"status": status}


# =========================================================
# PRETTY PRINT TEST CASES
# =========================================================


def pretty_print_test_cases(test_cases):

    print("\n==================== TEST CASES ====================\n")

    for i, tc in enumerate(test_cases, start=1):
        print(f"TEST #{i}")

        print("Title :", tc.get("title"))
        print("Description :", tc.get("description"))
        print("Steps :", tc.get("steps"))
        print("Expected :", tc.get("expected_result"))

        print("-" * 50)


# =========================================================
# PROCESS ANALYSIS
# =========================================================


def process_analysis(
    analysis_id, url, auth_required=None, login_email=None, login_password=None
):

    try:
        # ==================================================
        # MODE AUTHENTIFIÉ
        # ==================================================

        if auth_required == "yes":
            from app.services.authenticated_crawler import crawl_authenticated_pages

            print("\n[INFO] Analyse authentifiée activée")

            crawl_result = crawl_authenticated_pages(url, login_email, login_password)

        # ==================================================
        # MODE PUBLIC
        # ==================================================

        else:
            print("\n[INFO] Analyse publique classique")

            crawl_result = crawl_important_pages(url, max_pages=18, max_depth=2)

        # ==================================================
        # VÉRIFICATION DU CRAWL
        # ==================================================

        if not crawl_result["success"]:
            print(f"[ERROR] Échec exploration site pour analysis_id={analysis_id}")
            print(crawl_result["error"])

            update_analysis_status(analysis_id, "failed")

            return

        pages = crawl_result["pages"]

        print(
            f"\n[INFO] {len(pages)} page(s) récupérée(s) pour analysis_id={analysis_id}"
        )

        # ==================================================
        # FUSION MULTI-PAGES
        # ==================================================

        relevant_data = merge_relevant_data(pages)

        # ==================================================
        # FEATURES
        # ==================================================

        features = detect_features(relevant_data)

        relevant_data["features"] = features

        page_type = "multi_page_analysis"

        print("\n==================== FEATURES DETECTED ====================")

        for feature in features:
            print("-", feature)

        print("\nPAGE TYPE :", page_type)

        print("\n==================== PAGES ANALYSÉES ====================")

        for page in relevant_data["pages"]:
            print("-", page["url"], "|", page["page_type"])

        print(
            "\n==================== RÉSUMÉ DES ÉLÉMENTS MULTI-PAGES ===================="
        )

        print("Pages :", len(relevant_data["pages"]))
        print("Inputs :", len(relevant_data["inputs"]))
        print("Buttons :", len(relevant_data["buttons"]))
        print("Links :", len(relevant_data["links"]))
        print("Forms :", len(relevant_data["forms"]))
        print("Textareas :", len(relevant_data["textareas"]))
        print("Selects :", len(relevant_data["selects"]))
        print("Features :", len(features))

        # ==================================================
        # GÉNÉRATION IA
        # ==================================================
        print("\n=== SEMANTIC ACTIONS DETECTED ===")
        for action in relevant_data.get("semantic_actions", []):
            print(action)

        test_generation_result = generate_tests_with_custom_engine(
            page_type, relevant_data, url
        )

        if not test_generation_result["success"]:
            print(
                "[ERROR] Génération des tests échouée :",
                test_generation_result["error"],
            )

            update_analysis_status(analysis_id, "failed")

            return

        test_cases = test_generation_result["test_cases"]

        print("[DEBUG] Nombre de tests générés :", len(test_cases))

        if test_cases:
            print("[DEBUG] Premier test complet :", test_cases[0])

            print("[DEBUG] Clés du premier test :", test_cases[0].keys())

        # ==================================================
        # VERSION
        # ==================================================

        version = get_next_version(url)

        # ==================================================
        # SAVE TESTS
        # ==================================================

        save_test_cases(analysis_id, test_cases, version=version)

        print(
            f"[INFO] {len(test_cases)} cas de test sauvegardés pour analysis_id={analysis_id}"
        )

        print("\nSOURCE GENERATION :", test_generation_result["source"])

        pretty_print_test_cases(test_cases)

        # ==================================================
        # FIN
        # ==================================================

        update_analysis_status(analysis_id, "completed")

    except Exception as e:
        print("[ERROR] Erreur process_analysis :", str(e))

        update_analysis_status(analysis_id, "failed")


# =========================================================
# VALIDATE URL
# =========================================================


@main.route("/validate_url", methods=["POST"])
def validate_url():

    if "user_id" not in session:
        return jsonify({"success": False, "message": "Utilisateur non connecté."}), 401

    url = request.form.get("target_url")

    if not url:
        return jsonify({"success": False, "message": "URL obligatoire."}), 400

    result = fetch_page_html(url)

    if result["success"]:
        return jsonify({"success": True, "message": "URL valide et page accessible."})

    return jsonify({"success": False, "message": result["error"]}), 400


@main.route("/run_tests/<int:analysis_id>", methods=["POST"])
def run_tests(analysis_id):

    if "user_id" not in session:
        return jsonify({"success": False, "message": "Utilisateur non connecté."}), 401

    try:
        analysis = get_analysis_by_id(analysis_id)

        if not analysis:
            return jsonify({"success": False, "message": "Analyse introuvable."}), 404

        url = analysis[1]

        data = request.get_json(silent=True) or {}

        selected_only = data.get("selected_only", False)
        selected_ids = data.get("selected_ids", [])

        selected_ids = [
            int(test_id) for test_id in selected_ids if str(test_id).isdigit()
        ]

        all_test_cases = get_test_cases_by_analysis(analysis_id)

        if not all_test_cases:
            return jsonify(
                {"success": False, "message": "Aucun test trouvé pour cette analyse."}
            ), 404

        if selected_only:
            test_cases = [
                test for test in all_test_cases if int(test["id"]) in selected_ids
            ]
        else:
            test_cases = all_test_cases

        if not test_cases:
            return jsonify(
                {"success": False, "message": "Aucun test sélectionné valide."}
            ), 400

        print("[DEBUG] selected_only =", selected_only)
        print("[DEBUG] selected_ids =", selected_ids)
        print("[DEBUG] tests exécutés =", [test["id"] for test in test_cases])

        delete_results_by_analysis(analysis_id)

        for test in test_cases:
            try:
                execution_result = execute_selenium_script(test, url)

                status = execution_result.get("status", "failed")
                detail = execution_result.get("detail", "")

            except Exception as e:
                status = "failed"
                detail = str(e)

            update_test_status(test["id"], status)
            create_result(test["id"], status, detail)

        return jsonify(
            {
                "success": True,
                "message": "Tests exécutés avec succès.",
                "analysis_id": analysis_id,
                "executed_count": len(test_cases),
                "selected_only": selected_only,
                "selected_ids": selected_ids,
            }
        )

    except Exception as e:
        print("[ERROR] run_tests :", str(e))

        return jsonify({"success": False, "message": f"Erreur backend : {str(e)}"}), 500
