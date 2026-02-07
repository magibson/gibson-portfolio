from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(APP_DIR, "x_content.db")

app = Flask(__name__)
app.secret_key = "dev-secret-change-me"


PROMPT_TEMPLATES = [
    "A cinematic capture of {topic}. Soft light, crisp detail, and a quiet story.",
    "{topic} — framed with intention, texture, and a hint of motion.",
    "Moments like this: {topic}. Clean lines, natural tones, timeless feel.",
    "Finding beauty in {topic}. Subtle contrast, authentic mood, and depth.",
    "{topic} seen through my lens — calm, focused, and full of character.",
]


STATUSES = ["draft", "scheduled", "posted"]


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS drafts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                image_url TEXT,
                tags TEXT,
                scheduled_at TEXT,
                status TEXT NOT NULL DEFAULT 'draft',
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS threads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS thread_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                thread_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                position INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (thread_id) REFERENCES threads(id)
            )
            """
        )


# Initialize database on import
init_db()


@app.route("/")
def dashboard():
    with get_db() as conn:
        draft_count = conn.execute(
            "SELECT COUNT(*) FROM drafts WHERE status='draft'"
        ).fetchone()[0]
        scheduled_posts = conn.execute(
            "SELECT * FROM drafts WHERE status='scheduled' ORDER BY scheduled_at ASC"
        ).fetchall()
    return render_template(
        "dashboard.html",
        draft_count=draft_count,
        scheduled_posts=scheduled_posts,
    )


@app.post("/drafts/quick-add")
def quick_add_draft():
    content = request.form.get("content", "").strip()
    if not content:
        flash("Draft text is required.")
        return redirect(url_for("dashboard"))

    image_url = request.form.get("image_url", "").strip()
    tags = request.form.get("tags", "").strip()
    scheduled_at = request.form.get("scheduled_at", "").strip() or None
    created_at = datetime.utcnow().isoformat()
    status = "scheduled" if scheduled_at else "draft"

    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO drafts (content, image_url, tags, scheduled_at, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (content, image_url, tags, scheduled_at, status, created_at),
        )
    flash("Draft added to queue.")
    return redirect(url_for("dashboard"))


@app.route("/drafts", methods=["GET", "POST"])
def drafts():
    if request.method == "POST":
        content = request.form.get("content", "").strip()
        if not content:
            flash("Draft text is required.")
            return redirect(url_for("drafts"))
        image_url = request.form.get("image_url", "").strip()
        tags = request.form.get("tags", "").strip()
        scheduled_at = request.form.get("scheduled_at", "").strip() or None
        status = request.form.get("status", "draft")
        if status not in STATUSES:
            status = "draft"
        created_at = datetime.utcnow().isoformat()
        with get_db() as conn:
            conn.execute(
                """
                INSERT INTO drafts (content, image_url, tags, scheduled_at, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (content, image_url, tags, scheduled_at, status, created_at),
            )
        flash("Draft saved.")
        return redirect(url_for("drafts"))

    with get_db() as conn:
        drafts_list = conn.execute(
            "SELECT * FROM drafts ORDER BY created_at DESC"
        ).fetchall()
    return render_template("drafts.html", drafts=drafts_list, statuses=STATUSES)


@app.post("/drafts/update/<int:draft_id>")
def update_draft(draft_id: int):
    status = request.form.get("status", "draft")
    if status not in STATUSES:
        status = "draft"
    scheduled_at = request.form.get("scheduled_at", "").strip() or None
    with get_db() as conn:
        conn.execute(
            "UPDATE drafts SET status=?, scheduled_at=? WHERE id=?",
            (status, scheduled_at, draft_id),
        )
    flash("Draft updated.")
    return redirect(url_for("drafts"))


@app.post("/drafts/delete/<int:draft_id>")
def delete_draft(draft_id: int):
    with get_db() as conn:
        conn.execute("DELETE FROM drafts WHERE id=?", (draft_id,))
    flash("Draft removed.")
    return redirect(url_for("drafts"))


