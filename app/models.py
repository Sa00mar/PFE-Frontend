import json
from app.db import get_connection
from app.services.selector_extractor import extract_selectors_from_script


# CREATE USER (register)
def create_user(username, email, password, role="user"):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO users (username, email, password, role, created_at)
        VALUES (%s, %s, %s, %s, NOW())
    """,
        (username, email, password, role),
    )

    conn.commit()
    cur.close()
    conn.close()


# LOGIN USER
def get_user_by_login(email, password):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT * FROM users
        WHERE email=%s AND password=%s
    """,
        (email, password),
    )

    user = cur.fetchone()

    cur.close()
    conn.close()

    return user


def create_analysis(
    user_id,
    url,
    status,
    analysis_scope="single_page",
    target_feature="",
    test_types=None,
):
    conn = get_connection()
    cur = conn.cursor()

    if test_types is None:
        test_types = []

    if isinstance(test_types, list):
        test_types_text = ",".join(test_types)
    else:
        test_types_text = str(test_types)

    cur.execute(
        """
        INSERT INTO analyses (
            user_id,
            url,
            status,
            analysis_scope,
            target_feature,
            test_types
        )
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id
        """,
        (
            user_id,
            url,
            status,
            analysis_scope,
            target_feature,
            test_types_text,
        ),
    )

    analysis_id = cur.fetchone()[0]

    conn.commit()
    cur.close()
    conn.close()

    return analysis_id


def create_test(analysis_id, test_name, test_type):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO tests (analysis_id, test_name, test_type, created_at)
        VALUES (%s, %s, %s, NOW())
        RETURNING id
    """,
        (analysis_id, test_name, test_type),
    )

    test_id = cur.fetchone()[0]

    conn.commit()
    cur.close()
    conn.close()

    return test_id


def create_result(
    test_id,
    status,
    detail,
    screenshot_path=None,
    execution_run=1,
    execution_version="v1",
):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO results (
            test_id,
            result_status,
            detail,
            screenshot_path,
            execution_run,
            execution_version,
            created_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, NOW())
        """,
        (test_id, status, detail, screenshot_path, execution_run, execution_version),
    )

    conn.commit()
    cur.close()
    conn.close()


def add_history(user_id, action):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO history (user_id, action, created_at)
        VALUES (%s, %s, NOW())
    """,
        (user_id, action),
    )

    conn.commit()
    cur.close()
    conn.close()


def update_analysis_status(analysis_id, status):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        UPDATE analyses
        SET status = %s
        WHERE id = %s
    """,
        (status, analysis_id),
    )

    conn.commit()
    cur.close()
    conn.close()


