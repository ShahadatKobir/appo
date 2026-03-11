import os
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default_secret')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///mess.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ============================
# MODELS
# ============================
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    username = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(255))
    role = db.Column(db.String(10))  # 'admin' or 'member'

class Deposit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    amount = db.Column(db.Float)
    date = db.Column(db.DateTime, default=datetime.utcnow)

class Meal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    date = db.Column(db.Date)
    morning = db.Column(db.Float, default=0.2)
    lunch = db.Column(db.Float, default=0.4)
    dinner = db.Column(db.Float, default=0.4)
    status = db.Column(db.String(10), default='on')  # on/off

class Market(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))  # Market buyer
    date = db.Column(db.Date)
    item_list = db.Column(db.String(255))
    total_cost = db.Column(db.Float)
    approved = db.Column(db.Boolean, default=False)

class Extra(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50))  # gas, bill, manager, other
    amount = db.Column(db.Float)
    date = db.Column(db.Date, default=datetime.utcnow)

# ============================
# Database Init (Deployment safe)
# ============================
def create_db():
    db.create_all()
    if not User.query.filter_by(username="Shahadat").first():
        admin = User(
            name="Shahadat",
            username="Shahadat",
            password=generate_password_hash("123456", method='sha256'),
            role="admin"
        )
        db.session.add(admin)
        db.session.commit()
        print("Main admin Shahadat created")


@app.before_request
def before_request_func():
    if not hasattr(app, 'db_initialized'):
        create_db()
        app.db_initialized = True

# ============================
# Helper functions
# ============================
def get_total_deposit(user_id=None):
    query = Deposit.query
    if user_id:
        query = query.filter_by(user_id=user_id)
    total = sum([d.amount for d in query.all()])
    return total

def get_total_meal(user_id=None):
    query = Meal.query
    if user_id:
        query = query.filter_by(user_id=user_id)
    total = sum([m.morning + m.lunch + m.dinner for m in query.all()])
    return total

def get_total_market_cost():
    markets = Market.query.filter_by(approved=True).all()
    return sum([m.total_cost for m in markets])

def get_average_meal_rate():
    total_cost = get_total_market_cost()
    total_meal = get_total_meal()
    if total_meal == 0:
        return 0
    return round(total_cost / total_meal, 2)

def get_extra_total(user_id=None):
    extras = Extra.query.all()
    total_extra = sum([e.amount for e in extras])
    return total_extra
    # ============================
# ROUTES
# ============================

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['role'] = user.role
            flash("Login successful", "success")
            if user.role == "admin":
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('member_dashboard'))
        else:
            flash("Invalid credentials", "error")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ============================
# Admin Dashboard
# ============================
@app.route('/admin')
def admin_dashboard():
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    total_deposit = get_total_deposit()
    total_meal = get_total_meal()
    average_rate = get_average_meal_rate()
    total_market = get_total_market_cost()
    total_extra = get_extra_total()
    balance = total_deposit - total_market - total_extra
    return render_template('admin_dashboard.html',
                           total_deposit=total_deposit,
                           total_meal=total_meal,
                           average_rate=average_rate,
                           total_market=total_market,
                           total_extra=total_extra,
                           balance=balance)

# ============================
# Member Dashboard
# ============================
@app.route('/member')
def member_dashboard():
    if 'role' not in session or session['role'] != 'member':
        return redirect(url_for('login'))
    user_id = session['user_id']
    total_deposit = get_total_deposit(user_id)
    total_meal = get_total_meal(user_id)
    average_rate = get_average_meal_rate()
    total_market = get_total_market_cost()
    total_extra = get_extra_total()
    balance = total_deposit - (total_market + total_extra)
    return render_template('member_dashboard.html',
                           total_deposit=total_deposit,
                           total_meal=total_meal,
                           average_rate=average_rate,
                           total_market=total_market,
                           total_extra=total_extra,
                           balance=balance)

# ============================
# Deposit Route
# ============================
@app.route('/deposit', methods=['POST'])
def add_deposit():
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    user_id = int(request.form['user_id'])
    amount = float(request.form['amount'])
    deposit = Deposit(user_id=user_id, amount=amount)
    db.session.add(deposit)
    db.session.commit()
    flash("Deposit added successfully", "success")
    return redirect(url_for('admin_dashboard'))

# ============================
# Meal Route
# ============================
@app.route('/meal', methods=['POST'])
def add_meal():
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    user_id = int(request.form['user_id'])
    date_str = request.form['date']
    morning = float(request.form.get('morning', 0.2))
    lunch = float(request.form.get('lunch', 0.4))
    dinner = float(request.form.get('dinner', 0.4))
    date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
    meal = Meal(user_id=user_id, date=date_obj, morning=morning, lunch=lunch, dinner=dinner)
    db.session.add(meal)
    db.session.commit()
    flash("Meal updated successfully", "success")
    return redirect(url_for('admin_dashboard'))

# ============================
# Market Route
# ============================
@app.route('/market', methods=['POST'])
def add_market():
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    user_id = int(request.form['user_id'])
    date_str = request.form['date']
    item_list = request.form['item_list']
    total_cost = float(request.form['total_cost'])
    date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
    market = Market(user_id=user_id, date=date_obj, item_list=item_list, total_cost=total_cost)
    db.session.add(market)
    db.session.commit()
    flash("Market entry added", "success")
    return redirect(url_for('admin_dashboard'))

@app.route('/market/approve/<int:id>')
def approve_market(id):
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    market = Market.query.get(id)
    market.approved = True
    db.session.commit()
    flash("Market approved", "success")
    return redirect(url_for('admin_dashboard'))

# ============================
# Extra Cost Route
# ============================
@app.route('/extra', methods=['POST'])
def add_extra():
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    category = request.form['category']
    amount = float(request.form['amount'])
    extra = Extra(category=category, amount=amount)
    db.session.add(extra)
    db.session.commit()
    flash("Extra cost added", "success")
    return redirect(url_for('admin_dashboard'))

# ============================
# Auto Meal Generation (if needed)
# ============================
@app.route('/auto_meal', methods=['GET','POST'])
def auto_meal():
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    today = datetime.today().date()
    users = User.query.all()
    for user in users:
        existing = Meal.query.filter_by(user_id=user.id, date=today).first()
        if not existing:
            meal = Meal(user_id=user.id, date=today)
            db.session.add(meal)
    db.session.commit()
    flash("Auto meal sheet generated", "success")
    return redirect(url_for('admin_dashboard'))

# ============================
# Run App
# ============================
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
