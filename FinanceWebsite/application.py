import os
import feedparser
import webbrowser
import datetime
import database

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash



from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached

database.create_tables()




@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""


    username = db.execute("SELECT username FROM users WHERE id = :uid", uid=int(session['user_id']))[0]["username"]

    stocks = db.execute("SELECT symbol, shares FROM portfolio WHERE username = :username", username=username)

    total_sum = []


    for stock in stocks:
        symbol = str(stock["symbol"])
        shares = int(stock["shares"])
        name = lookup(symbol)["name"]
        price = lookup(symbol)["price"]
        total = shares * price
        stock["name"] = name
        stock["price"] = usd(price)
        stock["total"] = usd(total)
        total_sum.append(float(total))

    cash_available = db.execute("SELECT cash FROM users WHERE username = :username", username=username)[0]["cash"]
    cash_total = sum(total_sum) + cash_available

    return render_template("index.html", stocks=stocks, cash_available=usd(cash_available), cash_total=usd(cash_total))


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():

    if request.method == "POST":
        look = lookup(request.form.get("symbol"))
        shares = request.form.get("shares")
        if look == None:
            return apology("invalid symbol", 400)
        elif not shares.isdigit() or int(shares) < 1:
            return apology("share must be at least 1", 400)


        cash = db.execute("SELECT cash FROM users WHERE id = :uid", uid=int(session['user_id']))

        value = look["price"] * int(shares)


        if int(cash[0]["cash"]) < value:
            return apology("You don't have enough money to buy stock", 403)

        else:
            db.execute("UPDATE users SET cash = cash - :value WHERE id = :uid", value=value, uid=int(session['user_id']))

            db.execute("INSERT INTO history (username, operation, symbol, price, shares) VALUES (:username, 'BUY', :symbol, :price, :shares)",
            username=db.execute("SELECT username FROM users WHERE id = :uid", uid=int(session['user_id']))[0]["username"],
            symbol=look['symbol'], price=look['price'], shares=request.form.get('shares'))


            db.execute("INSERT INTO portfolio (username, symbol, shares) VALUES (:username, :symbol, :shares)",
            username=db.execute("SELECT username FROM users WHERE id = :uid", uid=int(session['user_id']))[0]["username"],
            symbol=look['symbol'], shares=request.form.get('shares'))


            return redirect("/")


    else:
        return render_template("buy.html")


@app.route("/check", methods=["GET"])
def check():

    username = request.args.get('username')

    other_username = db.execute("SELECT username FROM users WHERE username = :username", username=username)

    try:
        result = other_username[0]['username']
        if not result:
            return jsonify(True)
        else:
            return jsonify(False)
    except IndexError:
        return jsonify(True)


@app.route("/history")
@login_required
def history():
    username = db.execute("SELECT username FROM users WHERE id = :uid", uid=int(session['user_id']))[0]["username"]
    stocks = db.execute("SELECT operation, symbol, price, date, time, shares FROM history WHERE username = :username", username=username)

    for stock in stocks:
        symbol = str(stock["symbol"])
        name = lookup(symbol)["name"]
        stock["name"] = name

    return render_template("history.html", stocks=stocks)


@app.route("/login", methods=["GET", "POST"])
def login():

    session.clear()

    if request.method == "POST":
        if not request.form.get("username"):
            return apology("must provide username", 403)
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        session["user_id"] = rows[0]["id"]

        return redirect("/")
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():


    if request.method == "POST":

        look = lookup(request.form.get("symbol"))

        if look == None:
            return apology("invalid symbol", 400)

        else:
            return render_template("quoted.html", name=look["name"], symbol=look["symbol"], price=usd(look["price"]))

    else:
        return render_template("quote.html")


@app.route("/news", methods=["GET", "POST"])
@login_required
def news():

    return render_template('news.html')



@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        if not request.form.get("username"):
            return apology("You must provide username", 400)
        elif not request.form.get("password"):
            return apology("You must provide password", 400)
        elif request.form.get("password") != request.form.get("confirmation"):
            return apology("Your passwords don't match", 400)
        result = db.execute("INSERT INTO users (username, hash) VALUES (:username, :hash)",
                            username=request.form.get("username"), hash=generate_password_hash(request.form.get("password")))

        if not result:
            return apology("username unavailable", 400)


        rows = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))

        session["user_id"] = rows[0]["id"]

        return redirect("/")
    else:
        return render_template("register.html")


@app.route('/profile/', methods = ['GET', 'POST'])
@login_required
def profile():
    pass

@app.route('/charts/', methods = ['GET', 'POST'])
@login_required
def charts():

    return render_template('charts.html')

@app.route('/calendar/', methods = ['GET', 'POST'])
@login_required
def calendar():

    return render_template('calendar.html')


@app.route('/blog', methods = ['GET', 'POST'])
@login_required
def blog():

    if request.method == 'POST':
        entry_content = request.form.get('content')
        database.create_entry(entry_content, datetime.datetime.today().strftime("%b %d"))

    return render_template("blog.html", entries=database.retrieve_entries())


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    username = db.execute("SELECT username FROM users WHERE id = :uid", uid=int(session['user_id']))[0]["username"]

    if request.method == "POST":
        look = lookup(request.form.get("symbol"))

        shares = request.form.get("shares")

        user_shares = db.execute("SELECT shares FROM portfolio WHERE username = :username and symbol = :symbol",
                        username=username, symbol=str(request.form.get("symbol")))[0]["shares"]

        value = look["price"] * int(shares)

        if not request.form.get("symbol") or look == None:
            return apology("you must provide a stock", 400)
        elif not shares or not shares.isdigit() or int(shares) < 1 or int(shares) > int(user_shares):
            return apology("share number is invalid", 400)

        else:
            db.execute("UPDATE users SET cash = cash + :value WHERE id = :uid", value=value, uid=int(session['user_id']))

            db.execute("INSERT INTO history (username, operation, symbol, price, shares) VALUES (:username, 'SELL', :symbol, :price, :shares)",
            username=username, symbol=look['symbol'], price=look['price'], shares=request.form.get('shares'))

            if int(user_shares) == int(shares):
                db.execute("DELETE FROM portfolio WHERE username = :username and symbol = :symbol",
                            username=username, symbol=str(request.form.get("symbol")))

            elif int(user_shares) > int(shares):
                db.execute("UPDATE portfolio SET shares = :shares WHERE username = :username and symbol = :symbol",
                            shares=shares, username=username, symbol=request.form.get("symbol"))

        return redirect("/")

    else:
        symbols = db.execute("SELECT symbol FROM portfolio WHERE username = :username", username=username)

        return render_template("sell.html", symbols=symbols)


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
