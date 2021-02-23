import os
import sqlite3
from functools import wraps
from flask import Flask, request, url_for, render_template, redirect, session

currentDirectory = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)
app.secret_key = b"\xa3\x08\x94\xa2ED\x10\xa4@:6\xb6=i\xe8\xec"


def sqliteQuery(*query):
    dbConnection = sqlite3.connect(currentDirectory + "/peerCheckSystem.db")
    cursor = dbConnection.cursor()
    cursor.execute(*query)
    dbConnection.commit()


def sqliteGet(*query):
    cursor = sqlite3.connect(currentDirectory + "/peerCheckSystem.db").cursor()
    result = cursor.execute(*query).fetchall()
    return result


def signin_required(signed_in):
    def dec(f):
        @wraps(f)
        def wrapper():
            if int(signed_in) + int("user" in session) == 1:
                return redirect(url_for("index"))
            return f()
        return wrapper
    return dec


def search_logout(f):
    @wraps(f)
    def wrapper():
        if request.method == "POST" and request.form["button"] == "search":
            return redirect(url_for("search", query=request.form["search"]))
        if request.method == "POST" and request.form["button"] == "logout":
            session.clear()
            return redirect(url_for("index"))
        return f()
    return wrapper


@app.route("/", methods=["GET", "POST"])
@search_logout
def index():
    if "user" in session:
        return render_template("index.html", message=session["user"])
    return render_template("index.html", message="Sign in or sign up")


@app.route("/init")
def init():
    sqliteQuery("CREATE TABLE IF NOT EXISTS users (username TEXT, password TEXT, points INT, private BOOL)")
    return "Done"


@app.route("/signup", methods=["GET", "POST"])
@signin_required(False)
def signup():
    if request.method == "GET":
        return render_template("signup.html", background=True)
    result = sqliteGet("SELECT * FROM users WHERE username = ?", (request.form["username"],))
    if not result:
        sqliteQuery("INSERT INTO users (username, password, points, private) VALUES (?, ?, 0, 0)", (request.form["username"], request.form["password"]))
        return redirect(url_for("signin"))
    else:
        return render_template("signup.html", message="Username is already taken", background=True)


@app.route("/signin", methods=["GET", "POST"])
@signin_required(False)
def signin():
    if request.method == "GET":
        return render_template("signin.html", background=True)
    result = sqliteGet("SELECT * FROM users WHERE username = ?", (request.form["username"],))
    if not result:
        return render_template("signin.html", message="Username doesn't exist", background=True)
    elif result[0][1] != request.form["password"]:
        return render_template("signin.html", message="Incorrect password", background=True)
    else:
        session["user"] = result[0][0]
        return redirect(url_for("index"))


@app.route("/settings", methods=["GET", "POST"])
@signin_required(True)
@search_logout
def settings():
    if request.method == "GET":
        privateStatus = sqliteGet("SELECT private FROM users WHERE username = ?", (session["user"],))
        return render_template("settings.html", privateStatus=privateStatus[0][0])
    if request.method == "POST" and request.form["button"] == "update":
        privateStatus = bool(request.form.get("private"))
        sqliteQuery("UPDATE users SET private = ? WHERE username = ?", (privateStatus, session["user"]))
        return render_template("settings.html", privateStatus=privateStatus, message="Update successful")


@app.route("/search", methods=["GET", "POST"])
@signin_required(True)
@search_logout
def search():
    query = request.args.get("query")
    result = sqliteGet("SELECT username, private FROM users WHERE username LIKE ?", ("%" + query + "%",))
    names = [user[0] for user in result if not user[1] and user[0] != session["user"]]
    if request.method == "GET":
        return render_template("search.html", names=names, query=query)
    return render_template("search.html", names=names, query=query, message="Successfully added {} as friend".format(request.form["button"]))


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
