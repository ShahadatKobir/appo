from flask import Flask, render_template, request, redirect, flash, send_file
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
import pandas as pd

from models import db, User, Deposit, Meal, Market, ExtraCost, Notification

app = Flask(__name__)

app.config["SECRET_KEY"] = "mess_secret_key"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.before_first_request
def create_super_admin():

    admin = User.query.filter_by(username="shahadat").first()

    if not admin:

        new_admin = User(
            name="Shahadat",
            username="shahadat",
            password=generate_password_hash("1234"),
            role="super_admin"
        )

        db.session.add(new_admin)
        db.session.commit()


@app.route("/", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):

            login_user(user)

            if user.role == "member":
                return redirect("/member")
            else:
                return redirect("/admin")

        else:
            flash("Invalid login")

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():

    logout_user()
    return redirect("/")


@app.route("/admin")
@login_required
def admin_dashboard():

    if current_user.role == "member":
        return redirect("/member")

    users = User.query.all()
    deposits = Deposit.query.all()
    markets = Market.query.filter_by(approved=True).all()

    avg_rate = calculate_avg_meal_rate()

    return render_template(
        "admin_dashboard.html",
        users=users,
        deposits=deposits,
        markets=markets,
        avg_rate=avg_rate
    )


@app.route("/member")
@login_required
def member_dashboard():

    data = member_summary(current_user.id)

    notifications = Notification.query.filter_by(
        user_id=current_user.id
    ).all()

    return render_template(
        "member_dashboard.html",
        data=data,
        notifications=notifications
    )


@app.route("/add_member", methods=["GET", "POST"])
@login_required
def add_member():

    if current_user.role not in ["admin", "super_admin"]:
        return redirect("/")

    if request.method == "POST":

        name = request.form["name"]
        username = request.form["username"]
        password = generate_password_hash(request.form["password"])

        new_user = User(
            name=name,
            username=username,
            password=password,
            role="member"
        )

        db.session.add(new_user)
        db.session.commit()

        flash("Member added successfully")

        return redirect("/admin")

    return render_template("add_member.html")


@app.route("/add_deposit", methods=["GET", "POST"])
@login_required
def add_deposit():

    if current_user.role not in ["admin", "super_admin"]:
        return redirect("/")

    users = User.query.all()

    if request.method == "POST":

        user_id = request.form["user_id"]
        amount = float(request.form["amount"])

        d = Deposit(
            user_id=user_id,
            amount=amount
        )

        db.session.add(d)
        db.session.commit()

        send_notification(user_id, f"আপনার নামে {amount} টাকা ডিপোজিট যোগ হয়েছে")

        flash("Deposit added")

        return redirect("/admin")

    return render_template("add_deposit.html", users=users)


@app.route("/auto_meal", methods=["GET", "POST"])
@login_required
def auto_meal():

    if current_user.role not in ["admin", "super_admin"]:
        return redirect("/")

    users = User.query.filter_by(role="member").all()

    if request.method == "POST":

        today = date.today()

        for u in users:

            breakfast = 0.2 if request.form.get(f"b_{u.id}") else 0
            lunch = 0.4 if request.form.get(f"l_{u.id}") else 0
            dinner = 0.4 if request.form.get(f"d_{u.id}") else 0

            total = breakfast + lunch + dinner

            meal = Meal(
                user_id=u.id,
                date=today,
                breakfast=breakfast,
                lunch=lunch,
                dinner=dinner,
                total=total
            )

            db.session.add(meal)

        db.session.commit()

        flash("Meals saved successfully")

        return redirect("/admin")

    return render_template("auto_meal.html", users=users)
    # -------------------------------
# 1️⃣ Notification Function
# -------------------------------

def send_notification(user_id, message):

    n = Notification(
        user_id=user_id,
        message=message,
        date=datetime.utcnow()
    )

    db.session.add(n)
    db.session.commit()


# -------------------------------
# 2️⃣ Market Entry (Member)
# -------------------------------

@app.route("/market_entry", methods=["GET","POST"])
@login_required
def market_entry():

    if request.method == "POST":

        m = Market(
            date=date.today(),
            buyer_id=current_user.id,
            market_list=request.form["list"],
            cost=float(request.form["cost"]),
            approved=False
        )

        db.session.add(m)
        db.session.commit()

        flash("Market request sent")
        send_notification(current_user.id,"আপনার বাজার এন্ট্রি পাঠানো হয়েছে।")
        return redirect("/member")

    return render_template("market_entry.html")


