import os
import sqlite3
from ast import literal_eval
from base64 import b64encode
from datetime import date
from functools import wraps
from io import BytesIO

from flask import (Flask, json, redirect, render_template, request, session,
                   url_for)
from PIL import Image
from werkzeug.security import check_password_hash, generate_password_hash

DB = "./database.db"
IMAGES_DIR = "./static/images"
DEFAULT_BACKGROUND = "/static/background.png"
SUCCESS = json.dumps({"success": True})


class Method:
    GET = ["GET"]
    POST = ["POST"]
    BOTH = ["GET", "POST"]


def sqlite_execute(*query):
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    cursor.execute(*query)
    conn.commit()


def sqlite_get(*query):
    cursor = sqlite3.connect(DB).cursor()
    return cursor.execute(*query).fetchall()


def require_signin(signin_required):
    def dec(f):
        @wraps(f)
        def wrapper():
            if signin_required is not ("user" in session):
                return redirect(url_for("index")), 403
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


def api(method):
    def dec(f):
        @wraps(f)
        def wrapper():
            if (not request.is_json) or (request.method not in method):
                return error("Bad request."), 400
            if "user" not in session:
                return error("You must be signed in to perform this operation."), 403
            return f()
        return wrapper
    return dec


def get_groups():
    groups = sqlite_get(
        "SELECT name, members FROM groups WHERE members LIKE ?", ("%'" + session["user"] + "'%",))
    return [(group[0], [i if i != session["user"] else i + " (yourself)" for i in literal_eval(group[1])]) for group in groups]


def get_points():
    if "user" not in session:
        return 0
    return sqlite_get(
        "SELECT points FROM users WHERE username = ?", (session["user"],))[0][0]


def error(message):
    return json.dumps({"success": False, "message": message})


def init():
    with open(DB, "a"):
        pass
    # FIXME: Restrict access to this path.
    os.makedirs(IMAGES_DIR, exist_ok=True)
    sqlite_execute(
        "CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, password TEXT, points INT, private BOOL)")
    sqlite_execute(
        "CREATE TABLE IF NOT EXISTS groups (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, password TEXT, members TEXT, pending TEXT)")
    # Should we use usernames to refer to a user, or id's?
    sqlite_execute(
        "CREATE TABLE IF NOT EXISTS images (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, owner TEXT, active BOOL)")
    sqlite_execute(
        "CREATE TABLE IF NOT EXISTS tasks(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, owner TEXT, groups TEXT, deadline TEXT, category TEXT, points INT, completed BOOL)")


app = Flask(__name__)
app.secret_key = b"\xa3\x08\x94\xa2ED\x10\xa4@:6\xb6=i\xe8\xec"


@app.route("/", methods=Method.BOTH)
@search_logout
def index():
    if "user" in session:
        return render_template("index.html", message=f"{session['user']} (you have {get_points()} points)")
    return render_template("index.html", message="sign in or sign up")


@app.route("/signup", methods=Method.BOTH)
@require_signin(False)
def signup():
    if request.method == "GET":
        return render_template("signup.html")
    result = sqlite_get(
        "SELECT username FROM users WHERE username = ?", (request.json["username"],))
    if not result:
        sqlite_execute("INSERT INTO users (username, password, points, private) VALUES (?, ?, 0, 0)",
                       (request.json["username"], generate_password_hash(request.json["password"])))
        return json.dumps({"status": 0})
    return json.dumps({"success": False})


@app.route("/signin", methods=Method.BOTH)
@require_signin(False)
def signin():
    if request.method == "GET":
        return render_template("signin.html")
    result = sqlite_get(
        "SELECT username, password FROM users WHERE username = ?", (request.json["username"],))
    if not result:
        return error("Username does not exist.")
    if not check_password_hash(result[0][1], request.json["password"]):
        return error("Incorrect password.")
    session["user"] = result[0][0]
    return SUCCESS


