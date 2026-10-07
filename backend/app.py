from __future__ import annotations

import hashlib
import json
import os
import secrets
import sqlite3
import smtplib
import time
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from flask import Flask, jsonify, redirect, request, send_from_directory, session
from flask_cors import CORS
from dotenv import load_dotenv
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")
DATABASE_PATH = Path(os.getenv("RESTAURANT_DB", BASE_DIR / "restaurant.db"))
FRONTEND_DIST = BASE_DIR / "frontend" / "dist"
AUTH_USERNAME = os.getenv("AUTH_USERNAME")
AUTH_PASSWORD = os.getenv("AUTH_PASSWORD")
AUTH_PASSWORD_HASH = generate_password_hash(AUTH_PASSWORD) if AUTH_PASSWORD else ""
AUTH_SECRET_KEY = os.getenv("FLASK_SECRET_KEY") or os.urandom(32)
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
FACEBOOK_CLIENT_ID = os.getenv("FACEBOOK_CLIENT_ID")
FACEBOOK_CLIENT_SECRET = os.getenv("FACEBOOK_CLIENT_SECRET")

if not AUTH_USERNAME or not AUTH_PASSWORD:
    raise RuntimeError(
        "AUTH_USERNAME and AUTH_PASSWORD must be set before starting the portal. "
        "See .env.example for configuration."
    )

app = Flask(__name__)
app.config.update(
    DATABASE_PATH=str(DATABASE_PATH),
    SECRET_KEY=AUTH_SECRET_KEY,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Strict",
    SESSION_COOKIE_SECURE=os.getenv("FLASK_ENV") == "production",
    PERMANENT_SESSION_LIFETIME=timedelta(hours=int(os.getenv("SESSION_TIMEOUT_HOURS", 8))),
)
CORS(
    app,
    resources={r"/api/*": {"origins": os.getenv("CORS_ORIGINS", "http://localhost:5173")}},
    supports_credentials=False,
)


def get_db() -> sqlite3.Connection:
    connection = sqlite3.connect(app.config["DATABASE_PATH"])
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db() -> None:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_db() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT,
                provider TEXT NOT NULL DEFAULT 'email',
                provider_id TEXT,
                reset_token_hash TEXT,
                reset_expires_at INTEGER,
                created_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now'))
            );

            CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                role TEXT NOT NULL,
                initials TEXT NOT NULL,
                phone TEXT,
                email TEXT
            );

            CREATE TABLE IF NOT EXISTS weekly_shifts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER NOT NULL,
                week_start TEXT NOT NULL,
                weekday INTEGER NOT NULL,
                shift_type TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                is_off INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (employee_id) REFERENCES employees(id)
            );

            CREATE TABLE IF NOT EXISTS daily_menu (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                menu_date TEXT NOT NULL UNIQUE,
                meal TEXT NOT NULL,
                dessert TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS meal_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER NOT NULL,
                request_date TEXT NOT NULL,
                meal TEXT NOT NULL,
                note TEXT,
                status TEXT NOT NULL DEFAULT 'Pending',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (employee_id) REFERENCES employees(id)
            );
            """
        )
    seed_data()


def seed_data() -> None:
    with get_db() as connection:
        if connection.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
            admin_email = AUTH_USERNAME.lower()
            connection.execute(
                "INSERT INTO users (name, email, password_hash, provider) VALUES (?, ?, ?, ?)",
                (AUTH_USERNAME, admin_email, AUTH_PASSWORD_HASH, "email"),
            )

        if connection.execute("SELECT COUNT(*) FROM employees").fetchone()[0] > 0:
            return

        employees = [
            ("Amelia Morgan", "Manager", "AM"),
            ("Lucas Martin", "Manager", "LM"),
            ("Sofia Laurent", "Chef de cuisine", "SL"),
            ("Noah Bennett", "Chef de cuisine", "NB"),
            ("Emma Wilson", "Chef de second", "EW"),
            ("Oliver Reed", "Chef de second", "OR"),
            ("Mia Thompson", "Commis de cuisine", "MT"),
            ("Ethan Brooks", "Commis de cuisine", "EB"),
            ("Isla Carter", "Commis de cuisine", "IC"),
            ("Leo Foster", "Commis de cuisine", "LF"),
            ("Ava Johnson", "Commis de cuisine", "AJ"),
            ("Gabriel Kim", "Commis de cuisine", "GK"),
        ]
        employee_ids = []
        for name, role, initials in employees:
            cursor = connection.execute(
                "INSERT INTO employees (name, role, initials) VALUES (?, ?, ?)",
                (name, role, initials),
            )
            employee_ids.append(cursor.lastrowid)

        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        shift_types = ["Morning", "Afternoon", "Evening", "Off"]
        for employee_id in employee_ids:
            for weekday, weekday_name in enumerate(weekdays):
                shift = shift_types[(employee_id + weekday) % 4]
                if shift == "Off":
                    start_time, end_time = "", ""
                    is_off = 1
                else:
                    start_time, end_time = {
                        "Morning": ("06:00", "14:00"),
                        "Afternoon": ("14:00", "22:00"),
                        "Evening": ("22:00", "06:00"),
                    }[shift]
                    is_off = 0
                connection.execute(
                    """
                    INSERT INTO weekly_shifts
                    (employee_id, week_start, weekday, shift_type, start_time, end_time, is_off)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (employee_id, week_start.isoformat(), weekday, shift, start_time, end_time, is_off),
                )

        today_iso = today.isoformat()
        connection.execute(
            "INSERT INTO daily_menu (menu_date, meal, dessert) VALUES (?, ?, ?)",
            (
                today_iso,
                "Herb-roasted chicken with seasonal vegetables",
                "Vanilla panna cotta with berry compote",
            ),
        )


