import os
import sqlite3
from functools import wraps
from flask import Flask, request, url_for, render_template, redirect, session

currentDirectory = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)
app.secret_key = "Hspt"


def sqliteQuery(*query):
    dbConnection = sqlite3.connect(currentDirectory + "/peerCheckSystem.db")
    cursor = dbConnection.cursor()
    cursor.execute(*query)
    dbConnection.commit()


def sqliteGet(*query):
    cursor = sqlite3.connect(currentDirectory + "/peerCheckSystem.db").cursor()
    result = cursor.execute(*query).fetchall()
    return result


def search_route(f):
    @wraps(f)
    def wrapper():
        if request.method == "POST" and request.form["button"] == "search":
            return redirect(url_for("search", query=request.form["search"]))
        return f()
    return wrapper


def logout(f):
    @wraps(f)
    def wrapper():
        if request.method == "POST" and request.form["button"] == "logout":
            session.clear()
            return redirect(url_for("index"))
        return f()
    return wrapper


@app.route("/", methods=["GET", "POST"])
@search_route
@logout
def index():
    if "user" in session:
        return render_template("index.html", message=session["user"])
    else:
        return render_template("index.html", message="Sign in or sign up")


@app.route("/init")
def init():
    sqliteQuery("CREATE TABLE IF NOT EXISTS users (username TEXT, password TEXT, points INT, private BOOL)")
    return "Done"


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "GET":
        return render_template("signup.html", background=True)
    else:
        result = sqliteGet("SELECT * FROM users WHERE username = ?", (request.form["username"],))
        if not result:
            sqliteQuery("INSERT INTO users (username, password, points, private) VALUES (?, ?, 0, 0)", (request.form["username"], request.form["password"]))
            return redirect(url_for("signin"))
        else:
            return render_template("signup.html", message="Username is already taken", background=True)


@app.route("/signin", methods=["GET", "POST"])
def signin():
    if request.method == "GET":
        return render_template("signin.html", background=True)
    else:
        result = sqliteGet("SELECT * FROM users WHERE username = ?", (request.form["username"],))
        if not result:
            return render_template("signin.html", message="Username doesn't exist", background=True)
        elif result[0][1] != request.form["password"]:
            return render_template("signin.html", message="Incorrect password", background=True)
        else:
            session["user"] = result[0][0]
            return redirect(url_for("index"))


@app.route("/settings", methods=["GET", "POST"])
def settings():
    if request.method == "GET":
        privateStatus = sqliteGet("SELECT private FROM users WHERE username = ?", (session["user"],))
        return render_template("settings.html", privateStatus=privateStatus[0][0])
    else:
        privateStatus = bool(request.form.get("private"))
        sqliteQuery("UPDATE users SET private = ? WHERE username = ?", (privateStatus, session["user"]))
        return render_template("settings.html", privateStatus=privateStatus, message="Update successful")


@app.route("/search", methods=["GET", "POST"])
@search_route
@logout
def search():
    testnames = ["Nathaniel", "Zeke", "Daniil", "Petr", "Cristian", "Filip", "Federico", "J.J.", "Mate", "Franko"]
    return render_template("search.html", names=testnames, query=request.args.get("query"))


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