@app.route("/settings", methods=Method.BOTH)
@require_signin(True)
@search_logout
def settings():
    # GET
    if request.method == "GET":
        private = sqlite_get(
            "SELECT private FROM users WHERE username = ?", (session["user"],))[0][0]
        return render_template("settings.html", private=private)

    # Update private status
    if request.form.get("button") == "update":
        private = bool(request.form.get("private"))
        sqlite_execute(
            "UPDATE users SET private = ? WHERE username = ?", (private, session["user"]))
        return render_template("settings.html", private=private, message="Update successful")

    # Delete account
    if request.form.get("button") == "delete":
        sqlite_execute("DELETE FROM users WHERE username = ?",
                       (session["user"],))
        session.clear()
        return redirect(url_for("index"))

    # Upload background image
    if request.files and "image" in request.files:
        image_bytes = request.files["image"].read()
        pil_image = Image.open(BytesIO(image_bytes))
        WIDTH = 1280
        original_size = pil_image.size
        new_size = (WIDTH, WIDTH * original_size[1] // original_size[0])
        pil_image = pil_image.resize(new_size, Image.ANTIALIAS)
        image_bytes = BytesIO()
        pil_image.save(image_bytes, format="jpeg")
        image_bytes = image_bytes.getvalue()
        data_url = f"data:image/jpeg;base64,{b64encode(image_bytes).decode()}"
        table_name = f"{session['user']}-background"
        sqlite_execute(
            f"CREATE TABLE IF NOT EXISTS '{table_name}' (id INTEGER PRIMARY KEY AUTOINCREMENT, image TEXT, title TEXT)")
        sqlite_execute(
            f"INSERT INTO '{table_name}' (image, title) VALUES (?, ?)", (data_url, request.form["title"]))

        # Get the amount of Background image, if is equal to 10, delete number 10.
        AmountOfBackground = sqlite_get(
            f"SELECT COUNT(*) FROM '{table_name}'")[0][0]
        if(AmountOfBackground > 10):
            backgroundToDelete = sqlite_get(
                f"SELECT id FROM '{table_name}' ORDER BY id ASC LIMIT 1"
            )[0][0]
            print(
                backgroundToDelete
            )
            sqlite_execute(
                f"DELETE FROM '{table_name}' WHERE id = {backgroundToDelete}")
            sqlite_execute(f"ALTER TABLE '{table_name}' DROP id")
            sqlite_execute(
                f"ALTER TABLE '{table_name}' AUTO_INCREMENT = 1")
            sqlite_execute(
                f"ALTER TABLE '{table_name}' ADD id int UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY FIRST")

        return json.dumps({"status": 0})

    # Update password
    hashed_password = sqlite_get(
        "SELECT password FROM users WHERE username = ?", (session["user"],))[0][0]
    if not check_password_hash(hashed_password, request.json["old"]):
        return json.dumps({"success": False})
    sqlite_execute("UPDATE users SET password = ? WHERE username = ?",
                   (generate_password_hash(request.json["new"]), session["user"]))
    return json.dumps({"status": 0})


@app.route("/tasks", methods=Method.BOTH)
@require_signin(True)
@search_logout
def tasks():
    return render_template("tasks.html")


@app.route("/search", methods=Method.BOTH)
@require_signin(True)
@search_logout
def search():
    # GET
    if request.method == "GET":
        query = request.args.get("query")
        result = sqlite_get(
            "SELECT username, private FROM users WHERE username LIKE ?", ("%" + query + "%",))
        names = [user[0] for user in result if not user[1]]
        return render_template("search.html", names=names, query=query)
    for user, group in request.json.items():
        result = literal_eval(sqlite_get(
            "SELECT pending FROM groups WHERE name = ?", (group,))[0][0])
        if (any(i[1] == user for i in result)):
            pending = [[i[0] + [session["user"]], i[1]] if session["user"]
                       not in i[0] and i[1] == user else i for i in result]
        else:
            pending = result + [[[session["user"]], user]]
        sqlite_execute(
            "UPDATE groups SET pending = ? WHERE name = ?", (repr(pending), group))
    return json.dumps({"status": 0})


@app.route("/groups", methods=Method.BOTH)
@require_signin(True)
@search_logout
def groups():
    # GET
    if request.method == "GET":
        pendings = sqlite_get(
            "SELECT name, pending FROM groups WHERE pending LIKE ?", ("%'" + session["user"] + "'%",))
        invitations = []
        for n, p in pendings:
            try:
                invitors = [i for i in literal_eval(
                    p) if i[1] == session["user"]][0][0]
            except IndexError:
                continue
            invitations.append((invitors, n))
        return render_template("groups.html", groups=get_groups(), invitations=invitations)

        # Leave group
    if request.method == "POST" and "leave" in request.form:
        members = literal_eval(sqlite_get(
            "SELECT members FROM groups WHERE name = ?", (request.form["leave"],))[0][0])
        members.remove(session["user"])
        sqlite_execute("UPDATE groups SET members = ? WHERE name = ?",
                       (repr(members), request.form["leave"]))
        return redirect(url_for("groups"))
        # What if the group has no members left?

    # Accept or reject invitations
    form = request.form.get("accept") or request.form.get("reject")
    result = literal_eval(sqlite_get(
        "SELECT pending FROM groups WHERE name = ?", (form,))[0][0])
    pending = [i for i in result if i[1] != session["user"]]
    sqlite_execute("UPDATE groups SET pending = ? WHERE name = ?",
                   (repr(pending), form))
    if "accept" in request.form:
        members = literal_eval(sqlite_get(
            "SELECT members FROM groups WHERE name = ?", (form,))[0][0])
        members.append(session["user"])
        sqlite_execute(
            "UPDATE groups SET members = ? WHERE name = ?", (repr(members), form))
    return redirect(url_for("groups"))


@app.route("/api/group/join", methods=Method.POST)
@api(Method.POST)
def group_join():
    result = sqlite_get(
        "SELECT password, members FROM groups WHERE name = ?", (request.json["name"],))
    if not result:
        return error(f"\"{request.json['name']}\" does not exist. To create a new group, click \"Create Group\".")
    members = literal_eval(result[0][1])
    if session["user"] in members:
        return error(f"You are already a member of \"{request.json['name']}\".")
    if not check_password_hash(result[0][0], request.json["password"]):
        return error("Incorrect password.")
    members.append(session["user"])
    sqlite_execute("UPDATE groups SET members = ? WHERE name = ?",
                   (repr(members), request.json["name"]))
    return SUCCESS


@app.route("/api/group/create", methods=Method.POST)
@api(Method.POST)
def group_create():
    try:
        result = sqlite_get(
            "SELECT name FROM groups WHERE name = ?", (request.json["name"],))
        if result:
            return error(f"\"{request.json['name']}\" already exists. To join an existing group, click \"Join Group\".")
        sqlite_execute("INSERT INTO groups (name, password, members) VALUES (?, ?, ?)", (
            request.json["name"], generate_password_hash(request.json["password"]), repr([session["user"]])))
        return SUCCESS
    except sqlite3.OperationalError:
        return error("Database operation failed. Please try again.")


@app.route("/api/background/upload", methods=Method.POST)
def background_upload():
    if "user" not in session:
        return error("You must be signed in to perform this operation."), 403
    if (not request.method == "POST") or (not request.files) or ("image" not in request.files) or (not request.form) or ("title" not in request.form):
        return error("Bad request."), 400
    sqlite_execute("UPDATE images SET active = false")
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO images (title, owner, active) VALUES (?, ?, ?)",
                   (request.form["title"], session["user"], True))
    new_id = cursor.execute("SELECT last_insert_rowid()").fetchall()[0][0]
    conn.commit()
    request.files["image"].save(os.path.join(IMAGES_DIR, str(new_id)))
    return SUCCESS


