from __future__ import annotations

import os
import sqlite3
from datetime import date, timedelta
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory, session
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


def login_required(view):
    from functools import wraps

    @wraps(view)
    def protected(*args, **kwargs):
        if not session.get("authenticated"):
            return jsonify({"error": "Authentication required"}), 401
        return view(*args, **kwargs)

    return protected


@app.get("/api/auth/session")
def auth_session():
    return jsonify({"authenticated": bool(session.get("authenticated"))})


@app.post("/api/auth/login")
def login():
    payload = request.get_json(silent=True) or {}
    username = payload.get("username")
    password = payload.get("password")
    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400
    if username != AUTH_USERNAME or not check_password_hash(AUTH_PASSWORD_HASH, password):
        return jsonify({"error": "Invalid username or password"}), 401

    session.clear()
    session["authenticated"] = True
    session["username"] = username
    session.permanent = True
    return jsonify({"authenticated": True, "username": username})


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
