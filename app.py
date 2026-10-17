"""LoanWise — AI credit-risk scoring & smart loan approval (Streamlit, scikit-learn)."""
import datetime as dt

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from core import auth, ui
from core.engine import (CAT, GRADES, HOMES, NUM, PURPOSES, REGIONS, amortization, counterfactual, emi, generate, grade, list_apps, price, reason_codes,
                         save_app, to_score, train)

st.set_page_config(page_title="LoanWise · AI Credit Risk", page_icon="🏦", layout="wide")
ui.inject_css()
APP, ICON = "LoanWise", "🏦"
if not auth.auth_page(APP, "Instant, explainable loan decisions — credit scoring, risk-based pricing and portfolio analytics.",
                      ["⚡ Credit decision in seconds with a 300–900 score", "🧾 Reason codes & ‘how to get approved’ suggestions",
                       "💹 EMI, amortisation & prepayment simulator", "⚖️ Model validation: Gini, KS, calibration & fairness"], ICON,
                      demo={"name": "Credit Officer", "email": "demo@loanwise.ai", "password": "Demo@1234"}):
    st.stop()


@st.cache_data(show_spinner="Building the loan book…")
def data():
    return generate()


@st.cache_resource(show_spinner="Training credit-risk models…")
def models():
    return train(data())


df, bundle = data(), models()
names = list(bundle["results"])
uid = st.session_state.user["id"]
page = ui.sidebar(APP, ICON, ["🏦 Loan Application", "🗂️ My Applications", "💹 EMI Planner", "📊 Portfolio Analytics", "🧪 Model Validation", "👤 Account"])