# -------------------------------
# 3️⃣ Market Approve / Reject (Admin)
# -------------------------------

@app.route("/market_approve/<id>")
@login_required
def market_approve(id):

    if current_user.role not in ["admin","super_admin"]:
        return redirect("/")

    m = Market.query.get(id)
    m.approved = True
    db.session.commit()

    send_notification(m.buyer_id,"আপনার বাজার এন্ট্রি এপ্রুভ হয়েছে")
    return redirect("/admin")


@app.route("/market_reject/<id>")
@login_required
def market_reject(id):

    if current_user.role not in ["admin","super_admin"]:
        return redirect("/")

    m = Market.query.get(id)
    db.session.delete(m)
    db.session.commit()

    send_notification(m.buyer_id,"আপনার বাজার এন্ট্রি রিজেক্ট হয়েছে")
    return redirect("/admin")


# -------------------------------
# 4️⃣ Extra Cost System (Admin)
# -------------------------------

@app.route("/add_extra", methods=["GET","POST"])
@login_required
def add_extra():

    if current_user.role not in ["admin","super_admin"]:
        return redirect("/")

    if request.method == "POST":

        e = ExtraCost(
            category=request.form["category"],
            amount=float(request.form["amount"])
        )

        db.session.add(e)
        db.session.commit()

        flash("Extra cost added")
        return redirect("/admin")

    return render_template("add_extra.html")


# -------------------------------
# 5️⃣ Meal Rate Calculation
# -------------------------------

def calculate_avg_meal_rate():

    markets = Market.query.filter_by(approved=True).all()
    meals = Meal.query.all()

    total_market = sum(m.cost for m in markets)
    total_meal = sum(m.total for m in meals)

    if total_meal == 0:
        return 0

    return round(total_market / total_meal,2)


# -------------------------------
# 6️⃣ Member Summary Engine
# -------------------------------

def member_summary(user_id):

    deposits = Deposit.query.filter_by(user_id=user_id).all()
    meals = Meal.query.filter_by(user_id=user_id).all()
    markets = Market.query.filter_by(approved=True).all()
    extras = ExtraCost.query.all()

    total_deposit = sum(d.amount for d in deposits)
    total_meal = sum(m.total for m in meals)
    total_market = sum(m.cost for m in markets)

    total_all_meal = sum(m.total for m in Meal.query.all())
    avg_rate = 0
    if total_all_meal > 0:
        avg_rate = total_market / total_all_meal

    meal_cost = total_meal * avg_rate
    extra_total = sum(e.amount for e in extras)
    member_count = User.query.filter_by(role="member").count()

    extra_per_member = 0
    if member_count > 0:
        extra_per_member = extra_total / member_count

    total_cost = meal_cost + extra_per_member
    balance = total_deposit - total_cost

    return {
        "deposit":round(total_deposit,2),
        "meal":round(total_meal,2),
        "avg_rate":round(avg_rate,2),
        "meal_cost":round(meal_cost,2),
        "extra":round(extra_per_member,2),
        "total_cost":round(total_cost,2),
        "balance":round(balance,2)
    }


# -------------------------------
# 7️⃣ Excel Export
# -------------------------------

@app.route("/export_excel")
@login_required
def export_excel():

    if current_user.role not in ["admin","super_admin"]:
        return redirect("/")

    users = User.query.filter_by(role="member").all()
    data = []

    for u in users:

        s = member_summary(u.id)
        data.append({
            "Name": u.name,
            "Deposit": s["deposit"],
            "Meal": s["meal"],
            "Meal Cost": s["meal_cost"],
            "Extra Cost": s["extra"],
            "Total Cost": s["total_cost"],
            "Balance": s["balance"]
        })

    df = pd.DataFrame(data)
    file = "mess_summary.xlsx"
    df.to_excel(file,index=False)

    return send_file(file, as_attachment=True)


# -------------------------------
# 8️⃣ Run App
# -------------------------------

if __name__ == "__main__":

    app.run(debug=True)