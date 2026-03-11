from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

# -------------------------------
# 1️⃣ User Table
# -------------------------------
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    username = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(200))
    role = db.Column(db.String(20))  # member, admin, super_admin

# -------------------------------
# 2️⃣ Deposit Table
# -------------------------------
class Deposit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    amount = db.Column(db.Float)

# -------------------------------
# 3️⃣ Meal Table
# -------------------------------
class Meal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    date = db.Column(db.Date)
    breakfast = db.Column(db.Float, default=0.2)
    lunch = db.Column(db.Float, default=0.4)
    dinner = db.Column(db.Float, default=0.4)
    total = db.Column(db.Float, default=1.0)

# -------------------------------
# 4️⃣ Market Table
# -------------------------------
class Market(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date)
    buyer_id = db.Column(db.Integer)
    market_list = db.Column(db.String(300))
    cost = db.Column(db.Float)
    approved = db.Column(db.Boolean, default=False)

# -------------------------------
# 5️⃣ Extra Cost Table
# -------------------------------
class ExtraCost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50))  # gas, bill, manager, other
    amount = db.Column(db.Float)

# -------------------------------
# 6️⃣ Notification Table
# -------------------------------
class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    message = db.Column(db.String(300))
    seen = db.Column(db.Boolean, default=False)
    date = db.Column(db.DateTime)