if page == "🏦 Loan Application":
    ui.hero("Smart Loan Application", "Fill in the applicant’s profile — get a score, decision, price and explanation instantly", "🏦")
    with st.form("app"):
        t1, t2, t3 = st.tabs(["👤 Applicant", "💼 Financials", "📝 Loan"])
        with t1:
            c = st.columns(4)
            name = c[0].text_input("Applicant name", "Arjun Kumar")
            age = c[1].number_input("Age", 21, 70, 32)
            home = c[2].selectbox("Residence", HOMES, index=2)
            region = c[3].selectbox("Region", REGIONS)
        with t2:
            c = st.columns(4)
            income = c[0].number_input("Annual income (₹ lakh)", 1.0, 200.0, 8.0, 0.5)
            score_in = c[1].slider("Bureau credit score", 300, 900, 705)
            emp = c[2].number_input("Employment (years)", 0.0, 45.0, 3.0, 0.5)
            dti = c[3].slider("Existing debt-to-income", 0.0, 0.85, 0.32, 0.01)
            c = st.columns(4)
            existing = c[0].number_input("Existing loans", 0, 10, 1)
            late = c[1].number_input("Late payments (2 yrs)", 0, 12, 0)
        with t3:
            c = st.columns(4)
            amount = c[0].number_input("Loan amount (₹ lakh)", 0.5, 300.0, 10.0, 0.5)
            term = c[1].select_slider("Tenure (months)", [12, 24, 36, 48, 60, 84], 48)
            purpose = c[2].selectbox("Purpose", PURPOSES, index=3)
            model_name = c[3].selectbox("Risk model", names, index=names.index(bundle["best"]))
        cutoff = st.slider("Approval cut-off (max acceptable default probability)", 0.05, 0.35, 0.15, 0.01)
        go_ = st.form_submit_button("⚡ Get instant decision", type="primary", width="stretch")
    row = pd.DataFrame([dict(age=age, income_lpa=income, loan_amount_l=amount, term_months=term, credit_score=score_in, employment_years=emp, dti=dti,
                             existing_loans=existing, late_payments_2y=late, loan_to_income=amount / income, purpose=purpose, home=home, region=region)])
    mb = bundle["results"][model_name]
    p = float(mb["model"].predict_proba(row[NUM + CAT])[0, 1])
    sc, (g, gcolor), rate = int(to_score(p)), grade(p), price(p)
    decision = "APPROVED" if p < cutoff * 0.7 else "CONDITIONAL" if p < cutoff else "DECLINED"
    dcolor = {"APPROVED": "green", "CONDITIONAL": "amber", "DECLINED": "red"}[decision]
    e = emi(amount * 1e5, rate, term)
    new_dti = dti + e * 12 / (income * 1e5)
    k = st.columns(5)
    ui.kpi(k[0], "LoanWise score", sc, "🏅")
    ui.kpi(k[1], "Default risk", f"{p * 100:.1f}%", "📉")
    ui.kpi(k[2], "Risk grade", g, "🎚️")
    ui.kpi(k[3], "Offered rate", f"{rate:.2f}%", "💰")
    ui.kpi(k[4], "Monthly EMI", f"₹{e:,.0f}", "🗓️")
    l, r = st.columns([1, 1.3])
    with l:
        fig = go.Figure(go.Indicator(mode="gauge+number", value=sc, title={"text": "Credit score"},
                                     gauge={"axis": {"range": [300, 900]}, "bar": {"color": gcolor},
                                            "steps": [{"range": [300, 580], "color": "rgba(239,68,68,.18)"}, {"range": [580, 670], "color": "rgba(249,115,22,.15)"}, {"range": [670, 740], "color": "rgba(245,158,11,.15)"}, {"range": [740, 800], "color": "rgba(132,204,22,.15)"}, {"range": [800, 900], "color": "rgba(16,185,129,.18)"}]}))
        fig.update_layout(height=280)
        st.plotly_chart(fig, width="stretch")
        st.markdown(f"<div class='card' style='text-align:center'><span class='badge {dcolor}' style='font-size:1.2rem;padding:10px 22px'>{decision}</span><p style='margin-top:10px'>Post-loan debt-to-income: <b>{new_dti * 100:.0f}%</b> {'⚠️' if new_dti > 0.5 else '✅'}</p></div>", unsafe_allow_html=True)
    with r:
        st.markdown("#### 🧾 Key factors")
        codes = reason_codes(mb, row[NUM + CAT])
        if not codes:
            st.success("No significant adverse factors — strong application.")
        for t, d in codes:
            st.markdown(f"<div class='card' style='padding:10px 14px;margin-bottom:6px'>🔻 <b>{t}</b><div class='strength' style='margin-top:6px'><div style='width:{min(100, d * 400):.0f}%;background:#ef4444'></div></div><small style='color:var(--muted)'>adds ≈{d * 100:.1f} pts of default risk</small></div>", unsafe_allow_html=True)
        if decision != "APPROVED":
            cf = counterfactual(mb, row[NUM + CAT], cutoff * 0.7)
            tips = []
            if "amount" in cf: tips.append(f"reduce the loan to **₹{cf['amount']:.1f} L**")
            if "score" in cf: tips.append(f"raise the credit score to **{cf['score']}**")
            st.info("💡 To get approved: " + (" or ".join(tips) if tips else "add a co-applicant or collateral") + ".")
    if go_:
        save_app(uid, name, amount, p, sc, g, decision, rate, row.iloc[0].to_dict())
        auth.log("application", f"{name}: ₹{amount}L → {decision} ({sc})")
        st.toast(f"Application saved — {decision}")
        if decision == "APPROVED":
            st.balloons()

elif page == "🗂️ My Applications":
    ui.hero("My Applications", "Every decision you’ve run — stored securely per account", "🗂️")
    a = list_apps(uid)
    if a.empty:
        st.info("No applications yet — submit one from **Loan Application**.")
    else:
        a["date"] = pd.to_datetime(a.ts, unit="s").dt.strftime("%d %b %Y %H:%M")
        k = st.columns(4)
        ui.kpi(k[0], "Applications", len(a), "🗂️")
        ui.kpi(k[1], "Approval rate", f"{(a.decision == 'APPROVED').mean() * 100:.0f}%", "✅")
        ui.kpi(k[2], "Amount approved", f"₹{a.loc[a.decision == 'APPROVED', 'amount'].sum():,.1f} L", "💰")
        ui.kpi(k[3], "Avg score", f"{a.score.mean():.0f}", "🏅")
        st.dataframe(a[["date", "applicant", "amount", "score", "grade", "pd", "rate", "decision"]], width="stretch", hide_index=True,
                     column_config={"pd": st.column_config.ProgressColumn("Default prob.", min_value=0, max_value=1, format="%.2f"), "amount": st.column_config.NumberColumn("Amount (₹ L)")})
        st.download_button("⬇️ Export CSV", a.drop(columns="ts").to_csv(index=False), "loanwise_applications.csv")

