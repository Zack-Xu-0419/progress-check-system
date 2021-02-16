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


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/init")
def init():
    sqliteQuery("CREATE TABLE IF NOT EXISTS users(username TEXT, password TEXT, points INT, status BOOL)")
    return "done"


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "GET":
        return render_template("signup.html")
    else:
        sqliteQuery("INSERT INTO users (username, password, points) VALUES (?, ?, 0)", (request.form["username"], request.form["password"]))
        return "done"
#   TODO Detects if username is already taken.


@app.route("/signin", methods=["GET", "POST"])
def signin():
    if request.method == "GET":
        return render_template("signin.html")
    else:
        result = sqliteGet("SELECT * FROM users WHERE username = ?", (request.form["username"],))
        if not result:
            return "Username doesn't exist"
        elif result[0][1] != request.form["password"]:
            return "Incorrect password"
        else:
            return "Logged In!"


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