def database_error(message: str):
    return jsonify({"error": message}), 500


def user_from_row(row):
    return {
        "id": row["id"],
        "name": row["name"],
        "email": row["email"],
        "provider": row["provider"],
    }


def create_session(user):
    session.clear()
    session["authenticated"] = True
    session["user_id"] = user["id"]
    session["username"] = user["name"]
    session.permanent = True


def login_required(view):
    from functools import wraps

    @wraps(view)
    def protected(*args, **kwargs):
        if not session.get("authenticated"):
            return jsonify({"error": "Authentication required"}), 401
        return view(*args, **kwargs)

    return protected


def provider_url(provider, callback):
    client_id = {
        "google": GOOGLE_CLIENT_ID,
        "facebook": FACEBOOK_CLIENT_ID,
    }[provider]
    if not client_id:
        return None
    state = secrets.token_urlsafe(24)
    session["oauth_state"] = state
    session["oauth_provider"] = provider
    session["oauth_callback"] = callback
    base_url = os.getenv("APP_URL", "http://localhost:5000")
    params = {
        "client_id": client_id,
        "redirect_uri": f"{base_url}/api/auth/{provider}/callback",
        "response_type": "code",
        "scope": "openid email profile" if provider == "google" else "email",
        "access_type": "offline",
        "prompt": "select_account",
        "state": state,
    }
    if provider == "facebook":
        params.pop("access_type")
        params.pop("prompt")
    return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}" if provider == "google" else f"https://www.facebook.com/dialog/oauth?{urlencode(params)}"


