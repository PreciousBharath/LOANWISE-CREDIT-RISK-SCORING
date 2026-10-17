"""Authentication: SQLite user store with salted PBKDF2-SHA256 password hashing + login/register UI."""
import hashlib
import hmac
import os
import re
import sqlite3
import time
from pathlib import Path

import streamlit as st

DB = Path(__file__).resolve().parent.parent / "users.db"
DEMO = {"name": "Demo User", "email": "demo@example.com", "password": "Demo@1234"}


def _conn():
    con = sqlite3.connect(DB, check_same_thread=False)
    con.execute(
        "CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, email TEXT UNIQUE,"
        " salt BLOB, hash BLOB, created REAL, last_login REAL)"
    )
    con.execute(
        "CREATE TABLE IF NOT EXISTS activity (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, action TEXT, detail TEXT, ts REAL)"
    )
    return con


def _hash(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200_000)


def strength(pw: str):
    score = sum([len(pw) >= 8, bool(re.search(r"[A-Z]", pw) and re.search(r"[a-z]", pw)), bool(re.search(r"\d", pw)), bool(re.search(r"[^A-Za-z0-9]", pw))])
    return score, ["Too weak", "Weak", "Fair", "Good", "Strong"][score], ["#ef4444", "#ef4444", "#f59e0b", "#3b82f6", "#10b981"][score]


def create_user(name, email, password):
    salt = os.urandom(16)
    with _conn() as con:
        con.execute("INSERT INTO users (name, email, salt, hash, created) VALUES (?,?,?,?,?)", (name.strip(), email.lower().strip(), salt, _hash(password, salt), time.time()))


def verify(email, password):
    with _conn() as con:
        row = con.execute("SELECT id, name, email, salt, hash, created FROM users WHERE email=?", (email.lower().strip(),)).fetchone()
        if row and hmac.compare_digest(_hash(password, row[3]), row[4]):
            con.execute("UPDATE users SET last_login=? WHERE id=?", (time.time(), row[0]))
            return {"id": row[0], "name": row[1], "email": row[2], "created": row[5]}
    return None


def ensure_demo(demo=DEMO):
    with _conn() as con:
        if not con.execute("SELECT 1 FROM users WHERE email=?", (demo["email"],)).fetchone():
            create_user(demo["name"], demo["email"], demo["password"])


def log(action, detail=""):
    user = st.session_state.get("user")
    if user:
        with _conn() as con:
            con.execute("INSERT INTO activity (user_id, action, detail, ts) VALUES (?,?,?,?)", (user["id"], action, detail, time.time()))


def history(limit=50):
    user = st.session_state.get("user")
    with _conn() as con:
        return con.execute("SELECT action, detail, ts FROM activity WHERE user_id=? ORDER BY ts DESC LIMIT ?", (user["id"], limit)).fetchall()


def change_password(old, new):
    user = st.session_state["user"]
    if not verify(user["email"], old):
        return False
    salt = os.urandom(16)
    with _conn() as con:
        con.execute("UPDATE users SET salt=?, hash=? WHERE id=?", (salt, _hash(new, salt), user["id"]))
    return True


def auth_page(app_name, tagline, features, icon, demo=DEMO):
    """Renders a split hero + login/register card. Returns True once a user is signed in."""
    ensure_demo(demo)
    if st.session_state.get("user"):
        return True
    left, right = st.columns([1.15, 1], gap="large")
    with left:
        feats = "".join(f'<div class="auth-feature">{f}</div>' for f in features)
        st.markdown(
            f"""<div class="auth-hero fade-up"><div class="auth-logo">{icon}</div>
            <h1>{app_name}</h1><p>{tagline}</p>{feats}</div>""",
            unsafe_allow_html=True,
        )
    with right:
        st.markdown('<div class="auth-spacer"></div>', unsafe_allow_html=True)
        tab_login, tab_reg = st.tabs(["🔐 Sign in", "✨ Create account"])
        with tab_login:
            with st.form("login"):
                email = st.text_input("Email", placeholder="you@example.com")
                pw = st.text_input("Password", type="password")
                c1, c2 = st.columns(2)
                go = c1.form_submit_button("Sign in", width="stretch", type="primary")
                demo_go = c2.form_submit_button("Use demo account", width="stretch")
            if go or demo_go:
                u = verify(demo["email"], demo["password"]) if demo_go else verify(email, pw)
                if u:
                    st.session_state.user = u
                    st.toast(f"Welcome, {u['name'].split()[0]}! 👋")
                    log("login")
                    st.rerun()
                else:
                    st.error("Invalid email or password")
            st.caption(f"Demo: `{demo['email']}` / `{demo['password']}`")
        with tab_reg:
            with st.form("register"):
                name = st.text_input("Full name")
                email = st.text_input("Email ", placeholder="you@example.com")
                pw = st.text_input("Password ", type="password", help="8+ chars, upper & lower case, a number and a symbol")
                pw2 = st.text_input("Confirm password", type="password")
                agree = st.checkbox("I agree to the Terms & Privacy Policy")
                sub = st.form_submit_button("Create account", width="stretch", type="primary")
            if pw:
                s, label, color = strength(pw)
                st.markdown(f'<div class="strength"><div style="width:{s*25}%;background:{color}"></div></div><small style="color:{color};font-weight:700">{label}</small>', unsafe_allow_html=True)
            if sub:
                errors = []
                if len(name.strip()) < 3: errors.append("Name must be at least 3 characters")
                if not re.match(r"^\S+@\S+\.\S+$", email): errors.append("Enter a valid email")
                if strength(pw)[0] < 3: errors.append("Password is too weak")
                if pw != pw2: errors.append("Passwords do not match")
                if not agree: errors.append("Please accept the terms")
                if errors:
                    for e in errors: st.error(e)
                else:
                    try:
                        create_user(name, email, pw)
                        st.session_state.user = verify(email, pw)
                        log("register")
                        st.balloons()
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("An account with this email already exists")
    return False


def logout():
    log("logout")
    for k in list(st.session_state.keys()):
        if k != "theme":
            del st.session_state[k]
    st.rerun()
