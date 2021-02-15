import sqlite3
import os
import datetime
import time
from datetime import datetime, timedelta
from pathlib import Path

from flask import Flask, request, url_for, render_template, redirect, session

currentDirectory = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)

app.secret_key = "Hspt"

color = datetime.now().hour


@app.route('/')
def index():
    return render_template("index.html")

def sqliteQuery(query):
    dbConnection = sqlite3.connect(currentDirectory + "/peerCheckSystem.db")
    Cursor = dbConnection.cursor()
    Cursor.execute(query)
    dbConnection.commit()

def sqliteGet(query):
    dbConnection = sqlite3.connect(currentDirectory + "/peerCheckSystem.db")
    Cursor = dbConnection.cursor()
    result = Cursor.execute(query)
    result = result.fetchall()
    return result

def init():
    dbConnection = sqlite3.connect(currentDirectory + "/peerCheckSystem.db")
    initCursor = dbConnection.cursor()
    initCursor.execute(
        "CREATE TABLE IF NOT EXISTS users(username TEXT, password TEXT, points INT, status BOOL)")
    dbConnection.commit()
    return True

@app.route('/signup', methods = ["GET", "POST"])
def signup():
    if request.method == "GET":
        return render_template("signup.html")
    else:
        username = request.form["username"]
        password = request.form["password"]
        arguments = [username, password]
        query = "INSERT INTO users(username, password, points) VALUES ({user}, {password}, {points})".format(
            user=arguments[0], password=arguments[1], points=0)
        print(query)
        sqliteArgument(query=query)

@app.route('/init')
def init():
    dbConnection = sqlite3.connect(currentDirectory + "/peerCheckSystem.db")
    initCursor = dbConnection.cursor()
    initCursor.execute(
        "CREATE TABLE IF NOT EXISTS users(username TEXT, password TEXT, points INT, status BOOL)")
    dbConnection.commit()
    return "done"


@app.route('/signin', methods = ["GET", "POST"])
def signin():
    if request.method == "GET":
        return render_template("signin.html")
    else:
        username = request.form["username"]
        password = request.form["password"]
        query = "SELECT * FROM usere WHERE username = {username}".format(username=username)
        result = sqliteGet(query)
        if not result:
            return "Username doesn't exist"
        if result[0][1] == password:
            return "Logged In!"


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
