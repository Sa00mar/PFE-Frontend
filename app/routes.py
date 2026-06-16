from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    session,
    jsonify,
    send_file,
    flash,
)
import threading
import os

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
    get_next_execution_run_for_analysis,
    get_tested_urls_summary,
    get_url_execution_history,
    get_user_by_id,
    update_user_profile,
    get_dashboard_stats,
    get_success_rate_by_url,
    get_all_users,
    update_user_status,
    update_user_role,
    get_admin_dashboard_stats,
)

from app.services.page_fetcher import fetch_page_html
from app.services.custom_ia_engine import generate_tests_with_custom_engine
from app.services.site_crawler import crawl_important_pages
from app.services.multi_page_analyzer import merge_relevant_data
from app.services.feature_detector import detect_features
from app.services.selenium_executor import execute_selenium_script
from app.services.report_generator import generate_pdf_report

main = Blueprint("main", __name__)


def is_admin():
    return "user_id" in session and session.get("role") == "admin"


def require_admin():
    if "user_id" not in session:
        return redirect(url_for("main.login"))

    if session.get("role") != "admin":
        flash(
            "Accès réservé à l'administrateur. Si votre rôle vient d’être modifié, reconnectez-vous.",
            "danger",
        )
        return redirect(url_for("main.home"))

    return None


# =========================================================
# HOME
# =========================================================


@main.route("/")
def index():
    return redirect(url_for("main.login"))


# =========================================================
# ADMIN DASHBOARD
# =========================================================


@main.route("/admin/dashboard")
def admin_dashboard():
    access_error = require_admin()

    if access_error:
        return access_error

    stats = get_admin_dashboard_stats()

    return render_template(
        "admin_dashboard.html",
        stats=stats,
    )


# =========================================================
# ADMIN USERS
# =========================================================


@main.route("/admin/users")
def admin_users():
    access_error = require_admin()

    if access_error:
        return access_error

    users = get_all_users()

    return render_template(
        "admin_users.html",
        users=users,
    )


@main.route("/admin/users/<int:user_id>/toggle-status", methods=["POST"])
def admin_toggle_user_status(user_id):
    access_error = require_admin()

    if access_error:
        return access_error

    current_user = get_user_by_id(user_id)

    if not current_user:
        return "Utilisateur introuvable", 404

    if user_id == session.get("user_id"):
        flash("Vous ne pouvez pas désactiver votre propre compte.", "danger")
        return redirect(url_for("main.admin_users"))

    users = get_all_users()
    selected_user = None

    for user in users:
        if user["id"] == user_id:
            selected_user = user
            break

    if not selected_user:
        return "Utilisateur introuvable", 404

    new_status = not selected_user["is_active"]

    update_user_status(user_id, new_status)

    flash("Statut utilisateur mis à jour avec succès.", "success")

    return redirect(url_for("main.admin_users"))


@main.route("/admin/users/<int:user_id>/change-role", methods=["POST"])
def admin_change_user_role(user_id):
    access_error = require_admin()

    if access_error:
        return access_error

    if user_id == session.get("user_id"):
        flash("Vous ne pouvez pas modifier votre propre rôle.", "danger")
        return redirect(url_for("main.admin_users"))

    new_role = request.form.get("role")

    if new_role not in ["user", "admin"]:
        flash("Rôle invalide.", "danger")
        return redirect(url_for("main.admin_users"))

    update_user_role(user_id, new_role)

    flash("Rôle utilisateur mis à jour avec succès.", "success")

    return redirect(url_for("main.admin_users"))


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
            if not user[4]:
                error = (
                    "Votre compte est désactivé. Veuillez contacter l'administrateur."
                )
                return render_template("login.html", error=error)
            session["user_id"] = user[0]
            session["username"] = user[1]
            session["email"] = user[2]
            session["role"] = user[3]

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


