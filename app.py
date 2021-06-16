import os
import crypt
import sqlite3
from functools import wraps
from ast import literal_eval
from hmac import compare_digest
from flask import Flask, request, url_for, render_template, redirect, session, json

DB = "./database.db"


def sqlite_execute(*query):
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    cursor.execute(*query)
    conn.commit()


def sqlite_get(*query):
    cursor = sqlite3.connect(DB).cursor()
    return cursor.execute(*query).fetchall()


def signin_required(signed_in):
    def dec(f):
        @wraps(f)
        def wrapper():
            if signed_in is not ("user" in session):
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


def get_groups():
    groups = sqlite_get("SELECT name, members FROM groups WHERE members LIKE ?", ("%'" + session["user"] + "'%",))
    return [(group[0], literal_eval(group[1])) for group in groups]


app = Flask(__name__)
app.secret_key = b"\xa3\x08\x94\xa2ED\x10\xa4@:6\xb6=i\xe8\xec"

if not os.path.exists(DB):
    os.mknod(DB)

sqlite_execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, password TEXT, points INT, private BOOL); CREATE TABLE IF NOT EXISTS groups (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, password TEXT, members TEXT, pending TEXT)")


@app.route("/", methods=["GET", "POST"])
@search_logout
def index():
    if "user" in session:
        return render_template("index.html", message=session["user"])
    return render_template("index.html", message="Sign in or sign up")


@app.route("/signup", methods=["GET", "POST"])
@signin_required(False)
def signup():
    if request.method == "GET":
        return render_template("signup.html")
    result = sqlite_get("SELECT username FROM users WHERE username = ?", (request.json["username"],))
    if not result:
        crypt_pwd = crypt.crypt(request.json["password"], crypt.METHOD_SHA512)
        sqlite_execute("INSERT INTO users (username, password, points, private) VALUES (?, ?, 0, 0)", (request.json["username"], crypt_pwd))
        return json.dumps({"status": 0})
    return json.dumps({"status": 1})


@app.route("/signin", methods=["GET", "POST"])
@signin_required(False)
def signin():
    if request.method == "GET":
        return render_template("signin.html")
    result = sqlite_get("SELECT username, password FROM users WHERE username = ?", (request.json["username"],))
    if not result:
        return json.dumps({"status": 1})
    crypt_pwd = result[0][1]
    pwd = request.json["password"]
    if not compare_digest(crypt.crypt(pwd, crypt_pwd), crypt_pwd):
        return json.dumps({"status": 2})
    session["user"] = result[0][0]
    return json.dumps({"status": 0})


@app.route("/settings", methods=["GET", "POST"])
@signin_required(True)
@search_logout
def settings():
    # GET
    if request.method == "GET":
        private = sqlite_get("SELECT private FROM users WHERE username = ?", (session["user"],))[0][0]
        return render_template("settings.html", private=private)

    # Update private status
    if request.method == "POST" and request.form.get("button") == "update":
        private = bool(request.form.get("private"))
        sqlite_execute("UPDATE users SET private = ? WHERE username = ?", (private, session["user"]))
        return render_template("settings.html", private=private, message="Update successful")

    # Delete account
    if request.method == "POST" and request.form.get("button") == "delete":
        sqlite_execute("DELETE FROM users WHERE username = ?", (session["user"],))
        session.clear()
        return redirect(url_for("index"))

    # Update password
    crypt_pwd = sqlite_get("SELECT password FROM users WHERE username = ?", (session["user"],))[0][0]
    if not compare_digest(crypt.crypt(request.json["old"], crypt_pwd), crypt_pwd):
        return json.dumps({"status": 1})
    sqlite_execute("UPDATE users SET password = ? WHERE username = ?", (crypt.crypt(request.json["new"], crypt.METHOD_SHA512), session["user"]))
    return json.dumps({"status": 0})


@app.route("/search", methods=["GET", "POST"])
@signin_required(True)
@search_logout
def search():
    # GET
    if request.method == "GET":
        query = request.args.get("query")
        result = sqlite_get("SELECT username, private FROM users WHERE username LIKE ?", ("%" + query + "%",))
        names = [user[0] for user in result if not user[1] and user[0] != session["user"]]
        return render_template("search.html", names=names, query=query)
    for user, group in request.json.items():
        result = literal_eval(sqlite_get("SELECT pending FROM groups WHERE name = ?", (group,))[0][0])
        if (any(i[1] == user for i in result)):
            pending = [[i[0] + [session["user"]], i[1]] if session["user"] not in i[0] and i[1] == user else i for i in result]
        else:
            pending = result + [[[session["user"]], user]]
        sqlite_execute("UPDATE groups SET pending = ? WHERE name = ?", (repr(pending), group))
    return json.dumps({"status": 0})


@app.route("/groups", methods=["GET", "POST"])
@signin_required(True)
@search_logout
def groups():
    # GET
    if request.method == "GET":
        pendings = sqlite_get("SELECT name, pending FROM groups WHERE pending LIKE ?", ("%'" + session["user"] + "'%",))
        invitations = []
        for n, p in pendings:
            try:
                invitors = [i for i in literal_eval(p) if i[1] == session["user"]][0][0]
            except IndexError:
                continue
            invitations.append((invitors, n))
        return render_template("groups.html", groups=get_groups(), invitations=invitations)

    # Create or join group
    if request.method == "POST" and request.is_json:
        result = sqlite_get("SELECT password, members FROM groups WHERE name = ?", (request.json["name"],))
        if not result:
            if "confirm" not in request.json:
                return json.dumps({"status": 1})  # Confirm create
            # Create group
            sqlite_execute("INSERT INTO groups (name, password, members) VALUES (?, ?, ?)", (request.json["name"], crypt.crypt(request.json["password"], crypt.METHOD_SHA512), repr([session["user"]])))
            return json.dumps({"status": 0})
        # Join group
        members = literal_eval(result[0][1])
        if session["user"] in members:
            return json.dumps({"status": 2})  # Already a member
        if not compare_digest(crypt.crypt(request.json["password"], result[0][0]), result[0][0]):
            return json.dumps({"status": 3})  # Incorrect password
        members.append(session["user"])
        sqlite_execute("UPDATE groups SET members = ? WHERE name = ?", (repr(members), request.json["name"]))
        return json.dumps({"status": 0, "groups": get_groups()})

    # Leave group
    if request.method == "POST" and "leave" in request.form:
        members = literal_eval(sqlite_get("SELECT members FROM groups WHERE name = ?", (request.form["leave"],))[0][0])
        members.remove(session["user"])
        sqlite_execute("UPDATE groups SET members = ? WHERE name = ?", (repr(members), request.form["leave"]))
        return redirect(url_for("groups"))
        # What if the group has no members left?

    # Accept or reject invitations
    form = request.form.get("accept") or request.form.get("reject")
    result = literal_eval(sqlite_get("SELECT pending FROM groups WHERE name = ?", (form,))[0][0])
    pending = [i for i in result if i[1] != session["user"]]
    sqlite_execute("UPDATE groups SET pending = ? WHERE name = ?", (repr(pending), form))
    if "accept" in request.form:
        members = literal_eval(sqlite_get("SELECT members FROM groups WHERE name = ?", (form,))[0][0])
        members.append(session["user"])
        sqlite_execute("UPDATE groups SET members = ? WHERE name = ?", (repr(members), form))
    return redirect(url_for("groups"))


app.run(debug=True, host="0.0.0.0")
