from flask import Flask, render_template, request, redirect, url_for, session
import pandas as pd
import matplotlib.pyplot as plt
import os
from datetime import datetime

plt.style.use("seaborn-v0_8")

app = Flask(__name__)

app.secret_key = "my_secret_key_123"   # 🔐 Needed for login session (you can change this)

STUDENT_FILE = "students.csv"
PAYMENT_FILE = "payments.csv"

# Simple hardcoded credentials (for demo / project)
USERNAME = "admin"
PASSWORD = "admin123"

# ------------------- Create files if not exists -------------------
def init_files():
    if not os.path.exists(STUDENT_FILE):
        pd.DataFrame(columns=["ID","Name","Dept","Year","Total_Fee","Paid_Fee"]).to_csv(STUDENT_FILE, index=False)

    if not os.path.exists(PAYMENT_FILE):
        pd.DataFrame(columns=["ID","Date","Amount"]).to_csv(PAYMENT_FILE, index=False)

init_files()


# ------------------- LOGIN PAGE (START) -------------------
@app.route("/", methods=["GET", "POST"])
def login():
    # If already logged in, go to dashboard
    if "user" in session:
        return redirect(url_for("home"))

    error = None
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if username == USERNAME and password == PASSWORD:
            session["user"] = username  # save login in session
            return redirect(url_for("home"))
        else:
            error = "Invalid username or password"

    return render_template("login.html", error=error)


# ------------------- LOGOUT -------------------
@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))


# ------------------- Home Page (Dashboard) -------------------
@app.route("/dashboard")
def home():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("index.html")


# ------------------- Add Student -------------------
@app.route("/add_student", methods=["GET","POST"])
def add_student():
    if "user" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        ID = int(request.form["id"])
        name = request.form["name"]
        dept = request.form["dept"]
        year = int(request.form["year"])
        total_fee = float(request.form["total_fee"])

        df = pd.read_csv(STUDENT_FILE)

        if ID in df["ID"].values:
            return "⚠ Student Already Exists!"

        new_row = pd.DataFrame([[ID, name, dept, year, total_fee, 0]])
        new_row.columns = df.columns

        df = pd.concat([df, new_row], ignore_index=True)
        df.to_csv(STUDENT_FILE, index=False)

        return redirect("/students")

    return render_template("add_student.html")


# ------------------- Insert Payment -------------------
@app.route("/add_payment", methods=["GET","POST"])
def add_payment():
    if "user" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        sid = int(request.form["id"])
        amount = float(request.form["amount"])

        students = pd.read_csv(STUDENT_FILE)
        if sid not in students["ID"].values:
            return "❌ Student not found!"

        # update paid fee
        idx = students[students["ID"] == sid].index[0]
        students.at[idx, "Paid_Fee"] += amount
        students.to_csv(STUDENT_FILE, index=False)

        payments = pd.read_csv(PAYMENT_FILE)
        new_payment = pd.DataFrame([[sid, datetime.now().strftime("%Y-%m-%d"), amount]])
        new_payment.columns = payments.columns

        payments = pd.concat([payments, new_payment], ignore_index=True)
        payments.to_csv(PAYMENT_FILE, index=False)

        return redirect("/students")

    return render_template("add_payment.html")


# ------------------- Show All Students -------------------
@app.route("/students")
def show_students():
    if "user" not in session:
        return redirect(url_for("login"))

    df = pd.read_csv(STUDENT_FILE)

    # Add Balance Fee column
    df["Balance"] = df["Total_Fee"] - df["Paid_Fee"]

    return render_template("students.html", data=df.to_dict(orient="records"))



# ------------------- Charts -------------------
@app.route("/charts")
def charts():
    if "user" not in session:
        return redirect(url_for("login"))

    df = pd.read_csv(STUDENT_FILE)

    # ---------- Paid vs Pending (Donut Chart) ----------
    paid = df["Paid_Fee"].sum()
    pending = (df["Total_Fee"] - df["Paid_Fee"]).sum()

    fig, ax = plt.subplots(figsize=(5, 5))
    values = [paid, pending]
    labels = ["Paid", "Pending"]
    colors = ["#4CAF50", "#FF7043"]  # green & orange

    wedges, texts, autotexts = ax.pie(
        values,
        labels=labels,
        autopct="%1.1f%%",
        startangle=90,
        colors=colors,
        wedgeprops={"width": 0.4, "edgecolor": "white"},  # donut
        pctdistance=0.8
    )
    ax.set_title("Paid vs Pending Fee (Total)")
    ax.set_aspect("equal")
    plt.tight_layout()
    plt.savefig("static/pie.png")
    plt.close(fig)

    # ---------- Department-wise Paid vs Balance (Grouped Bar) ----------
    if not df.empty:
        dept_totals = df.groupby("Dept")[["Total_Fee", "Paid_Fee"]].sum()
        dept_totals["Balance"] = dept_totals["Total_Fee"] - dept_totals["Paid_Fee"]

        fig, ax = plt.subplots(figsize=(7, 4))
        x = range(len(dept_totals))
        width = 0.35

        ax.bar(
            [i - width/2 for i in x],
            dept_totals["Paid_Fee"],
            width,
            label="Paid",
            color="#42A5F5"
        )
        ax.bar(
            [i + width/2 for i in x],
            dept_totals["Balance"],
            width,
            label="Balance",
            color="#EF5350"
        )

        ax.set_xticks(list(x))
        ax.set_xticklabels(dept_totals.index)
        ax.set_ylabel("Amount")
        ax.set_title("Department-wise Fee Status")
        ax.legend()
        plt.tight_layout()
        plt.savefig("static/dept_bar.png")
        plt.close(fig)

    # ---------- Monthly Fee Collection Trend (Line Chart) ----------
    pay = pd.read_csv(PAYMENT_FILE)
    if not pay.empty:
        pay["Date"] = pd.to_datetime(pay["Date"])
        monthly = pay.groupby(pay["Date"].dt.to_period("M"))["Amount"].sum()

        fig, ax = plt.subplots(figsize=(7, 4))
        ax.plot(
            monthly.index.astype(str),
            monthly.values,
            marker="o",
            linestyle="-",
            linewidth=2,
        )
        ax.set_title("Monthly Fee Collection Trend")
        ax.set_xlabel("Month")
        ax.set_ylabel("Amount Collected")
        plt.xticks(rotation=45)
        ax.grid(alpha=0.3)
        plt.tight_layout()
        plt.savefig("static/line.png")
        plt.close(fig)

    return render_template("charts.html")



if __name__ == "__main__":
    app.run(debug=True)