def get_analysis_status(analysis_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT status FROM analyses WHERE id=%s", (analysis_id,))
    result = cur.fetchone()

    cur.close()
    conn.close()

    if result:
        return result[0]
    return "not_found"


def get_analysis_by_id(analysis_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            id,
            url,
            status,
            created_at,
            analysis_scope,
            target_feature,
            test_types
        FROM analyses
        WHERE id = %s
    """,
        (analysis_id,),
    )

    row = cur.fetchone()

    cur.close()
    conn.close()

    return row


def save_test_cases(analysis_id, test_cases, version="v1"):
    conn = get_connection()
    cur = conn.cursor()

    for test in test_cases:
        steps_json = json.dumps(test.get("steps", []), ensure_ascii=False)

        cur.execute(
            """
            INSERT INTO tests (
                analysis_id,
                test_name,
                test_type,
                priority,
                steps,
                expected_result,
                version,
                status,
                selenium_script,
                cypress_script,
                created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
        """,
            (
                analysis_id,
                test.get("name"),
                test.get("type"),
                test.get("priority"),
                steps_json,
                test.get("expected_result"),
                version,
                "pending",
                test.get("selenium_script"),
                test.get("cypress_script"),
            ),
        )

    conn.commit()
    cur.close()
    conn.close()


def get_test_cases_by_analysis(analysis_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            id,
            test_name,
            test_type,
            priority,
            steps,
            expected_result,
            version,
            status,
            selenium_script,
            cypress_script,
            created_at
        FROM tests
        WHERE analysis_id = %s
        ORDER BY id ASC
    """,
        (analysis_id,),
    )

    rows = cur.fetchall()

    cur.close()
    conn.close()

    test_cases = []

    for row in rows:
        try:
            steps = json.loads(row[4]) if row[4] else []
        except Exception:
            steps = []

        test_cases.append(
            {
                "id": row[0],
                "name": row[1],
                "type": row[2],
                "priority": row[3],
                "steps": steps,
                "expected_result": row[5],
                "version": row[6],
                "status": row[7],
                "selenium_script": row[8],
                "cypress_script": row[9],
                "created_at": row[10],
            }
        )

    return test_cases


def update_test_status(test_id, status):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        UPDATE tests
        SET status = %s
        WHERE id = %s
    """,
        (status, test_id),
    )

    conn.commit()
    cur.close()
    conn.close()


def get_executed_results_by_analysis(analysis_id, execution_run=None):
    conn = get_connection()
    cur = conn.cursor()

    if execution_run is None:
        cur.execute(
            """
            SELECT COALESCE(MAX(r.execution_run), 0)
            FROM results r
            JOIN tests t ON r.test_id = t.id
            WHERE t.analysis_id = %s
            """,
            (analysis_id,),
        )

        execution_run = cur.fetchone()[0]

    if not execution_run:
        cur.close()
        conn.close()
        return []

    cur.execute(
        """
        SELECT
            t.id,
            t.test_name,
            t.test_type,
            t.priority,
            t.steps,
            t.expected_result,
            t.version,
            r.result_status,
            t.selenium_script,
            t.cypress_script,
            r.detail,
            r.screenshot_path,
            r.created_at,
            r.execution_run,
            r.execution_version
        FROM results r
        JOIN tests t ON r.test_id = t.id
        WHERE t.analysis_id = %s
          AND r.execution_run = %s
        ORDER BY r.id ASC
        """,
        (analysis_id, execution_run),
    )

    rows = cur.fetchall()

    cur.close()
    conn.close()

    executed_results = []

    for row in rows:
        try:
            steps = json.loads(row[4]) if row[4] else []
        except Exception:
            steps = []

        selector_info = extract_selectors_from_script(row[8])

        executed_results.append(
            {
                "id": row[0],
                "name": row[1],
                "type": row[2],
                "priority": row[3],
                "steps": steps,
                "expected_result": row[5],
                "version": row[6],
                "status": row[7],
                "selenium_script": row[8],
                "cypress_script": row[9],
                "detail": row[10],
                "screenshot_path": row[11],
                "executed_at": row[12],
                "execution_run": row[13],
                "execution_version": row[14],
                "element_name": selector_info.get("element_name"),
                "selector": selector_info.get("selector"),
            }
        )

    return executed_results


def get_next_version(url):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT COUNT(*)
        FROM analyses
        WHERE url = %s
    """,
        (url,),
    )

    count = cur.fetchone()[0]

    cur.close()
    conn.close()

    return f"v{count}"


def delete_results_by_analysis(analysis_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        DELETE FROM results
        WHERE test_id IN (
            SELECT id FROM tests WHERE analysis_id = %s
        )
    """,
        (analysis_id,),
    )

    conn.commit()
    cur.close()
    conn.close()


def reset_tests_status_by_analysis(analysis_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        UPDATE tests
        SET status = 'pending'
        WHERE analysis_id = %s
    """,
        (analysis_id,),
    )

    conn.commit()
    cur.close()
    conn.close()


def get_next_execution_version_for_analysis(analysis_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT COUNT(DISTINCT r.execution_version)
        FROM results r
        JOIN tests t ON r.test_id = t.id
        WHERE t.analysis_id = %s
        """,
        (analysis_id,),
    )

    count = cur.fetchone()[0] or 0

    cur.close()
    conn.close()

    return f"v{count + 1}"


def get_next_execution_run_for_analysis(analysis_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT COALESCE(MAX(r.execution_run), 0)
        FROM results r
        JOIN tests t ON r.test_id = t.id
        WHERE t.analysis_id = %s
        """,
        (analysis_id,),
    )

    last_run = cur.fetchone()[0] or 0

    cur.close()
    conn.close()

    next_run = last_run + 1

    return next_run, f"v{next_run}"


def get_tested_urls_summary(user_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        WITH latest_analysis AS (
            SELECT DISTINCT ON (a.url)
                a.id,
                a.url,
                a.created_at,
                t.version AS analysis_version
            FROM analyses a
            JOIN tests t ON t.analysis_id = a.id
            WHERE a.user_id = %s
            ORDER BY a.url, a.created_at DESC, t.id DESC
        ),
        latest_execution AS (
            SELECT DISTINCT ON (a.url)
                a.url,
                a.id AS analysis_id,
                t.version AS analysis_version,
                r.execution_run,
                r.execution_version,
                r.created_at AS executed_at
            FROM analyses a
            JOIN tests t ON t.analysis_id = a.id
            JOIN results r ON r.test_id = t.id
            WHERE a.user_id = %s
              AND r.execution_run IS NOT NULL
              AND r.execution_version IS NOT NULL
            ORDER BY a.url, r.created_at DESC
        ),
        latest_stats AS (
            SELECT
                a.id AS analysis_id,
                r.execution_run,
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE r.result_status = 'passed') AS passed,
                COUNT(*) FILTER (WHERE r.result_status = 'failed') AS failed,
                COUNT(*) FILTER (WHERE r.result_status = 'pending') AS pending
            FROM analyses a
            JOIN tests t ON t.analysis_id = a.id
            JOIN results r ON r.test_id = t.id
            WHERE a.user_id = %s
              AND r.execution_run IS NOT NULL
              AND r.execution_version IS NOT NULL
            GROUP BY a.id, r.execution_run
        )
        SELECT
            la.id,
            la.url,
            COALESCE(la.analysis_version, 'Non générée') AS latest_analysis_version,
            COALESCE(le.execution_version, 'Non exécutée') AS latest_execution_version,
            le.executed_at,
            COALESCE(ls.total, 0) AS total,
            COALESCE(ls.passed, 0) AS passed,
            COALESCE(ls.failed, 0) AS failed,
            COALESCE(ls.pending, 0) AS pending,
            le.analysis_id AS latest_executed_analysis_id
        FROM latest_analysis la
        LEFT JOIN latest_execution le ON le.url = la.url
        LEFT JOIN latest_stats ls
            ON ls.analysis_id = le.analysis_id
           AND ls.execution_run = le.execution_run
        ORDER BY la.created_at DESC
        """,
        (user_id, user_id, user_id),
    )

    rows = cur.fetchall()

    cur.close()
    conn.close()

    urls = []

    for row in rows:
        total = row[5]
        passed = row[6]
        failed = row[7]
        pending = row[8]

        if total == 0:
            global_status = "Non exécuté"
        elif failed > 0:
            global_status = "FAIL"
        elif pending > 0:
            global_status = "PENDING"
        else:
            global_status = "PASS"

        urls.append(
            {
                "analysis_id": row[9] or row[0],
                "url": row[1],
                "analysis_version": row[2],
                "execution_version": row[3],
                "executed_at": row[4],
                "total": total,
                "passed": passed,
                "failed": failed,
                "pending": pending,
                "global_status": global_status,
                "execution_state": "Exécuté" if total > 0 else "Non exécuté",
            }
        )

    return urls


def get_url_execution_history(user_id, reference_analysis_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT url
        FROM analyses
        WHERE id = %s AND user_id = %s
        """,
        (reference_analysis_id, user_id),
    )

    ref = cur.fetchone()

    if not ref:
        cur.close()
        conn.close()
        return None, []

    url = ref[0]

    cur.execute(
        """
        SELECT
            a.id AS analysis_id,
            t.version AS analysis_version,
            r.execution_run,
            r.execution_version,
            MAX(r.created_at) AS executed_at,
            COUNT(*) AS total,
            COUNT(*) FILTER (WHERE r.result_status = 'passed') AS passed,
            COUNT(*) FILTER (WHERE r.result_status = 'failed') AS failed,
            COUNT(*) FILTER (WHERE r.result_status = 'pending') AS pending
        FROM analyses a
        JOIN tests t ON t.analysis_id = a.id
        JOIN results r ON r.test_id = t.id
        WHERE a.user_id = %s
          AND a.url = %s
          AND r.execution_run IS NOT NULL
          AND r.execution_version IS NOT NULL
        GROUP BY
            a.id,
            t.version,
            r.execution_run,
            r.execution_version
        ORDER BY
            a.id DESC,
            r.execution_run DESC
        """,
        (user_id, url),
    )

    rows = cur.fetchall()

    cur.close()
    conn.close()

    history = []

    for row in rows:
        total = row[5]
        passed = row[6]
        failed = row[7]
        pending = row[8]

        if total == 0:
            global_status = "Non exécuté"
        elif failed > 0:
            global_status = "FAIL"
        elif pending > 0:
            global_status = "PENDING"
        else:
            global_status = "PASS"

        history.append(
            {
                "analysis_id": row[0],
                "analysis_version": row[1],
                "execution_run": row[2],
                "execution_version": row[3],
                "executed_at": row[4],
                "total": total,
                "passed": passed,
                "failed": failed,
                "pending": pending,
                "global_status": global_status,
            }
        )

    return (url,)


