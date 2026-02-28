import os
import sqlite3
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, flash, session

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "fallback-secret")

# Admin credentials from .env
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Asd@12")

DB_PATH = "messages.db"


# ---------- Helpers ----------
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def require_admin():
    return session.get("admin_logged_in", False)


@app.context_processor
def inject_admin_status():
    return {"is_admin": session.get("admin_logged_in", False)}


# Create DB table once at startup
init_db()


# ---------- Public Routes ----------
@app.route("/")
def home():
    return render_template("index.html", title="Home")


@app.route("/about")
def about():
    return render_template("about.html", title="About")


@app.route("/contact", methods=["GET", "POST"])
def contact():
    success = False

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        msg = request.form.get("message", "").strip()

        if not name or not email or not msg:
            flash("من فضلك املأ كل البيانات", "error")
            return redirect(url_for("contact"))

        conn = get_db()
        conn.execute(
            "INSERT INTO messages (name, email, message, created_at) VALUES (?, ?, ?, ?)",
            (name, email, msg, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
        conn.commit()
        conn.close()

        flash("تم إرسال رسالتك بنجاح ✅", "success")
        success = True
        return redirect(url_for("contact"))

    return render_template("contact.html", title="Contact", success=success)


# ---------- Admin Routes ----------
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["admin_logged_in"] = True
            flash("تم تسجيل الدخول ✅", "success")
            return redirect(url_for("admin_messages"))

        flash("بيانات الدخول غير صحيحة", "error")
        return redirect(url_for("admin_login"))

    return render_template("admin_login.html", title="Admin Login")


@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_logged_in", None)
    flash("تم تسجيل الخروج", "success")
    return redirect(url_for("home"))


@app.route("/admin/messages")
def admin_messages():
    if not require_admin():
        return redirect(url_for("admin_login"))

    q = request.args.get("q", "").strip()

    conn = get_db()
    if q:
        rows = conn.execute("""
            SELECT * FROM messages
            WHERE name LIKE ? OR email LIKE ? OR message LIKE ?
            ORDER BY id DESC
        """, (f"%{q}%", f"%{q}%", f"%{q}%")).fetchall()
    else:
        rows = conn.execute("SELECT * FROM messages ORDER BY id DESC").fetchall()
    conn.close()

    return render_template("messages.html", messages=rows, q=q)


@app.route("/admin/messages/<int:msg_id>/delete", methods=["POST"])
def delete_message(msg_id):
    if not require_admin():
        return redirect(url_for("admin_login"))

    conn = get_db()
    conn.execute("DELETE FROM messages WHERE id = ?", (msg_id,))
    conn.commit()
    conn.close()

    flash("تم حذف الرسالة ✅", "success")
    return redirect(url_for("admin_messages"))


if __name__ == "__main__":
    app.run()