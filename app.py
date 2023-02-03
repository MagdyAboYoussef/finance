import os
#export API_KEY=pk_d27ac1f1efd749cbafad189963b39da4
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash
import json
from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    user_id = session["user_id"]
    shares = db.execute("SELECT share,sum(amount),sum(cost),name from transactions where user_id = ? GROUP BY share,name",user_id)
    cash = db.execute("SELECT cash from users where id =?",user_id)[0]['cash']
    try:
        total_cost = db.execute("SELECT sum(cost) from transactions where user_id= ?",user_id)[0]['sum(cost)']+cash
        return render_template("index.html" ,data = shares,cost = total_cost,cash=cash,func = lookup,float=float,length=len)
    except:
        return render_template("index.html",length=len)



@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":
        if not request.form.get("shares"):
            return apology("Invalid shares",400)

        try:
            int(request.form.get("shares"))
        except:
            return apology("Invalid shares",400)

        if int(request.form.get("shares")) <=0:
            return apology("Invalid shares",400)


        symbol = request.form.get("symbol")
        amount = float(request.form.get("shares"))
        if not request.form.get("shares") or int(amount)<=0:
            return apology("Invalid amount")
        if not lookup(symbol):
            return apology("Invalid symbol")
        price = float(lookup(symbol)['price'])
        name = lookup(symbol)['name']
        user_id = session["user_id"]
        cash = db.execute("SELECT cash from users where id = ?",user_id)[0]['cash']
        cost = price*amount
        print(cost)
        if cash >= price*amount:
            cash = cash-(price*amount)
            db.execute("UPDATE users set cash = ? where id =?",cash,user_id)
            db.execute("INSERT into transactions (amount,share,cost,user_id,name,action,current_price) values(?,?,?,?,?,?,?)",amount,symbol,price*amount,user_id,name,"buy",price)
            return redirect("/")
        else:
            return apology("Not enough money :(")


    else:
        return render_template("buy.html")
    return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    user_id = session["user_id"]

    data= db.execute("SELECT * from transactions where user_id = ?",user_id)
    #{'id': 8, 'date': '2023-01-22 12:34:25', 'amount': 5, 'share': 'NFLX', 'cost': 1712.5, 'user_id': 10, 'name': 'Netflix Inc.', 'action': 'buy'},
    return render_template("history.html",data = data)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method =="POST":
        if not request.form.get("symbol"):
            return apology("Symbol is empty")
        symbol= request.form.get("symbol")
        APIresponse = lookup(symbol)
        if not lookup(symbol):
            return apology("Invalid symbol")
        name = APIresponse.get("name")
        price = APIresponse.get("price")
        return render_template("quoted.html",name = name,price = price,symbol=symbol)

    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":
        # Ensure username was submitted
        print(db.execute("SELECT * from users where username = ?",request.form.get("username")))
        if not request.form.get("username") or not request.form.get("password") :
            return apology("fields are empty", 400)

        # Ensure password was submitted
        elif len(db.execute("SELECT * from users where username = ?",request.form.get("username")))>0 :
            return apology("Username exists", 400)
        elif not request.form.get("confirmation") or (request.form.get("password") != request.form.get("confirmation")):
            return apology("Password confirmation doesn't match", 400)
        else:
            db.execute("INSERT into users (username,hash) values(?,?)", request.form.get("username"),generate_password_hash(request.form.get("password")))
            return redirect("/", 200)
    return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method== "POST":
        if not request.form.get("shares"):
            return apology("Invalid shares",400)
        try:
            int(request.form.get("shares"))
        except:
            return apology("Invalid shares",400)

        if int(request.form.get("shares")) <=0:
            return apology("Invalid shares",400)

        symbol = request.form.get("symbol")
        amount = int(request.form.get("shares")) *-1
        user_id = session["user_id"]
        amount_owned= int(db.execute("SELECT sum(amount) from transactions where user_id =? and share = ?",user_id,symbol)[0]['sum(amount)'])
        print(type(amount_owned))
        print(amount)
        if amount_owned < (amount *-1):
            return apology("Not enough shares")
        else:
            cash = db.execute("SELECT cash from users where id = ?",user_id)[0]['cash']
            APIresponse = lookup(symbol)
            price = APIresponse.get("price")
            name = APIresponse.get("name")
            cash = cash+(price*(amount*-1))
            db.execute("UPDATE users set cash = ? where id =?",cash,user_id)
            db.execute("INSERT into transactions (amount,share,cost,user_id,name,action,current_price) values(?,?,?,?,?,?,?)",amount,symbol,(price*(amount*-1)),user_id,name,"sell",price)

            return redirect("/")
    else:
        user_id = session["user_id"]

        x = db.execute("SELECT share, SUM(amount) as total_amount from transactions where user_id =? and action = 'buy' GROUP BY share HAVING total_amount > 0", user_id)
        return render_template("sell.html",data = x)

@app.route("/cash", methods=["GET", "POST"])
@login_required
def add_cash():
    if request.method == "POST":
        amount = float(request.form.get("amount"))
        user_id = session["user_id"]

        initial = db.execute("SELECT cash from users where id =?",user_id)[0]['cash']
        total_cash= int(amount+ initial)

        db.execute("UPDATE users set cash = ? where id =?",total_cash,user_id)
        return redirect("/")

    else:
        return render_template("cash.html")
