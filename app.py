import os
# other imports...
from flask import Flask, render_template, request, redirect, url_for, session
# ...
app = Flask(__name__)
# use env var secret key in production; fallback for local dev
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret")

from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "supersecretkey"

# In-memory storage
users = {}        # username -> password_hash
expenses = {}     # username -> list of expenses

@app.route("/", methods=["GET"])
def index():
    if "username" not in session:
        return render_template("index.html", logged_in=False)
    
    username = session["username"]
    # Ensure expenses dict has a list for this user
    if username not in expenses:
        expenses[username] = []

    user_expenses = expenses[username]
    balances = calculate_balances(user_expenses)
    settlements = calculate_settlements(balances)

    return render_template("index.html", logged_in=True,
                           username=username,
                           expenses=user_expenses,
                           balances=balances,
                           settlements=settlements)


@app.route("/register", methods=["POST"])
def register():
    username = request.form["username"].strip()
    password = request.form["password"].strip()

    if username in users:
        return "<script>alert('Username already exists!');window.location.href='/'</script>"

    users[username] = generate_password_hash(password)
    expenses[username] = []  # initialize expenses
    session["username"] = username
    return redirect(url_for("index"))


@app.route("/login", methods=["POST"])
def login():
    username = request.form["username"].strip()
    password = request.form["password"].strip()

    if username not in users or not check_password_hash(users[username], password):
        return "<script>alert('Invalid username or password!');window.location.href='/'</script>"

    # Initialize expenses if missing
    if username not in expenses:
        expenses[username] = []

    session["username"] = username
    return redirect(url_for("index"))


@app.route("/logout")
def logout():
    session.pop("username", None)
    return redirect(url_for("index"))


@app.route("/add", methods=["POST"])
def add_expense():
    if "username" not in session:
        return redirect(url_for("index"))

    username = session["username"]
    if username not in expenses:
        expenses[username] = []

    paid_by = request.form["paid_by"].strip()
    amount = request.form["amount"]
    members_raw = request.form["members"].split(",")

    # Clean members list
    members = [m.strip() for m in members_raw if m.strip()]
    if not members:
        return "<script>alert('Invalid members list! No empty names allowed.');window.location.href='/'</script>"

    try:
        amount = float(amount)
        if amount <= 0:
            raise ValueError
    except ValueError:
        return "<script>alert('Enter a valid positive amount');window.location.href='/'</script>"

    expense_id = len(expenses[username]) + 1
    expense = {
        "id": expense_id,
        "paid_by": paid_by,
        "amount": amount,
        "members": members
    }
    expenses[username].append(expense)
    return redirect(url_for("index"))


@app.route("/delete/<int:expense_id>")
def delete_expense(expense_id):
    if "username" not in session:
        return redirect(url_for("index"))
    username = session["username"]
    if username not in expenses:
        expenses[username] = []

    expenses[username] = [e for e in expenses[username] if e["id"] != expense_id]
    return redirect(url_for("index"))


@app.route("/edit/<int:expense_id>", methods=["GET", "POST"])
def edit_expense(expense_id):
    if "username" not in session:
        return redirect(url_for("index"))
    username = session["username"]
    if username not in expenses:
        expenses[username] = []

    user_expenses = expenses[username]
    expense = next((e for e in user_expenses if e["id"] == expense_id), None)
    if not expense:
        return redirect(url_for("index"))

    if request.method == "POST":
        paid_by = request.form["paid_by"].strip()
        amount = request.form["amount"]
        members_raw = request.form["members"].split(",")
        members = [m.strip() for m in members_raw if m.strip()]
        if not members:
            return "<script>alert('Invalid members list!');window.location.href='/'</script>"
        try:
            amount = float(amount)
            if amount <= 0:
                raise ValueError
        except ValueError:
            return "<script>alert('Enter a valid positive amount');window.location.href='/'</script>"

        expense["paid_by"] = paid_by
        expense["amount"] = amount
        expense["members"] = members
        return redirect(url_for("index"))

    return render_template("edit.html", expense=expense)


def calculate_balances(user_expenses):
    balances = {}
    for expense in user_expenses:
        payer = expense["paid_by"]
        amount = expense["amount"]
        members = expense["members"]
        share = amount / len(members)

        balances[payer] = balances.get(payer, 0) + amount
        for member in members:
            balances[member] = balances.get(member, 0) - share
    return balances


def calculate_settlements(balances):
    pos = {k: v for k, v in balances.items() if v > 0}
    neg = {k: v for k, v in balances.items() if v < 0}
    settlements = []

    pos_list = sorted(pos.items(), key=lambda x: x[1], reverse=True)
    neg_list = sorted(neg.items(), key=lambda x: x[1])

    i = 0
    j = 0
    while i < len(pos_list) and j < len(neg_list):
        creditor, credit = pos_list[i]
        debtor, debt = neg_list[j]
        pay_amount = min(credit, -debt)

        settlements.append(f"{debtor} owes {creditor} ₹{pay_amount:.2f}")

        pos_list[i] = (creditor, credit - pay_amount)
        neg_list[j] = (debtor, debt + pay_amount)

        if pos_list[i][1] == 0:
            i += 1
        if neg_list[j][1] == 0:
            j += 1
    return settlements


if __name__ == "__main__":
    # debug only if explicitly set
    debug_mode = os.environ.get("DEBUG", "False").lower() in ("1", "true", "yes")
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=debug_mode)

