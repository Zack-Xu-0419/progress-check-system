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
    sqliteQuery("CREATE TABLE IF NOT EXISTS users (username TEXT, password TEXT, points INT, private BOOL); CREATE TABLE IF NOT EXISTS groups (name TEXT, password TEXT, members TEXT, pending TEXT)")
    return "Done"


@app.route("/signup", methods=["GET", "POST"])
@signin_required(False)
def signup():
    if request.method == "GET":
        return render_template("signup.html", background=True)
    result = sqliteGet("SELECT username FROM users WHERE username = ?", (request.json["username"],))
    if not result:
        sqliteQuery("INSERT INTO users (username, password, points, private) VALUES (?, ?, 0, 0)", (request.json["username"], request.json["password"]))
        return json.dumps({"status": 0})
    return json.dumps({"status": 1})


@app.route("/signin", methods=["GET", "POST"])
@signin_required(False)
def signin():
    if request.method == "GET":
        return render_template("signin.html", background=True)
    result = sqliteGet("SELECT username, password FROM users WHERE username = ?", (request.json["username"],))
    if not result:
        return json.dumps({"status": 1})
    if result[0][1] != request.json["password"]:
        return json.dumps({"status": 2})
    session["user"] = result[0][0]
    groups = sqliteGet("SELECT name, members FROM groups WHERE members LIKE ?", ("%'" + session["user"] + "'%",))
    session["groups"] = [(group[0], ast.literal_eval(group[1])) for group in groups]
    return json.dumps({"status": 0})


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
    sqliteQuery("DELETE FROM users WHERE username = ?", (session["user"],))
    session.clear()
    return redirect(url_for("index"))


@app.route("/search", methods=["GET", "POST"])
@signin_required(True)
@search_logout
def search():
    if request.method == "GET":
        query = request.args.get("query")
        result = sqliteGet("SELECT username, private FROM users WHERE username LIKE ?", ("%" + query + "%",))
        names = [user[0] for user in result if not user[1] and user[0] != session["user"]]
        return render_template("search.html", names=names, query=query)
    for user, group in request.json.items():
        result = ast.literal_eval(sqliteGet("SELECT pending FROM groups WHERE name = ?", (group,))[0][0])
        if (any(i[1] == user for i in result)):
            pending = [[i[0] + [session["user"]], i[1]] if session["user"] not in i[0] and i[1] == user else i for i in result]
        else:
            pending = result + [[[session["user"]], user]]
        sqliteQuery("UPDATE groups SET pending = ? WHERE name = ?", (repr(pending), group))
    return json.dumps({"status": 0})


@app.route("/group", methods=["GET", "POST"])
@signin_required(True)
@search_logout
def group():
    if request.method == "GET":
        result = sqliteGet("SELECT name, pending FROM groups WHERE pending LIKE ?", ("%'" + session["user"] + "'%",))
        invitations = [[[i for i in ast.literal_eval(p) if i[1] == session["user"]][0][0], n] for n, p in result]
        return render_template("group.html", invitations=invitations)
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
    if request.method == "POST" and "leave" in request.form:
        members = ast.literal_eval(sqliteGet("SELECT members FROM groups WHERE name = ?", (request.form["leave"],))[0][0])
        members.remove(session["user"])
        sqliteQuery("UPDATE groups SET members = ? WHERE name = ?", (repr(members), request.form["leave"]))
        session["groups"] = [i for i in session["groups"] if i[0] != request.form["leave"]]
        session.modified = True
        return render_template("group.html")
        # What if the group has no members left?
    form = request.form.get("accept") or request.form.get("reject")
    result = ast.literal_eval(sqliteGet("SELECT pending FROM groups WHERE name = ?", (form,))[0][0])
    pending = [i for i in result if i[1] != session["user"]]
    sqliteQuery("UPDATE groups SET pending = ? WHERE name = ?", (repr(pending), form))
    if "accept" in request.form:
        members = ast.literal_eval(sqliteGet("SELECT members FROM groups WHERE name = ?", (request.form["accept"],))[0][0])
        members.append(session["user"])
        sqliteQuery("UPDATE groups SET members = ? WHERE name = ?", (repr(members), request.form["accept"]))
        session["groups"].append((request.form["accept"], members))
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
