"""LoanWise engine: synthetic applicant book, default-risk models, scorecard, pricing, reason codes, counterfactuals, EMI."""
import json
import sqlite3
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.calibration import calibration_curve
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, roc_curve
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

DB = Path(__file__).resolve().parent.parent / "users.db"
PURPOSES = ["home_improvement", "education", "business", "vehicle", "medical", "wedding", "debt_consolidation", "travel"]
HOMES = ["own", "mortgage", "rent"]
REGIONS = ["South", "North", "West", "East"]
NUM = ["age", "income_lpa", "loan_amount_l", "term_months", "credit_score", "employment_years", "dti", "existing_loans", "late_payments_2y", "loan_to_income"]
CAT = ["purpose", "home", "region"]
PURPOSE_RISK = {"home_improvement": -0.2, "education": 0.1, "business": 0.45, "vehicle": -0.1, "medical": 0.3, "wedding": 0.25, "debt_consolidation": 0.35, "travel": 0.4}


def generate(n=15000, seed=11):
    r = np.random.default_rng(seed)
    age = r.integers(21, 65, n)
    income = np.round(r.lognormal(1.9, 0.55, n), 2)  # lakhs per annum
    amount = np.round(income * r.uniform(0.3, 3.5, n), 2)
    term = r.choice([12, 24, 36, 48, 60, 84], n, p=[.1, .2, .3, .15, .15, .1])
    late = r.poisson(0.6, n)
    score = np.clip(r.normal(735, 70, n) - late * 28, 300, 900).round()
    emp = np.clip(r.gamma(2, 3, n), 0, age - 20).round(1)
    dti = np.clip(r.beta(2, 5, n) * 0.9, 0.02, 0.85).round(3)
    existing = r.poisson(1.0, n)
    purpose = r.choice(PURPOSES, n)
    home = r.choice(HOMES, n, p=[.35, .25, .4])
    region = r.choice(REGIONS, n)
    lti = amount / income
    z = (-3.1 - 0.014 * (score - 735) + 2.6 * (dti - 0.25) + 0.35 * (lti - 1.5) + 0.32 * late + 0.18 * existing - 0.05 * emp
         + np.vectorize(PURPOSE_RISK.get)(purpose) + 0.25 * (home == "rent") + 0.004 * (term - 36) - 0.008 * (age - 35) + r.normal(0, 0.35, n))
    default = (r.random(n) < 1 / (1 + np.exp(-z))).astype(int)
    return pd.DataFrame({"age": age, "income_lpa": income, "loan_amount_l": amount, "term_months": term, "credit_score": score, "employment_years": emp,
                         "dti": dti, "existing_loans": existing, "late_payments_2y": late, "loan_to_income": lti.round(3), "purpose": purpose, "home": home,
                         "region": region, "default": default})


def _prep():
    return ColumnTransformer([("num", StandardScaler(), NUM), ("cat", OneHotEncoder(handle_unknown="ignore"), CAT)])


MODELS = {
    "Logistic Scorecard": lambda: make_pipeline(_prep(), LogisticRegression(max_iter=2000)),
    "Gradient Boosting": lambda: make_pipeline(_prep(), HistGradientBoostingClassifier(max_iter=300, learning_rate=0.05, random_state=0)),
    "Random Forest": lambda: make_pipeline(_prep(), RandomForestClassifier(n_estimators=300, min_samples_leaf=20, n_jobs=-1, random_state=0)),
}


def train(df):
    X, y = df[NUM + CAT], df["default"]
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.25, stratify=y, random_state=0)
    out = {}
    for name, mk in MODELS.items():
        m = mk().fit(Xtr, ytr)
        p = m.predict_proba(Xte)[:, 1]
        fpr, tpr, _ = roc_curve(yte, p)
        frac, mean_pred = calibration_curve(yte, p, n_bins=10, strategy="quantile")
        out[name] = {"model": m, "proba": p, "auc": roc_auc_score(yte, p), "gini": 2 * roc_auc_score(yte, p) - 1, "ks": float(np.max(tpr - fpr)), "roc": (fpr, tpr), "calib": (mean_pred, frac)}
    return {"results": out, "X_test": Xte, "y_test": yte.values, "best": max(out, key=lambda k: out[k]["auc"])}


