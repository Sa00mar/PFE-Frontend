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