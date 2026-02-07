import json
import os
import sqlite3
from flask import Flask, g, jsonify, redirect, render_template, request, url_for

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE = os.path.join(BASE_DIR, "portfolio.db")
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

app = Flask(__name__)


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def load_config():
    if not os.path.exists(CONFIG_PATH):
        return {}
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def init_db():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    cur = db.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            tagline TEXT NOT NULL,
            bio TEXT NOT NULL
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            enabled INTEGER NOT NULL DEFAULT 1,
            sort_order INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS photos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 0
        )
        """
    )

    config = load_config()
    default_tagline = config.get(
        "tagline",
        "Timeless portraits, real moments, and bold imagery for modern brands.",
    )
    default_bio = config.get(
        "bio",
        "Matt Gibson is a New Jersey-based photographer specializing in portraits, events, real estate, and headshots.\n"
        "With a calm, collaborative approach, Matt creates images that feel natural, elevated, and authentically you.",
    )

    cur.execute("SELECT 1 FROM settings WHERE id = 1")
    if cur.fetchone() is None:
        cur.execute(
            "INSERT INTO settings (id, tagline, bio) VALUES (1, ?, ?)",
            (default_tagline, default_bio),
        )

    seed_services = [
        "Portraits",
        "Events",
        "Real Estate",
        "Headshots",
    ]
    for idx, name in enumerate(seed_services):
        cur.execute("SELECT 1 FROM services WHERE name = ?", (name,))
        if cur.fetchone() is None:
            cur.execute(
                "INSERT INTO services (name, enabled, sort_order) VALUES (?, 1, ?)",
                (name, idx),
            )

    cur.execute("SELECT COUNT(*) as count FROM photos")
    photo_count = cur.fetchone()["count"]
    if photo_count == 0:
        for idx in range(1, 10):
            url = f"https://picsum.photos/seed/mattgibson{idx}/900/700"
            cur.execute(
                "INSERT INTO photos (url, sort_order) VALUES (?, ?)",
                (url, idx),
            )

    db.commit()
    db.close()


@app.route("/")
def index():
    db = get_db()
    settings = db.execute("SELECT * FROM settings WHERE id = 1").fetchone()
    photos = db.execute(
        "SELECT * FROM photos ORDER BY sort_order ASC, id ASC"
    ).fetchall()
    services = db.execute(
        "SELECT * FROM services WHERE enabled = 1 ORDER BY sort_order ASC, id ASC"
    ).fetchall()

    return render_template(
        "index.html",
        settings=settings,
        photos=photos,
        services=services,
    )


@app.route("/admin")
def admin():
    db = get_db()
    settings = db.execute("SELECT * FROM settings WHERE id = 1").fetchone()
    photos = db.execute(
        "SELECT * FROM photos ORDER BY sort_order ASC, id ASC"
    ).fetchall()
    services = db.execute(
        "SELECT * FROM services ORDER BY sort_order ASC, id ASC"
    ).fetchall()

    return render_template(
        "admin.html",
        settings=settings,
        photos=photos,
        services=services,
    )


@app.route("/admin/settings", methods=["POST"])
def admin_settings():
    tagline = request.form.get("tagline", "").strip()
    bio = request.form.get("bio", "").strip()
    if not tagline or not bio:
        return redirect(url_for("admin"))

    db = get_db()
    db.execute(
        "UPDATE settings SET tagline = ?, bio = ? WHERE id = 1",
        (tagline, bio),
    )
    db.commit()
    return redirect(url_for("admin"))


@app.route("/admin/photos/add", methods=["POST"])
def admin_add_photo():
    url = request.form.get("url", "").strip()
    if not url:
        return redirect(url_for("admin"))

    db = get_db()
    cur = db.execute("SELECT COALESCE(MAX(sort_order), 0) + 1 as next_sort FROM photos")
    next_sort = cur.fetchone()["next_sort"]
    db.execute(
        "INSERT INTO photos (url, sort_order) VALUES (?, ?)",
        (url, next_sort),
    )
    db.commit()
    return redirect(url_for("admin"))


@app.route("/admin/photos/delete/<int:photo_id>", methods=["POST"])
def admin_delete_photo(photo_id):
    db = get_db()
    db.execute("DELETE FROM photos WHERE id = ?", (photo_id,))
    db.commit()
    return redirect(url_for("admin"))


@app.route("/admin/reorder", methods=["POST"])
def admin_reorder():
    data = request.get_json(silent=True)
    if not data or "order" not in data:
        return jsonify({"status": "error"}), 400

    order = data.get("order", [])
    if not isinstance(order, list):
        return jsonify({"status": "error"}), 400

    db = get_db()
    for idx, photo_id in enumerate(order):
        db.execute(
            "UPDATE photos SET sort_order = ? WHERE id = ?",
            (idx, photo_id),
        )
    db.commit()
    return jsonify({"status": "ok"})


@app.route("/admin/services", methods=["POST"])
def admin_services():
    db = get_db()
    services = db.execute("SELECT id, name FROM services").fetchall()
    enabled_ids = set(int(sid) for sid in request.form.getlist("service"))

    for service in services:
        enabled = 1 if service["id"] in enabled_ids else 0
        db.execute(
            "UPDATE services SET enabled = ? WHERE id = ?",
            (enabled, service["id"]),
        )

    db.commit()
    return redirect(url_for("admin"))


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=8089, debug=True)