def get_user_by_id(user_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT id, username, email, role, created_at
        FROM users
        WHERE id = %s
        """,
        (user_id,),
    )

    row = cur.fetchone()

    cur.close()
    conn.close()

    if not row:
        return None

    return {
        "id": row[0],
        "username": row[1],
        "email": row[2],
        "role": row[3],
        "created_at": row[4],
    }


def update_user_profile(user_id, username):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        UPDATE users
        SET username = %s
        WHERE id = %s
        """,
        (username, user_id),
    )

    conn.commit()
    cur.close()
    conn.close()


def get_dashboard_stats(user_id):
    conn = get_connection()
    cur = conn.cursor()

    # Nombre total d'analyses de l'utilisateur
    cur.execute(
        """
        SELECT COUNT(*)
        FROM analyses
        WHERE user_id = %s
        """,
        (user_id,),
    )
    total_analyses = cur.fetchone()[0]

    # Nombre total de tests générés
    cur.execute(
        """
        SELECT COUNT(*)
        FROM tests t
        JOIN analyses a ON a.id = t.analysis_id
        WHERE a.user_id = %s
        """,
        (user_id,),
    )
    total_tests = cur.fetchone()[0]

    # Statistiques des résultats exécutés
    cur.execute(
        """
        SELECT
            COUNT(*) AS total_executions,
            COUNT(*) FILTER (WHERE r.result_status = 'passed') AS passed,
            COUNT(*) FILTER (WHERE r.result_status = 'failed') AS failed,
            COUNT(*) FILTER (WHERE r.result_status = 'pending') AS pending
        FROM results r
        JOIN tests t ON t.id = r.test_id
        JOIN analyses a ON a.id = t.analysis_id
        WHERE a.user_id = %s
        """,
        (user_id,),
    )

    row = cur.fetchone()

    total_executions = row[0] or 0
    passed = row[1] or 0
    failed = row[2] or 0
    pending = row[3] or 0

    # Taux de réussite : on ignore PENDING car ce n'est ni un vrai succès ni un vrai échec
    pass_fail_total = passed + failed

    if pass_fail_total > 0:
        success_rate = round((passed / pass_fail_total) * 100, 1)
    else:
        success_rate = 0

    cur.close()
    conn.close()

    return {
        "total_analyses": total_analyses,
        "total_tests": total_tests,
        "total_executions": total_executions,
        "passed": passed,
        "failed": failed,
        "pending": pending,
        "success_rate": success_rate,
    }


