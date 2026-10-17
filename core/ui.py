"""Theming & UI helpers: multiple colour themes, glassmorphism cards, animations and Plotly styling."""
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

THEMES = {
    "🌌 Aurora": {"bg": "#0b0d17", "bg2": "#141830", "card": "rgba(26,30,58,.72)", "text": "#eef0ff", "muted": "#9aa0c3", "a": "#7c3aed", "b": "#06b6d4"},
    "🌊 Ocean": {"bg": "#04131f", "bg2": "#0a2233", "card": "rgba(12,40,60,.72)", "text": "#e6f6ff", "muted": "#8fb3c7", "a": "#2563eb", "b": "#22d3ee"},
    "🌅 Sunset": {"bg": "#160b12", "bg2": "#26121d", "card": "rgba(48,20,34,.72)", "text": "#fff1f4", "muted": "#c9a0ad", "a": "#f97316", "b": "#ec4899"},
    "🌿 Emerald": {"bg": "#06130e", "bg2": "#0d241b", "card": "rgba(16,44,32,.72)", "text": "#eafff5", "muted": "#94c2ad", "a": "#059669", "b": "#a3e635"},
    "🌙 Midnight": {"bg": "#020617", "bg2": "#0f172a", "card": "rgba(15,23,42,.78)", "text": "#e2e8f0", "muted": "#94a3b8", "a": "#6366f1", "b": "#a855f7"},
}


def theme():
    return THEMES[st.session_state.get("theme", list(THEMES)[0])]