@app.route("/api/task/new", methods=Method.POST)
@api(Method.POST)
def new_task():
    name = request.json['name']
    groups = request.json['groups']
    deadline = request.json['deadline']
    category = request.json['category']
    result = sqlite_get(
        "SELECT name FROM tasks WHERE name = ? AND owner = ?", (name, session["user"]))
    if result:
        return error(f"You already have a task called \"{name}\".")
    try:
        points = int(request.json['points'])
        if points < 0:
            raise ValueError
    except ValueError:
        return error("\"Points\" must be a nonnegative integer.")
    try:
        date.fromisoformat(deadline)
    except ValueError as err:
        return error("Deadline has invalid format: {}.".format(str(err)))
    sqlite_execute("INSERT INTO tasks (name, owner, groups, deadline, category, points, completed) VALUES (?, ?, ?, ?, ?, ?, true)",
                   (name, session["user"], groups, deadline, category, points))
    return SUCCESS


@app.route("/api/task/complete", methods=Method.POST)
@api(Method.POST)
def complete_task():
    name = request.json["name"]
    checked = request.json["checked"]
    result = sqlite_get(
        "SELECT points FROM tasks WHERE name = ? AND owner = ?", (name, session["user"]))
    if not result:
        return error(f"Task \"{name}\" not found.")
    points = result[0][0]
    assert len(result) == 1
    assert points >= 0
    sqlite_execute("UPDATE tasks SET completed = ? WHERE name = ? AND owner = ?",
                   (checked, name, session["user"]))
    sqlite_execute("UPDATE users SET points = points + ?", (points if checked else -points,))
    return SUCCESS


@app.context_processor
def processor():
    def get_all_backgrounds():
        assert "user" in session
        return [(f"/static/images/{id}", title, active) for (id, title, active) in sqlite_get("SELECT id, title, active FROM images WHERE owner = ?", (session["user"],))]

    def get_active_background():
        if "user" not in session:
            return DEFAULT_BACKGROUND
        try:
            return f"/static/images/{sqlite_get('SELECT id FROM images WHERE owner = ? AND active = true', (session['user'],))[0][0]}"
        except IndexError:
            return DEFAULT_BACKGROUND

    def get_groups():
        if "user" not in session:
            return []
        try:
            return [item[0] for item in sqlite_get(
                "SELECT name FROM groups WHERE members LIKE ?", ("%'" + session["user"] + "'%",))]
        except sqlite3.OperationalError:
            return []

    def get_tasks():
        def get_delta_days(deadline):
            delta_date = date.fromisoformat(deadline) - date.today()
            return delta_date.days
        assert "user" in session
        tasks = sqlite_get(
            "SELECT name, groups, deadline, completed, points FROM tasks WHERE owner = ?", (session["user"],))
        result = [{"name": task[0], "groups": task[1],
                   "deadline": task[2], "delta_days": get_delta_days(task[2]), "completed": task[3], "points": task[4]} for task in tasks]
        return result

    return {"get_all_backgrounds": get_all_backgrounds, "get_active_background": get_active_background, "get_groups": get_groups, "get_tasks": get_tasks}


if __name__ == "__main__":
    init()
    app.run(debug=True, host="0.0.0.0")