def get_success_rate_by_url(user_id, limit=5):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            a.url,
            COUNT(r.id) AS total,
            SUM(CASE WHEN r.result_status = 'passed' THEN 1 ELSE 0 END) AS passed,
            SUM(CASE WHEN r.result_status = 'failed' THEN 1 ELSE 0 END) AS failed,
            SUM(CASE WHEN r.result_status = 'pending' THEN 1 ELSE 0 END) AS pending,
            ROUND(
                (
                    SUM(CASE WHEN r.result_status = 'passed' THEN 1 ELSE 0 END)::numeric
                    / NULLIF(COUNT(r.id), 0)
                ) * 100,
                1
            ) AS success_rate
        FROM analyses a
        JOIN tests t ON t.analysis_id = a.id
        JOIN results r ON r.test_id = t.id
        WHERE a.user_id = %s
        GROUP BY a.url
        ORDER BY success_rate DESC, total DESC
        LIMIT %s
        """,
        (user_id, limit),
    )

    rows = cur.fetchall()

    cur.close()
    conn.close()

    url_rates = []

    for row in rows:
        url_rates.append(
            {
                "url": row[0],
                "total": row[1],
                "passed": row[2],
                "failed": row[3],
                "pending": row[4],
                "success_rate": float(row[5]) if row[5] is not None else 0,
            }
        )

    return url_rates
