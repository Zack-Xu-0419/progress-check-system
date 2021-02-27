import os
import ast
import sqlite3
from functools import wraps
from flask import Flask, request, url_for, render_template, redirect, session, json

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
        if request.method == "POST" and not request.is_json and "button" in request.form:
            if request.form["button"] == "search":
                return redirect(url_for("search", query=request.form["search"]))
            if request.form["button"] == "logout":
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
    sqliteQuery("CREATE TABLE IF NOT EXISTS users (username TEXT, password TEXT, points INT, private BOOL); CREATE TABLE IF NOT EXISTS groups (name TEXT, password TEXT, members TEXT)")
    return "Done"


@app.route("/signup", methods=["GET", "POST"])
@signin_required(False)
def signup():
    if request.method == "GET":
        return render_template("signup.html", background=True)
    result = sqliteGet("SELECT username FROM users WHERE username = ?", (request.form["username"],))
    if not result:
        sqliteQuery("INSERT INTO users (username, password, points, private) VALUES (?, ?, 0, 0)", (request.form["username"], request.form["password"]))
        return redirect(url_for("signin"))
    return render_template("signup.html", message="Username is already taken", background=True)


@app.route("/signin", methods=["GET", "POST"])
@signin_required(False)
def signin():
    if request.method == "GET":
        return render_template("signin.html", background=True)
    result = sqliteGet("SELECT username, password FROM users WHERE username = ?", (request.form["username"],))
    if not result:
        return render_template("signin.html", message="Username doesn't exist", background=True)
    if result[0][1] != request.form["password"]:
        return render_template("signin.html", message="Incorrect password", background=True)
    session["user"] = result[0][0]
    groups = sqliteGet("SELECT name, members FROM groups WHERE members LIKE ?", ("%'" + session["user"] + "'%",))
    session["groups"] = [(group[0], ast.literal_eval(group[1])) for group in groups]
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


@app.route("/group", methods=["GET", "POST"])
@signin_required(True)
@search_logout
def group():
    if request.method == "GET":
        return render_template("group.html")
    if request.method == "POST" and request.is_json:
        result = sqliteGet("SELECT * FROM groups WHERE name = ?", (request.json["name"],))
        if not result:
            return json.dumps({"status": 1})
        members = ast.literal_eval(result[0][2])
        if session["user"] in members:
            return json.dumps({"status": 2})
        if result[0][1] != request.json["password"]:
            return json.dumps({"status": 3})
        members.append(session["user"])
        sqliteQuery("UPDATE groups SET members = ? WHERE name = ?", (repr(members), result[0][0]))
        session["groups"].append((result[0][0], members))
        session.modified = True
        return json.dumps({"status": 0})
    result = sqliteGet("SELECT members FROM groups WHERE name = ?", (request.form["leave"],))[0][0]
    members = ast.literal_eval(result)
    members.remove(session["user"])
    sqliteQuery("UPDATE groups SET members = ? WHERE name = ?", (repr(members), request.form["leave"]))
    session["groups"] = [i for i in session["groups"] if i[0] != request.form["leave"]]
    session.modified = True
    return render_template("group.html")


@app.route("/group/create", methods=["POST"])
def group_create():
    sqliteQuery("INSERT INTO groups (name, password, members) VALUES (?, ?, ?)", (request.json["name"], request.json["password"], repr([session["user"]])))
    session["groups"].append((request.json["name"], [session["user"]]))
    session.modified = True
    return json.dumps({"status": 0})


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
