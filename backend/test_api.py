import requests
import sqlite3
import time
import os
from datetime import datetime, timedelta

BASE = "http://127.0.0.1:8000"


def pp(label, ok):
    status = "OK" if ok else "FAIL"
    print(f"[ {status} ] {label}")


def register(email, password, first_name, last_name, role="job_seeker", city="Lahore"):
    r = requests.post(f"{BASE}/api/v1/auth/register", json={
        "email": email,
        "password": password,
        "first_name": first_name,
        "last_name": last_name,
        "role": role,
        "city": city,
    })
    return r


def login(email, password):
    r = requests.post(f"{BASE}/api/v1/auth/login", json={
        "email": email,
        "password": password,
    })
    if r.status_code == 200:
        data = r.json()
        return data.get("access_token"), data.get("user", {}).get("user_id")
    return None, None


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def promote_user_to_admin(db_path, user_id):
    """Directly update role in SQLite for testing with safety.
    - Applies busy_timeout to avoid lock issues
    - Verifies the user exists before and after
    """
    con = sqlite3.connect(db_path)
    try:
        con.execute("PRAGMA busy_timeout = 3000")
        cur = con.cursor()

        # Ensure users table exists and user is present
        cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='users'")
        if not cur.fetchone():
            raise RuntimeError(f"No 'users' table in DB: {db_path}")

        cur.execute("SELECT user_id, role FROM users WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
        if not row:
            raise RuntimeError(f"User {user_id} not found in DB: {db_path}")

        cur.execute("UPDATE users SET role = ? WHERE user_id = ?", ("admin", user_id))
        con.commit()

        # Verify
        cur.execute("SELECT role FROM users WHERE user_id = ?", (user_id,))
        role = cur.fetchone()
        if not role or role[0] != "admin":
            raise RuntimeError("Promotion did not persist")
    finally:
        con.close()


def pick_db_for_server() -> str:
    """Choose the most likely DB used by the running server.
    Prefers dev_punjab_rozgar.db (DevelopmentSettings default) if it exists;
    otherwise falls back to punjab_rozgar.db under backend.
    """
    candidates = [
        os.path.join(os.getcwd(), "dev_punjab_rozgar.db"),
        os.path.join(os.getcwd(), "backend", "punjab_rozgar.db"),
        os.path.join(os.getcwd(), "punjab_rozgar.db"),
        os.path.join(os.getcwd(), "backend", "app", "punjab_rozgar.db"),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    # As a last resort, return the first candidate (will create a new file, not ideal)
    return candidates[0]


def main():
    print("Running E2E: employer posts → admin approves → visible to job seeker")

    # 1) Health check
    r = requests.get(f"{BASE}/health")
    ok = (r.status_code == 200 and r.json().get("status") == "healthy")
    pp("Health", ok)
    if not ok:
        return

    # 2) Register employer and login
    employer_email = "emp_e2e@example.com"
    employer_pwd = "EmpPass123!"
    register(employer_email, employer_pwd, "Emp", "Loyer", role="employer")
    emp_token, emp_user_id = login(employer_email, employer_pwd)
    pp("Employer login", emp_token is not None)
    if not emp_token:
        return

    # 3) Create job as employer (should be DRAFT)
    payload = {
        "title": "E2E Test Engineer",
        "description": "Automate and validate flows",
        "category": "Engineering",
        "location_city": "Lahore",
        "job_type": "full_time",
        "application_deadline": (datetime.utcnow() + timedelta(days=7)).isoformat()
    }
    r = requests.post(f"{BASE}/api/v1/jobs/", json=payload, headers=bearer(emp_token))
    ok = r.status_code == 200
    pp("Employer create job", ok)
    if not ok:
        print(r.text)
        return
    job = r.json()
    job_id = job["job_id"]

    # 4) Register a user and promote to admin directly in DB
    admin_email = "admin_e2e@example.com"
    admin_pwd = "AdminPass123!"
    register(admin_email, admin_pwd, "Ad", "Min", role="job_seeker")
    admin_token, admin_user_id = login(admin_email, admin_pwd)
    pp("Admin candidate login", admin_token is not None)
    if not admin_user_id:
        return

    # Promote in the SQLite DB that the server likely uses
    db_path = pick_db_for_server()
    try:
        promote_user_to_admin(db_path, admin_user_id)
    except Exception as e:
        pp(f"DB promotion failed ({db_path})", False)
        print(e)
        return

    # Give the server a moment to see changes (SQLite WAL + async sessions)
    time.sleep(0.2)

    # Re-login to pick up role changes
    # Retry re-login briefly in case of reload
    admin_token = None
    for _ in range(3):
        tok, _ = login(admin_email, admin_pwd)
        if tok:
            admin_token = tok
            break
        time.sleep(0.3)
    pp("Admin (promoted) re-login", admin_token is not None)
    if not admin_token:
        print("Login failed after promotion; verify DB path:", db_path)
        return

    # 5) Approve job via admin endpoint
    r = requests.put(
        f"{BASE}/api/v1/admin/jobs/{job_id}/status",
        json={"status": "active"},
        headers=bearer(admin_token)
    )
    ok = r.status_code == 200
    pp("Admin approves job", ok)
    if not ok:
        print(r.text)
        return

    # 6) Verify job is visible in public listing
    r = requests.get(f"{BASE}/api/v1/jobs/?only_active=true&search=E2E%20Test%20Engineer")
    ok = r.status_code == 200 and any(j.get("job_id") == job_id for j in r.json())
    pp("Job visible to seekers", ok)

    print("\nDone.")


if __name__ == "__main__":
    main()