@app.route("/threads", methods=["GET", "POST"])
def threads():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        if not title:
            flash("Thread title is required.")
            return redirect(url_for("threads"))
        created_at = datetime.utcnow().isoformat()
        with get_db() as conn:
            conn.execute(
                "INSERT INTO threads (title, created_at) VALUES (?, ?)",
                (title, created_at),
            )
        flash("Thread created.")
        return redirect(url_for("threads"))

    with get_db() as conn:
        threads_list = conn.execute(
            "SELECT * FROM threads ORDER BY created_at DESC"
        ).fetchall()
    return render_template("threads.html", threads=threads_list)


@app.route("/threads/<int:thread_id>")
def thread_detail(thread_id: int):
    with get_db() as conn:
        thread = conn.execute(
            "SELECT * FROM threads WHERE id=?", (thread_id,)
        ).fetchone()
        if not thread:
            flash("Thread not found.")
            return redirect(url_for("threads"))
        items = conn.execute(
            """
            SELECT * FROM thread_items
            WHERE thread_id=?
            ORDER BY position ASC
            """,
            (thread_id,),
        ).fetchall()
    return render_template("thread_detail.html", thread=thread, items=items)


@app.post("/threads/<int:thread_id>/add")
def add_thread_item(thread_id: int):
    content = request.form.get("content", "").strip()
    if not content:
        flash("Tweet text is required.")
        return redirect(url_for("thread_detail", thread_id=thread_id))
    created_at = datetime.utcnow().isoformat()
    with get_db() as conn:
        max_pos = conn.execute(
            "SELECT COALESCE(MAX(position), 0) FROM thread_items WHERE thread_id=?",
            (thread_id,),
        ).fetchone()[0]
        conn.execute(
            """
            INSERT INTO thread_items (thread_id, content, position, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (thread_id, content, max_pos + 1, created_at),
        )
    return redirect(url_for("thread_detail", thread_id=thread_id))


@app.post("/threads/delete/<int:thread_id>")
def delete_thread(thread_id: int):
    with get_db() as conn:
        conn.execute("DELETE FROM thread_items WHERE thread_id=?", (thread_id,))
        conn.execute("DELETE FROM threads WHERE id=?", (thread_id,))
    flash("Thread deleted.")
    return redirect(url_for("threads"))


@app.post("/threads/<int:thread_id>/item/<int:item_id>/delete")
def delete_thread_item(thread_id: int, item_id: int):
    with get_db() as conn:
        conn.execute("DELETE FROM thread_items WHERE id=?", (item_id,))
    return redirect(url_for("thread_detail", thread_id=thread_id))


def swap_positions(conn: sqlite3.Connection, a_id: int, b_id: int) -> None:
    a_pos = conn.execute("SELECT position FROM thread_items WHERE id=?", (a_id,)).fetchone()
    b_pos = conn.execute("SELECT position FROM thread_items WHERE id=?", (b_id,)).fetchone()
    if not a_pos or not b_pos:
        return
    conn.execute("UPDATE thread_items SET position=? WHERE id=?", (b_pos[0], a_id))
    conn.execute("UPDATE thread_items SET position=? WHERE id=?", (a_pos[0], b_id))


@app.post("/threads/<int:thread_id>/item/<int:item_id>/move/<direction>")
def move_thread_item(thread_id: int, item_id: int, direction: str):
    with get_db() as conn:
        items = conn.execute(
            "SELECT id FROM thread_items WHERE thread_id=? ORDER BY position ASC",
            (thread_id,),
        ).fetchall()
        ids = [row[0] for row in items]
        if item_id not in ids:
            return redirect(url_for("thread_detail", thread_id=thread_id))
        index = ids.index(item_id)
        if direction == "up" and index > 0:
            swap_positions(conn, ids[index], ids[index - 1])
        elif direction == "down" and index < len(ids) - 1:
            swap_positions(conn, ids[index], ids[index + 1])
    return redirect(url_for("thread_detail", thread_id=thread_id))


@app.route("/generator", methods=["GET", "POST"])
def generator():
    suggestions = []
    topic = ""
    if request.method == "POST":
        topic = request.form.get("topic", "").strip()
        if not topic:
            flash("Please enter a topic or photo description.")
            return redirect(url_for("generator"))
        suggestions = [
            template.format(topic=topic)
            for template in PROMPT_TEMPLATES[:3]
        ]
    return render_template("generator.html", suggestions=suggestions, topic=topic)


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=8086, debug=True)