def exchange_oauth_token(provider, code):
    if provider == "google":
        data = urlencode({
            "code": code,
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uri": f"{os.getenv('APP_URL', 'http://localhost:5000')}/api/auth/google/callback",
            "grant_type": "authorization_code",
        })
        request_obj = Request(
            "https://oauth2.googleapis.com/token",
            data=data.encode(),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        with urlopen(request_obj, timeout=10) as response:
            token_data = json.loads(response.read().decode())
        request_obj = Request(
            "https://openidconnect.googleapis.com/v1/userinfo",
            headers={"Authorization": f"Bearer {token_data['access_token']}"},
        )
        with urlopen(request_obj, timeout=10) as response:
            return json.loads(response.read().decode())

    data = urlencode({
        "code": code,
        "client_id": FACEBOOK_CLIENT_ID,
        "client_secret": FACEBOOK_CLIENT_SECRET,
        "redirect_uri": f"{os.getenv('APP_URL', 'http://localhost:5000')}/api/auth/facebook/callback",
    })
    request_obj = Request(
        "https://graph.facebook.com/oauth/access_token",
        data=data.encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urlopen(request_obj, timeout=10) as response:
        token_data = json.loads(response.read().decode())
    request_obj = Request(
        f"https://graph.facebook.com/v2.0/me?fields=id,name,email&access_token={token_data['access_token']}",
    )
    with urlopen(request_obj, timeout=10) as response:
        return json.loads(response.read().decode())


def save_oauth_user(provider, provider_id, name, email):
    with get_db() as connection:
        existing = connection.execute(
            "SELECT * FROM users WHERE provider = ? AND provider_id = ?",
            (provider, provider_id),
        ).fetchone()
        if existing:
            return user_from_row(existing)
        existing_by_email = connection.execute(
            "SELECT * FROM users WHERE email = ?",
            (email.lower(),),
        ).fetchone()
        if existing_by_email:
            connection.execute(
                "UPDATE users SET provider = ?, provider_id = ? WHERE id = ?",
                (provider, provider_id, existing_by_email["id"]),
            )
            return user_from_row(connection.execute(
                "SELECT * FROM users WHERE id = ?", (existing_by_email["id"],)
            ).fetchone())
        cursor = connection.execute(
            "INSERT INTO users (name, email, provider, provider_id) VALUES (?, ?, ?, ?)",
            (name, email.lower(), provider, provider_id),
        )
        return user_from_row(connection.execute(
            "SELECT * FROM users WHERE id = ?", (cursor.lastrowid,)
        ).fetchone())


@app.get("/api/auth/session")
def auth_session():
    return jsonify({"authenticated": bool(session.get("authenticated")), "user": {
        "name": session.get("username"),
        "email": session.get("email"),
    } if session.get("authenticated") else None})


@app.post("/api/auth/login")
def login():
    payload = request.get_json(silent=True) or {}
    email = (payload.get("email") or "").strip().lower()
    password = payload.get("password") or ""
    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400
    with get_db() as connection:
        user = connection.execute(
            "SELECT * FROM users WHERE email = ? AND provider = 'email'", (email,)
        ).fetchone()
    if not user or not user["password_hash"] or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Invalid email or password"}), 401
    create_session(user_from_row(user))
    session["email"] = user["email"]
    return jsonify({"authenticated": True, "user": user_from_row(user)})


@app.post("/api/auth/signup")
def signup():
    payload = request.get_json(silent=True) or {}
    name = (payload.get("name") or "").strip()
    email = (payload.get("email") or "").strip().lower()
    password = payload.get("password") or ""
    if len(name) < 2 or len(email) < 5 or len(password) < 8:
        return jsonify({"error": "Enter a valid name, email, and password of at least 8 characters"}), 400
    if not all(character.isprintable() for character in name + email + password):
        return jsonify({"error": "Invalid characters entered"}), 400
    with get_db() as connection:
        if connection.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone():
            return jsonify({"error": "An account with this email already exists"}), 409
        cursor = connection.execute(
            "INSERT INTO users (name, email, password_hash, provider) VALUES (?, ?, ?, ?)",
            (name, email, generate_password_hash(password), "email"),
        )
        user = user_from_row(connection.execute(
            "SELECT * FROM users WHERE id = ?", (cursor.lastrowid,)
        ).fetchone())
    create_session(user)
    session["email"] = user["email"]
    return jsonify({"authenticated": True, "user": user}), 201


@app.post("/api/auth/forgot-password")
def forgot_password():
    email = (request.get_json(silent=True) or {}).get("email", "").strip().lower()
    if not email:
        return jsonify({"error": "Email is required"}), 400
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    expires_at = int(time.time()) + 3600
    with get_db() as connection:
        connection.execute(
            "UPDATE users SET reset_token_hash = ?, reset_expires_at = ? WHERE email = ?",
            (token_hash, expires_at, email),
        )
    if not all(os.getenv(name) for name in ("SMTP_HOST", "SMTP_PORT", "SMTP_USERNAME", "SMTP_PASSWORD", "MAIL_FROM", "APP_URL")):
        return jsonify({"error": "Password reset email is not configured"}), 503
    reset_url = f"{os.getenv('APP_URL', 'http://localhost:5000')}/reset-password?token={token}"
    try:
        with smtplib.SMTP(os.getenv("SMTP_HOST"), int(os.getenv("SMTP_PORT")), timeout=10) as smtp:
            smtp.starttls()
            smtp.login(os.getenv("SMTP_USERNAME"), os.getenv("SMTP_PASSWORD"))
            message = f"Subject: Reset your Maison password\r\nFrom: {os.getenv('MAIL_FROM')}\r\nTo: {email}\r\n\r\nUse this secure link to reset your password:\n{reset_url}\n\nThis link expires in one hour."
            smtp.sendmail(os.getenv("MAIL_FROM"), email, message)
    except Exception as error:
        app.logger.error("Password reset email failed: %s", error)
        return jsonify({"error": "Unable to send reset email"}), 503
    return jsonify({"message": "If that account exists, a reset link has been sent."})


@app.post("/api/auth/reset-password")
def reset_password():
    payload = request.get_json(silent=True) or {}
    token = payload.get("token", "")
    password = payload.get("password", "")
    if not token or len(password) < 8:
        return jsonify({"error": "A valid token and password of at least 8 characters are required"}), 400
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    with get_db() as connection:
        user = connection.execute(
            "SELECT * FROM users WHERE reset_token_hash = ? AND reset_expires_at > ?",
            (token_hash, int(time.time())),
        ).fetchone()
        if not user:
            return jsonify({"error": "Reset link is invalid or expired"}), 400
        connection.execute(
            "UPDATE users SET password_hash = ?, reset_token_hash = NULL, reset_expires_at = NULL WHERE id = ?",
            (generate_password_hash(password), user["id"]),
        )
    return jsonify({"message": "Password updated successfully"})


@app.get("/api/auth/<provider>")
def oauth_start(provider):
    if provider not in {"google", "facebook"}:
        return jsonify({"error": "Unsupported sign-in provider"}), 400
    url = provider_url(provider, request.args.get("callback", "/"))
    if not url:
        return jsonify({"error": f"{provider.title()} sign-in is not configured"}), 503
    return jsonify({"url": url})


@app.get("/api/auth/<provider>/callback")
def oauth_callback(provider):
    if provider not in {"google", "facebook"}:
        return jsonify({"error": "Unsupported sign-in provider"}), 400
    code = request.args.get("code", "")
    state = request.args.get("state", "")
    if state != session.get("oauth_state"):
        return jsonify({"error": "Invalid OAuth state"}), 400
    try:
        profile = exchange_oauth_token(provider, code)
        provider_id = profile.get("id")
        email = profile.get("email", "").lower()
        name = profile.get("name", email.split("@")[0])
        if not provider_id or not email:
            return jsonify({"error": "The provider did not return a required account detail"}), 401
        user = save_oauth_user(provider, str(provider_id), name, email)
        create_session(user_from_row(user))
        session["email"] = user["email"]
        session.pop("oauth_state", None)
        session.pop("oauth_provider", None)
        session.pop("oauth_callback", None)
        return redirect(os.getenv("FRONTEND_URL", "http://localhost:5173"))
    except Exception as error:
        app.logger.error("OAuth authentication failed: %s", error)
        return jsonify({"error": "Unable to complete social sign-in"}), 502


@app.post("/api/auth/logout")
def logout():
    session.clear()
    return jsonify({"authenticated": False})


@app.get("/api/staff")
@login_required
def staff():
    with get_db() as connection:
        rows = connection.execute(
            "SELECT id, name, role, initials FROM employees ORDER BY role, name"
        ).fetchall()
    return jsonify([dict(row) for row in rows])


@app.get("/api/schedule")
@login_required
def schedule():
    week_start = request.args.get("week_start", (date.today() - timedelta(days=date.today().weekday())).isoformat())
    with get_db() as connection:
        rows = connection.execute(
            """
            SELECT e.id AS employee_id, e.name, e.role, e.initials,
                   ws.weekday, ws.shift_type, ws.start_time, ws.end_time, ws.is_off
            FROM weekly_shifts ws
            JOIN employees e ON e.id = ws.employee_id
            WHERE ws.week_start = ?
            ORDER BY ws.weekday, e.role, e.name
            """,
            (week_start,),
        ).fetchall()
    return jsonify([dict(row) for row in rows])


@app.get("/api/menu")
@login_required
def menu():
    with get_db() as connection:
        rows = connection.execute(
            "SELECT * FROM daily_menu ORDER BY menu_date DESC LIMIT 7"
        ).fetchall()
    return jsonify([dict(row) for row in rows])


@app.post("/api/meal-requests")
@login_required
def create_meal_request():
    payload = request.get_json(silent=True) or {}
    required = ("employee_id", "request_date", "meal")
    if any(not payload.get(field) for field in required):
        return jsonify({"error": "employee_id, request_date, and meal are required"}), 400
    try:
        with get_db() as connection:
            cursor = connection.execute(
                "INSERT INTO meal_requests (employee_id, request_date, meal, note) VALUES (?, ?, ?, ?)",
                (payload["employee_id"], payload["request_date"], payload["meal"], payload.get("note", "")),
            )
            row = connection.execute(
                "SELECT * FROM meal_requests WHERE id = ?", (cursor.lastrowid,)
            ).fetchone()
    except sqlite3.IntegrityError:
        return jsonify({"error": "The selected employee does not exist"}), 400
    return jsonify(dict(row)), 201


@app.get("/api/meal-requests")
@login_required
def meal_requests():
    with get_db() as connection:
        rows = connection.execute(
            """
            SELECT r.*, e.name, e.role
            FROM meal_requests r
            JOIN employees e ON e.id = r.employee_id
            ORDER BY r.created_at DESC
            """
        ).fetchall()
    return jsonify([dict(row) for row in rows])


@app.get("/api/health")
def health():
    return jsonify({"status": "ok", "database": DATABASE_PATH.name})


@app.get("/assets/<path:filename>")
def frontend_assets(filename: str):
    return send_from_directory(FRONTEND_DIST / "assets", filename)


@app.get("/")
@app.get("/<path:path>")
def index(path: str = ""):
    if FRONTEND_DIST.exists() and (FRONTEND_DIST / "index.html").exists():
        return send_from_directory(FRONTEND_DIST, "index.html")
    return jsonify({"message": "Frontend not built yet. Run npm run build."}), 200


init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=os.getenv("FLASK_DEBUG", "0") == "1")