@main.route("/")
@main.route("/home")
def home():
    if "user_id" not in session:
        return redirect(url_for("main.login"))

    user_id = session["user_id"]

    stats = get_dashboard_stats(user_id)
    url_rates = get_success_rate_by_url(user_id)

    return render_template(
        "home.html",
        stats=stats,
        url_rates=url_rates,
    )


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

        # Nouveaux champs : scope + types de tests
        analysis_scope = request.form.get("analysis_scope", "single_page")
        target_feature = request.form.get("target_feature", "").strip()
        test_types = request.form.getlist("test_types")

        # Sécurité : valeurs par défaut
        if not test_types:
            test_types = ["functional", "ui"]

        if analysis_scope not in ["single_page", "full_site", "specific_feature"]:
            analysis_scope = "single_page"

        if analysis_scope != "specific_feature":
            target_feature = ""

        if not url:
            return render_template("new_test.html", error="URL obligatoire")

        user_id = session["user_id"]

        analysis_id = create_analysis(
            user_id=user_id,
            url=url,
            status="pending",
            analysis_scope=analysis_scope,
            target_feature=target_feature,
            test_types=test_types,
        )

        threading.Thread(
            target=process_analysis,
            args=(
                analysis_id,
                url,
                auth_required,
                analysis_scope,
                target_feature,
                test_types,
            ),
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

    user_id = session["user_id"]

    tested_urls = get_tested_urls_summary(user_id)

    return render_template("my_tests.html", tested_urls=tested_urls)


@main.route("/my_tests/url/<int:analysis_id>")
def url_execution_history(analysis_id):

    if "user_id" not in session:
        return redirect(url_for("main.login"))

    user_id = session["user_id"]

    url, history = get_url_execution_history(user_id, analysis_id)

    if not url:
        return "URL introuvable", 404

    return render_template(
        "url_execution_history.html",
        url=url,
        history=history,
    )


# =========================================================
# SETTINGS
# =========================================================


@main.route("/settings", methods=["GET", "POST"])
def settings():
    if "user_id" not in session:
        return redirect(url_for("main.login"))

    user_id = session["user_id"]

    if request.method == "POST":
        username = request.form.get("username", "").strip()

        if username:
            update_user_profile(user_id, username)
            session["username"] = username
            flash("Profil mis à jour avec succès.", "success")
        else:
            flash("Le nom ne peut pas être vide.", "danger")

        return redirect(url_for("main.settings"))

    user = get_user_by_id(user_id)

    return render_template("settings.html", user=user)


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


def detect_main_feature_for_report(url, tests):
    """
    Déduit une fonctionnalité principale simple pour le rapport.
    Cette fonction sert uniquement à rendre le rapport plus lisible.
    """

    url_lower = (url or "").lower()
    tests_text = " ".join(
        [
            str(test.get("name", "")) + " " + str(test.get("expected_result", ""))
            for test in tests
        ]
    ).lower()

    full_text = url_lower + " " + tests_text

    if "login" in full_text or "connexion" in full_text:
        return "Authentification utilisateur"

    if "contact" in full_text or "formulaire" in full_text:
        return "Formulaire de contact"

    if "register" in full_text or "inscription" in full_text:
        return "Inscription utilisateur"

    if "checkout" in full_text or "commande" in full_text:
        return "Processus de commande"

    if "search" in full_text or "recherche" in full_text:
        return "Recherche"

    return "Fonctionnalité web principale"


def format_analysis_scope_for_report(analysis_scope):
    """
    Transforme la valeur technique du scope en texte lisible.
    """

    scopes = {
        "single_page": "Page actuelle uniquement",
        "full_site": "Site complet",
        "specific_feature": "Fonctionnalité précise",
    }

    return scopes.get(analysis_scope, analysis_scope or "Non renseigné")


def detect_test_types_for_report(tests):
    """
    Déduit les types de tests réellement présents dans les résultats.
    """

    labels = {
        "positive": "Tests positifs",
        "negative": "Tests négatifs",
        "ui": "Tests UI",
        "navigation": "Tests de navigation",
        "security": "Tests de sécurité",
        "seo": "Tests SEO",
        "functional": "Tests fonctionnels",
    }

    detected = []

    for test in tests:
        test_type = str(test.get("type", "")).lower()

        if test_type in labels and labels[test_type] not in detected:
            detected.append(labels[test_type])

    if not detected:
        return "Non renseigné"

    return ", ".join(detected)


def format_test_types_for_report(test_types):
    """
    Transforme les types techniques sauvegardés en base
    en libellés lisibles pour le rapport.
    """

    if not test_types:
        return "Non renseigné"

    labels = {
        "functional": "Tests fonctionnels",
        "ui": "Tests UI",
        "security": "Tests de sécurité",
        "seo": "Tests SEO",
        "positive": "Tests positifs",
        "negative": "Tests négatifs",
        "navigation": "Tests de navigation",
    }

    if isinstance(test_types, str):
        raw_types = [item.strip() for item in test_types.split(",") if item.strip()]
    else:
        raw_types = test_types

    formatted = []

    for test_type in raw_types:
        value = labels.get(str(test_type).lower(), str(test_type))

        if value not in formatted:
            formatted.append(value)

    if not formatted:
        return "Non renseigné"

    return ", ".join(formatted)


@main.route("/test_results/<int:analysis_id>")
def test_results(analysis_id):

    if "user_id" not in session:
        return redirect(url_for("main.login"))

    analysis = get_analysis_by_id(analysis_id)

    if not analysis:
        return "Analysis not found", 404

    selected_run = request.args.get("run", type=int)
    source = request.args.get("from", "")
    executed_results = get_executed_results_by_analysis(
        analysis_id,
        execution_run=selected_run,
    )

    execution_version = ""
    execution_run = None

    if executed_results:
        execution_version = executed_results[0].get("execution_version", "")
        execution_run = executed_results[0].get("execution_run")

    if source == "history":
        back_url = url_for("main.url_execution_history", analysis_id=analysis_id)
        back_label = "Retour à l'historique"
    else:
        back_url = url_for("main.analysis_result", analysis_id=analysis_id)
        back_label = "Retour aux cas de test"

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
        "execution_version": execution_version,
        "execution_run": execution_run,
        "back_url": back_url,
        "back_label": back_label,
    }

    return render_template("test_results.html", data=data)