def inject_css():
    t = theme()
    anim = "" if st.session_state.get("motion", True) else "*{animation:none!important;transition:none!important}"
    st.markdown(
        f"""<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&display=swap');
:root {{ --a:{t['a']}; --b:{t['b']}; --bg:{t['bg']}; --bg2:{t['bg2']}; --card:{t['card']}; --text:{t['text']}; --muted:{t['muted']}; }}
html, body, [class*="css"], .stApp, .stMarkdown, button, input, textarea {{ font-family:'Plus Jakarta Sans',sans-serif !important; }}
.stApp {{ background: radial-gradient(1200px 600px at -10% -10%, color-mix(in srgb, var(--a) 28%, transparent), transparent 60%),
          radial-gradient(900px 500px at 110% 110%, color-mix(in srgb, var(--b) 22%, transparent), transparent 60%), var(--bg); color: var(--text); }}
[data-testid="stHeader"] {{ background: transparent; }}
[data-testid="stSidebar"] {{ background: color-mix(in srgb, var(--bg2) 88%, transparent); backdrop-filter: blur(16px); border-right: 1px solid rgba(255,255,255,.06); }}
h1,h2,h3,h4 {{ color: var(--text) !important; font-weight: 800 !important; }}
p, label, .stCaption, [data-testid="stMarkdownContainer"] {{ color: var(--text); }}
.block-container {{ padding-top: 2rem; animation: pageIn .6s cubic-bezier(.2,.8,.2,1); }}
@keyframes pageIn {{ from {{ opacity:0; transform: translateY(14px); }} }}
.fade-up {{ animation: pageIn .7s cubic-bezier(.2,.8,.2,1) both; }}
.hero {{ padding: 26px 30px; border-radius: 22px; background: linear-gradient(135deg, var(--a), var(--b)); color: #fff; position: relative; overflow: hidden; margin-bottom: 18px;
        box-shadow: 0 20px 50px -20px var(--a); animation: pageIn .6s both; }}
.hero::after {{ content:''; position:absolute; width:380px; height:380px; border-radius:50%; border:60px solid rgba(255,255,255,.08); right:-120px; top:-160px; animation: spin 30s linear infinite; }}
.hero h1 {{ color:#fff !important; margin:0; font-size: 2rem; }} .hero p {{ color: rgba(255,255,255,.9); margin: 4px 0 0; }}
@keyframes spin {{ to {{ transform: rotate(360deg); }} }}
.kpi {{ background: var(--card); border: 1px solid rgba(255,255,255,.07); border-radius: 18px; padding: 18px; backdrop-filter: blur(14px);
       transition: transform .3s, box-shadow .3s; animation: pageIn .6s both; height: 100%; }}
.kpi:hover {{ transform: translateY(-5px); box-shadow: 0 18px 36px -18px var(--a); }}
.kpi .label {{ color: var(--muted); font-size: .85rem; font-weight: 600; }} .kpi .value {{ font-size: 1.55rem; font-weight: 800; color: var(--text); }}
.kpi .icon {{ width: 44px; height: 44px; border-radius: 13px; display: grid; place-items: center; font-size: 22px; background: linear-gradient(135deg, var(--a), var(--b)); float: right; }}
.kpi .delta-up {{ color: #10b981; font-weight: 700; font-size: .8rem; }} .kpi .delta-down {{ color: #ef4444; font-weight: 700; font-size: .8rem; }}
.card {{ background: var(--card); border: 1px solid rgba(255,255,255,.07); border-radius: 18px; padding: 18px 20px; backdrop-filter: blur(14px); animation: pageIn .6s both; margin-bottom: 12px; }}
.badge {{ display:inline-block; padding: 3px 11px; border-radius: 999px; font-size: .75rem; font-weight: 700; background: color-mix(in srgb, var(--a) 25%, transparent); color: #fff; margin: 2px; }}
.badge.red {{ background: rgba(239,68,68,.22); color: #fca5a5; }} .badge.green {{ background: rgba(16,185,129,.22); color: #6ee7b7; }} .badge.amber {{ background: rgba(245,158,11,.22); color: #fcd34d; }}
.pulse {{ display:inline-block; width:10px; height:10px; border-radius:50%; background:#10b981; box-shadow:0 0 0 0 #10b981; animation: ping 1.5s infinite; margin-right:6px; }}
@keyframes ping {{ 70% {{ box-shadow: 0 0 0 10px transparent; }} 100% {{ box-shadow: 0 0 0 0 transparent; }} }}
.stButton>button, .stFormSubmitButton>button, .stDownloadButton>button {{ border-radius: 12px !important; font-weight: 700 !important; transition: all .25s !important; }}
.stButton>button[kind="primary"], .stFormSubmitButton>button[kind="primary"] {{ background: linear-gradient(135deg, var(--a), var(--b)) !important; border: none !important; color:#fff !important; }}
.stButton>button:hover, .stFormSubmitButton>button:hover {{ transform: translateY(-2px); box-shadow: 0 10px 22px -10px var(--a); }}
[data-testid="stMetric"] {{ background: var(--card); border-radius: 16px; padding: 14px 16px; border: 1px solid rgba(255,255,255,.07); }}
.stTabs [data-baseweb="tab-list"] {{ gap: 6px; }} .stTabs [data-baseweb="tab"] {{ border-radius: 10px; padding: 8px 16px; background: rgba(255,255,255,.04); }}
.stTabs [aria-selected="true"] {{ background: linear-gradient(135deg, var(--a), var(--b)) !important; color:#fff !important; }}
.auth-spacer {{ height: 6vh; }}
.auth-hero {{ margin-top: 6vh; padding: 40px; border-radius: 26px; background: linear-gradient(135deg, var(--a), var(--b)); color:#fff; position: relative; overflow:hidden; box-shadow: 0 30px 60px -25px var(--a); }}
.auth-hero::before {{ content:''; position:absolute; width:420px; height:420px; border-radius:50%; border:70px solid rgba(255,255,255,.08); right:-160px; top:-160px; animation: spin 40s linear infinite; }}
.auth-hero h1 {{ color:#fff !important; font-size: 2.6rem; margin: 10px 0 6px; }} .auth-hero p {{ color: rgba(255,255,255,.92); font-size: 1.05rem; }}
.auth-logo {{ width: 64px; height: 64px; border-radius: 18px; background: rgba(255,255,255,.2); display:grid; place-items:center; font-size: 34px; animation: float 4s ease-in-out infinite; }}
@keyframes float {{ 50% {{ transform: translateY(-8px) rotate(-4deg); }} }}
.auth-feature {{ background: rgba(255,255,255,.13); padding: 11px 15px; border-radius: 14px; margin-top: 10px; font-weight: 600; animation: pageIn .6s both; }}
.auth-feature:nth-child(4) {{ animation-delay: .1s }} .auth-feature:nth-child(5) {{ animation-delay: .2s }} .auth-feature:nth-child(6) {{ animation-delay: .3s }} .auth-feature:nth-child(7) {{ animation-delay: .4s }}
.strength {{ height: 6px; border-radius: 9px; background: rgba(255,255,255,.1); overflow:hidden; margin-top: -6px; }} .strength div {{ height: 100%; transition: width .4s; }}
.user-chip {{ display:flex; align-items:center; gap:10px; padding:10px; border-radius:14px; background: var(--card); margin-bottom: 8px; }}
.avatar {{ width:38px; height:38px; border-radius:50%; display:grid; place-items:center; font-weight:800; color:#fff; background: linear-gradient(135deg, var(--a), var(--b)); }}
{anim}
</style>""",
        unsafe_allow_html=True,
    )
    _plotly_theme(t)


