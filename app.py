import os
import sqlite3
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


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "GET":
        if "user" in session:
            return render_template("index.html", message=session["user"])
        else:
            return render_template("index.html", message="Sign in or sign up")
    else:
        if request.form["button"] == "logout":
            session.clear()
            return render_template("index.html", message="Logged out")


@app.route("/init")
def init():
    sqliteQuery("CREATE TABLE IF NOT EXISTS users(username TEXT, password TEXT, points INT, status BOOL)")
    return "Done"


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "GET":
        return render_template("signup.html")
    else:
        result = sqliteGet("SELECT * FROM users WHERE username = ?", (request.form["username"],))
        if not result:
            sqliteQuery("INSERT INTO users (username, password, points) VALUES (?, ?, 0)", (request.form["username"], request.form["password"]))
            return redirect(url_for("signin"))
        else:
            return render_template("signup.html", message="Username is already taken")


@app.route("/signin", methods=["GET", "POST"])
def signin():
    if request.method == "GET":
        return render_template("signin.html")
    else:
        result = sqliteGet("SELECT * FROM users WHERE username = ?", (request.form["username"],))
        if not result:
            return render_template("signin.html", message="Username doesn't exist")
        elif result[0][1] != request.form["password"]:
            return render_template("signin.html", message="Incorrect password")
        else:
            session["user"] = result[0][0]
            return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