@main.route("/download-report-pdf/<int:analysis_id>")
def download_report_pdf(analysis_id):
    selected_run = request.args.get("run", type=int)

    if "user_id" not in session:
        return redirect(url_for("main.login"))

    analysis = get_analysis_by_id(analysis_id)

    if not analysis:
        return "Analyse introuvable", 404

    executed_results = get_executed_results_by_analysis(
        analysis_id,
        execution_run=selected_run,
    )

    execution_version = ""
    execution_run = None
    if executed_results:
        execution_version = executed_results[0].get("execution_version", "")
        execution_run = executed_results[0].get("execution_run")

    if not executed_results:
        return "Aucun résultat d'exécution trouvé pour cette analyse.", 404

    url = analysis[1]
    first_result = executed_results[0] if executed_results else {}

    detected_feature = detect_main_feature_for_report(url, executed_results)

    analysis_scope = analysis[4] if len(analysis) > 4 else "single_page"
    target_feature = analysis[5] if len(analysis) > 5 else ""
    stored_test_types = analysis[6] if len(analysis) > 6 else ""

    main_feature = target_feature if target_feature else detected_feature

    report_analysis = {
        "id": analysis[0],
        "url": url,
        "page_type": detected_feature,
        "main_feature": main_feature,
        "analysis_scope": format_analysis_scope_for_report(analysis_scope),
        "test_types": format_test_types_for_report(
            stored_test_types or detect_test_types_for_report(executed_results)
        ),
        "version": first_result.get("version", ""),
        "execution_version": execution_version,
        "execution_run": execution_run,
        "executed_at": first_result.get("executed_at", ""),
    }

    report_tests = []

    for result in executed_results:
        report_tests.append(
            {
                "id": result.get("id"),
                "name": result.get("name"),
                "type": result.get("type"),
                "priority": result.get("priority"),
                "version": result.get("version"),
                "status": result.get("status"),
                "steps": result.get("steps"),
                "expected_result": result.get("expected_result"),
                "execution_message": result.get("detail")
                or result.get("execution_message"),
                "screenshot_path": result.get("screenshot_path"),
                "selenium_script": result.get("selenium_script"),
                "cypress_script": result.get("cypress_script"),
                "execution_version": execution_version,
                "execution_run": execution_run,
            }
        )

    reports_dir = os.path.join("static", "reports")
    os.makedirs(reports_dir, exist_ok=True)

    suffix = f"_execution_{execution_version}" if execution_version else ""

    html_filename = f"rapport_analyse_{analysis_id}{suffix}.html"
    pdf_filename = f"rapport_analyse_{analysis_id}{suffix}.pdf"

    html_path = os.path.join(reports_dir, html_filename)
    pdf_path = os.path.join(reports_dir, pdf_filename)

    generate_pdf_report(
        analysis=report_analysis,
        tests=report_tests,
        html_output_path=html_path,
        pdf_output_path=pdf_path,
    )

    return send_file(
        os.path.abspath(pdf_path),
        as_attachment=True,
        download_name=pdf_filename,
    )


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
    analysis_id,
    url,
    auth_required=None,
    analysis_scope="single_page",
    target_feature="",
    test_types=None,
):

    try:
        # ==================================================
        # MODE AUTHENTIFIÉ
        # ==================================================
        if test_types is None:
            test_types = ["functional", "ui"]

        print("\n==================== OPTIONS ANALYSE ====================")
        print("Scope :", analysis_scope)
        print("Target feature :", target_feature if target_feature else "Aucune")
        print("Types de tests :", test_types)

        if auth_required == "yes":
            from app.services.authenticated_crawler import crawl_authenticated_pages

            print("\n[INFO] Analyse authentifiée activée")

            crawl_result = crawl_authenticated_pages(
                url=url,
                analysis_scope=analysis_scope,
            )

        # ==================================================
        # MODE PUBLIC
        # ==================================================

        else:
            print("\n[INFO] Analyse publique classique")

            if analysis_scope in ["single_page", "specific_feature"]:
                crawl_result = crawl_important_pages(url, max_pages=1, max_depth=0)
            else:
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

        relevant_data["analysis_scope"] = analysis_scope
        relevant_data["target_feature"] = target_feature
        relevant_data["test_types"] = test_types

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
            page_type=page_type,
            relevant_data=relevant_data,
            url=url,
            analysis_scope=analysis_scope,
            target_feature=target_feature,
            test_types=test_types,
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

        execution_run, execution_version = get_next_execution_run_for_analysis(
            analysis_id
        )

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

        for test in test_cases:
            try:
                execution_result = execute_selenium_script(test, url)

                status = execution_result.get("status", "failed")
                detail = execution_result.get("detail", "")
                screenshot_path = execution_result.get("screenshot_path")

            except Exception as e:
                status = "failed"
                detail = str(e)
                screenshot_path = None

            update_test_status(test["id"], status)
            create_result(
                test_id=test["id"],
                status=status,
                detail=detail,
                screenshot_path=screenshot_path,
                execution_run=execution_run,
                execution_version=execution_version,
            )

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


@main.route("/analysis/<int:analysis_id>/test-result/<int:test_id>")
def test_result_detail(analysis_id, test_id):
    analysis = get_analysis_by_id(analysis_id)
    results = get_executed_results_by_analysis(analysis_id)

    selected_test = None

    for result in results:
        if result["id"] == test_id:
            selected_test = result
            break

    if not analysis or not selected_test:
        return "Résultat introuvable", 404

    data = {
        "id": analysis[0],
        "url": analysis[1],
        "status": analysis[2],
        "created_at": analysis[3],
        "test": selected_test,
    }

    return render_template("test_result_detail.html", data=data)