def _plotly_theme(t):
    tpl = go.layout.Template(pio.templates["plotly_dark"])
    tpl.layout.paper_bgcolor = "rgba(0,0,0,0)"
    tpl.layout.plot_bgcolor = "rgba(0,0,0,0)"
    tpl.layout.font = dict(family="Plus Jakarta Sans", color=t["text"])
    tpl.layout.colorway = [t["a"], t["b"], "#f59e0b", "#ef4444", "#10b981", "#ec4899", "#3b82f6"]
    tpl.layout.margin = dict(l=10, r=10, t=40, b=10)
    pio.templates["app"] = tpl
    pio.templates.default = "app"


def hero(title, subtitle, icon=""):
    st.markdown(f'<div class="hero"><h1>{icon} {title}</h1><p>{subtitle}</p></div>', unsafe_allow_html=True)


def kpi(col, label, value, icon, delta=None, up=True):
    d = f'<div class="{"delta-up" if up else "delta-down"}">{"▲" if up else "▼"} {delta}</div>' if delta else ""
    col.markdown(f'<div class="kpi"><div class="icon">{icon}</div><div class="label">{label}</div><div class="value">{value}</div>{d}</div>', unsafe_allow_html=True)


def card(html):
    st.markdown(f'<div class="card">{html}</div>', unsafe_allow_html=True)


def sidebar(app_name, icon, pages):
    """Sidebar with user chip, navigation, theme picker and logout. Returns selected page."""
    from core.auth import logout

    with st.sidebar:
        st.markdown(f"<h2 style='margin:0 0 10px'>{icon} {app_name}</h2>", unsafe_allow_html=True)
        u = st.session_state.user
        initials = "".join(p[0] for p in u["name"].split()[:2]).upper()
        st.markdown(f'<div class="user-chip"><div class="avatar">{initials}</div><div><b>{u["name"]}</b><br><small style="color:var(--muted)">{u["email"]}</small></div></div>', unsafe_allow_html=True)
        page = st.radio("Navigate", pages, label_visibility="collapsed")
        st.divider()
        st.selectbox("🎨 Theme", list(THEMES), key="theme")
        st.toggle("✨ Animations", value=True, key="motion")
        if st.button("🚪 Logout", width="stretch"):
            logout()
    return page


def account_page():
    from core.auth import change_password, history, strength
    import datetime as dt

    u = st.session_state.user
    hero("My Account", "Profile, security and activity history", "👤")
    c1, c2 = st.columns(2)
    with c1:
        card(f"<h3>{u['name']}</h3><p>📧 {u['email']}<br>📅 Member since {dt.datetime.fromtimestamp(u['created']).strftime('%d %b %Y')}</p>")
        with st.form("pw"):
            st.markdown("**🔑 Change password**")
            old = st.text_input("Current password", type="password")
            new = st.text_input("New password", type="password")
            if st.form_submit_button("Update password", type="primary"):
                if strength(new)[0] < 3:
                    st.error("New password is too weak")
                elif change_password(old, new):
                    st.success("Password updated")
                else:
                    st.error("Current password is incorrect")
    with c2:
        st.markdown("**🕒 Recent activity**")
        rows = history()
        if not rows:
            st.info("No activity yet")
        for a, d, ts in rows[:15]:
            st.markdown(f"<div class='card' style='padding:10px 14px;margin-bottom:6px'><b>{a}</b> <small style='color:var(--muted)'>· {dt.datetime.fromtimestamp(ts).strftime('%d %b %H:%M')}</small><br><small>{d}</small></div>", unsafe_allow_html=True)
