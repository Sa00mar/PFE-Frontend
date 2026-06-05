import json 
from app.db import get_connection


# CREATE USER (register)
def create_user(username, email, password, role="user"):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO users (username, email, password, role, created_at)
        VALUES (%s, %s, %s, %s, NOW())
    """, (username, email, password, role))

    conn.commit()
    cur.close()
    conn.close()


# LOGIN USER
def get_user_by_login(email, password):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT * FROM users
        WHERE email=%s AND password=%s
    """, (email, password))

    user = cur.fetchone()

    cur.close()
    conn.close()

    return user

def create_analysis(user_id, url, status):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO analyses (user_id, url, status, created_at)
        VALUES (%s, %s, %s, NOW())
        RETURNING id
    """, (user_id, url, status))

    analysis_id = cur.fetchone()[0]

    conn.commit()
    cur.close()
    conn.close()

    return analysis_id

def create_test(analysis_id, test_name, test_type):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO tests (analysis_id, test_name, test_type, created_at)
        VALUES (%s, %s, %s, NOW())
        RETURNING id
    """, (analysis_id, test_name, test_type))

    test_id = cur.fetchone()[0]

    conn.commit()
    cur.close()
    conn.close()

    return test_id

def create_result(test_id, status, detail):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO results (test_id, result_status, detail, created_at)
        VALUES (%s, %s, %s, NOW())
    """, (test_id, status, detail))

    conn.commit()
    cur.close()
    conn.close()

def add_history(user_id, action):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO history (user_id, action, created_at)
        VALUES (%s, %s, NOW())
    """, (user_id, action))

    conn.commit()
    cur.close()
    conn.close()

def update_analysis_status(analysis_id, status):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE analyses
        SET status = %s
        WHERE id = %s
    """, (status, analysis_id))

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

    cur.execute("""
        SELECT id, url, status, created_at
        FROM analyses
        WHERE id = %s
    """, (analysis_id,))

    row = cur.fetchone()

    cur.close()
    conn.close()

    return row

def save_test_cases(analysis_id, test_cases, version="v1"):
    conn = get_connection()
    cur = conn.cursor()

    for test in test_cases:
        steps_json = json.dumps(test.get("steps", []), ensure_ascii=False)

        cur.execute("""
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
        """, (
            analysis_id,
            test.get("name"),
            test.get("type"),
            test.get("priority"),
            steps_json,
            test.get("expected_result"),
            version,
            "pending",
            test.get("selenium_script"),
            test.get("cypress_script")
        ))

    conn.commit()
    cur.close()
    conn.close()


def get_test_cases_by_analysis(analysis_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
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
    """, (analysis_id,))

    rows = cur.fetchall()

    cur.close()
    conn.close()

    test_cases = []

    for row in rows:
        try:
            steps = json.loads(row[4]) if row[4] else []
        except Exception:
            steps = []

        test_cases.append({
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
            "created_at": row[10]
        })

    return test_cases


def update_test_status(test_id, status):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE tests
        SET status = %s
        WHERE id = %s
    """, (status, test_id))

    conn.commit()
    cur.close()
    conn.close()


def get_executed_results_by_analysis(analysis_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
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
            r.created_at
        FROM results r
        JOIN tests t ON r.test_id = t.id
        WHERE t.analysis_id = %s
        ORDER BY r.id ASC
    """, (analysis_id,))

    rows = cur.fetchall()

    cur.close()
    conn.close()

    executed_results = []

    for row in rows:
        try:
            steps = json.loads(row[4]) if row[4] else []
        except Exception:
            steps = []

        executed_results.append({
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
            "executed_at": row[11]
        })

    return executed_results


def get_next_version(url):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT COUNT(*)
        FROM analyses
        WHERE url = %s
    """, (url,))

    count = cur.fetchone()[0]

    cur.close()
    conn.close()

    return f"v{count}"

def delete_results_by_analysis(analysis_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        DELETE FROM results
        WHERE test_id IN (
            SELECT id FROM tests WHERE analysis_id = %s
        )
    """, (analysis_id,))

    conn.commit()
    cur.close()
    conn.close()


def reset_tests_status_by_analysis(analysis_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE tests
        SET status = 'pending'
        WHERE analysis_id = %s
    """, (analysis_id,))

    conn.commit()
    cur.close()
    conn.close()