elif page == "💹 EMI Planner":
    ui.hero("EMI & Prepayment Planner", "See exactly where every rupee goes — and how much a prepayment saves", "💹")
    c = st.columns(5)
    P = c[0].number_input("Loan (₹ lakh)", 0.5, 500.0, 25.0, 0.5) * 1e5
    rate = c[1].number_input("Interest rate (%)", 5.0, 30.0, 10.5, 0.1)
    n = c[2].slider("Tenure (months)", 6, 360, 120, 6)
    pre = c[3].number_input("One-time prepayment (₹ lakh)", 0.0, 100.0, 2.0, 0.5) * 1e5
    pm = c[4].slider("Prepay in month", 1, n, min(24, n))
    base, opt = amortization(P, rate, n), amortization(P, rate, n, pre, pm)
    k = st.columns(4)
    ui.kpi(k[0], "Monthly EMI", f"₹{emi(P, rate, n):,.0f}", "🗓️")
    ui.kpi(k[1], "Total interest", f"₹{base.interest.sum() / 1e5:,.2f} L", "💸")
    ui.kpi(k[2], "Interest saved", f"₹{(base.interest.sum() - opt.interest.sum()) / 1e5:,.2f} L", "🎉")
    ui.kpi(k[3], "Months saved", f"{len(base) - len(opt)}", "⏩")
    c1, c2 = st.columns([1.6, 1])
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=base.month, y=base.balance, name="Balance (no prepayment)", line=dict(width=3)))
    fig.add_trace(go.Scatter(x=opt.month, y=opt.balance, name="Balance (with prepayment)", line=dict(width=3, dash="dot")))
    fig.update_layout(title="Outstanding balance", height=380, legend=dict(orientation="h", y=-0.2))
    c1.plotly_chart(fig, width="stretch")
    c2.plotly_chart(px.pie(names=["Principal", "Interest"], values=[P, base.interest.sum()], hole=0.6, title="Total payment split"), width="stretch")
    yearly = base.assign(year=(base.month - 1) // 12 + 1).groupby("year")[["principal", "interest"]].sum().reset_index()
    st.plotly_chart(px.bar(yearly, x="year", y=["principal", "interest"], title="Yearly principal vs interest", barmode="stack"), width="stretch")
    with st.expander("📄 Full amortisation schedule"):
        st.dataframe(base.round(0), width="stretch", hide_index=True)

elif page == "📊 Portfolio Analytics":
    ui.hero("Portfolio Analytics", f"Risk profile of {len(df):,} historical loans", "📊")
    m = bundle["results"][bundle["best"]]["model"]
    d = df.copy()
    d["pd"] = m.predict_proba(d[NUM + CAT])[:, 1]
    d["score"] = to_score(d.pd)
    d["grade"] = [grade(p)[0] for p in d.pd]
    k = st.columns(4)
    ui.kpi(k[0], "Loans", f"{len(d):,}", "📚")
    ui.kpi(k[1], "Observed default rate", f"{d.default.mean() * 100:.1f}%", "⚠️")
    ui.kpi(k[2], "Book value", f"₹{d.loan_amount_l.sum() / 100:,.0f} Cr", "🏦")
    ui.kpi(k[3], "Expected loss (LGD 45%)", f"₹{(d.pd * d.loan_amount_l * 0.45).sum() / 100:,.1f} Cr", "📉")
    c1, c2 = st.columns(2)
    gs = d.groupby("grade").agg(loans=("pd", "size"), default_rate=("default", "mean")).reindex([g for g, *_ in GRADES]).reset_index()
    fig = go.Figure(go.Bar(x=gs.grade, y=gs.loans, name="Loans", marker_color=[c for *_, c in GRADES]))
    fig.add_trace(go.Scatter(x=gs.grade, y=gs.default_rate, name="Default rate", yaxis="y2", line=dict(width=3, color="white"), mode="lines+markers"))
    fig.update_layout(title="Risk grades: volume & realised default rate", yaxis2=dict(overlaying="y", side="right", tickformat=".0%"), height=380)
    c1.plotly_chart(fig, width="stretch")
    c2.plotly_chart(px.histogram(d, x="score", color=d.default.map({0: "Repaid", 1: "Defaulted"}), nbins=60, barmode="overlay", opacity=0.7, title="Score distribution by outcome"), width="stretch")
    c1, c2 = st.columns(2)
    pr = d.groupby("purpose").default.mean().sort_values().reset_index()
    c1.plotly_chart(px.bar(pr, x="default", y="purpose", orientation="h", title="Default rate by purpose", color="default", color_continuous_scale="Reds"), width="stretch")
    d["score_band"] = pd.cut(d.credit_score, [300, 600, 650, 700, 750, 800, 900])
    sb = d.groupby("score_band", observed=True).default.mean().reset_index()
    sb["score_band"] = sb.score_band.astype(str)
    c2.plotly_chart(px.line(sb, x="score_band", y="default", markers=True, title="Bureau score band vs default rate"), width="stretch")

elif page == "🧪 Model Validation":
    ui.hero("Model Validation", "Discrimination, calibration, lift and fairness — the checks a credit-risk team runs", "🧪")
    res = bundle["results"]
    t = pd.DataFrame({n: {"AUC": r["auc"], "Gini": r["gini"], "KS": r["ks"]} for n, r in res.items()}).T
    st.dataframe(t.style.format("{:.3f}").background_gradient(cmap="Blues"), width="stretch")
    c1, c2 = st.columns(2)
    fig = go.Figure()
    for n_, r in res.items():
        fig.add_trace(go.Scatter(x=r["roc"][0], y=r["roc"][1], name=f"{n_} (Gini {r['gini']:.2f})", line=dict(width=3)))
    fig.add_trace(go.Scatter(x=[0, 1], y=[0, 1], line=dict(dash="dash", color="gray"), showlegend=False))
    fig.update_layout(title="ROC curves", height=380, legend=dict(orientation="h", y=-0.25))
    c1.plotly_chart(fig, width="stretch")
    fig = go.Figure()
    for n_, r in res.items():
        fig.add_trace(go.Scatter(x=r["calib"][0], y=r["calib"][1], name=n_, mode="lines+markers", line=dict(width=3)))
    fig.add_trace(go.Scatter(x=[0, 0.6], y=[0, 0.6], line=dict(dash="dash", color="gray"), showlegend=False))
    fig.update_layout(title="Calibration: predicted vs observed default", xaxis_title="predicted PD", yaxis_title="observed default rate", height=380, legend=dict(orientation="h", y=-0.25))
    c2.plotly_chart(fig, width="stretch")
    best = res[bundle["best"]]
    y, p = bundle["y_test"], best["proba"]
    order = np.argsort(-p)
    cum = np.cumsum(y[order]) / y.sum()
    pct = np.arange(1, len(y) + 1) / len(y)
    c1, c2 = st.columns(2)
    fig = go.Figure(go.Scatter(x=pct, y=cum, name="Model", fill="tozeroy", line=dict(width=3)))
    fig.add_trace(go.Scatter(x=[0, 1], y=[0, 1], name="Random", line=dict(dash="dash", color="gray")))
    fig.update_layout(title=f"Cumulative gains — top 20% riskiest catch {cum[int(len(y) * .2)] * 100:.0f}% of defaults", height=360, xaxis_tickformat=".0%", yaxis_tickformat=".0%")
    c1.plotly_chart(fig, width="stretch")
    with c2:
        thr = st.slider("Approval cut-off", 0.05, 0.4, 0.15, 0.01)
        X = bundle["X_test"].assign(approved=p < thr, age_band=pd.cut(bundle["X_test"].age, [20, 30, 40, 50, 70], labels=["21-30", "31-40", "41-50", "51+"]))
        fair = X.groupby(["region"]).approved.mean().rename("Region").reset_index().rename(columns={"region": "group"})
        fair2 = X.groupby("age_band", observed=True).approved.mean().rename("Age band").reset_index().rename(columns={"age_band": "group"})
        f = pd.concat([fair.assign(attr="Region"), fair2.assign(attr="Age band").rename(columns={"Age band": "Region"})])
        st.plotly_chart(px.bar(f, x="group", y="Region", color="attr", title="Fairness check — approval rate by group", labels={"Region": "approval rate"}, height=320), width="stretch")
        gap = X.groupby("region").approved.mean()
        st.caption(f"Demographic-parity ratio across regions: **{gap.min() / gap.max():.2f}** (≥ 0.80 passes the four-fifths rule)")
else:
    ui.account_page()