def to_score(p):
    """Map default probability → 300–900 credit-style score (PDO = 50, 735 ≈ 6 % PD)."""
    odds = (1 - p) / np.clip(p, 1e-6, None)
    return np.clip(735 + 50 / np.log(2) * np.log(odds / (0.94 / 0.06)), 300, 900).round()


GRADES = [("A", 0.04, "#10b981"), ("B", 0.08, "#84cc16"), ("C", 0.15, "#f59e0b"), ("D", 0.25, "#f97316"), ("E", 1.01, "#ef4444")]


def grade(p):
    for g, cut, color in GRADES:
        if p < cut:
            return g, color
    return "E", "#ef4444"


def price(p, base=9.5):
    """Risk-based pricing: base rate + expected-loss premium (LGD 45 %) + risk margin."""
    return round(min(24.0, base + p * 30 + (2.0 if p > 0.15 else 0.5 if p > 0.08 else 0)), 2)


def emi(principal, annual_rate, months):
    r = annual_rate / 1200
    return principal * r * (1 + r) ** months / ((1 + r) ** months - 1) if r else principal / months


def amortization(principal, annual_rate, months, prepay=0.0, prepay_month=0):
    r, bal, e, rows = annual_rate / 1200, principal, emi(principal, annual_rate, months), []
    for m in range(1, months + 1):
        if bal <= 0:
            break
        interest = bal * r
        princ = min(e - interest, bal)
        bal -= princ
        if prepay and m == prepay_month:
            bal = max(0, bal - prepay)
        rows.append({"month": m, "emi": princ + interest, "principal": princ, "interest": interest, "balance": max(bal, 0)})
    return pd.DataFrame(rows)


def reason_codes(model_bundle, row):
    """Top adverse factors: features whose shift to a 'good' reference value lowers PD the most."""
    m = model_bundle["model"]
    base = m.predict_proba(row)[0, 1]
    ref = {"credit_score": 800, "dti": 0.15, "loan_to_income": 1.0, "late_payments_2y": 0, "existing_loans": 0, "employment_years": 8, "term_months": 36, "home": "own"}
    text = {"credit_score": "Credit score below preferred range", "dti": "High debt-to-income ratio", "loan_to_income": "Loan amount high relative to income",
            "late_payments_2y": "Recent late payments", "existing_loans": "Number of existing loans", "employment_years": "Short employment history",
            "term_months": "Long loan tenure", "home": "Rented residence"}
    out = []
    for f, v in ref.items():
        r = row.copy()
        if f == "loan_to_income":
            r["loan_amount_l"] = r["income_lpa"] * v
        r[f] = v
        d = base - m.predict_proba(r)[0, 1]
        if d > 0.005:
            out.append((text[f], d))
    return sorted(out, key=lambda x: -x[1])[:4]


def counterfactual(model_bundle, row, target=0.08):
    """Smallest loan amount reduction (and credit-score improvement) that achieves PD below target."""
    m = model_bundle["model"]
    sugg = {}
    for frac in np.linspace(1, 0.2, 33):
        r = row.copy(); r["loan_amount_l"] = row["loan_amount_l"] * frac; r["loan_to_income"] = r["loan_amount_l"] / r["income_lpa"]
        if m.predict_proba(r)[0, 1] < target:
            sugg["amount"] = float(r["loan_amount_l"].iloc[0]); break
    for s in range(int(row["credit_score"].iloc[0]), 901, 10):
        r = row.copy(); r["credit_score"] = s
        if m.predict_proba(r)[0, 1] < target:
            sugg["score"] = s; break
    return sugg


# ---------------- application history ----------------
def _con():
    c = sqlite3.connect(DB, check_same_thread=False)
    c.execute("CREATE TABLE IF NOT EXISTS applications (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, applicant TEXT, amount REAL, pd REAL, score REAL, grade TEXT, decision TEXT, rate REAL, data TEXT, ts REAL)")
    return c


def save_app(uid, applicant, amount, pd_, score, grade_, decision, rate, data: dict):
    with _con() as c:
        c.execute("INSERT INTO applications (user_id, applicant, amount, pd, score, grade, decision, rate, data, ts) VALUES (?,?,?,?,?,?,?,?,?,?)", (uid, applicant, amount, pd_, score, grade_, decision, rate, json.dumps(data), time.time()))


def list_apps(uid):
    with _con() as c:
        return pd.read_sql_query("SELECT id, applicant, amount, pd, score, grade, decision, rate, ts FROM applications WHERE user_id=? ORDER BY ts DESC", c, params=(uid,))
