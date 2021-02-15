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
def init():
    return render_template("index.html")



if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
